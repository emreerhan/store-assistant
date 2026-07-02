## Context

This repository is currently a clean OpenSpec scaffold with no application code. The change introduces a small local demo application for a 30-minute walkthrough: a conversational LLM-based assistant that stores and retrieves store phone numbers, persists all important records, traces LLM activity, and terminates with a saved summary.

The agent must be conversational, but the safety-critical and correctness-critical behavior should be deterministic. The LLM will help classify user intent, extract simple slots, and generate the final summary. Python code will own phone validation, state transitions, passphrase checks, database writes, lookups, off-scope counting, and termination.

## Goals / Non-Goals

**Goals:**

- Build a Python conversational agent using PydanticAI with OpenAI as the default live model provider.
- Provide a Streamlit chat UI suitable for local demo.
- Persist stores, conversations, messages, summaries, and local trace records in SQLite.
- Validate US phone numbers before saving and reprompt on invalid input.
- Gate store lookups behind a configurable passphrase, defaulting to `open-sesame`.
- Support repeated save and lookup operations in any order in a single conversation.
- Terminate on explicit done-style utterances or after 3 consecutive off-scope attempts.
- Save a concise summary that includes successful operations, failed attempts, and off-scope attempts.
- Add pytest coverage for core behavior without requiring live OpenAI calls.

**Non-Goals:**

- Multi-user authentication, authorization, or production-grade secret management.
- Distributed deployment, hosted database infrastructure, or external tracing services.
- International phone validation beyond US phone formats.
- A polished production UI beyond the minimal local Streamlit demo.
- Complex semantic store matching beyond normalized-name lookup.

## Decisions

### Use a deterministic conversation controller with narrow LLM responsibilities

The system will model conversation state explicitly, for example:

- `idle`
- `awaiting_save_name`
- `awaiting_save_phone`
- `awaiting_lookup_name`
- `awaiting_passphrase`
- `ended`

The LLM will classify intent, extract store name and phone candidates when present, and generate the final summary. The controller will decide what happens next and will call persistence functions directly.

Alternatives considered:

- Fully agentic tool-calling flow: more flexible, but it makes passphrase gating and invalid-phone reprompts harder to guarantee.
- Fully rule-based chatbot: easier to test, but it would not satisfy the LLM-framework expectation as directly and would be less conversational.

### Use PydanticAI with OpenAI by default

PydanticAI provides structured agent outputs and test-model support, which fits a small Python project that needs reliable intent and slot extraction. OpenAI will be the default live provider through `OPENAI_API_KEY`.

Alternatives considered:

- LangChain: viable, but heavier for this narrow state-machine-driven assistant.
- LlamaIndex: better suited for retrieval-augmented knowledge workflows than this CRUD-style assistant.
- Local Ollama-only model: useful for offline use, but the agreed default is OpenAI.

### Use SQLite for persistence and tracing

SQLite is sufficient for a local demo, requires no server, and can store both business data and inspection records. The implementation will create tables for:

- `stores`
- `conversations`
- `messages`
- `summaries`
- `llm_traces`

Store saves will upsert by normalized store name so repeated saves update the existing record.

Alternatives considered:

- JSON or CSV files: acceptable for persistence, but weaker for queryable tracing and summary inspection.
- Postgres: unnecessary operational overhead for a local demo.

### Use Streamlit for the demo UI

Streamlit gives a minimal local chat interface with low implementation overhead. The UI should include the chat surface and a basic trace or summary inspection view backed by SQLite.

Alternatives considered:

- CLI: simpler, but less effective for a 30-minute demo.
- FastAPI plus frontend: more flexible, but unnecessary for the target scope.

### Treat passphrase configuration as demo security

The lookup passphrase will be configurable with `STORE_LOOKUP_PASSPHRASE` and default to `open-sesame`. The implementation must not perform the lookup until the passphrase is correct. Wrong passphrase attempts should not reveal the store phone.

Alternatives considered:

- Hardcoding only in code: simplest, but less clear and harder to change during demo.
- Real user authentication: out of scope for this project.

## Risks / Trade-offs

- LLM misclassifies user intent -> Mitigation: keep state machine authoritative, constrain structured outputs, and cover common flows with tests.
- Passphrase gate is demo-level only -> Mitigation: document that it is not production authentication and keep lookup execution behind deterministic comparison.
- US phone parsing edge cases -> Mitigation: normalize to a single accepted format and reprompt with clear examples when invalid.
- OpenAI API unavailable during demo -> Mitigation: keep tests on fake models and consider a simple fallback message for runtime configuration errors.
- Trace database may contain sensitive conversation text -> Mitigation: store locally only and avoid using real secrets or personal data in demos.
- Streamlit session state can diverge from persisted conversation state -> Mitigation: create a conversation record at session start and persist each message/action as it occurs.

## Migration Plan

This is a new application, so no data migration is required. Implementation should initialize the SQLite schema idempotently on startup. Rollback is removing the new application files and generated local SQLite database.

## Open Questions

- None blocking implementation. Current agreed defaults are OpenAI, Streamlit, US-only phone validation, SQLite persistence/tracing, upsert-by-name, 3 off-scope attempts, and passphrase default `open-sesame`.
