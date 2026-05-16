import json
import ollama
from pydantic import BaseModel
from fastmcp.client import Client


class VlogDecisions(BaseModel):
    style: str = "homevideo"          # "cinematic", "youtube", "homevideo"
    trim_each_clip: bool = False
    trim_seconds: float = 0.0
    output_resolution: str = "1080p"  # "720p", "1080p", "4k"


class VlogPlan(BaseModel):
    decisions: VlogDecisions
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
                    "You are a professional video editor. "
                    "Follow these steps in order: "
                    "1. Call get_available_styles to understand the style options. "
                    "2. Call get_all_metadata to analyze all clips. "
                    "3. Call get_shortest_clip to know the minimum clip duration. "
                    "When you have enough information, respond with ONLY a raw JSON object, "
                    "no explanation, no markdown, no backticks, nothing else. "
                    "The JSON must have exactly these fields: "
                    "style (one of 'cinematic', 'youtube', 'homevideo'), "
                    "trim_each_clip (bool), "
                    "trim_seconds (float, 0 means no trim, must be at least 3.0 if trimming), "
                    "output_resolution (one of '720p', '1080p', '4k'). "
                    "Choose style based on clip content and total duration. "
                    "Choose output_resolution based on the resolution of most clips. "
                    "Set trim_each_clip to true only if clips are significantly different in length. "
                    "trim_seconds must never be less than the shortest clip duration."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"I have {len(filenames)} video clips to stitch into a vlog. "
                    "Call get_available_styles, then get_all_metadata, then get_shortest_clip, "
                    "then return your editing decisions as a raw JSON object only."
                ),
            },
        ]

        metadata = []
        max_iterations = 15
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

                    result = await client.call_tool(
                        tool_call.function.name,
                        tool_call.function.arguments,
                    )

                    if tool_call.function.name == "get_all_metadata":
                        print(f">>> tool result: get_all_metadata returned {len(result.structured_content.get('result', []))} clips")
                        try:
                            metadata = result.data.result
                        except:
                            pass
                    else:
                        try:
                            print(f">>> tool result: {result.structured_content or result.content[0].text}")
                        except:
                            print(f">>> tool result: {result}")

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
                        decisions = VlogDecisions.model_validate_json(raw)

                        # Fetch metadata if not captured yet
                        if not metadata:
                            meta_result = await client.call_tool("get_all_metadata", {})
                            try:
                                metadata = meta_result.data.result
                            except:
                                metadata = []

                        print(f">>> decisions: {decisions}")
                        return VlogPlan(decisions=decisions, metadata=metadata)

                    except Exception as e:
                        print(f">>> failed to parse decisions: {e}")
                        history.append({"role": "assistant", "content": content})
                        history.append({
                            "role": "user",
                            "content": (
                                "Return ONLY a raw JSON object with exactly these fields: "
                                "style ('cinematic', 'youtube', or 'homevideo'), "
                                "trim_each_clip (bool), trim_seconds (float), "
                                "output_resolution ('720p', '1080p', or '4k'). "
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
                style="homevideo",
                trim_each_clip=False,
                trim_seconds=0.0,
                output_resolution="1080p",
            ),
            metadata=metadata,
        )


async def generate_vlog_decisions(filenames: list[str]) -> VlogPlan:
    return await run_vlog_decisions(filenames)