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

This metadata exists because the IL2CPP runtime needs it for reflection, serialization, and garbage collection. Unity could encrypt it (some games do), but most don't.

## What Il2CppDumper Does

Il2CppDumper reads both files and correlates them:

- Maps binary addresses to method names: `0x1a3400 → CoinManager$$AddCoins`
- Reconstructs C# class definitions with field offsets
- Extracts all string literals with their binary addresses

### Output files

**`dump.cs`** — Reconstructed C# class definitions:
```csharp
public class CoinManager : MonoBehaviour
{
    public int coinBalance;  // 0x1C
    public float multiplier; // 0x20

    // RVA: 0x1A3400
    public void AddCoins(int amount) { }

    // RVA: 0x1A3480
    public int GetBalance() { }
}
```

No method bodies — just declarations with addresses.

**`script.json`** — Machine-readable mappings:
```json
{
  "ScriptMethod": [
    {
      "Address": 1717248,
      "Name": "CoinManager$$AddCoins",
      "Signature": "void CoinManager$$AddCoins(CoinManager* this, int32_t amount, MethodInfo* method)"
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
void CoinManager$$AddCoins(long param_1, int param_2, long param_3) {
    if (*(long *)(param_1 + 0x10) == 0) {
        il2cpp_runtime_class_init(CoinManager__TypeInfo);
    }
    int iVar1 = *(int *)(param_1 + 0x1c);  // this->coinBalance (field at offset 0x1C)
    iVar1 = iVar1 + param_2;                // coinBalance + amount
    *(int *)(param_1 + 0x1c) = iVar1;       // this->coinBalance = result
    return;
}
```

Key patterns:
- `param_1` is `this` (the object pointer)
- Field accesses are `*(type *)(param_1 + offset)` — match offsets to `dump.cs`
- `il2cpp_runtime_class_init` initializes static class data on first access
- `il2cpp_object_new` allocates a new managed object
- Virtual calls go through method tables: `(*(code **)(*param_1 + vtable_offset))(param_1, ...)`

## Why This Is a Lever

Without metadata, Ghidra shows you 53,000 functions named `FUN_001a3400`. With metadata, that function is `CoinManager$$AddCoins`. You know its class, you know the field offsets from `dump.cs`, you can search for related classes.

The metadata doesn't tell you what the function *does* — that's what decompilation is for. But it tells you where to look. That's the difference between reading 53,000 functions and reading 20.
