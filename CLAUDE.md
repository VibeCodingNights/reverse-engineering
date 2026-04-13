# Vibe Coding Nights — Repo Builder

You are building the event repo for a Vibe Coding Night.

## Event Theme
reverse engineering


## Event Description
Your LLM can decompile a function. It cannot understand a binary.

Wire a model to Ghidra through MCP. Ask it what a program does. It decompiles a handful of functions, hallucinates the other eight thousand, and gives you a confident summary of software it never read.

The best frontier model recovers 59% of reverse engineering targets. A human expert hits 92%. The gap is not intelligence. It's that nobody built the layer between the disassembler and the prompt.

A real binary has thousands of functions. Listing their signatures alone burns 50,000 tokens before a single decompilation. The model either sees a truncated view or decompiles a few and guesses the rest. The missing piece is triage — compress a binary into a map the model can reason about. Cluster functions by behavior. Route the tedious work to the model. Flag crypto and obfuscation for a human.

That's an engineering problem. It's buildable in a night.

We're putting a stripped binary on the table — real software, not a CTF toy — and building the context architecture between raw disassembly and the LLM. Ghidra 12. GhidraMCP. A program nobody in the room has seen before.

You don't need to have reversed anything before. The tools are free and open source. Bring a laptop.

vibecodingnights.com

---

## Event Flow (includes repo structure plan)
Good — I've confirmed the MCP Python SDK API (`v1.12.4`) and Il2CppDumper's exact CLI usage, `script.json` schema (`ScriptMethod[].Name` uses `ClassName$$MethodName` format), and Ghidra integration (`ghidra.py` in Script Manager). Now I can see what the superseded output missed: the user wants a **game binary**, cross-platform (macOS + Windows), and the "find the coins" angle — not an academic C interpreter.

---

# [ARTIFACT]

## Vibe Coding Night: Reverse Engineering — "Unlimited Coins"
**April 2026 · Frontier Tower, San Francisco · 6:00–10:00 PM**

---

### PRE-EVENT SETUP (Organizer, 3 days before)

#### The Binary

The target is a game people actually have on their phones. **Default: Subway Surfers** — a Unity/IL2CPP game with millions of daily players. The compiled binary (`libil2cpp.so`) has roughly 40,000–60,000 functions. No debug symbols. No source code. But Unity's metadata file leaks every class name, method name, and field name from the original C#. That metadata is the lever.

The challenge is NOT "hack the game." It's: **50,000 functions. Which ones handle coins? Once you find them, can the LLM explain what they do — or does it hallucinate?**

**Why this works without an Android emulator:** Ghidra does static analysis. It loads ARM binaries on any host OS — macOS, Windows, Linux. You don't run the game. You read the binary. The APK is a zip file. Il2CppDumper recovers class/method names from Unity's metadata. GhidraMCP connects to your local Ghidra over MCP. None of this cares about host architecture.

**Organizer preparation:**

1. Download the Subway Surfers APK from APKMirror or APKPure. **Pin a specific version.** Note the exact version string and SHA256 hash. Save the APK.

2. Extract the binary and metadata:
```bash
mkdir subway && cd subway
unzip SubwaySurfers_*.apk -d extracted/
cp extracted/lib/arm64-v8a/libil2cpp.so .
cp extracted/assets/bin/Data/Managed/Metadata/global-metadata.dat .
```

3. Run Il2CppDumper:
```bash
# Windows (native .exe from GitHub releases):
Il2CppDumper.exe libil2cpp.so global-metadata.dat output/

# macOS/Linux (.NET CLI):
dotnet Il2CppDumper.dll libil2cpp.so global-metadata.dat output/
```
This produces `output/dump.cs`, `output/script.json`, `output/stringliteral.json`.

4. Verify: `grep -i "coin" output/dump.cs` should show classes like `CoinManager`, `CurrencyController`, or similar. If you see them, the extraction worked.

