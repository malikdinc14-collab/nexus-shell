# Implementation Plan: Nexus Core

## Overview

This implementation plan converts the Nexus Core design into discrete coding tasks that build incrementally toward a complete autonomous AI operating system. The focus is on implementing the Thought Firewall, RLM unification, MemEvolve integration, and comprehensive testing.

## Tasks

- [x] 1. Implement Thought Firewall Security Layer
  - Create ThoughtFilter class in `integration/core/utils/`
  - Implement regex-based thought tag detection and removal
  - Add stream splitting logic for user vs Letta outputs
  - _Requirements: 1.3, 1.4, 3.3_

- [x] 1.1 Write property test for Thought Firewall
  - **Property 5: Thought Firewall Integrity**
  - **Validates: Requirements 1.4**

- [x] 1.2 Write property test for stream sanitization
  - **Property 12: Letta Stream Sanitization**
  - **Validates: Requirements 3.3**

- [ ] 2. Implement RLM Service with Letta Memory Integration
  - Create `RLMService` class in `integration/core/rlm_service.py` that wraps the existing RLM library
  - Integrate with Letta client to access conversation history, core memory, and archival memory
  - Implement context-as-variable storage with Letta memory components as REPL variables
  - Add FINAL() statement recognition and answer extraction
  - Support recursive_llm() calls for context partitioning
  - _Requirements: 1.2, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ] 2.1 Write property test for RLM context isolation
  - **Property 2: RLM Context Isolation**
  - **Validates: Requirements 1.2**

- [ ] 2.2 Write property test for RLM conditional invocation
  - **Property 3: RLM Conditional Invocation**
  - **Validates: Requirements 1.2, 4.2**

- [ ] 2.3 Write property test for RLM REPL environment with Letta memory
  - **Property 13: RLM REPL Environment with Letta Memory**
  - **Validates: Requirements 4.3, 4.6**

- [ ] 2.4 Write property test for RLM iterative processing
  - **Property 14: RLM Iterative Processing**
  - **Validates: Requirements 4.2**

- [ ] 2.5 Write property test for FINAL recognition
  - **Property 15: RLM FINAL Recognition**
  - **Validates: Requirements 4.4**

- [ ] 2.6 Write property test for recursive capability
  - **Property 16: RLM Recursive Capability**
  - **Validates: Requirements 4.5**

- [ ] 2.7 Write property test for RLM Letta memory integration
  - **Property 17: RLM Letta Memory Integration**
  - **Validates: Requirements 4.6**

- [ ] 3. Update Integration Gateway with Conditional RLM Invocation
  - Modify `integration/core/nexus_gateway.py` to use ThoughtFilter
  - Implement conditional RLM invocation based on context size and complexity
  - Add logic to determine when RLM is needed vs standard MLX inference
  - Implement dual stream routing (User vs Letta)
  - Add RLMService integration for complex queries
  - _Requirements: 1.2, 1.3, 3.1, 3.2_

- [ ] 3.1 Write property test for stream separation
  - **Property 10: Stream Separation**
  - **Validates: Requirements 3.1**

- [ ] 3.2 Write property test for user stream completeness
  - **Property 11: User Stream Completeness**
  - **Validates: Requirements 3.2**

- [ ] 4. Checkpoint - Ensure core security tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement MLX Integration with Speculative Decoding
  - Ensure all inference goes through MLX module
  - Implement speculative decoding with draft and target models
  - Add flexible configuration system for different model combinations
  - Add network monitoring to prevent external API calls
  - Implement inference latency monitoring
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 5.1 Write property test for local inference only
  - **Property 6: Local Inference Only**
  - **Validates: Requirements 2.1, 2.2**

- [ ] 5.2 Write property test for inference latency
  - **Property 7: Inference Latency**
  - **Validates: Requirements 2.3**

- [ ] 5.3 Write property test for speculative decoding performance
  - **Property 8: Speculative Decoding Performance**
  - **Validates: Requirements 2.4**

- [ ] 5.4 Write property test for MLX configuration flexibility
  - **Property 9: MLX Configuration Flexibility**
  - **Validates: Requirements 2.5**

