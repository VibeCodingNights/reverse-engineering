#!/usr/bin/env python3
"""Survey the binary: how many functions, how many classes, how many tokens.

Connects to GhidraMCP, lists all functions, groups by IL2CPP class prefix,
and does the token math that makes the problem legible.

Usage:
    python survey.py
"""

import asyncio
import re
from collections import Counter

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Rough estimate: 1 token per 4 chars of decompiled C
CHARS_PER_TOKEN = 4
AVG_FUNCTION_CHARS = 800  # average decompiled function length
CONTEXT_WINDOW = 200_000


def parse_class_name(function_name: str) -> str:
    """Extract class name from IL2CPP ClassName$$MethodName format."""
    if "$$" in function_name:
        return function_name.split("$$")[0]
    # Ghidra default names
    if function_name.startswith("FUN_"):
        return "(unnamed)"
    return "(other)"


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "ghidra_mcp"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("Listing all functions...")
            result = await session.call_tool("list_functions", arguments={})
            raw = result.content[0].text

            # Parse function names — one per line
            functions = [line.strip() for line in raw.strip().split("\n") if line.strip()]
            total = len(functions)

            # Group by class
            class_counts = Counter(parse_class_name(f) for f in functions)
            named_classes = {k: v for k, v in class_counts.items() if k not in ("(unnamed)", "(other)")}
            unnamed_count = class_counts.get("(unnamed)", 0)

            # Token math
            total_tokens = total * (AVG_FUNCTION_CHARS // CHARS_PER_TOKEN)
            budget_ratio = total_tokens / CONTEXT_WINDOW

            print(f"""
{'='*60}
BINARY SURVEY
{'='*60}

Functions: {total:,} across {len(named_classes):,} named classes
Unnamed functions (FUN_*): {unnamed_count:,}

Estimated tokens to decompile all: ~{total_tokens:,}
Context window: {CONTEXT_WINDOW:,} tokens

You're {budget_ratio:.0f}x over budget.
{'='*60}
""")

            # Top classes by method count
            top = class_counts.most_common(20)
            print("Top 20 classes by method count:")
            for cls, count in top:
                tokens = count * (AVG_FUNCTION_CHARS // CHARS_PER_TOKEN)
                print(f"  {cls:<40} — {count:>4} methods  (~{tokens:,} tokens)")

            # Find coin-related classes
            coin_classes = {k: v for k, v in named_classes.items()
                           if any(term in k.lower() for term in
                                  ["coin", "currency", "money", "balance", "wallet", "iap", "purchase", "reward"])}

            if coin_classes:
                print(f"\nCoin/currency-related classes:")
                for cls, count in sorted(coin_classes.items(), key=lambda x: -x[1]):
                    tokens = count * (AVG_FUNCTION_CHARS // CHARS_PER_TOKEN)
                    print(f"  {cls:<40} — {count:>4} methods  (~{tokens:,} tokens)")

                total_coin_methods = sum(coin_classes.values())
                total_coin_tokens = total_coin_methods * (AVG_FUNCTION_CHARS // CHARS_PER_TOKEN)
                print(f"\nEven just the coin-related classes: {total_coin_methods} methods, ~{total_coin_tokens:,} tokens")
                print(f"Which of those {total_coin_methods} methods actually touch the coin balance?")
                print("That's the problem.")


if __name__ == "__main__":
    asyncio.run(main())
