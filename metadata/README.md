# Metadata

Pre-generated Il2CppDumper output for **Subway Surfers 6.04.0**.

The metadata was decrypted before dumping -- Subway Surfers encrypts `global-metadata.dat` with a page-based XOR cipher (key `0x66`). See `target/decrypt_metadata.py` and `docs/IL2CPP_PRIMER.md` for details.

These files contain class names, method names, field names, and string literals recovered from Unity's `global-metadata.dat`. They do NOT contain the binary itself or any decompiled code.

## Files

| File | Contents |
|---|---|
| `dump.cs` | C# class definitions with field offsets and method RVAs. Every class, every method, every field — but no implementations. |
| `script.json` | Address-to-name mappings. Feed this to Ghidra's `ghidra.py` script to rename all functions from `FUN_00xxxxxx` to `ClassName$$MethodName`. |
| `stringliteral.json` | All string literals embedded in the binary, with their addresses. Search this for "coin", "balance", "purchase", etc. |

## How Generated

```bash
# From Subway Surfers 6.04.0
# SHA256: 00e45db1a8cfb99cf71bad6e3f6f427fea349196f3813631e537e15b4e5c0088
# Metadata was decrypted first (XOR 0x66):
python target/decrypt_metadata.py global-metadata.dat global-metadata-decrypted.dat
Il2CppDumper libil2cpp.so global-metadata-decrypted.dat output/
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
