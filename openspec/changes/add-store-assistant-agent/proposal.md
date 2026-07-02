## Why

The project needs a small, demoable conversational agent that can reliably save and retrieve store contact information while enforcing validation, lookup authorization, persistence, and conversation wrap-up behavior. Creating this as an OpenSpec change keeps the behavioral contract clear before implementation.

## What Changes

- Add a Python-based conversational store assistant backed by an LLM framework.
- Allow users to save grocery or retail store records by collecting store name and US phone number.
- Validate phone numbers, reprompting without saving when the input is invalid.
- Persist store records in SQLite, upserting by normalized store name.
- Allow users to retrieve a store phone by name only after entering the configured passphrase.
- Support repeated save and retrieval operations in any order within one conversation.
- End conversations when the user is done or after 3 consecutive off-scope attempts.
- Generate and persist a concise conversation summary covering successful operations, failed attempts, and off-scope attempts.
- Provide a minimal Streamlit chat UI for local demonstration.
- Trace LLM calls and conversation activity to local SQLite tables for later inspection.
- Add automated tests covering core conversation behavior.

## Capabilities

### New Capabilities

- `store-assistant-agent`: Conversational agent behavior for saving, retrieving, validating, gating, tracing, summarizing, and demoing store information.

### Modified Capabilities

- None.

## Impact

- Adds a new Python application structure for agent logic, persistence, tracing, and UI.
- Adds SQLite schema and access code for stores, conversations, messages, summaries, and traces.
- Adds PydanticAI, Streamlit, OpenAI provider configuration, and pytest-based test dependencies.
- Requires `OPENAI_API_KEY` for live LLM usage and supports `STORE_LOOKUP_PASSPHRASE`, defaulting to `open-sesame`, for lookup authorization.
