#!/usr/bin/env python3
"""End-to-end pipeline: hunt -> decompile -> ask the LLM.

Searches metadata for coin-related classes, decompiles the top candidate
via GhidraMCP, and sends the decompilation to Claude with a targeted prompt.

Usage:
    python ask.py [--metadata-dir ../metadata]

Requires: ANTHROPIC_API_KEY environment variable.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ANALYSIS_PROMPT = """Here are the decompiled methods of {class_name} from a mobile game binary.
This class was identified as the most likely handler for in-game currency based on
metadata analysis (matched terms: {matched_terms}).

{decompiled_code}

Answer these questions:
1. How are coins stored? Is it a local variable, a field on the object, PlayerPrefs, a file, or a server value?
2. When coins are added (AddCoins or similar), does the function make a network request or validate with a server?
3. Is there any integrity checking — checksums, encryption, or server-side validation?
4. Could a memory editor (like GameGuardian) modify the coin balance at runtime? Why or why not?
5. What would you need to verify that your analysis is correct? What are you uncertain about?

Be specific. Cite function names and field offsets. Flag anything you're guessing about."""


def hunt_top_class(metadata_dir: Path) -> tuple[str, list[str]]:
    """Find the most relevant coin-related class from metadata. Returns (class_name, matched_terms)."""
    from collections import Counter, defaultdict

    terms = ["coin", "currency", "balance", "purchase", "reward", "money", "wallet"]
    class_hits = defaultdict(set)

    # Search script.json
    script_path = metadata_dir / "script.json"
    if script_path.exists():
        with open(script_path) as f:
            data = json.load(f)
        for entry in data.get("ScriptMethod", []):
            name = entry.get("Name", "").lower()
            if "$$" in name:
                cls = entry["Name"].split("$$")[0]
                for term in terms:
                    if term in name:
                        class_hits[cls].add(term)

    # Search dump.cs
    dump_path = metadata_dir / "dump.cs"
    if dump_path.exists():
        import re
        current_class = None
        with open(dump_path) as f:
            for line in f:
                match = re.match(r'\s*(?:public|private|internal)?\s*class\s+(\w+)', line)
                if match:
                    current_class = match.group(1)
                if current_class:
                    lower = line.lower()
                    for term in terms:
                        if term in lower:
                            class_hits[current_class].add(term)

    if not class_hits:
        print("No coin-related classes found in metadata.", file=sys.stderr)
        sys.exit(1)

    # Pick the class with the most distinct term matches
    top_class = max(class_hits.items(), key=lambda x: len(x[1]))
    return top_class[0], list(top_class[1])


async def decompile_class(class_name: str, script_json_path: str) -> str:
    """Decompile all methods of a class via GhidraMCP."""
    with open(script_json_path) as f:
        data = json.load(f)

    methods = [
        entry for entry in data.get("ScriptMethod", [])
        if entry.get("Name", "").startswith(f"{class_name}$$")
    ]

    if not methods:
        print(f"No methods found for {class_name} in script.json", file=sys.stderr)
        sys.exit(1)

    print(f"Decompiling {len(methods)} methods for {class_name}...", file=sys.stderr)

    server_params = StdioServerParameters(command="python", args=["-m", "ghidra_mcp"])
    parts = []

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            for i, method in enumerate(methods):
                name = method["Name"]
                sys.stderr.write(f"  [{i+1}/{len(methods)}] {name}\n")
                try:
                    result = await session.call_tool(
                        "decompile_function",
                        arguments={"name": name}
                    )
                    parts.append(f"// --- {name} ---\n{result.content[0].text}\n")
                except Exception as e:
                    parts.append(f"// --- {name} ---\n// FAILED: {e}\n")

    return "\n".join(parts)


def ask_claude(class_name: str, matched_terms: list[str], decompiled_code: str) -> str:
    """Send decompiled code to Claude for analysis."""
    client = anthropic.Anthropic()

    prompt = ANALYSIS_PROMPT.format(
        class_name=class_name,
        matched_terms=", ".join(matched_terms),
        decompiled_code=decompiled_code,
    )

    print(f"\nSending {len(decompiled_code):,} chars to Claude...", file=sys.stderr)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def main():
    parser = argparse.ArgumentParser(description="End-to-end: hunt -> decompile -> ask")
    parser.add_argument("--metadata-dir", default="../metadata",
                        help="Path to Il2CppDumper output directory")
    parser.add_argument("--class-name", help="Override: decompile this class instead of hunting")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Set ANTHROPIC_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    metadata_dir = Path(args.metadata_dir)
    script_json = metadata_dir / "script.json"

    if not script_json.exists():
        print(f"Error: script.json not found at {script_json}", file=sys.stderr)
        sys.exit(1)

    # Step 1: Hunt
    if args.class_name:
        class_name = args.class_name
        matched_terms = ["(user-specified)"]
        print(f"Using specified class: {class_name}", file=sys.stderr)
    else:
        print("Hunting for coin-related classes...", file=sys.stderr)
        class_name, matched_terms = hunt_top_class(metadata_dir)
        print(f"Top candidate: {class_name} (matched: {', '.join(matched_terms)})", file=sys.stderr)

    # Step 2: Decompile
    decompiled = asyncio.run(decompile_class(class_name, str(script_json)))

    # Step 3: Ask
    analysis = ask_claude(class_name, matched_terms, decompiled)

    print(f"\n{'='*60}")
    print(f"ANALYSIS: {class_name}")
    print(f"{'='*60}\n")
    print(analysis)


if __name__ == "__main__":
    main()
