# Programmatic MCP Access

For people building MCP clients instead of using Claude Desktop.

## Install

```bash
pip install "mcp>=1.12"
```

## Connect to GhidraMCP

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["-m", "ghidra_mcp"],
)

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"{tool.name}: {tool.description}")

            # List all functions
            result = await session.call_tool("list_functions", arguments={})
            print(result.content[0].text)

            # Decompile a specific function
            # IL2CPP names use ClassName$$MethodName format
            result = await session.call_tool(
                "decompile_function",
                arguments={"name": "SYBO_Subway_Coins_CoinManager$$Coin_OnCoinPickedUp"}
            )
            print(result.content[0].text)

asyncio.run(main())
```

## Key Tools

| Tool | Arguments | Returns |
|---|---|---|
| `list_functions` | `{}` | All function names in the binary |
| `decompile_function` | `{"name": "ClassName$$Method"}` | Decompiled C code |
| `get_callgraph` | `{"address": "0x...", "max_depth": 2}` | Callers and callees |
| `list_strings` | `{"filter": "coin"}` | Matching string literals |
| `get_disassembly` | `{"address": "0x...", "length": 100}` | Raw disassembly |
| `set_comment` | `{"address": "0x...", "comment": "...", "comment_type": "plate"}` | Sets a comment |
| `set_function_signature` | `{"address": "0x...", "signature": "int foo(void* this)"}` | Renames/retypes a function |

## Batch Decompilation Example

```python
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def decompile_class(session: ClientSession, class_name: str, script_json_path: str):
    """Decompile all methods of a class using script.json for lookup."""
    with open(script_json_path) as f:
        script = json.load(f)

    methods = [
        entry for entry in script.get("ScriptMethod", [])
        if entry["Name"].startswith(f"{class_name}$$")
    ]

    print(f"Found {len(methods)} methods for {class_name}")

    results = {}
    for method in methods:
        name = method["Name"]
        result = await session.call_tool(
            "decompile_function",
            arguments={"name": name}
        )
        results[name] = result.content[0].text
        print(f"  Decompiled: {name}")

    return results

async def main():
    server_params = StdioServerParameters(command="python", args=["-m", "ghidra_mcp"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            results = await decompile_class(session, "SYBO_Subway_Coins_CoinManager", "metadata/script.json")

            with open("SYBO_Subway_Coins_CoinManager_decompiled.c", "w") as f:
                for name, code in results.items():
                    f.write(f"// --- {name} ---\n{code}\n\n")

            print(f"Wrote {len(results)} decompilations to SYBO_Subway_Coins_CoinManager_decompiled.c")

asyncio.run(main())
```
