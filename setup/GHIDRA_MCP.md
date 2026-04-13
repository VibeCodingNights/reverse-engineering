# Ghidra + GhidraMCP Setup

Get Ghidra talking to Claude through MCP.

## Install Ghidra 12

1. Download from [ghidra-sre.org](https://ghidra-sre.org).
2. Requires **JDK 21+**.
   - **macOS:** `brew install openjdk@21`
   - **Windows:** Download from [adoptium.net](https://adoptium.net). Add to PATH.
3. Extract the Ghidra archive. Run `ghidraRun` (macOS/Linux) or `ghidraRun.bat` (Windows).

### Troubleshooting JDK

If Ghidra won't start:
```bash
# Check your Java version
java -version

# macOS — point Ghidra at Homebrew's JDK
export JAVA_HOME=$(/usr/libexec/java_home -v 21)

# Windows — set JAVA_HOME in System Environment Variables
# JAVA_HOME = C:\Program Files\Eclipse Adoptium\jdk-21.x.x
```

## Install GhidraMCP

1. Clone or download [GhidraMCP](https://github.com/LaurieWired/GhidraMCP).
2. Build the extension:
   ```bash
   cd GhidraMCP
   gradle -PGHIDRA_INSTALL_DIR=/path/to/ghidra buildExtension
   ```
   The `.zip` extension file lands in `dist/`.
3. In Ghidra: **File > Install Extensions > Add** — select the `.zip`.
4. Restart Ghidra.

### Alternative: GhydraMCP (multi-instance support)

If you want multiple Ghidra instances or SSE transport:
```bash
pip install ghydramcp
```
See [github.com/starsong-consulting/GhydraMCP](https://github.com/starsong-consulting/GhydraMCP).

## Start the MCP Bridge

After installing the extension:

1. Open a binary in Ghidra (start with `warmup/warmup`).
2. Let auto-analysis complete.
3. The GhidraMCP bridge starts automatically with the extension. By default it listens on `localhost:8080`.

## Configure Claude Desktop

Copy `claude_desktop_config.json` from this directory to:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Restart Claude Desktop. You should see GhidraMCP tools available in the tool list.

## Verify

In Claude Desktop, ask:

> "List all functions in the current binary."

You should see the warmup binary's 10 functions: `main`, `process`, `greet`, `fibonacci`, `reverse_string`, `add`, `multiply`, `max_val`, `min_val`, `sum_to`.

If you see them, the setup works. Move on to the game binary.

## Verify (Programmatic)

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["-m", "ghidra_mcp"],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("list_functions", arguments={})
        print(result.content[0].text)
```

If this prints function names, you're good.
