# Il2CppDumper Setup

Recover class and method names from a Unity/IL2CPP binary.

## What This Does

Unity compiles C# to C++ via IL2CPP. The compiled binary (`libil2cpp.so`) has no debug symbols — but Unity ships a metadata file (`global-metadata.dat`) alongside it that contains every class name, method name, field name, and string literal from the original C#.

Il2CppDumper reads both files and produces:
- **`dump.cs`** — C# class definitions with field offsets and method addresses
- **`script.json`** — Address-to-name mappings for Ghidra import
- **`stringliteral.json`** — All string literals with binary addresses

## Install Il2CppDumper

### Windows (native)

1. Download the latest release from [github.com/Perfare/Il2CppDumper/releases](https://github.com/Perfare/Il2CppDumper/releases).
2. Extract. You get `Il2CppDumper.exe`.

### macOS / Linux (.NET CLI)

1. Install .NET SDK: `brew install dotnet` (macOS) or see [dotnet.microsoft.com](https://dotnet.microsoft.com).
2. Download the release `.zip` — you need `Il2CppDumper.dll`.

## Extract from APK

```bash
mkdir subway && cd subway
unzip SubwaySurfers_*.apk -d extracted/
cp extracted/lib/arm64-v8a/libil2cpp.so .
cp extracted/assets/bin/Data/Managed/Metadata/global-metadata.dat .
```

Or use `target/extract.py` which automates this.

## Run Il2CppDumper

```bash
# Windows:
Il2CppDumper.exe libil2cpp.so global-metadata.dat output/

# macOS/Linux:
dotnet Il2CppDumper.dll libil2cpp.so global-metadata.dat output/
```

### Verify

```bash
grep -i "coin" output/dump.cs
```

You should see classes like `SYBO_Subway_Coins_CoinManager`, `CurrencyExchangePopup`, or similar. If you see them, the extraction worked.

## Import Names into Ghidra

1. Open `libil2cpp.so` in Ghidra. Let auto-analysis finish (5–15 min for a large binary).
2. Open **Window > Script Manager**.
3. Run `ghidra.py` from the Il2CppDumper output directory.
4. When prompted, point it at `output/script.json`.
5. Functions rename from `FUN_00xxxxxx` to `SYBO_Subway_Coins_CoinManager$$Coin_OnCoinPickedUp`, `PlayerController$$Update`, etc.

## Skip All of This

If you grabbed a USB drive at the event, it has a **pre-analyzed Ghidra project** with Il2CppDumper names already applied and auto-analysis complete. Open it directly in Ghidra — no extraction, no import, no waiting.

The `metadata/` directory in this repo also has the pre-generated Il2CppDumper output files for the pinned APK version.
