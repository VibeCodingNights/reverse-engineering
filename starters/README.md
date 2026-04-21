# Starter Scripts

Working scripts, not stubs. Each one does something useful out of the box.

## Requirements

```bash
pip install -e .
# Only if you want ask.py --api to call the Anthropic API:
pip install -e .[llm]
```

Set `GHIDRA_BRIDGE` to the path of `bridge_mcp_ghidra.py` from your GhidraMCP clone:

```bash
export GHIDRA_BRIDGE=/path/to/GhidraMCP/bridge_mcp_ghidra.py
```

`ask.py --api` also needs `ANTHROPIC_API_KEY`. Without `--api` it prints the prompt for pasting into Claude Desktop.

## Scripts

### `survey.py` — How big is the problem?

Connects to GhidraMCP, lists all functions, groups by class prefix, does the token math.

```bash
python survey.py
```

Output tells you how many functions, how many classes, how many tokens you'd need to decompile everything, and why that's impossible. The "holy shit" script.

### `hunt.py` — Find coin-related functions

Searches `dump.cs` and `stringliteral.json` for economy-related terms. Cross-references classes appearing in multiple searches. No GhidraMCP connection needed — works on metadata files alone.

```bash
python hunt.py [--metadata-dir ../metadata]
```

Output: ranked list of classes most likely to handle coins, currency, and purchases.

### `class_decompile.py` — Decompile one class

Given a class name, looks up its methods in `script.json`, decompiles each via GhidraMCP. Outputs all decompilations — one class's worth of C, small enough for a single prompt.

```bash
python class_decompile.py SYBO_Subway_Coins_CoinManager [--script-json ../metadata/script.json]
```

### `ask.py` — End-to-end pipeline

Runs hunt -> picks the top class -> decompiles it -> builds a targeted prompt. Default: prints the prompt for pasting into Claude Desktop. With `--api`: calls the Anthropic API directly.

```bash
python ask.py [--metadata-dir ../metadata]           # print prompt
python ask.py --api                                   # call API (needs ANTHROPIC_API_KEY)
```

## What to Do With These

1. Run `survey.py` to understand the scale.
2. Run `hunt.py` to find candidates.
3. Run `class_decompile.py` on the top candidate.
4. Read the decompiled output. Do you believe it?
5. Run `ask.py` to see what Claude thinks.
6. Now build something better.
