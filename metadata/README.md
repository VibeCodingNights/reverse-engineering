# Metadata

Pre-generated Il2CppDumper output for the pinned APK version.

These files contain class names, method names, field names, and string literals recovered from Unity's `global-metadata.dat`. They do NOT contain the binary itself or any decompiled code.

## Files

| File | Contents |
|---|---|
| `dump.cs` | C# class definitions with field offsets and method RVAs. Every class, every method, every field — but no implementations. |
| `script.json` | Address-to-name mappings. Feed this to Ghidra's `ghidra.py` script to rename all functions from `FUN_00xxxxxx` to `ClassName$$MethodName`. |
| `stringliteral.json` | All string literals embedded in the binary, with their addresses. Search this for "coin", "balance", "purchase", etc. |

## How Generated

```bash
# From the pinned APK version (see target/DOWNLOAD.md for version and hash)
Il2CppDumper libil2cpp.so global-metadata.dat output/
```

## Using These Files

**Without Ghidra:** `dump.cs` and `stringliteral.json` are searchable text. The starter scripts in `starters/` parse these directly.

```bash
grep -i "coin" dump.cs
python ../starters/hunt.py
```

**With Ghidra:** Import names via `script.json`:
1. Open `libil2cpp.so` in Ghidra
2. Window > Script Manager > run `ghidra.py`
3. Point at `script.json`

See [`setup/IL2CPP_SETUP.md`](../setup/IL2CPP_SETUP.md) for details.

## Note

These files will be committed by the event organizer after extracting from the pinned APK version. If you're setting up the event, see the organizer instructions in CLAUDE.md.
