# Bundestag MCP

This is a simple [MCP](https://modelcontextprotocol.io/) server to chat with the German Bundestag via their [published protocols](https://dip.bundestag.de/).

## Install
* Clone and cd this repo

## Pip install dependencies
```sh
uv pip install -e .
```

Install into bundestag-mcp server for [Claude Desktop](https://claude.ai/download)

```json
# /Users/xxx/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
      "bundestag-mcp": {
          "command": "uv",
          "args": [
              "--directory",
              "/ABSOLUTE/PATH/TO/PARENT/FOLDER/bundestag-mcp/",
              "run",
              "server.py"
          ]
      }
  }
}
```


## Debug
```sh
npx @modelcontextprotocol/inspector uv --directory /Users/mdl/workspace/luebken/bundestag-mcp/ run server.py
```

## Test / Example

Prompt: Was wurde in der letzten Plenarsitzung im Bundestag diskutiert?

## Resources
*  https://dip.bundestag.de/%C3%BCber-dip/hilfe/api
*  https://search.dip.bundestag.de/api/v1/swagger-ui/
*  https://modelcontextprotocol.io/quickstart/server