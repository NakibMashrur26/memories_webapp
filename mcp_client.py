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
                    "First call get_editing_guidelines to understand the rules. "
                    "Then use the other tools to gather information about the clips. "
                    "When you have enough information, respond with ONLY a raw JSON object, "
                    "no explanation, no markdown, no backticks, nothing else. "
                    "The JSON must have exactly these fields: "
                    "trim_each_clip (bool), trim_seconds (float), "
                    "add_fade_in (bool), add_fade_out (bool). "
                    "trim_seconds means the maximum number of seconds to KEEP from each clip. "
                    "For example, trim_seconds=5 means keep only the first 5 seconds of each clip. "
                    "trim_seconds must always be greater than the shortest clip duration or set to 0 to keep full clips. "
                    "Never set trim_seconds below 3.0."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"I have {len(filenames)} video clips to stitch into a vlog. "
                    "First call get_editing_guidelines, then analyze the clips using the other tools, "
                    "then return your editing decisions as a raw JSON object only."
                ),
            },
        ]

        metadata = []
        max_iterations = 10
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
                        decisions = VlogDecisions.model_validate_json(raw)

                        # If metadata wasn't captured via tool, fetch it now
                        if not metadata:
                            meta_result = await client.call_tool("get_all_metadata", {})
                            try:
                                metadata = meta_result.data.result
                            except:
                                metadata = []

                        return VlogPlan(decisions=decisions, metadata=metadata)
                    except Exception as e:
                        print(f">>> failed to parse decisions: {e}")
                        history.append({"role": "assistant", "content": content})
                        history.append({
                            "role": "user",
                            "content": "Return your final editing decisions as a raw JSON object only. No explanation, no markdown, no backticks.",
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
            ),
            metadata=metadata,
        )


async def generate_vlog_decisions(filenames: list[str]) -> VlogPlan:
    return await run_vlog_decisions(filenames)