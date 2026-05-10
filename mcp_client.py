import asyncio
import json
import ollama
from fastmcp import Client
from pydantic import BaseModel


class VlogDecisions(BaseModel):
    trim_each_clip: bool
    trim_seconds: float
    add_fade_in: bool
    add_fade_out: bool
    speed: float


async def run_vlog_decisions(filenames: list[str]) -> VlogDecisions:
    async with Client("http://localhost:8050/sse") as client:
        # Get available tools from MCP server
        mcp_tools = await client.list_tools()

        # Convert MCP tools to Ollama format
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

        # Initial prompt
        history = [
            {
                "role": "system",
                "content": (
                    "You are a professional video editor. "
                    "Use the available tools to gather information about the clips, "
                    "then make editing decisions. "
                    "When you have enough information, return your final decisions as JSON with these fields: "
                    "trim_each_clip (bool), trim_seconds (float), "
                    "add_fade_in (bool), add_fade_out (bool), speed (float)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"I have {len(filenames)} video clips to stitch into a vlog. "
                    "Use the tools to analyze them and return your editing decisions as JSON."
                ),
            },
        ]

        # Tool calling loop
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            print(f">>> iteration {iteration}")

            response = ollama.chat(
                model="phi3:mini",
                messages=history,
                tools=ollama_tools,
            )

            # If Ollama wants to call tools
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

                    print(f">>> tool result: {result}")

                    history.append({
                        "role": "tool",
                        "content": json.dumps(result) if isinstance(result, dict) else str(result),
                        "name": tool_call.function.name,
                    })

            # If Ollama returns a final answer
            else:
                print(f">>> final response: {response.message.content}")
                try:
                    raw = response.message.content.strip()
                    raw = raw.replace("```json", "").replace("```", "").strip()
                    decisions = VlogDecisions.model_validate_json(raw)
                    return decisions
                except Exception as e:
                    print(f">>> failed to parse decisions: {e}")
                    # Return safe defaults
                    return VlogDecisions(
                        trim_each_clip=False,
                        trim_seconds=0.0,
                        add_fade_in=True,
                        add_fade_out=True,
                        speed=1.0,
                    )

        # Max iterations reached, return defaults
        print(">>> max iterations reached, using defaults")
        return VlogDecisions(
            trim_each_clip=False,
            trim_seconds=0.0,
            add_fade_in=True,
            add_fade_out=True,
            speed=1.0,
        )


def generate_vlog_decisions(filenames: list[str]) -> VlogDecisions:
    return asyncio.run(run_vlog_decisions(filenames))


if __name__ == "__main__":
    # Quick test
    decisions = generate_vlog_decisions([])
    print(f">>> decisions: {decisions}")