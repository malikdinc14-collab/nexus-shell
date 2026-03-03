# Requirements Document

## Introduction

Nexus Core is a local, autonomous AI operating system designed to overcome the limitations of static LLMs (amnesia, context limits, stagnation) through a modular architecture comprising Letta, RLM, MemEvolve, MLX, and an Integration Layer.

## Glossary

- **Letta**: The persistent memory engine and state manager
- **RLM**: Recursive Language Model - the reasoning engine capable of recursive thought generation
- **MemEvolve**: The evolutionary engine for post-hoc optimization
- **MLX**: The local inference execution layer (Apple Silicon) with speculative decoding capabilities
- **Integration_Layer**: The central dispatcher and connective tissue between modules
- **Thought_Firewall**: A security mechanism preventing raw reasoning traces from contaminating persistent memory
- **Agent**: The autonomous entity combining reasoning and memory capabilities
- **User**: The human operator interacting via a UI (Parallax/OpenCode)
- **System**: The background automated processes (MemEvolve)
- **Persona_Lock**: A security mechanism preventing agents from modifying their core identity and behavioral constraints
- **Tool_Sandbox**: A security validation system ensuring MemEvolve-generated tools are safe and non-malicious
- **Observability_Layer**: Structured logging, metrics, and debugging infrastructure for system transparency
- **Context_Manager**: Intelligent conversation history management with summarization and pruning
- **Model_Registry**: Central catalog for MLX model lifecycle management and versioning

## Requirements

### Requirement 1

**User Story:** As a user, I want to interact with an AI system that maintains persistent memory across sessions, so that I can have continuous, context-aware conversations without losing previous interactions.

#### Acceptance Criteria

1. THE Letta SHALL serve as the single source of truth for Agent and User state
2. WHEN a user sends a message requiring long context processing, THE Integration_Layer SHALL invoke the RLM module with context stored as variables, not in prompts
3. WHEN a response is completed, THE Integration_Layer SHALL sanitize the output by removing all thought tags before sending the final message to Letta
4. THE System SHALL never store raw reasoning traces or thoughts in the permanent Letta database

### Requirement 2

**User Story:** As a user, I want the AI system to perform local inference without sending my data to external services, so that my privacy and data sovereignty are maintained.

#### Acceptance Criteria

1. THE System SHALL use the MLX module for all LLM and Embedding inference to ensure local privacy
2. THE System SHALL run entirely on localhost (127.0.0.1) with no external cloud calls
3. WHEN inference is requested, THE System SHALL complete processing within 200ms start latency
4. THE MLX module SHALL support multiple model configurations including speculative decoding for performance optimization
5. THE System SHALL allow experimentation with different quantization levels, model combinations, and optimization strategies

### Requirement 3

**User Story:** As a user, I want to see the AI's reasoning process while ensuring it doesn't contaminate the permanent memory, so that I can understand how conclusions are reached while maintaining clean state.

#### Acceptance Criteria

1. WHILE the RLM is generating a response, THE System SHALL stream "Thought" tokens separately from "Content" tokens
2. THE User SHALL receive both thought streams and final responses
3. THE Letta SHALL receive only final responses and tool calls, never thought streams

### Requirement 4

**User Story:** As a user, I want the system to handle extremely long contexts (100k+ tokens) without performance degradation, so that I can analyze large documents, codebases, and datasets effectively.

#### Acceptance Criteria

1. THE RLM SHALL store context as Python variables in a REPL environment rather than passing context in prompts
2. WHEN processing long contexts exceeding standard limits, THE RLM SHALL enable the LLM to write Python code to explore context programmatically
3. THE RLM SHALL provide a secure REPL environment with access to context, query, recursive_llm function, and regex capabilities
4. WHEN the LLM is ready to respond, THE RLM SHALL recognize FINAL("answer") statements and return the extracted answer
5. THE RLM SHALL support recursive processing by allowing recursive_llm(sub_query, sub_context) calls for context partitioning
6. WHEN invoked, THE RLM SHALL integrate with Letta's memory system to access conversation history, core memory, and archival memory as context variables

### Requirement 5

