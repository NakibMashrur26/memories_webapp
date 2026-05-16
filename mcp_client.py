import json
import ollama
from pydantic import BaseModel
from fastmcp.client import Client # type: ignore


class VlogDecisions(BaseModel):
    style: str = "homevideo"
    trim_each_clip: bool = False
    trim_seconds: float = 0.0
    output_resolution: str = "1080p"


class VlogPlan(BaseModel):
    decisions: VlogDecisions
    metadata: list[dict]


STYLE_PROMPTS = {
    "homevideo": (
        "The user has chosen the Home Video style. "
        "This means: clean cuts, no fades, fast encoding. "
        "Your job is to decide: "
        "whether to trim clips (trim_each_clip), "
        "how long to keep each clip (trim_seconds, 0 = keep full clip), "
        "and output resolution based on clip resolution. "
        "Keep it simple — preserve the natural feel of the footage."
    ),
    "youtube": (
        "The user has chosen the YouTube style. "
        "This means: fast cuts, energetic feel, audio normalization. "
        "Your job is to decide: "
        "whether to trim clips (trim_each_clip) to keep pace up, "
        "how long to keep each clip (trim_seconds, 0 = keep full clip), "
        "and output resolution based on clip resolution. "
        "Trim aggressively if clips are long — YouTube viewers want fast pacing."
    ),
    "cinematic": (
        "The user has chosen the Cinematic style. "
        "This means: slow fades, high quality encoding, dramatic feel. "
        "Your job is to decide: "
        "whether to trim clips (trim_each_clip), "
        "how long to keep each clip (trim_seconds, 0 = keep full clip), "
        "and output resolution — prefer higher resolution for cinematic quality. "
        "Be selective with trimming — cinematic style benefits from longer, breathing shots."
    ),
}


async def run_vlog_decisions(filenames: list[str], style: str = "homevideo") -> VlogPlan:
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

        style_guidance = STYLE_PROMPTS.get(style, STYLE_PROMPTS["homevideo"])

        history = [
            {
                "role": "system",
                "content": (
                    "You are a professional video editor. "
                    f"{style_guidance} "
                    "Follow these steps: "
                    "1. Call get_all_metadata to analyze all clips. "
                    "2. Call get_shortest_clip to know the minimum clip duration. "
                    "3. Call get_available_resolutions to see resolution options. "
                    "Then respond with ONLY a raw JSON object, "
                    "no explanation, no markdown, no backticks, nothing else. "
                    "The JSON must have exactly these fields: "
                    f"style (must be '{style}'), "
                    "trim_each_clip (bool), "
                    "trim_seconds (float, 0 means no trim, must be at least 3.0 if trimming), "
                    "output_resolution (one of '720p', '1080p', '4k'). "
                    "trim_seconds must never be less than the shortest clip duration."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"I have {len(filenames)} video clips to stitch into a {style} style vlog. "
                    "Call get_all_metadata, then get_shortest_clip, then get_available_resolutions, "
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

                        # Ensure style always matches what user selected
                        decisions.style = style

                        # Fetch metadata if not captured yet
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
                            "content": (
                                f"Return ONLY a raw JSON object with exactly these fields: "
                                f"style (must be '{style}'), "
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
                style=style,
                trim_each_clip=False,
                trim_seconds=0.0,
                output_resolution="1080p",
            ),
            metadata=metadata,
        )


async def generate_vlog_decisions(filenames: list[str], style: str = "homevideo") -> VlogPlan:
    return await run_vlog_decisions(filenames, style)