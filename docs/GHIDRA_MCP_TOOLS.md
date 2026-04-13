# GhidraMCP Tool Reference

Quick reference for GhidraMCP tools available through MCP.

## Core Tools

### `list_functions`

List all function names in the current binary.

```python
result = await session.call_tool("list_functions", arguments={})
```

Returns one function name per line. For IL2CPP binaries with names applied, these are `ClassName$$MethodName` format. Unnamed functions show as `FUN_00xxxxxx`.

**Warning:** On a 53,000-function binary, this returns a lot of data. Consider filtering client-side or using `list_strings` to narrow your search first.

### `decompile_function`

Decompile a function by name.

```python
result = await session.call_tool(
    "decompile_function",
    arguments={"name": "CoinManager$$AddCoins"}
)
```

Returns decompiled C code. For IL2CPP binaries, the code reflects the C++ transpilation — field accesses are pointer arithmetic, virtual calls go through vtables.

### `get_callgraph`

Get the callers and callees of a function.

```python
result = await session.call_tool(
    "get_callgraph",
    arguments={"address": "0x1a3400", "max_depth": 2}
)
```

Returns a tree of function calls — who calls this function, and what does it call. Essential for tracing coin flow through multiple classes.

### `list_strings`

Search for string literals in the binary.

```python
result = await session.call_tool(
    "list_strings",
    arguments={"filter": "coin"}
)
```

Returns matching strings with their addresses. Cross-reference with `stringliteral.json` for more complete results (Il2CppDumper catches strings that Ghidra's string analysis might miss).

### `get_disassembly`

Get raw assembly for an address range.

```python
result = await session.call_tool(
    "get_disassembly",
    arguments={"address": "0x1a3400", "length": 100}
)
```

Returns ARM64 (or x86) assembly. Useful for verifying decompiler output or checking field access patterns that the decompiler may have gotten wrong.

## Annotation Tools

### `set_comment`

Add a comment to an address in Ghidra.

```python
result = await session.call_tool(
    "set_comment",
    arguments={
        "address": "0x1a3400",
        "comment": "Adds coins to player balance. No server validation.",
        "comment_type": "plate"  # plate, pre, post, eol, repeatable
    }
)
```

Comment types:
- `plate` — appears above the function (best for function-level summaries)
- `pre` — appears before a specific line
- `post` — appears after a specific line
- `eol` — end-of-line comment
- `repeatable` — shows up at every reference to this address

### `set_function_signature`

Rename a function and set its type signature.

```python
result = await session.call_tool(
    "set_function_signature",
    arguments={
        "address": "0x1a3400",
        "signature": "int CoinManager_GetBalance(void* this)"
    }
)
```

This changes how the function appears in Ghidra and in subsequent decompilations. Useful for the annotation loop — rename a function, then re-decompile its callers to see improved output.

## Patterns

### Trace a class

```python
# 1. Find methods for a class
functions = await session.call_tool("list_functions", arguments={})
class_methods = [f for f in functions.content[0].text.split("\n")
                 if f.startswith("CoinManager$$")]

# 2. Decompile each
for method in class_methods:
    result = await session.call_tool("decompile_function", arguments={"name": method})
    print(f"--- {method} ---")
    print(result.content[0].text)
```

### Follow the call graph

```python
# 1. Decompile the entry point
result = await session.call_tool("decompile_function",
    arguments={"name": "CoinManager$$AddCoins"})

# 2. Get its callees
callgraph = await session.call_tool("get_callgraph",
    arguments={"address": "0x1a3400", "max_depth": 1})

# 3. Decompile each callee
# Parse callgraph output for function names, decompile each
```

### Annotate and re-decompile

```python
# 1. Analyze a function
result = await session.call_tool("decompile_function",
    arguments={"name": "CoinManager$$AddCoins"})

# 2. Add your understanding as a comment
await session.call_tool("set_comment", arguments={
    "address": "0x1a3400",
    "comment": "Adds coins. Writes to field 0x1C (coinBalance). No server call.",
    "comment_type": "plate"
})

# 3. Decompile a caller — your comment now appears in context
result = await session.call_tool("decompile_function",
    arguments={"name": "RewardManager$$GrantReward"})
```
