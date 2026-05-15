import asyncio
import json
import ollama
from pydantic import BaseModel
from fastmcp.client import Client


class VlogDecisions(BaseModel):
    trim_each_clip: bool
    trim_seconds: float
    add_fade_in: bool
    add_fade_out: bool
    transition: str = "cut"
    output_resolution: str = "1080p"
    audio_normalize: bool = False


class VlogPlan(BaseModel):
    decisions: VlogDecisions
    ffmpeg_command: str = ""
    metadata: list[dict]


async def run_vlog_decisions(filenames: list[str]) -> VlogPlan:
    async with Client("http://localhost:8050/sse") as client:
        mcp_tools = await client.list_tools()

        ollama_tools = []
        for tool in mcp_tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            })

        print(f">>> available tools: {[t.name for t in mcp_tools]}")

        history = [
            {
                "role": "system",
                "content": (
                    "You are a professional video editor with ffmpeg expertise. "
                    "Follow these steps in order: "
                    "1. Call get_editing_guidelines to understand constraints. "
                    "2. Call get_all_metadata to analyze all clips in one call. "
                    "3. Call get_ffmpeg_capabilities to understand available filters. "
                    "4. Build an ffmpeg command and call validate_ffmpeg_command to check it. "
                    "5. If valid, return ONLY a raw JSON object with this exact structure: "
                    '{"ffmpeg_command": "your ffmpeg command here"} '
                    "No explanation, no markdown, no backticks, nothing else. "
                    "The ffmpeg command must: "
                    "use -f concat -safe 0 -i uploads/concat.txt as input, "
                    "output to outputs/OUTPUT_FILENAME, "
                    "use -c:v libx264 -c:a aac -movflags +faststart."
                    "The ffmpeg command must start with 'ffmpeg -y' and "
                    "replace OUTPUT_FILENAME with the actual output filename."
               ),
            },
            {
                "role": "user",
                "content": (
                    f"I have {len(filenames)} video clips to stitch into a vlog. "
                    "The output filename is OUTPUT_FILENAME. "
                    "Follow the steps: get_editing_guidelines, get_all_metadata, "
                    "get_ffmpeg_capabilities, build command, validate_ffmpeg_command, "
                    "then return the JSON with ffmpeg_command."
                ),
            },
        ]

        metadata = []
        max_iterations = 25
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            print(f">>> iteration {iteration}")

            response = ollama.chat(
                model="qwen2.5:7b",
                messages=history,
                tools=ollama_tools,
            )

            if response.message.tool_calls:
                history.append({
                    "role": "assistant",
                    "content": response.message.content or "",
                    "tool_calls": response.message.tool_calls,
                })

                for tool_call in response.message.tool_calls:
                    print(f">>> calling tool: {tool_call.function.name}")
                    print(f">>> with args: {tool_call.function.arguments}")

                    result = await client.call_tool(
                        tool_call.function.name,
                        tool_call.function.arguments,
                    )

                    if tool_call.function.name == "get_all_metadata":
                        print(f">>> tool result: get_all_metadata returned {len(result.structured_content.get('result', []))} clips")
                    elif tool_call.function.name == "get_clip_metadata":
                        print(f">>> tool result: {result.content[0].text if result.content else 'no result'}")
                    else:
                        print(f">>> tool result: {result.structured_content or result.content[0].text}")

                    # Capture metadata if get_all_metadata was called
                    if tool_call.function.name == "get_all_metadata":
                        try:
                            metadata = result.data.result
                        except:
                            pass

                    history.append({
                        "role": "tool",
                        "content": json.dumps(result) if isinstance(result, dict) else str(result),
                        "name": tool_call.function.name,
                    })

            else:
                content = response.message.content or ""
                print(f">>> final response: {content}")

                if content.strip():
                    try:
                        raw = content.strip().replace("```json", "").replace("```", "").strip()
                        parsed = json.loads(raw)

                        # If metadata wasn't captured via tool, fetch it now
                        if not metadata:
                            meta_result = await client.call_tool("get_all_metadata", {})
                            try:
                                metadata = meta_result.data.result
                            except:
                                metadata = []

                        # Check if model returned ffmpeg_command directly
                        if "ffmpeg_command" in parsed:
                            return VlogPlan(
                                decisions=VlogDecisions(
                                    trim_each_clip=False,
                                    trim_seconds=0.0,
                                    add_fade_in=True,
                                    add_fade_out=True,
                                    transition="cut",
                                    output_resolution="1080p",
                                    audio_normalize=False,
                                ),
                                ffmpeg_command=parsed["ffmpeg_command"],
                                metadata=metadata,
                            )

                        # Otherwise try to parse as VlogDecisions
                        decisions = VlogDecisions.model_validate_json(raw)
                        return VlogPlan(decisions=decisions, metadata=metadata)

                    except Exception as e:
                        print(f">>> failed to parse decisions: {e}")
                        history.append({"role": "assistant", "content": content})
                        history.append({
                            "role": "user",
                            "content": (
                                "Return ONLY a raw JSON object with this structure: "
                                '{"ffmpeg_command": "your ffmpeg command here"} '
                                "No explanation, no markdown, no backticks."
                            ),
                        })

        print(">>> max iterations reached, using defaults")
        if not metadata:
            meta_result = await client.call_tool("get_all_metadata", {})
            try:
                metadata = meta_result.data.result
            except:
                metadata = []

        return VlogPlan(
            decisions=VlogDecisions(
                trim_each_clip=False,
                trim_seconds=0.0,
                add_fade_in=True,
                add_fade_out=True,
                transition="cut",
                output_resolution="1080p",
                audio_normalize=False,
            ),
            metadata=metadata,
        )


async def generate_vlog_decisions(filenames: list[str]) -> VlogPlan:
    return await run_vlog_decisions(filenames)