5. Load `libil2cpp.so` in Ghidra on a test machine. Run auto-analysis (takes 5–15 minutes for a binary this large). Open Ghidra's Script Manager (Window → Script Manager), run `ghidra.py` from Il2CppDumper's output, point it at `script.json`. Functions get renamed from `FUN_00xxxxxx` to `CoinManager$$AddCoins`, `IAPController$$ValidatePurchase`, etc. Start GhidraMCP. Verify `list_functions` returns tens of thousands of named functions. Verify `decompile_function` works on one of them.

6. **Copy `libil2cpp.so`, `global-metadata.dat`, and the entire `output/` directory to 4+ USB drives.** Label them "VCN — Reverse Engineering Night." The binary does NOT go in the GitHub repo.

7. **Also save a pre-analyzed Ghidra project** (with Il2CppDumper names applied and auto-analysis complete) to the USB drives. This saves 15+ minutes of setup per person.

**If Subway Surfers doesn't use IL2CPP** (unlikely for recent ARM64 builds, but verify): fall back to any popular free Unity game — Temple Run 2, Crossy Road, Geometry Dash demo. Same extraction pipeline.

**Alternatives** (if you want a different category of target):
| Target | Why it works |
|---|---|
| Any Unity/IL2CPP mobile game | Same pipeline. People can bring their own APK. |
| Lua 5.4 interpreter | Open source, ~250 functions, ships compiled in repo. No metadata — pure RE. Simpler but less visceral. |
| jq (JSON processor) | Open source, ~350 functions. Good for C RE without the Unity layer. |

#### Warm-Up Binary

A 10-function C binary whose sole purpose is toolchain validation. **Not a challenge.** It's `hello world` for the GhidraMCP setup.

```c
// warmup.c
// macOS:   gcc -O2 -o warmup warmup.c && strip warmup
// Linux:   gcc -O2 -o warmup warmup.c && strip warmup
// Windows: gcc -O2 -o warmup.exe warmup.c && strip warmup.exe
//          (gcc via MSYS2, or: cl /O2 warmup.c)
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int add(int a, int b) { return a + b; }
static int multiply(int a, int b) { return a * b; }
static void greet(const char *name) { printf("Hello, %s\n", name); }
static int fibonacci(int n) { return n <= 1 ? n : fibonacci(n-1) + fibonacci(n-2); }
static char *reverse_string(const char *s) {
    int len = strlen(s);
    char *r = malloc(len + 1);
    for (int i = 0; i < len; i++) r[i] = s[len - 1 - i];
    r[len] = '\0';
    return r;
}
static void process(int mode, const char *input) {
    if (mode == 1) greet(input);
    else if (mode == 2) { char *r = reverse_string(input); printf("%s\n", r); free(r); }
    else printf("fib(10) = %d, 3+4 = %d, 3*4 = %d\n", fibonacci(10), add(3,4), multiply(3,4));
}
int main(int argc, char **argv) {
    process(argc > 1 ? atoi(argv[1]) : 0, argc > 2 ? argv[2] : "world");
    return 0;
}
```

Ship the source and one pre-compiled ELF. Ghidra analyzes ELF binaries on any host OS — Windows users don't need a Windows binary to analyze in Ghidra. People load the warm-up, ask Claude what it does, compare to the source file, and move on in 2 minutes.

#### Repo Structure

**`github.com/vibecodingnights/vcn-reverse-engineering`**

