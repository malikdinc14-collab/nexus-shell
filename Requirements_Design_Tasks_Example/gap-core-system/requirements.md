# Requirements: GAP Core System with Plan Layer

## 1. Intent & Scope
**Intent**: Implement the core Gated Agent Protocol system with a clear separation between **Tasks** (what must be done) and **Plan** (how it's allowed to be executed).
**Scope**: Core GAP engine including manifest parsing, gate enforcement, ledger tracking, and the new Plan layer that attaches execution envelopes to approved tasks.

## 2. Core Principles
1. **Separate Necessity from Permission**: Tasks describe what must change; Plan describes how those changes are allowed to be executed.
2. **Manual Authority Phase**: At this stage, the LLM does not suggest ACL, models, locality, or checkpoints. The supervisor explicitly sets them.
3. **Consent Ledger, Not Automation**: GAP records proposals, requires human approval, tracks state, and detects drift. It does not sandbox, auto-route models, optimize execution, or make decisions.

## 3. Functional Requirements

### 3.1 Manifest Definition (Req-1)
- **3.1.1**: The system MUST parse YAML manifests defining workflow phases (requirements, design, tasks, implementation)
- **3.1.2**: Each phase MUST specify artifact location and gate status (true/false)
- **3.1.3**: Phases MUST declare dependencies (needs: [previous_phase])
- **3.1.4**: The system MUST support protocol inheritance (extends: [protocol: software-engineering])

### 3.2 Task Management (Req-2)
- **3.2.1**: Tasks MUST exist in two synchronized formats:
  - **Machine-readable**: `.gap/tasks.yaml` (structured YAML for validation and processing)
  - **Human-readable**: `docs/tasks.md` (markdown for supervisor review and editing)
- **3.2.2**: Tasks MUST contain only logical decomposition (description, traceability, expected outputs)
- **3.2.3**: Tasks MUST NOT contain execution context (no ACL, model choice, locality, checkpoints)
- **3.2.4**: Tasks MUST be proposed by the agent and approved/edited by the supervisor
- **3.2.5**: Each task MUST trace back to specific design and requirement IDs
- **3.2.6**: Changes in one task format MUST be automatically reflected in the other

### 3.3 Plan Layer (Req-3)
- **3.3.1**: Plan MUST be constructed ONLY after tasks are accepted by supervisor
- **3.3.2**: Plan MUST attach execution envelope to each approved task containing:
  - ACL: What files the executor may touch
  - Execution venue: Local vs Cloud
  - Model: Which cognition is permitted
  - Checkpoints: Where human review is required
- **3.3.3**: Plan MUST be authored (or at least completed) by the supervisor, not the agent
- **3.3.4**: Plan MUST preserve tasks unchanged (tasks = epistemic record, plan = operational record)

### 3.4 Gate Enforcement (Req-4)
- **3.4.1**: The system MUST enforce phase gates according to manifest definition
- **3.4.2**: Gates MUST block progress until supervisor approval
- **3.4.3**: The system MUST validate traceability chains before allowing phase transitions
- **3.4.4**: Checkpoints MUST enforce human interruption at declared boundaries

### 3.5 Ledger & Audit (Req-5)
- **3.5.1**: The system MUST maintain immutable ledger of all state transitions
- **3.5.2**: Each approval MUST be recorded with timestamp and decision context
- **3.5.3**: Audit trails MUST link every task to its requirement and design origins
- **3.5.4**: The ledger MUST record Plan envelope approvals with all execution parameters

### 3.6 CLI Interface (Req-6)
- **3.6.1**: `gap check status` MUST display current state of all phases and gates
- **3.6.2**: `gap scribe create` MUST generate artifacts for any phase
- **3.6.3**: `gap gate list/approve` MUST manage gate approvals
- **3.6.4**: `gap check traceability` MUST verify chain of custody from requirements → tasks
- **3.6.5**: `gap gate approve TASK-ID --edit-envelope` MUST allow supervisor to fill Plan fields

## 4. Non-Functional Requirements

### 4.1 Security (Req-7)
- **4.1.1**: GAP MUST NOT enforce security or sandbox code (it's a consent ledger, not protection)
- **4.1.2**: ACL MUST be visible and explicitly accepted (presented for judgment, not executed for protection)
- **4.1.3**: The system MUST NOT contain routing advisors, automatic model suggestions, or budget logic

### 4.2 Performance (Req-8)
- **4.2.1**: Status checks MUST complete within 2 seconds
- **4.2.2**: Ledger operations MUST not block user interactions
- **4.2.3**: The system MUST handle projects with up to 1000 tasks

### 4.3 Compatibility (Req-9)
- **4.3.1**: MUST support Python 3.10+
- **4.3.2**: MUST work on macOS, Linux, and Windows
- **4.3.3**: MUST not require external services (YAML/File-based ledger)

## 5. Acceptance Criteria

### 5.1 Core Workflow (AC-1)
- Given a valid manifest, when user runs `gap check status`, then system displays current gate states
- Given requirements are approved, when agent proposes design, then system allows design creation
- Given tasks are proposed, when supervisor approves tasks, then system enables Plan construction
- Given Plan is complete, when execution begins, then system enforces declared checkpoints

### 5.2 Plan Construction (AC-2)
- Given approved tasks, when supervisor runs `gap gate approve TASK-1 --edit-envelope`, then system presents ACL/model/locality/checkpoint fields
- Given filled envelope, when supervisor confirms, then system creates/updates `.gap/plan.yaml`
- Given Plan exists, when execution begins, then system enforces declared checkpoints

### 5.3 Traceability (AC-3)
- Given complete workflow, when user runs `gap check traceability`, then system validates all links
- Given broken traceability, when gate transition attempted, then system blocks with clear error
- Given audit request, when user queries ledger, then system shows complete decision history

## 6. Constraints
- **No AI suggestions**: LLM must not propose execution parameters in Manual Authority Phase
- **No automation logic**: GAP must remain "brutally unintelligent" - no routing, optimization, or decision-making
- **No security enforcement**: ACL is declaration, not enforcement; external tooling may honor it
- **No model orchestration**: Model assignment is permission record, not routing logic
- **No drift detection**: Out of scope for current implementation