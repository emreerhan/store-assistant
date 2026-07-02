# Store Assistant

A small conversational agent that saves and retrieves store phone numbers. The app uses a deterministic Python conversation controller for validation, persistence, and passphrase-gated lookups, with an LLM used for intent extraction and final summaries.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Create a local `.env` or export values in your shell:

```bash
export OPENAI_API_KEY="..."
export STORE_LOOKUP_PASSPHRASE="open-sesame"
export STORE_ASSISTANT_DB_PATH="data/store_assistant.sqlite3"
```

`STORE_LOOKUP_PASSPHRASE` defaults to `open-sesame`. `STORE_ASSISTANT_DB_PATH` defaults to `data/store_assistant.sqlite3`.

## Run the Demo

```bash
streamlit run streamlit_app.py
```

The Streamlit app provides a chat interface and local inspection tabs for saved stores, summaries, messages, and LLM traces.

## Run Tests

```bash
python -m pytest
```

Tests use a deterministic fake/heuristic LLM client and do not require live OpenAI calls.