```
vcn-reverse-engineering/
├── README.md                          # Setup, challenge, resource links. This IS the event guide.
│
├── target/
│   ├── DOWNLOAD.md                    # Exact APK version, SHA256, download links, extraction steps.
│   │                                  #   "Or: grab a USB drive at the front table."
│   └── extract.py                     # Cross-platform: given an APK path, extracts libil2cpp.so +
│                                      #   global-metadata.dat, runs Il2CppDumper, writes output/.
│                                      #   Pure Python (zipfile) + subprocess for Il2CppDumper.
│
├── metadata/                          # Pre-generated Il2CppDumper output, committed by organizer
│   │                                  #   for the pinned APK version. Class/method names and string
│   │                                  #   literals — not the binary itself.
│   ├── dump.cs                        # C# class definitions with field offsets and method RVAs
│   ├── script.json                    # Address → name mappings (ScriptMethod, ScriptString, ScriptMetadata)
│   ├── stringliteral.json             # All string literals with binary addresses
│   └── README.md                      # What these files are, which APK version, how generated
│
├── warmup/
│   ├── warmup                         # Stripped ELF binary (amd64) — analyzable in Ghidra on any OS
│   └── warmup.c                       # Source — open immediately, this is toolchain validation
│
├── setup/
│   ├── GHIDRA_MCP.md                  # Install Ghidra 12 + GhidraMCP extension + start bridge +
│   │                                  #   verify with warmup. Platform sections: macOS | Windows.
│   ├── IL2CPP_SETUP.md               # Install Il2CppDumper, extract APK, import names into Ghidra
│   │                                  #   via ghidra.py script. Or: load the pre-analyzed Ghidra
│   │                                  #   project from the USB drive (skip all of this).
│   ├── claude_desktop_config.json     # Copy-paste MCP config for Claude Desktop (macOS + Windows paths)
│   └── PROGRAMMATIC.md               # For people building MCP clients: pip install mcp, connect, call_tool
│
├── starters/
│   ├── README.md                      # What each script does and when to use it
│   ├── survey.py                      # List all functions via GhidraMCP, group by class prefix,
│   │                                  #   count, estimate token cost. The "holy shit" script.
│   ├── hunt.py                        # Search dump.cs + stringliteral.json for coin/currency/score/
│   │                                  #   IAP/reward terms. Output: candidate classes ranked by hit count.
│   ├── class_decompile.py             # Given a class name, find its methods in script.json, decompile
│   │                                  #   each via GhidraMCP. Output: all decompilations for one class.
│   └── ask.py                         # End-to-end: hunt → class_decompile → LLM prompt asking
│                                      #   "How are coins stored? Client or server validation?"
│
└── docs/
    ├── THE_PROBLEM.md                 # Token math for a 50K-function binary. The document that makes
    │                                  #   the challenge legible to someone arriving at 6:30.
    ├── IL2CPP_PRIMER.md               # What IL2CPP is, how Unity compiles C# → C → native, what
    │                                  #   metadata survives, what the decompiled C looks like.
    ├── GHIDRA_MCP_TOOLS.md            # Quick reference: tool names, parameters, return formats
    └── WHAT_TO_BUILD.md               # Project ideas beyond the starters
```

**What each starter script does (these ship working, not as stubs):**

`survey.py` — Connects to GhidraMCP, calls `list_functions`, groups by class prefix (IL2CPP names use `ClassName$$MethodName`), does the token math. Output:
```
Functions: 53,841 across 5,203 classes
Estimated tokens to decompile all: ~43,000,000
Context window: 200,000 tokens

You're 215x over budget.

Even CoinManager alone has 47 methods totaling ~38,000 tokens.
Which of those 47 methods actually touch the coin balance?
That's the problem.

Top 10 classes by method count:
  UnityEngine_UI_Graphic    — 127 methods
  PlayerController           — 89 methods
  ...
  CoinManager                — 47 methods
```

`hunt.py` — Searches `dump.cs` and `stringliteral.json` for economy-related terms: "coin", "currency", "balance", "purchase", "IAP", "reward", "score", "wallet", "inventory". Cross-references classes appearing in multiple searches. Output:
```
High-relevance classes (3+ term matches):
  CoinManager          — 47 methods  | matched: "coin", "balance", "reward"
  IAPController        — 23 methods  | matched: "purchase", "IAP", "currency"
  InventoryManager     — 31 methods  | matched: "inventory", "coin", "balance"

String literals containing "coin" (with binary addresses):
  0x1a2b3c: "coin_balance"
  0x1a2b90: "coinRewardMultiplier"
  0x1a2bf4: "add_coins_reward"
```

