#!/usr/bin/env python3
"""Decompile all methods of a single class via GhidraMCP.

Looks up methods in script.json, decompiles each through MCP,
writes all decompilations to stdout or a file.

Usage:
    python class_decompile.py CoinManager
    python class_decompile.py CoinManager --script-json ../metadata/script.json
    python class_decompile.py CoinManager -o CoinManager_decompiled.c
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def find_class_methods(script_json_path: str, class_name: str) -> list[dict]:
    """Find all methods for a class in script.json."""
    with open(script_json_path) as f:
        data = json.load(f)

    methods = []
    for entry in data.get("ScriptMethod", []):
        name = entry.get("Name", "")
        if name.startswith(f"{class_name}$$"):
            methods.append({
                "name": name,
                "method": name.split("$$", 1)[1],
                "address": entry.get("Address"),
                "signature": entry.get("Signature", ""),
            })

    return methods


async def decompile_methods(methods: list[dict]) -> list[dict]:
    """Decompile each method via GhidraMCP."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "ghidra_mcp"],
    )

    results = []
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            for i, method in enumerate(methods):
                name = method["name"]
                sys.stderr.write(f"  [{i+1}/{len(methods)}] Decompiling {name}...\n")

                try:
                    result = await session.call_tool(
                        "decompile_function",
                        arguments={"name": name}
                    )
                    code = result.content[0].text
                    results.append({**method, "code": code, "error": None})
                except Exception as e:
                    sys.stderr.write(f"    Error: {e}\n")
                    results.append({**method, "code": None, "error": str(e)})

    return results


def format_output(class_name: str, results: list[dict]) -> str:
    """Format decompilation results as a single C file."""
    lines = []
    lines.append(f"// Decompiled methods for class: {class_name}")
    lines.append(f"// Total methods: {len(results)}")

    succeeded = sum(1 for r in results if r["code"])
    failed = sum(1 for r in results if r["error"])
    lines.append(f"// Decompiled: {succeeded}, Failed: {failed}")
    lines.append("")

    for result in results:
        lines.append(f"// --- {result['name']} ---")
        if result.get("signature"):
            lines.append(f"// Signature: {result['signature']}")
        if result.get("address"):
            lines.append(f"// Address: 0x{result['address']:x}" if isinstance(result['address'], int)
                         else f"// Address: {result['address']}")
        lines.append("")

        if result["code"]:
            lines.append(result["code"])
        else:
            lines.append(f"// DECOMPILATION FAILED: {result['error']}")

        lines.append("")
        lines.append("")

    return "\n".join(lines)


def _default_script_json() -> str:
    """Resolve script.json relative to this script, not CWD."""
    return str(Path(__file__).resolve().parent.parent / "metadata" / "script.json")


def main():
    parser = argparse.ArgumentParser(description="Decompile all methods of a class via GhidraMCP")
    parser.add_argument("class_name", help="Class name to decompile (e.g., SYBO_Subway_Coins_CoinManager)")
    parser.add_argument("--script-json", default=_default_script_json(),
                        help="Path to script.json from Il2CppDumper")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    script_path = Path(args.script_json)
    if not script_path.exists():
        print(f"Error: script.json not found at {script_path}", file=sys.stderr)
        print("Provide the path with --script-json", file=sys.stderr)
        sys.exit(1)

    # Find methods
    methods = find_class_methods(str(script_path), args.class_name)

    if not methods:
        print(f"No methods found for class '{args.class_name}'", file=sys.stderr)
        print("\nAvailable classes with similar names:", file=sys.stderr)

        with open(script_path) as f:
            data = json.load(f)

        classes = set()
        search = args.class_name.lower()
        for entry in data.get("ScriptMethod", []):
            name = entry.get("Name", "")
            if "$$" in name:
                cls = name.split("$$")[0]
                if search in cls.lower():
                    classes.add(cls)

        for cls in sorted(classes)[:20]:
            print(f"  {cls}", file=sys.stderr)

        sys.exit(1)

    print(f"Found {len(methods)} methods for {args.class_name}", file=sys.stderr)

    # Decompile
    results = asyncio.run(decompile_methods(methods))

    # Output
    output = format_output(args.class_name, results)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