**User Story:** As a system administrator, I want the AI to automatically improve its capabilities based on past interactions using advanced reasoning over large interaction logs, so that the system becomes more effective over time.

#### Acceptance Criteria

1. WHEN a session concludes or on explicit command, THE MemEvolve module SHALL use RLM to analyze large interaction logs from Letta
2. THE MemEvolve SHALL provide RLM with access to conversation history, agent performance metrics, and capability gaps as context variables
3. IF the agent failed to retrieve correct information, THEN MemEvolve SHALL use RLM to synthesize new Python tools by analyzing patterns across large datasets
4. WHILE MemEvolve is running, THE System SHALL operate asynchronously to avoid blocking live User inference
5. THE MemEvolve SHALL use RLM to process multi-session analysis that exceeds traditional context limits

### Requirement 6

**User Story:** As a system administrator, I want the system to manage memory pressure automatically, so that performance remains optimal during extended usage.

#### Acceptance Criteria

1. WHEN system memory pressure is high, THE System SHALL trigger Austerity Mode (garbage collection) via nexus_ctl
2. THE System SHALL maintain performance standards during memory management operations

### Requirement 7

**User Story:** As a security administrator, I want to ensure that MemEvolve only generates safe tools, so that the system cannot be compromised by malicious or dangerous capabilities.

#### Acceptance Criteria

1. WHEN MemEvolve synthesizes a new tool, THE Tool_Sandbox SHALL validate the tool code for safety before registration
2. THE Tool_Sandbox SHALL reject tools that attempt to access system files, network resources, or execute arbitrary commands
3. THE Tool_Sandbox SHALL reject tools that attempt to modify agent personas, core memory, or security settings
4. WHEN a tool fails validation, THE System SHALL log the rejection and notify administrators
5. THE System SHALL maintain a whitelist of approved tool patterns and capabilities

### Requirement 8

**User Story:** As a security administrator, I want to ensure that agents cannot modify their own personas or core behavioral constraints, so that the system maintains consistent and safe behavior.

#### Acceptance Criteria

1. THE System SHALL prevent agents from modifying their persona definitions or core memory blocks
2. WHEN an agent attempts persona modification, THE Persona_Lock SHALL block the operation and log the attempt
3. THE System SHALL only allow authorized administrators to modify agent personas through secure channels
4. THE System SHALL validate that all persona modifications maintain safety constraints and behavioral boundaries
5. THE System SHALL maintain immutable backups of original persona configurations


### Requirement 9

**User Story:** As a system administrator, I want comprehensive observability and debugging capabilities, so that I can diagnose issues, monitor performance, and understand system behavior in production.

#### Acceptance Criteria

1. THE System SHALL implement structured logging with unique trace IDs across all components for request tracking
2. THE System SHALL track and expose performance metrics including RLM invocation frequency, MLX model usage, and memory pressure events
3. THE System SHALL provide a secure debug mode that captures full reasoning traces without contaminating Letta's persistent memory
4. THE System SHALL expose health check endpoints to verify all modules are functioning correctly
5. THE System SHALL log all critical decisions including RLM invocation triggers, model selection, and MemEvolve actions

### Requirement 10

**User Story:** As a system administrator, I want to track and control resource usage, so that I can manage costs and prevent resource exhaustion.

#### Acceptance Criteria

1. THE System SHALL track token usage per component with separate accounting for RLM inference and evolution
2. THE System SHALL enforce configurable token budget limits per RLM session with graceful degradation
3. THE System SHALL log cost metrics for all LLM operations to enable usage analysis
4. WHERE fallback is enabled, WHEN token budgets are exceeded, THE System SHALL fall back to standard inference with user notification
5. THE System SHALL provide model selection heuristics based on query complexity and resource availability

### Requirement 11

**User Story:** As a system administrator, I want to measure the effectiveness of MemEvolve-synthesized tools, so that I can understand which capabilities are valuable and which should be deprecated.

#### Acceptance Criteria

1. THE System SHALL track usage metrics for all synthesized tools including invocation count and success rate
2. THE System SHALL measure tool effectiveness by comparing agent performance before and after tool deployment
3. THE System SHALL automatically flag tools that have not been used within a configurable time period for deprecation review
4. THE System SHALL maintain an audit log of all tool synthesis events with capability gap analysis
5. THE System SHALL support A/B testing to compare agent performance with and without specific tools