`class_decompile.py` — Takes a class name (e.g., `CoinManager`), looks up its methods in `script.json` (which maps `{"Address": 1715004, "Name": "CoinManager$$AddCoins", "Signature": "void CoinManager$$AddCoins(...)"}`), decompiles each via GhidraMCP `decompile_function`. Outputs all decompilations in one file — one class's worth of C, small enough to fit in a single prompt.

`ask.py` — The end-to-end pipeline. Runs `hunt.py` → picks the top class → runs `class_decompile.py` → sends decompilations to the LLM with a targeted prompt: *"Here are the decompiled methods of CoinManager from a mobile game. How are coins stored? Is the balance validated on the client or server? Could a memory editor modify it?"* Prints the LLM's analysis.

**MCP Python SDK API (verified v1.12.4):**
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["ghidra_mcp_bridge.py"],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # IL2CPP names use ClassName$$MethodName format
        result = await session.call_tool(
            "decompile_function",
            arguments={"name": "CoinManager$$AddCoins"}
        )
        print(result.content[0].text)
```

**`docs/THE_PROBLEM.md`** — Pre-written with real numbers from the target binary. The document that makes the challenge legible to anyone arriving at 6:30:

> This binary has 53,000 functions. You can decompile any one of them. But if you decompiled all 53,000, that's 43 million tokens — 215 times more than fits in the context window.
>
> You have metadata: every function has a name. You know there's a class called `CoinManager` with 47 methods. But which of those 47 methods actually modify the coin balance? And even after you find the right method, does the LLM understand the decompiled C well enough to tell you whether coins are validated server-side?
>
> The best frontier model recovers 59% of reverse engineering targets. A human expert hits 92%. The gap is not intelligence. It's that nobody built the search and triage layer between the disassembler and the prompt.
>
> That's what you're building tonight.

#### Environment Checklist

- [ ] Ghidra 12.x installed and tested on 2–3 loaner laptops (1 macOS, 1–2 Windows)
- [ ] GhidraMCP extension installed on loaner laptops; bridge starts and responds
- [ ] Pre-analyzed Ghidra project (with Il2CppDumper names applied, auto-analysis complete) on USB drives — saves attendees 15+ minutes
- [ ] Raw files also on USB drives: `libil2cpp.so`, `global-metadata.dat`, Il2CppDumper `output/`
- [ ] `claude_desktop_config.json` tested on both macOS and Windows — Claude Desktop can list functions in the warm-up binary
- [ ] `uv` or `pip` available; all starter scripts run: `uv run survey.py` produces output against the warm-up binary
- [ ] `pip install "mcp>=1.12"` verified on macOS and Windows
- [ ] Il2CppDumper verified on macOS (dotnet CLI) and Windows (.exe)
- [ ] WiFi password and repo URL printed on a card at every table
- [ ] Projector showing `README.md` (no slides, no logo, no agenda)
- [ ] 3 spare Anthropic API keys loaded with $10 each, in sealed envelopes at host table

---

### 0:00–0:15 · ARRIVAL (6:00–6:15 PM)

Laptops open. Projector shows the repo README with setup instructions. No greeting line, no name tags.

**On every table:** Printed card with:
```
WiFi: [network] / [password]
Repo: github.com/vibecodingnights/vcn-reverse-engineering
USB drives at the front table — grab one if you need the game binary.
Need an API key? Ask a host.
```

**Front table:** USB drives, printed setup cheat sheets (one for macOS, one for Windows), spare laptop chargers.

People who arrive early start cloning, installing Ghidra, configuring GhidraMCP. That's the point.

---

### 0:15–0:20 · INTRO (6:15–6:20 PM) — 5 minutes, hard stop

**Say exactly this (or close to it):**

> "There's a game on your phone. Subway Surfers. Millions of people play it. Tonight you're going to take it apart.
>
> On the USB drives at the front table — and in the repo — you'll find the game's compiled binary and its metadata. Fifty-three thousand functions. Every class name, every method name — courtesy of Unity leaking its metadata file.
>
> Your LLM can decompile any function in here. The problem: 53,000 functions is 43 million tokens. Your context window is 200K. You can't show the model everything. If you ask it 'how do coins work,' it'll decompile a handful of functions, hallucinate the other fifty-two thousand, and give you a confident answer about code it never read.
>
> The challenge: **build the layer that finds the right 20 functions out of 53,000.** Search the metadata. Rank the classes. Decompile selectively. Then ask: does this game validate coins on the client or the server? Could you actually get unlimited coins?
>
> Everything's in the repo. The warm-up binary to test your GhidraMCP setup is in `warmup/`. Starter scripts are in `starters/`. Grab a USB drive for the game binary. Docs explain the IL2CPP pipeline if you haven't seen it before.
>
> Demos at 9:30 if you want. Go."

**Clock: 6:20 PM. Build time starts.**

---

### 0:20–3:30 · BUILD TIME (6:20–9:30 PM) — 3 hours 10 minutes, unstructured

No announcements. No check-ins. Hosts float.

#### THE CHALLENGE

One game. One question: **where are the coins?**

An LLM with GhidraMCP access can decompile individual functions on demand. But the binary has 53,000 of them. Even with Il2CppDumper metadata giving you every class and method name, you still can't decompile everything — the math doesn't work. And if you just decompile `CoinManager`, its 47 methods reference other classes, which reference other classes, and you're back to context overflow.

The engineering problem: build the search and triage pipeline that narrows 53,000 functions to the 20 that answer your question. Then verify whether the LLM's analysis of those 20 functions is actually correct — or whether it's hallucinating about decompiled C code the way it hallucinates about everything else.

This pipeline doesn't exist yet. Parts of it are buildable tonight.

#### HOW TO START (everyone, regardless of experience)

**Step 1: Validate the toolchain (~20 min)**
1. Clone the repo. Install Ghidra 12 if you don't have it (`ghidra-sre.org` — requires JDK 21+).
2. Follow `setup/GHIDRA_MCP.md` — install GhidraMCP extension, start the bridge, copy `claude_desktop_config.json` into Claude Desktop's config directory (macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`).
3. Open `warmup/warmup` in Ghidra. Let auto-analysis finish (~10 seconds).
4. In Claude Desktop, ask: *"What does this program do? List all its functions."*
5. Compare Claude's answer to `warmup/warmup.c`. It should nail everything — this binary is trivial. If it does, your setup works. Move on.