- [ ] 6. Implement MemEvolve Integration with RLM Analysis
  - Update MemEvolve config to connect to `data/letta/sqlite.db`
  - Integrate RLMService for analyzing large interaction logs and multi-session patterns
  - Add `nexus_ctl --evolve` command hook
  - Implement asynchronous analysis execution with RLM-powered insights
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 6.1 Write property test for evolution analysis trigger
  - **Property 18: Evolution Analysis Trigger**
  - **Validates: Requirements 5.1**

- [ ] 6.2 Write property test for MemEvolve RLM integration
  - **Property 19: MemEvolve RLM Integration**
  - **Validates: Requirements 5.2**

- [ ] 6.3 Write property test for adaptive tool synthesis
  - **Property 20: Adaptive Tool Synthesis**
  - **Validates: Requirements 5.3**

- [ ] 6.4 Write property test for asynchronous evolution
  - **Property 21: Asynchronous Evolution**
  - **Validates: Requirements 5.4**

- [ ] 6.5 Write property test for multi-session analysis
  - **Property 22: Multi-Session Analysis**
  - **Validates: Requirements 5.5**

- [ ] 7. Implement Memory Management and Performance Monitoring
  - Add memory pressure detection
  - Implement Austerity Mode trigger via nexus_ctl
  - Add performance monitoring during cleanup operations
  - _Requirements: 6.1, 6.2_

- [ ] 7.1 Write property test for memory management trigger
  - **Property 23: Memory Management Trigger**
  - **Validates: Requirements 6.1**

- [ ] 7.2 Write property test for performance during cleanup
  - **Property 24: Performance During Cleanup**
  - **Validates: Requirements 6.2**

- [ ] 8. Implement State Consistency and Error Handling
  - Add Letta state consistency validation
  - Implement error recovery mechanisms
  - Add comprehensive logging and monitoring
  - _Requirements: 1.1_

- [ ] 8.1 Write property test for state consistency
  - **Property 1: State Consistency**
  - **Validates: Requirements 1.1**

- [ ] 8.2 Write unit tests for error handling
  - Test thought firewall failures and recovery
  - Test MLX inference failures and fallbacks
  - Test MemEvolve analysis failures

- [ ] 9. Integration Testing and System Validation
  - Wire all components together
  - Test end-to-end workflows including security validation
  - Validate all security properties
  - _Requirements: All_

- [ ] 9.1 Write integration tests for complete workflows
  - Test user message to response pipeline
  - Test evolution analysis workflow with tool validation
  - Test memory management workflow
  - Test security violation detection and response

- [ ] 10. Implement Security Validation Systems
  - Create Tool_Sandbox for MemEvolve tool validation
  - Implement Persona_Lock for agent identity protection
  - Add security audit logging and monitoring
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 10.1 Write property test for tool safety validation
  - **Property 25: Tool Safety Validation**
  - **Validates: Requirements 7.1**

- [ ] 10.2 Write property test for dangerous tool rejection
  - **Property 26: Dangerous Tool Rejection**
  - **Validates: Requirements 7.2, 7.3**

- [ ] 10.3 Write property test for tool validation logging
  - **Property 27: Tool Validation Logging**
  - **Validates: Requirements 7.4**

- [ ] 10.4 Write property test for persona modification prevention
  - **Property 28: Persona Modification Prevention**
  - **Validates: Requirements 8.1, 8.2**

- [ ] 10.5 Write property test for persona modification logging
  - **Property 29: Persona Modification Logging**
  - **Validates: Requirements 8.2**

- [ ] 10.6 Write property test for authorized persona changes
  - **Property 30: Authorized Persona Changes Only**
  - **Validates: Requirements 8.3**

- [ ] 10.7 Write property test for persona safety constraints
  - **Property 31: Persona Safety Constraints**
  - **Validates: Requirements 8.4**

- [ ] 10.8 Write property test for persona backup integrity
  - **Property 32: Persona Backup Integrity**
  - **Validates: Requirements 8.5**

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- Checkpoints ensure incremental validation of critical functionality
- All components must maintain loose coupling through the Integration Layer