### Requirement 12

**User Story:** As a user, I want the system to manage conversation history intelligently, so that long-running sessions remain performant and contextually relevant.

#### Acceptance Criteria

1. WHEN conversation history exceeds a configurable threshold, THE System SHALL automatically summarize older exchanges
2. THE System SHALL implement semantic pruning to retain important context while removing redundant exchanges
3. WHEN building RLM context, THE System SHALL prioritize recent and semantically relevant conversation history
4. THE System SHALL move old conversations to archival memory with semantic search capabilities
5. THE System SHALL maintain conversation coherence across summarization boundaries

### Requirement 13

**User Story:** As a security administrator, I want protection against prompt injection attacks, so that users cannot manipulate the agent's behavior through crafted inputs.

#### Acceptance Criteria

1. THE System SHALL detect and neutralize common prompt injection patterns in user inputs
2. THE System SHALL enforce privilege separation between user messages and system messages
3. THE System SHALL monitor for jailbreak attempts and log security violations
4. THE System SHALL implement rate limiting to prevent abuse through excessive requests
5. THE System SHALL validate that user inputs do not contain instructions that override system prompts or safety constraints

### Requirement 14

**User Story:** As a system administrator, I want comprehensive model lifecycle management, so that I can version, update, and optimize MLX models without system downtime.

#### Acceptance Criteria

1. THE System SHALL track model versions and associate outputs with the model version that produced them
2. THE System SHALL support hot swapping of models without requiring system restart
3. THE System SHALL maintain a model registry with metadata including size, quantization, performance characteristics, and compatibility
4. THE System SHALL automatically select models based on available memory, query complexity, and latency requirements
5. THE System SHALL validate model compatibility before deployment

### Requirement 15

**User Story:** As a developer, I want comprehensive testing infrastructure, so that I can ensure system reliability and catch regressions early.

#### Acceptance Criteria

1. THE System SHALL include end-to-end integration tests covering complete user journeys
2. THE System SHALL implement chaos testing to validate behavior under component failures
3. THE System SHALL maintain performance benchmarks tracking inference latency, RLM overhead, and memory usage
4. THE System SHALL run regression tests ensuring new MemEvolve tools do not break existing functionality
5. THE System SHALL validate system behavior under resource constraints and degraded conditions

### Requirement 16

**User Story:** As a user, I want transparency into what the system is doing, so that I can understand its capabilities and trust its decisions.

#### Acceptance Criteria

1. THE System SHALL provide status indicators showing when RLM is analyzing large contexts versus using standard inference
2. THE User SHALL be able to query available capabilities and see MemEvolve-synthesized tools
3. WHEN MemEvolve synthesizes a new tool, THE System SHALL notify the user of the new capability
4. THE System SHALL provide an optional reasoning transparency mode showing RLM's exploration process
5. THE System SHALL explain why specific models or processing strategies were selected for a query

### Requirement 17

**User Story:** As a system administrator, I want graceful degradation strategies, so that the system remains functional even when components fail.

#### Acceptance Criteria

1. THE System SHALL maintain a component health matrix tracking the status of all modules
2. WHERE fallback is enabled, WHEN RLM fails, THE System SHALL fall back to standard inference with user notification
3. WHEN MemEvolve is unavailable, THE System SHALL continue processing inference requests normally
4. THE System SHALL implement automatic retry with exponential backoff for transient failures
5. THE System SHALL use circuit breakers to prevent cascading failures across components

### Requirement 18

**User Story:** As a system administrator, I want unified configuration management, so that I can control system behavior consistently across environments.

#### Acceptance Criteria

1. THE System SHALL use a unified configuration file as the single source of truth for all module settings
2. THE System SHALL support environment-specific configurations for development, testing, and production
3. THE System SHALL allow runtime configuration changes for non-critical settings without requiring restart
4. THE System SHALL validate all configuration changes before applying them
5. THE System SHALL log all configuration changes with timestamps and user attribution