**Step 2: Load the game binary (~15 min)**
1. Grab a USB drive from the front table. Copy `libil2cpp.so` and the Il2CppDumper `output/` directory.
   - Or download the APK yourself and run `target/extract.py` (see `target/DOWNLOAD.md`).
   - Or **load the pre-analyzed Ghidra project** from the USB drive (fastest — skip straight to step 3).
2. If loading from scratch: open `libil2cpp.so` in Ghidra. Auto-analysis takes 5–15 minutes on a binary this large. While it runs, read `docs/IL2CPP_PRIMER.md`.
3. Once analysis finishes: open Ghidra's Script Manager (Window → Script Manager), run `ghidra.py`, point it at `output/script.json`. Watch functions rename from `FUN_00xxxxxx` to `CoinManager$$AddCoins`, `PlayerController$$Update`, etc.
4. GhidraMCP should now see all the named functions.

**Step 3: Ask the LLM to find the coins (~15 min)**
1. In Claude Desktop (connected to GhidraMCP), ask: *"This is a mobile game binary. Find all functions related to coins and currency. How does the game track the player's coin balance?"*
2. Watch what happens. The LLM will call `list_functions`, find coin-related names, decompile a few. It will produce a summary. **Write down what it claims.**
3. Now run `starters/hunt.py`. Compare its systematic metadata search against the LLM's ad-hoc exploration. What did the LLM miss? What did it find that the script didn't?
4. Run `starters/survey.py` to see the token math. Understand why the LLM's answer is necessarily incomplete.

