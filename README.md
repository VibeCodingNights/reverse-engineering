# Reverse Engineering

**Vibe Coding Night — April 2026**

Your LLM can decompile a function. It cannot understand a binary.

Wire a model to Ghidra through MCP. Ask it what a program does. It decompiles a handful of functions, hallucinates the other eight thousand, and gives you a confident summary of software it never read.

Tonight's target: a real game with 53,000 functions. The challenge isn't "hack the game." It's: **which 20 functions out of 53,000 answer your question?**

---

## The Problem

The binary has 53,000 functions. Decompiling all of them would burn 43 million tokens — 215x more than fits in a context window. Even listing their signatures blows the budget.

You have metadata: every function has a name (courtesy of Unity leaking its metadata file). You know there's a class called `CoinManager` with 47 methods. But which of those 47 methods actually modify the coin balance? And when the LLM reads the decompiled C, does it understand it — or does it hallucinate?

The best frontier model recovers 59% of reverse engineering targets. A human expert hits 92%. The gap is not intelligence. It's that nobody built the layer between the disassembler and the prompt.

**That's what you're building tonight.**

---

## Quick Start

### 1. Validate the toolchain (~20 min)

```bash
git clone https://github.com/vibecodingnights/reverse-engineering.git
cd reverse-engineering
```

Install [Ghidra 12](https://ghidra-sre.org) (requires JDK 21+). Follow [`setup/GHIDRA_MCP.md`](setup/GHIDRA_MCP.md) to install the GhidraMCP extension and start the bridge.

Copy [`setup/claude_desktop_config.json`](setup/claude_desktop_config.json) into Claude Desktop's config directory:
- **macOS:** `~/Library/Application Support/Claude/`
- **Windows:** `%APPDATA%\Claude\`

Open `warmup/warmup` in Ghidra. Let auto-analysis finish (~10 seconds). In Claude Desktop, ask:

> *"What does this program do? List all its functions."*

Compare the answer to [`warmup/warmup.c`](warmup/warmup.c). If it nails everything, your setup works. Move on.

### 2. Load the game binary (~15 min)

Grab a USB drive from the front table. Copy `libil2cpp.so` and the Il2CppDumper `output/` directory.

Or download the APK yourself and run `target/extract.py` — see [`target/DOWNLOAD.md`](target/DOWNLOAD.md).

Or **load the pre-analyzed Ghidra project** from the USB drive (fastest path — skip straight to step 3).

If loading from scratch:
1. Open `libil2cpp.so` in Ghidra. Auto-analysis takes 5–15 minutes. While it runs, read [`docs/IL2CPP_PRIMER.md`](docs/IL2CPP_PRIMER.md).
2. Open Script Manager (Window > Script Manager), run `ghidra.py`, point it at `output/script.json`.
3. Watch functions rename from `FUN_00xxxxxx` to `CoinManager$$AddCoins`.

### 3. Ask the LLM to find the coins (~15 min)

In Claude Desktop (connected to GhidraMCP), ask:

> *"This is a mobile game binary. Find all functions related to coins and currency. How does the game track the player's coin balance?"*

Watch what happens. Write down what it claims.

Now run the starter scripts:

```bash
pip install "mcp>=1.12" anthropic
python starters/hunt.py        # systematic metadata search
python starters/survey.py      # token math — the "holy shit" script
```

Compare the systematic search against the LLM's ad-hoc exploration. What did it miss?

**You've now seen the problem. Now build.**

---

## Repo Structure

```
├── target/           APK extraction — DOWNLOAD.md + extract.py
├── metadata/         Pre-generated Il2CppDumper output (class/method names)
├── warmup/           10-function binary for toolchain validation
├── setup/            Ghidra + GhidraMCP + Claude Desktop config
├── starters/         Working scripts: survey, hunt, decompile, ask
└── docs/             The problem, IL2CPP primer, tool reference, project ideas
```

## What to Build

See [`docs/WHAT_TO_BUILD.md`](docs/WHAT_TO_BUILD.md) for project ideas. The short version:

- **Better hunters.** Follow call graphs. Cross-reference field offsets. Cluster related classes.
- **Selective decompilation.** Decompile a cluster, summarize each class, feed summaries to the LLM. Where's the accuracy cliff?
- **Answer the question.** Trace coin flow end-to-end. Client-side or server-side validation? Could you actually get unlimited coins?
- **Annotation loops.** Use the LLM to rename and comment functions. Does the second pass improve?
- **Dynamic analysis.** Hook functions with Frida at runtime. Does dynamic data correct static hallucinations?

## Resources

| Resource | Link |
|---|---|
| GhidraMCP (LaurieWired) | [github.com/LaurieWired/GhidraMCP](https://github.com/LaurieWired/GhidraMCP) |
| GhydraMCP (Starsong, multi-instance) | [github.com/starsong-consulting/GhydraMCP](https://github.com/starsong-consulting/GhydraMCP) |
| Il2CppDumper (Perfare) | [github.com/Perfare/Il2CppDumper](https://github.com/Perfare/Il2CppDumper) |
| ida-pro-mcp | [github.com/mrexodia/ida-pro-mcp](https://github.com/mrexodia/ida-pro-mcp) |
| radare2-mcp | [github.com/radareorg/radare2-mcp](https://github.com/radareorg/radare2-mcp) |
| frida-mcp | [github.com/dnakov/frida-mcp](https://github.com/dnakov/frida-mcp) |
| Frida | [frida.re](https://frida.re) |
| Reversecore_MCP | [github.com/sjkim1127/Reversecore_MCP](https://github.com/sjkim1127/Reversecore_MCP) |
| Awesome-RE-MCP | [github.com/crowdere/Awesome-RE-MCP](https://github.com/crowdere/Awesome-RE-MCP) |
| MCP Python SDK | [github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) |
| Ghidra 12 | [ghidra-sre.org](https://ghidra-sre.org) |
| APKMirror | [apkmirror.com](https://apkmirror.com) |

---

[vibecodingnights.com](https://vibecodingnights.com)
