import json
import ollama
from pydantic import BaseModel
from fastmcp.client import Client


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
        "Trim aggressively if clips are long — YouTube viewers want fast pacing. "
        "If clips are already short (under 10 seconds), set trim_each_clip to false."
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

        # Fetch metadata and shortest clip upfront so we can pass constraints to prompt
        metadata = []
        shortest_duration = 0.0
        try:
            meta_result = await client.call_tool("get_all_metadata", {})
            metadata = meta_result.data.result
            shortest_result = await client.call_tool("get_shortest_clip", {})
            shortest_duration = shortest_result.data.duration_seconds
            print(f">>> pre-fetched {len(metadata)} clips, shortest: {shortest_duration}s")
        except Exception as e:
            print(f">>> pre-fetch failed: {e}")

        style_guidance = STYLE_PROMPTS.get(style, STYLE_PROMPTS["homevideo"])

        history = [
            {
                "role": "system",
                "content": (
                    "You are a professional video editor. "
                    f"{style_guidance} "
                    "The clip metadata has already been fetched for you. "
                    "Respond with ONLY a raw JSON object, "
                    "no explanation, no markdown, no backticks, nothing else. "
                    "The JSON must have exactly these fields: "
                    f"style (must be '{style}'), "
                    "trim_each_clip (bool), "
                    "trim_seconds (float, 0 means no trim), "
                    "output_resolution (one of '720p', '1080p', '4k'). "
                    f"IMPORTANT: trim_seconds must be 0 (no trim) or greater than {shortest_duration} seconds. "
                    f"The shortest clip is {shortest_duration} seconds — never set trim_seconds below this value. "
                    "If clips are already short, set trim_each_clip to false and trim_seconds to 0."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"I have {len(filenames)} video clips to stitch into a {style} style vlog. "
                    f"Here is the metadata: {json.dumps(metadata)}. "
                    f"The shortest clip is {shortest_duration} seconds. "
                    "Return your editing decisions as a raw JSON object only."
                ),
            },
        ]

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

                        # Safety net — if trim_seconds is below shortest clip, disable trimming
                        if decisions.trim_each_clip and decisions.trim_seconds < shortest_duration:
                            print(f">>> trim_seconds {decisions.trim_seconds} below shortest clip {shortest_duration}, disabling trim")
                            decisions.trim_each_clip = False
                            decisions.trim_seconds = 0.0

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