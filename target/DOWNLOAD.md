# Downloading the Target Binary

The target binary does NOT ship in this repo. Get it from a USB drive at the event or download the APK yourself.

## Option 1: USB Drive (fastest)

Grab a USB drive from the front table. It contains:
- `libil2cpp.so` — the compiled game binary (ARM64)
- `global-metadata.dat` — Unity's metadata file
- `output/` — pre-generated Il2CppDumper output (dump.cs, script.json, stringliteral.json)
- A pre-analyzed Ghidra project with names applied and auto-analysis complete

The pre-analyzed Ghidra project saves you 15+ minutes. Open it directly in Ghidra.

## Option 2: Download the APK

**Target: Subway Surfers**

1. Go to [APKMirror](https://apkmirror.com) or [APKPure](https://apkpure.com).
2. Search for "Subway Surfers".
3. Download the **arm64-v8a** variant (`.apk`, not `.apks` or `.xapk`).
4. Verify the SHA256 hash matches the one posted at the event.

## Option 3: extract.py (automated)

Once you have the APK:

```bash
python target/extract.py path/to/SubwaySurfers.apk
```

This extracts `libil2cpp.so` and `global-metadata.dat`, then runs Il2CppDumper if it's installed.

## After Extraction

You should have:
```
libil2cpp.so          — the binary to analyze in Ghidra
global-metadata.dat   — Unity metadata (needed by Il2CppDumper)
output/
  dump.cs             — C# class definitions with offsets
  script.json         — address-to-name mappings for Ghidra
  stringliteral.json  — string literals with addresses
```

Verify: `grep -i "coin" output/dump.cs` should show coin-related classes.

Next: Follow [`setup/IL2CPP_SETUP.md`](../setup/IL2CPP_SETUP.md) to import names into Ghidra.
