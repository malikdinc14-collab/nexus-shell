# Plan: Pi Frontend Integration

## Authority & Governance
This document establishes the authorized execution parameters for integrating the `pi` CLI into Nexus Shell.

### 1. Model Selection
- **Phase 1 (Infrastructure Analysis)**: Authorized for `gemini-2.5-flash` natively via the local `@google/gemini-cli`.
- **Phase 2 (Integration Scripting)**: Authorized for `gemini-2.5-flash` natively via the local `@google/gemini-cli` acting as the Swarm Worker.

### 2. Inference Locality
- All code generation MUST be executed via the `gemini` CLI running on the local host machine within the active shell session.
- No third-party APIs (OpenRouter, OpenAI) are authorized to read or write code for this implementation.

### 3. Execution Dependency
- Execution is strictly prohibited until this document is formally approved and moved from `.gap/proposals/` to `.gap/` by the human operator.