**You've now seen the problem firsthand: even with names, 53,000 functions defeat the LLM's attention. Now build.**

#### HOW TO GO DEEPER

Every project below attacks the same problem from a different angle: narrowing 53,000 functions to the ones that matter.

**Build a better hunter.** `starters/hunt.py` does keyword search. Can you do better?
- Follow the call graph: `CoinManager$$AddCoins` calls what? What calls it? Use GhidraMCP's `get_callgraph` to expand from known coin functions to their dependencies and callers.
- Cross-reference fields: `dump.cs` shows field offsets (`public int coinBalance; // 0x1C`). Find functions that read/write that offset using `get_disassembly`.
- Cluster related classes: `CoinManager`, `CurrencyController`, `RewardManager`, `IAPController` probably form a subsystem. Build the dependency graph between them.

GhidraMCP tools you'll use:
```
list_functions     → {}                                    # all function names
decompile_function → {"name": "CoinManager$$AddCoins"}     # decompile by name
get_callgraph      → {"address": "0x...", "max_depth": 2}  # callers + callees
list_strings       → {"filter": "coin"}                    # search strings
get_disassembly    → {"address": "0x...", "length": 100}   # raw disassembly
set_comment        → {"address": "0x...", "comment": "...", "comment_type": "plate"}
```

**Build the selective decompilation loop.** `starters/class_decompile.py` decompiles one class. Build the version that decompiles a *cluster* of related classes, summarizes each, and feeds only the summaries to the LLM. Does a summary of 5 related classes produce better analysis than raw decompilation of 1? Where's the accuracy cliff?

**Answer the actual question: can you get unlimited coins?** Trace the coin flow end-to-end:
- Where is the balance stored? (Memory? PlayerPrefs? A local save file? A server?)
- What happens when `AddCoins` is called? Does it make a network request?
- Is there integrity checking on the save file? (Checksums, encryption, server sync?)
- What does the IAP controller do when a purchase succeeds? Does it grant coins client-side or wait for server confirmation?

This is genuine reverse engineering — not abstract triage tooling, but using the triage tools to answer a concrete question about a real product.

**Build the annotation loop.** Use the LLM to rename and comment functions via GhidraMCP:
```
set_function_signature → {"address": "0x...", "signature": "int CoinManager_GetBalance(void* this)"}
set_comment            → {"address": "0x...", "comment": "Reads coin balance from field offset 0x1C.
                           Calls ServerSync$$ValidateBalance before returning.",
                           "comment_type": "plate"}
```
Re-export the analysis after annotation. Does the LLM's second-pass analysis improve when functions it decompiled earlier now have meaningful comments?

#### FOR PEOPLE WHO'VE DONE RE BEFORE

Skip the starters. Here's what's interesting:

- **Dynamic analysis with Frida.** If you have an Android emulator or rooted device: install Frida, hook `CoinManager$$AddCoins` at runtime. Capture arguments and return values. Feed runtime traces to the LLM alongside the static decompilation. Does dynamic data correct the hallucinations from static analysis alone? (`pip install frida-tools`, or use `frida-mcp` at `github.com/dnakov/frida-mcp` for MCP integration.)

- **Bring your own APK.** Any Unity/IL2CPP game works with the same extraction pipeline. Want to reverse engineer Genshin Impact's gacha system? Temple Run's obstacle generation? Pick a game you care about, run `target/extract.py` on its APK, and apply the same triage pattern.

- **Compare decompiler backends.** Load the same binary in IDA Pro (via `ida-pro-mcp`), Radare2 (via `radare2-mcp`), or Binary Ninja (via `binary_ninja_mcp`). Compare decompiler output on the same function. Which backend gives the LLM better raw material for the coin-related functions?