- [ ] 12. Implement Observability and Debugging Infrastructure
  - Create ObservabilityService with structured logging and trace ID propagation
  - Implement metrics collection for RLM, MLX, and MemEvolve operations
  - Add secure debug mode for capturing reasoning traces
  - Implement health check endpoints for all modules
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 12.1 Write property test for structured logging with trace IDs
  - **Property 33: Structured Logging with Trace IDs**
  - **Validates: Requirements 9.1**

- [ ] 12.2 Write property test for performance metrics collection
  - **Property 34: Performance Metrics Collection**
  - **Validates: Requirements 9.2**

- [ ] 12.3 Write property test for debug mode isolation
  - **Property 35: Debug Mode Isolation**
  - **Validates: Requirements 9.3**

- [ ] 12.4 Write property test for health check completeness
  - **Property 36: Health Check Completeness**
  - **Validates: Requirements 9.4**

- [ ] 13. Implement Resource Management and Cost Control
  - Create ResourceManager for token tracking and budget enforcement
  - Implement per-component token usage accounting
  - Add configurable budget limits with optional graceful degradation
  - Create cost reporting and analytics
  - Add fallback configuration (enabled/disabled/selective per component)
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 13.1 Write property test for token usage tracking
  - **Property 37: Token Usage Tracking**
  - **Validates: Requirements 10.1**

- [ ] 13.2 Write property test for token budget enforcement
  - **Property 38: Token Budget Enforcement**
  - **Validates: Requirements 10.2, 10.4**

- [ ] 14. Implement Tool Analytics and Feedback Loop
  - Create ToolAnalytics service for usage tracking
  - Implement effectiveness measurement comparing before/after performance
  - Add automatic deprecation candidate detection
  - Implement A/B testing framework for tool evaluation
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 14.1 Write property test for tool usage metrics
  - **Property 39: Tool Usage Metrics**
  - **Validates: Requirements 11.1**

- [ ] 14.2 Write property test for tool effectiveness measurement
  - **Property 40: Tool Effectiveness Measurement**
  - **Validates: Requirements 11.2**

- [ ] 14.3 Write property test for tool deprecation detection
  - **Property 41: Tool Deprecation Detection**
  - **Validates: Requirements 11.3**

- [ ] 15. Implement Context Management System
  - Create ContextManager for intelligent conversation history management
  - Implement automatic summarization for old exchanges
  - Add semantic pruning to remove redundant content
  - Implement context prioritization for RLM invocations
  - Add archival memory integration
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ] 15.1 Write property test for conversation summarization
  - **Property 42: Conversation Summarization**
  - **Validates: Requirements 12.1**

- [ ] 15.2 Write property test for semantic pruning
  - **Property 43: Semantic Pruning**
  - **Validates: Requirements 12.2**

- [ ] 15.3 Write property test for context prioritization
  - **Property 44: Context Prioritization for RLM**
  - **Validates: Requirements 12.3**

- [ ] 16. Implement Prompt Injection Defense
  - Create PromptDefense service for input sanitization
  - Implement pattern-based injection detection
  - Add privilege separation for user vs system messages
  - Implement jailbreak attempt monitoring
  - Add rate limiting per user
  - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [ ] 16.1 Write property test for prompt injection detection
  - **Property 45: Prompt Injection Detection**
  - **Validates: Requirements 13.1**

- [ ] 16.2 Write property test for privilege separation
  - **Property 46: Privilege Separation**
  - **Validates: Requirements 13.2**

- [ ] 16.3 Write property test for jailbreak monitoring
  - **Property 47: Jailbreak Monitoring**
  - **Validates: Requirements 13.3**

- [ ] 16.4 Write property test for rate limiting
  - **Property 48: Rate Limiting**
  - **Validates: Requirements 13.4**

- [ ] 17. Implement Model Registry and Lifecycle Management
  - Create ModelRegistry for centralized model management
  - Implement model version tracking and metadata storage
  - Add hot swapping capability for zero-downtime updates
  - Implement automatic model selection based on constraints
  - Add model compatibility validation
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [ ] 17.1 Write property test for model version tracking
  - **Property 49: Model Version Tracking**
  - **Validates: Requirements 14.1**

