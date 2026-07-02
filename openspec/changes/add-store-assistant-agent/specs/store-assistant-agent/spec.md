## ADDED Requirements

### Requirement: Conversational save flow
The system SHALL allow a user to save a store record by collecting a store name and a US phone number through conversation.

#### Scenario: User provides name and valid phone in one request
- **WHEN** the user asks to save a store and provides both a store name and a valid US phone number
- **THEN** the system SHALL persist the store record and confirm the save succeeded

#### Scenario: User provides missing save details
- **WHEN** the user asks to save a store without a store name or phone number
- **THEN** the system SHALL ask for the missing field before saving

### Requirement: US phone validation
The system MUST validate phone input as a US phone number before saving a store record.

#### Scenario: Invalid phone is rejected
- **WHEN** the user provides an invalid phone number during the save flow
- **THEN** the system MUST not save the store record and MUST reprompt for a valid US phone number

#### Scenario: Valid phone is normalized
- **WHEN** the user provides a valid US phone number during the save flow
- **THEN** the system SHALL normalize the phone number to a consistent stored format before persisting it

### Requirement: Store persistence
The system SHALL persist store records in SQLite and upsert records by normalized store name.

#### Scenario: New store is saved
- **WHEN** the user completes a save flow for a store name that does not already exist
- **THEN** the system SHALL insert a new store record with the display name, normalized name, phone number, and timestamps

#### Scenario: Existing store is updated
- **WHEN** the user completes a save flow for a store name that already exists after normalization
- **THEN** the system SHALL update the existing store record phone number instead of creating a duplicate

### Requirement: Passphrase-gated lookup
The system MUST require a correct secret passphrase before retrieving a store phone number.

#### Scenario: Lookup prompts for passphrase
- **WHEN** the user asks to retrieve a store by name
- **THEN** the system MUST request the lookup passphrase before querying for or returning the store phone number

#### Scenario: Incorrect passphrase blocks lookup
- **WHEN** the user provides an incorrect passphrase during lookup
- **THEN** the system MUST not perform the store lookup and MUST not reveal the store phone number

#### Scenario: Correct passphrase allows lookup
- **WHEN** the user provides the correct passphrase during lookup
- **THEN** the system SHALL perform the store lookup by normalized name

### Requirement: Store retrieval response
The system SHALL communicate the stored phone number when an authorized lookup succeeds.

#### Scenario: Authorized lookup finds a store
- **WHEN** the user has provided the correct passphrase and the requested store exists
- **THEN** the system SHALL respond with the store phone number

#### Scenario: Authorized lookup misses a store
- **WHEN** the user has provided the correct passphrase and the requested store does not exist
- **THEN** the system SHALL tell the user that the store was not found

### Requirement: Multi-operation conversation
The system SHALL support saving and retrieving stores as many times as the user wants, in any order, within the same conversation until termination.

#### Scenario: User performs repeated mixed operations
- **WHEN** the user saves a store, retrieves a store, and saves another store in the same conversation
- **THEN** the system SHALL complete each operation without requiring a new conversation

### Requirement: Conversation termination
The system MUST terminate the conversation when the user expresses they are done or after 3 consecutive off-scope attempts.

#### Scenario: User says they are done
- **WHEN** the user sends an utterance such as "I'm done" or "I'm good"
- **THEN** the system MUST end the conversation and proceed to summary generation

#### Scenario: User repeatedly goes off-scope
- **WHEN** the user sends 3 consecutive off-scope utterances
- **THEN** the system MUST end the conversation and proceed to summary generation

#### Scenario: In-scope message resets off-scope count
- **WHEN** the user sends an in-scope save or lookup message after one or more off-scope utterances
- **THEN** the system SHALL reset the consecutive off-scope count

### Requirement: Conversation summary persistence
The system SHALL generate and save a concise summary of the conversation in SQLite when the conversation ends.

#### Scenario: Summary includes conversation outcomes
- **WHEN** the conversation ends
- **THEN** the system SHALL save a summary that includes successful operations, failed attempts, and off-scope attempts

### Requirement: Local tracing
The system SHALL record local trace information for LLM calls and conversation activity to SQLite.

#### Scenario: LLM call is traced
- **WHEN** the system performs an LLM call for intent extraction or summary generation
- **THEN** the system SHALL save trace data including call type, inputs, outputs, model identifier, latency, and any error

#### Scenario: Conversation message is persisted
- **WHEN** the user or assistant sends a message
- **THEN** the system SHALL save the message role, content, conversation identifier, and timestamp

### Requirement: Minimal demo UI
The system SHALL provide a local Streamlit UI for demonstrating the assistant.

#### Scenario: User interacts through Streamlit
- **WHEN** the user opens the Streamlit app locally
- **THEN** the system SHALL show a chat interface that supports the save, lookup, termination, and trace-inspection flows

### Requirement: Automated tests
The system SHALL include automated tests for core conversation behavior without requiring live OpenAI calls.

#### Scenario: Core flows are covered by tests
- **WHEN** the test suite runs
- **THEN** it SHALL verify at least invalid-phone reprompt behavior and passphrase-gated lookup behavior