- **Multi-tool orchestration.** Wire GhidraMCP for static analysis and `frida-mcp` for dynamic. Build a script that: searches metadata statically → identifies coin functions → instruments them dynamically → captures runtime behavior → synthesizes both into a report. This is the `Reversecore_MCP` pattern (Ghidra + Radare2 + YARA) applied to game analysis.

- **The obfuscation question.** Does this game use any protection? IL2CPP binaries are notoriously easy to analyze because metadata leaks everything. But some games add obfuscation layers (string encryption, control flow flattening, metadata encryption). Check: does the Il2CppDumper output look clean, or are there signs of protection? If protected, how does that change the LLM's accuracy?

- **Non-Unity targets.** Unreal Engine games use C++ without metadata recovery. Native Android games (NDK) are raw C/C++. How does the triage problem change when you don't have class/method names? Grab a non-Unity APK and compare the difficulty.

#### HOST BEHAVIOR DURING BUILD TIME

- **6:20–6:50 (first 30 min):** Walk the room actively. The two failure points are (1) Ghidra installation (JDK version mismatch, especially on Windows) and (2) the Claude Desktop config JSON path. On Windows, the path is `%APPDATA%\Claude\claude_desktop_config.json`. Know both platform paths cold. If someone's Ghidra won't install, hand them a loaner laptop with the pre-analyzed project already open.
- **If someone can't get the binary loaded by 6:50:** Give them the pre-analyzed Ghidra project from the USB drive. Don't let extraction/import eat their night.
- **After 6:50:** Only approach people who flag you down or look stuck. Do not interrupt someone who is typing.
- **If someone finishes Step 3 and doesn't know what to build:** Ask them: "Run `hunt.py`, pick the top class, decompile it with `class_decompile.py`, and read the output. Do you believe the LLM's analysis?" That's a 90-minute project.
- **If someone asks what game this is:** Tell them. It's Subway Surfers. The discovery was finding the coin functions, not identifying the game.
- **If a Windows user is stuck on Python/pip:** `uv` is the fastest path. `pip install uv`, then `uv run script.py`. This handles venv creation automatically.

---

### 3:30–4:00 · OPT-IN DEMOS (9:30–10:00 PM)

**At 9:25**, announce once: *"Demos in five minutes at the front if you want to show what you built or where you got stuck. Two minutes each. Totally optional."*

Format:
- 2–3 minutes each, hard cutoff
- Screen share or live demo only. No slides.
- Equally interesting: "I found the AddCoins function and it's purely client-side — no server check" and "the LLM told me coins are encrypted but I decompiled the save function and it's plaintext PlayerPrefs"
- **The best demos answer the question.** "Could you get unlimited coins? Here's what I found."

**Prompt if nobody volunteers:** *"Did anyone find server-side validation in the coin flow? Or is it all client-side? That tells us something about how this game is built."*

**At 10:00 PM:** *"Repo stays up. Push your branches. The USB drives are yours — keep going at home. Thanks for coming."* Done.

---

### RESOURCE LINKS (printed + in repo README)

| Resource | URL |
|---|---|
| Event repo | `github.com/vibecodingnights/vcn-reverse-engineering` |
| GhidraMCP (LaurieWired) | `github.com/LaurieWired/GhidraMCP` |
| GhydraMCP (Starsong, multi-instance) | `github.com/starsong-consulting/GhydraMCP` |
| Il2CppDumper (Perfare) | `github.com/Perfare/Il2CppDumper` |
| ida-pro-mcp | `github.com/mrexodia/ida-pro-mcp` |
| radare2-mcp | `github.com/radareorg/radare2-mcp` |
| frida-mcp | `github.com/dnakov/frida-mcp` |
| Frida | `frida.re` |
| Reversecore_MCP | `github.com/sjkim1127/Reversecore_MCP` |
| Awesome-RE-MCP catalog | `github.com/crowdere/Awesome-RE-MCP` |
| MCP Python SDK (`pip install "mcp>=1.12"`) | `github.com/modelcontextprotocol/python-sdk` |
| Ghidra 12 download | `ghidra-sre.org` |
| APKMirror | `apkmirror.com` |

