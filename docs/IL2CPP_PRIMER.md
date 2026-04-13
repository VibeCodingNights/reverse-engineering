# IL2CPP Primer

What IL2CPP is, how Unity compiles C# to native code, and what survives in the binary.

## The Compilation Pipeline

```
C# source → IL bytecode → IL2CPP transpiler → C++ source → Clang/GCC → native binary
```

1. Game developers write C# in Unity.
2. Unity's C# compiler produces IL (Intermediate Language) bytecode — same as any .NET assembly.
3. **IL2CPP** transpiles that IL to C++ source code.
4. The platform's C++ compiler (Clang for iOS/Android, MSVC for Windows) compiles the C++ to a native binary.

The result: `libil2cpp.so` (Android), `GameAssembly.dll` (Windows), or a framework binary (iOS). This is a normal native binary — no bytecode, no JIT, no managed runtime.

## What Survives

### In the binary (`libil2cpp.so`)

- Machine code for every C# method (compiled through C++ intermediate)
- IL2CPP runtime calls: `il2cpp_runtime_class_init`, `il2cpp_object_new`, `il2cpp_array_new`, etc.
- Virtual method dispatch tables
- Static field storage
- **No symbol names** (stripped)

### In the metadata (`global-metadata.dat`)

Unity ships a metadata file alongside the binary. This file contains:

- **Every class name** from the original C#
- **Every method name** and its signature
- **Every field name** and its offset within the class
- **Every string literal** used in the C# source
- Type information, interface implementations, enum values

This metadata exists because the IL2CPP runtime needs it for reflection, serialization, and garbage collection. Unity could encrypt it (some games do) — see the "Metadata Encryption" section below.

## What Il2CppDumper Does

Il2CppDumper reads both files and correlates them:

- Maps binary addresses to method names: `0x1a3400 → SYBO_Subway_Coins_CoinManager$$Coin_OnCoinPickedUp`
- Reconstructs C# class definitions with field offsets
- Extracts all string literals with their binary addresses

### Output files

**`dump.cs`** — Reconstructed C# class definitions:
```csharp
// Namespace: SYBO.Subway.Coins
public class CoinManager : MonoBehaviour // IL2CPP name: SYBO_Subway_Coins_CoinManager
{
    public CoinStats coinStats;  // 0x18
    public CoinCurve coinCurve;  // 0x20

    // RVA: 0x1A3400
    public void Coin_OnCoinPickedUp(Coin coin) { }

    // RVA: 0x1A3480
    public void RewardCoin(Vector3 position) { }
}
```

No method bodies — just declarations with addresses.

**`script.json`** — Machine-readable mappings:
```json
{
  "ScriptMethod": [
    {
      "Address": 1717248,
      "Name": "SYBO_Subway_Coins_CoinManager$$Coin_OnCoinPickedUp",
      "Signature": "void SYBO_Subway_Coins_CoinManager$$Coin_OnCoinPickedUp(CoinManager* this, Coin* coin, MethodInfo* method)"
    }
  ]
}
```

The `$$` separator is an IL2CPP convention: `ClassName$$MethodName`.

**`stringliteral.json`** — String literals:
```json
[
  {"value": "coin_balance", "address": "0x1a2b3c"},
  {"value": "coinRewardMultiplier", "address": "0x1a2b90"}
]
```

## What the Decompiled C Looks Like

When Ghidra decompiles an IL2CPP function, you get C that reflects the transpiled C++, not the original C#:

```c
void SYBO_Subway_Coins_CoinManager$$Coin_OnCoinPickedUp
                (long param_1, long param_2, long param_3) {
    long lVar1;

    if (*(long *)(param_1 + 0x10) == 0) {
        il2cpp_runtime_class_init(SYBO_Subway_Coins_CoinManager__TypeInfo);
    }
    lVar1 = *(long *)(param_2 + 0x28);       // coin->coinValue
    if (lVar1 == 0) {
        il2cpp_raise_null_reference_exception();
    }
    lVar1 = *(long *)(param_1 + 0x18);       // this->coinStats (field at offset 0x18)
    if (lVar1 != 0) {
        SYBO_Subway_Coins_CoinStats$$AddPickedUpCoins(lVar1, 1, 0);
    }
    return;
}
```

Key patterns:
- `param_1` is `this` (the object pointer)
- `param_2` is the first argument (e.g., a `Coin` object)
- Field accesses are `*(type *)(param_1 + offset)` -- match offsets to `dump.cs`
- `il2cpp_runtime_class_init` initializes static class data on first access
- `il2cpp_object_new` allocates a new managed object
- Virtual calls go through method tables: `(*(code **)(*param_1 + vtable_offset))(param_1, ...)`

## Why This Is a Lever

Without metadata, Ghidra shows you 118,813 functions named `FUN_001a3400`. With metadata, that function is `SYBO_Subway_Coins_CoinManager$$Coin_OnCoinPickedUp`. You know its class, you know the field offsets from `dump.cs`, you can search for related classes.

The metadata doesn't tell you what the function *does* -- that's what decompilation is for. But it tells you where to look. That's the difference between reading 118,813 functions and reading 20.

## Metadata Encryption

Some games encrypt `global-metadata.dat` to hinder analysis. Subway Surfers (6.04.0) uses a page-based XOR cipher with byte key `0x66`. The metadata file is divided into pages, and each page is XORed against the key byte.

Il2CppDumper expects plaintext metadata. If you feed it an encrypted `global-metadata.dat`, it will fail to parse the header. The script `target/decrypt_metadata.py` handles Subway Surfers' encryption scheme -- run it before Il2CppDumper:

```bash
python target/decrypt_metadata.py global-metadata.dat global-metadata-decrypted.dat
Il2CppDumper libil2cpp.so global-metadata-decrypted.dat output/
```

The metadata committed in `metadata/` has already been decrypted. If you're using the USB drive or the pre-generated files, you don't need to run the decryption step.

Other games may use different encryption schemes (AES, custom ciphers, metadata structure randomization). The XOR `0x66` pattern is specific to this version of Subway Surfers.
