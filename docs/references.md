# Technical references

Checked on 2026-09-02:

- [OpenAI Codex Projects](https://learn.chatgpt.com/docs/projects) — ChatGPT
  chats and Codex chats have separate surfaces; New chat can add an existing
  ChatGPT chat to a Codex chat.
- [OpenAI Codex Remote](https://learn.chatgpt.com/docs/remote-connections) —
  mobile control uses the connected host's files, tools, and permissions, and
  stops when that host is unavailable.
- [OpenAI API MCP tool filters](https://platform.openai.com/docs/api-reference/responses/create)
  — remote MCP tools can be filtered by read-only annotations.
- [Official MCP Python SDK](https://py.sdk.modelcontextprotocol.io/) — current
  v2 server API and supported transports.
- [Official MCP Python SDK: tools](https://py.sdk.modelcontextprotocol.io/servers/tools/)
  — tool schemas, names, and `ToolAnnotations`; annotations are hints rather
  than enforcement.
- [MCP maintainers on tool annotations](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/)
  — risk vocabulary, trust limits, and why hard guarantees belong in the
  authorization or runtime layer.
