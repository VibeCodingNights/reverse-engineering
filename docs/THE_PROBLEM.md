# The Problem

This binary has 53,000 functions.

You can decompile any one of them. But if you decompiled all 53,000, that's 43 million tokens — 215 times more than fits in the context window.

## The Math

| | Count |
|---|---|
| Functions in binary | ~53,000 |
| Named classes (from IL2CPP metadata) | ~5,200 |
| Average decompiled function length | ~800 characters |
| Characters per token (rough) | ~4 |
| **Total tokens to decompile everything** | **~43,000,000** |
| Context window | 200,000 |
| **Over budget by** | **~215x** |

## What Happens When You Ask the LLM

You connect GhidraMCP and ask: *"How do coins work in this game?"*

The model calls `list_functions`. It gets back 53,000 names. That alone might burn 50,000 tokens. It scans the names, picks a few that look coin-related, decompiles maybe 5–10 of them. It writes a confident summary.

**It just summarized a 53,000-function binary by reading 10 functions.** That's 0.02% coverage. The other 99.98% is hallucination-by-omission.

## Why Metadata Isn't Enough

You have Il2CppDumper output: every class name, every method name, every field name. You know there's a `CoinManager` class with 47 methods. Great. But:

- Which of those 47 methods actually modify the coin balance?
- `CoinManager$$AddCoins` calls functions in `ServerSync`, `SaveManager`, and `InventoryController`. Are those calls important?
- The string literal `"coin_balance"` appears at address `0x1a2b3c`. Which function reads it? Is it the real balance or a display value?

Names tell you *where to look*. They don't tell you *what happens*.

## Why Decompiled C Is Hard

Even when you decompile the right function, the LLM has to understand decompiled C — not human-written C. Decompiled C has:
- No variable names (just `iVar1`, `lVar2`, `uVar3`)
- No type information beyond what the decompiler infers
- Inlined functions that bloat the apparent complexity
- Compiler optimizations that restructure control flow
- IL2CPP runtime calls (`il2cpp_runtime_class_init`, `il2cpp_object_new`) mixed into the logic

The best frontier model recovers 59% of reverse engineering targets from decompiled code. A human expert hits 92%. The gap is not intelligence. It's that the model is reading code optimized for machines, not for understanding.

## What Needs to Be Built

The missing piece is **triage** — compress the binary into a map the model can reason about:

1. **Search.** Don't list all 53,000 functions. Search the metadata for relevant terms. Cross-reference classes. Build a ranked candidate list.

2. **Expand.** From a candidate function, follow the call graph. What does it call? What calls it? Build the dependency cluster.

3. **Decompile selectively.** Decompile the cluster, not the binary. One class might be 20–50 methods, fitting in a single prompt.

4. **Summarize and re-prompt.** Summarize each class. Feed summaries to the model. Ask targeted questions.

5. **Verify.** The model's analysis is a hypothesis. Check it against the disassembly. Cross-reference with string literals. Look for what the model didn't mention.

None of these steps require new AI capabilities. They require engineering. That's what you're building tonight.
