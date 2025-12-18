
## Changelog

### [1.1.0] - 2025-12-14
#### Features
*   **GPT-5 Support**: Full compatibility with OpenAI's `gpt-5.1` and `gpt-5.2-pro` models using the new `client.responses.create` API.
*   **True Streaming**: Implemented real-time token-by-token streaming for GPT-5 models, replacing the previous buffering behavior.
*   **Thinking Status**: Added visual "🤔 Thinking..." status for models with extended reasoning phases (like `gpt-5.2-pro`). The bot now indicates when it is reasoning, even if the API is silent.
*   **Robust Content Extraction**: Improved parsing logic to handle deeply nested response structures and object representations from the `Responses` API.
*   **Configurable Tool Support**: Added `.env` configuration for OpenAI tools:
    *   **Web Search**: `ENABLE_WEB_SEARCH`
    *   **File Search**: `ENABLE_FILE_SEARCH` (with `FILE_SEARCH_VECTOR_STORE_IDS`)
    *   **Code Interpreter**: `ENABLE_CODE_INTERPRETER`
    *   **Computer Use**: `ENABLE_COMPUTER_USE`
    *   **MCP**: Support for connecting to external Model Context Protocol servers via `ENABLE_MCP`.

### Technical Details
*   Updated `bot/openai_helper.py` to use `client.responses.create` with `stream=True`.
*   Implemented `stream_generator` to yield `StreamChunk` objects from `response.output_text.delta` and `response.in_progress` events.
*   Refactored `get_chat_response_stream` to handle the new `reasoning` delta type.
*   Bumped `openai` dependency to `>=1.58.1`.