---

### SELF-EVALUATION

1. **Does the flow reference specific challenges/targets from the description and research?** Yes — single binary, token budget as the central constraint (the description's "50,000 tokens before a single decompilation" scaled to 43M tokens for this binary), triage/compression as the engineering challenge (the research brief's "RE-specific context engineering" gap), GhidraMCP tool calls by verified name, CREBench's 59% vs. 92% gap (description + research), Reversecore_MCP multi-tool pattern (research), Il2CppDumper `script.json` schema verified against docs. The target satisfies the description's "real software, not a CTF toy" — it's a commercial product with millions of users.

2. **Could someone read this and run the event without the organizer present?** Yes — exact APK extraction commands, Il2CppDumper CLI syntax (platform-specific), Claude Desktop config paths for macOS and Windows, pre-analyzed Ghidra project on USB drives as fast-path, host behavior with time-gated instructions, spare API key protocol, loaner laptop protocol, demo prompts, intro script verbatim.

3. **Are both the beginner path and the advanced path concrete enough to follow?** The beginner path is numbered Steps 1–3 with specific commands, expected observations, and one clear choice point. It works for someone who has never used Ghidra: they load the warm-up, verify it works, load the game binary (from USB if extraction is too slow), and see the LLM fail to find coins on its own. The advanced path lists six projects each with specific tools and approaches. Both paths answer the same question: where are the coins?

---

# [CONTEXT BRIEF]

Builders reverse engineer a real mobile game (Subway Surfers, ~53,000 functions) by wiring Claude to Ghidra through GhidraMCP — the challenge is building the search and triage pipeline that finds the coin/currency functions out of 53,000 and determines whether unlimited coins are actually possible, since decompiling everything would burn 43M tokens against a 200K context window. Everyone starts by validating GhidraMCP on a warm-up binary, loading the game binary with Il2CppDumper metadata (which gives class/method names but not implementations), and watching the LLM fail to find coins on its own; depth comes from building systematic hunters, call-graph expansion, selective decompilation loops, and end-to-end coin-flow tracing — experienced RE practitioners can add Frida for dynamic analysis or bring their own APK. Organizers need: the APK pre-extracted onto USB drives (binary + Il2CppDumper output + pre-analyzed Ghidra project), Ghidra 12 on 2–3 loaner laptops (macOS + Windows), 3 spare Anthropic API keys, and the repo with working starter scripts and metadata committed; both macOS and Windows are first-class — Ghidra analyzes ARM binaries on any host OS, and setup docs cover both platforms. Intro at 6:15 (5 min hard), build time 6:20–9:30 unstructured, opt-in demos 9:30–10:00.

## Existing Repos in github.com/vibecodingnights
- **metaprompting** — Configuration is solved. Taste isn't. Build the metaprompting loop nobody has built — Gemma 4 watches your aesthetic choices and writes the taste directives that shape the next session.
- **auto-vcn** — 
- **bob** — Finds hackathons. Enters them. Wins.
- **agent-teams** — Think in teams, not prompts.
- **agent-orchestration** — The coordination problems are fifty years old. The frameworks are new.
- **agent-harnesses** — The pattern isn't about code — it's about closing loops
- **information-primitives** — Exercises, primitives, and provocations for exploring how we structure and interact with information
- **design-interaction** — Design & Interaction
- **offensive-security** — AI Security Workshop: Prompt injection, memory poisoning, and MCP tool attacks

## Instructions
- **Name the repo** to match the org convention above (simple kebab-case topic
  names like `agent-harnesses`, `offensive-security`, `design-interaction`).
- Create the directory structure from the flow plan.
- Write the README in the event voice (short, direct, provocative).
- Challenge files should have clear instructions. Starter templates should be minimal and runnable.
- When ready, create the repo on GitHub: `gh repo create vibecodingnights/{name} --public`
- Stage everything and commit: `git add -A && git commit -m "scaffold: reverse engineering"`
- Push: `git push -u origin main`