- [ ] 17.2 Write property test for model hot swapping
  - **Property 50: Model Hot Swapping**
  - **Validates: Requirements 14.2**

- [ ] 17.3 Write property test for model registry metadata
  - **Property 51: Model Registry Metadata**
  - **Validates: Requirements 14.3**

- [ ] 17.4 Write property test for automatic model selection
  - **Property 52: Automatic Model Selection**
  - **Validates: Requirements 14.4**

- [ ] 18. Implement Enhanced Testing Infrastructure
  - Create end-to-end integration test suite
  - Implement chaos testing framework
  - Add performance benchmark tracking
  - Create regression test suite for MemEvolve tools
  - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [ ] 18.1 Write integration tests for complete user journeys
  - **Property 53: Integration Test Coverage**
  - **Validates: Requirements 15.1**

- [ ] 18.2 Write chaos tests for component failures
  - **Property 54: Chaos Testing Resilience**
  - **Validates: Requirements 15.2**

- [ ] 18.3 Write performance benchmark suite
  - **Property 55: Performance Benchmark Tracking**
  - **Validates: Requirements 15.3**

- [ ] 19. Implement User Transparency Features
  - Add status indicators for processing modes
  - Implement capability discovery endpoint
  - Add evolution notifications for new tools
  - Implement optional reasoning transparency mode
  - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [ ] 19.1 Write property test for status indicators
  - **Property 56: Status Indicator Transparency**
  - **Validates: Requirements 16.1**

- [ ] 19.2 Write property test for capability discovery
  - **Property 57: Capability Discovery**
  - **Validates: Requirements 16.2**

- [ ] 19.3 Write property test for evolution notifications
  - **Property 58: Evolution Notifications**
  - **Validates: Requirements 16.3**

- [ ] 20. Implement Graceful Degradation System
  - Create CircuitBreaker for failure management
  - Implement component health matrix
  - Add configurable fallback chains (optional per component)
  - Implement retry with exponential backoff
  - Add circuit breaker pattern for cascading failure prevention
  - Add fallback configuration options (enabled/disabled/selective)
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

- [ ] 20.1 Write property test for component health matrix
  - **Property 59: Component Health Matrix**
  - **Validates: Requirements 17.1**

- [ ] 20.2 Write property test for RLM fallback strategy
  - **Property 60: RLM Fallback Strategy**
  - **Validates: Requirements 17.2**

- [ ] 20.3 Write property test for partial functionality
  - **Property 61: Partial Functionality Maintenance**
  - **Validates: Requirements 17.3**

- [ ] 20.4 Write property test for circuit breaker protection
  - **Property 62: Circuit Breaker Protection**
  - **Validates: Requirements 17.5**

- [ ] 21. Implement Configuration Management System
  - Create ConfigManager for unified configuration
  - Implement environment-specific configuration support
  - Add runtime configuration capability
  - Implement configuration validation
  - Add configuration change auditing
  - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_

- [ ] 21.1 Write property test for unified configuration
  - **Property 63: Unified Configuration**
  - **Validates: Requirements 18.1**

- [ ] 21.2 Write property test for environment-specific configs
  - **Property 64: Environment-Specific Configs**
  - **Validates: Requirements 18.2**

- [ ] 21.3 Write property test for runtime configuration
  - **Property 65: Runtime Configuration**
  - **Validates: Requirements 18.3**

- [ ] 21.4 Write property test for configuration validation
  - **Property 66: Configuration Validation**
  - **Validates: Requirements 18.4**

- [ ] 22. Final Integration and System Validation
  - Wire all new components together
  - Test complete system with all enhancements
  - Validate observability across all workflows
  - Ensure graceful degradation works end-to-end
  - _Requirements: All_

- [ ] 22.1 Write comprehensive system integration tests
  - Test observability, resource management, and degradation together
  - Validate tool analytics and context management integration
  - Test security features with prompt injection scenarios
  - Validate model registry with hot swapping scenarios
