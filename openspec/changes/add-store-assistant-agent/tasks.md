## 1. Project Setup

- [x] 1.1 Create Python package structure for the store assistant application.
- [x] 1.2 Add project dependency metadata for PydanticAI, OpenAI provider support, Streamlit, pytest, and local development commands.
- [x] 1.3 Add environment configuration for `OPENAI_API_KEY`, `STORE_LOOKUP_PASSPHRASE`, and SQLite database path with safe local defaults.
- [x] 1.4 Add a README section or usage notes covering setup, passphrase default, test execution, and Streamlit launch.

## 2. Persistence and Validation

- [x] 2.1 Implement idempotent SQLite schema initialization for stores, conversations, messages, summaries, and LLM traces.
- [x] 2.2 Implement store repository functions for normalized-name upsert and lookup.
- [x] 2.3 Implement conversation repository functions for creating conversations, saving messages, ending conversations, and saving summaries.
- [x] 2.4 Implement local trace repository functions for recording LLM call type, inputs, outputs, model, latency, and errors.
- [x] 2.5 Implement US phone validation and normalization utilities.
- [x] 2.6 Implement store-name normalization utilities used by both save and lookup flows.

## 3. Conversation Controller

- [x] 3.1 Implement conversation state models for idle, save-detail collection, lookup-detail collection, passphrase collection, and ended states.
- [x] 3.2 Implement save flow handling for complete requests, missing store names, missing phone numbers, invalid phone reprompts, and successful saves.
- [x] 3.3 Implement lookup flow handling that requests the passphrase before executing any store lookup.
- [x] 3.4 Implement passphrase checking using configured `STORE_LOOKUP_PASSPHRASE` with default `open-sesame`.
- [x] 3.5 Implement authorized lookup responses for found and missing stores.
- [x] 3.6 Implement support for repeated save and lookup operations in any order within one conversation.
- [x] 3.7 Implement done-utterance detection and 3-consecutive-off-scope termination behavior.
- [x] 3.8 Implement off-scope counter reset when the user returns to an in-scope save or lookup request.

## 4. LLM Integration and Tracing

- [x] 4.1 Implement PydanticAI structured output for intent classification and slot extraction.
- [x] 4.2 Integrate OpenAI as the default live LLM provider.
- [x] 4.3 Ensure deterministic controller logic owns validation, passphrase checks, database writes, and lookups.
- [x] 4.4 Trace every LLM call to SQLite, including successful outputs and errors.
- [x] 4.5 Implement final summary generation with the LLM and persist the summary when conversations end.
- [x] 4.6 Provide fake or stub model support so tests do not require live OpenAI calls.

## 5. Streamlit Demo UI

- [x] 5.1 Implement a Streamlit chat interface backed by one persisted conversation per UI session.
- [x] 5.2 Display assistant responses for save, lookup, invalid phone, wrong passphrase, not-found, off-scope, and termination flows.
- [x] 5.3 Add a local inspection view for saved stores, conversation summaries, and trace records.
- [x] 5.4 Ensure the UI prevents additional messages from mutating an ended conversation.

## 6. Tests and Verification

- [x] 6.1 Add tests for invalid-phone reprompt behavior and verify invalid input is not saved.
- [x] 6.2 Add tests for passphrase-gated lookup and verify wrong passphrases do not reveal store phones.
- [x] 6.3 Add tests for repeated mixed save and lookup operations within one conversation.
- [x] 6.4 Add tests for done/off-scope termination and persisted summary creation.
- [x] 6.5 Add tests for SQLite tracing of LLM calls and persisted messages.
- [x] 6.6 Run the automated test suite and fix failures.
- [ ] 6.7 Manually verify the Streamlit demo can save, retrieve, terminate, and show persisted traces locally.
