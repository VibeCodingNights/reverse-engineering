# What to Build

Every project below attacks the same problem: narrowing 53,000 functions to the ones that answer your question.

## For Everyone

### Better Hunter

`starters/hunt.py` does keyword search on metadata. Can you do better?

- **Call graph expansion.** `CoinManager$$AddCoins` calls what? What calls it? Use GhidraMCP's `get_callgraph` to expand from known coin functions to their dependencies and callers. Build the full coin subsystem graph.

- **Field cross-referencing.** `dump.cs` shows field offsets: `public int coinBalance; // 0x1C`. Find all functions that read or write to offset `0x1C` on a `CoinManager` object. That's your real list of coin-modifying functions, regardless of their name.

- **Class clustering.** `CoinManager`, `CurrencyController`, `RewardManager`, `IAPController` probably form a subsystem. Build the dependency graph between them. Which classes call which? What's the boundary of the "economy" subsystem?

### Selective Decompilation Pipeline

`starters/class_decompile.py` decompiles one class. Build the version that:

1. Takes a cluster of related classes (not just one)
2. Decompiles all methods in the cluster
3. Summarizes each class (method names, what each does in one line)
4. Feeds only the summaries to the LLM
5. Lets the LLM ask for full decompilation of specific methods

Does a summary of 5 related classes produce better analysis than raw decompilation of 1? Where's the accuracy cliff? At what compression ratio does the model start hallucinating?

### Answer the Actual Question

Trace the coin flow end-to-end:

- **Storage.** Where is the balance stored? A field on `CoinManager`? `PlayerPrefs`? A local save file? A server database?
- **Modification.** What happens when `AddCoins` is called? Does it write to a field and return? Does it call a save function? Does it make a network request?
- **Integrity.** Is there a checksum on the save file? Encryption? A server-side balance that syncs?
- **IAP.** What does the IAP controller do when a purchase succeeds? Does it grant coins immediately or wait for server confirmation?
- **Verdict.** Could you get unlimited coins with a memory editor? Why or why not?

This is genuine reverse engineering — using triage tools to answer a concrete question about a real product.

### Annotation Loop

Use the LLM to rename and comment functions via GhidraMCP, then re-analyze:

1. Decompile `CoinManager$$AddCoins`
2. Ask the LLM what it does
3. Write the LLM's understanding as a Ghidra comment via `set_comment`
4. Decompile functions that *call* `AddCoins` — the comment now appears in their decompilation context
5. Does the LLM's analysis of the callers improve with the annotated callee?

Build the automated version: decompile → analyze → annotate → re-decompile callers → repeat.

---

## For Experienced RE Practitioners

### Dynamic Analysis with Frida

If you have an Android emulator or rooted device:

```bash
pip install frida-tools
# or for MCP integration:
# github.com/dnakov/frida-mcp
```

Hook `CoinManager$$AddCoins` at runtime. Capture arguments and return values. Feed runtime traces to the LLM alongside the static decompilation.

**The question:** Does dynamic data correct the hallucinations from static analysis alone? Where does static analysis get it wrong that runtime traces get it right?

### Bring Your Own APK

Any Unity/IL2CPP game works with the same extraction pipeline. `target/extract.py` handles the APK extraction. Run it on whatever game you want to reverse.

The same triage pattern applies: metadata search → class ranking → selective decompilation → targeted analysis.

### Compare Decompiler Backends

Load the same binary in multiple tools:
- **IDA Pro** via [ida-pro-mcp](https://github.com/mrexodia/ida-pro-mcp)
- **Radare2** via [radare2-mcp](https://github.com/radareorg/radare2-mcp)
- **Binary Ninja** via binary_ninja_mcp

Compare decompiler output on the same function. Which backend gives the LLM better raw material?

### Multi-Tool Orchestration

Wire GhidraMCP for static analysis and frida-mcp for dynamic:

1. Search metadata statically → identify coin functions
2. Instrument them dynamically with Frida → capture runtime behavior
3. Feed both static decompilation and dynamic traces to the LLM
4. Synthesize a report

This is the [Reversecore_MCP](https://github.com/sjkim1127/Reversecore_MCP) pattern applied to game analysis.

### The Obfuscation Question

Does this game use protection? IL2CPP binaries are notoriously easy to analyze because metadata leaks everything. But some games add:
- String encryption
- Control flow flattening
- Metadata encryption (Il2CppDumper fails)
- Anti-tampering checks

Check: does the Il2CppDumper output look clean? Are there signs of protection? If protected, how does that change the LLM's accuracy?

### Non-Unity Targets

Unreal Engine uses C++ without metadata recovery. Native NDK games are raw C/C++. How does the triage problem change when you don't have class/method names? Grab a non-Unity APK and compare.
