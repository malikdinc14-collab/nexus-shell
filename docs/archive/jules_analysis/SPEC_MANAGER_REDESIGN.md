# Spec Manager Module - Gated Agent Protocol Integration

**Date**: January 29, 2026  
**Context**: Redesigning Spec Manager to support Gated Agent Protocol workflow

---

## The Gated Agent Protocol (GAP) - CORRECTED

GAP is a **Security Containment Layer** for autonomous AI agents, not just a workflow system. It enforces **Read-Open / Write-Locked** state machines with embedded Access Control Lists (ACLs).

### Core Innovation: Plan-Derived Access Control

The key insight is that **ACLs are embedded in the artifacts themselves**. When an agent creates a `plan.md`, it includes a machine-parsable Access Control block:

```markdown
## Access Control
```yaml
allow_write:
  - "src/auth.py"
  - "tests/test_auth.py"
allow_exec:
  - "pytest tests/"
```
```

When the human approves the plan, they're also approving the ACL. The harness then **physically enforces** these permissions at the kernel level.

### The Software Development Protocol

GAP provides a reference protocol for software development with 4 gates:


### Roles
1. **Analyst** - Intent Elicitation (Context, Goals, EARS Constraints)
2. **Architect** - System Design (Interfaces, Diagrams, Invariants)
3. **Planner** - Task Planning (Step Decomposition, Traceability)
4. **Craft** - Implementation (Code, PBT, Walkthrough)

### Gates (Sequential, Non-Skippable)
1. **gate_intent** → `intent.md` (Analyst) - **Read-Only**
2. **gate_invariant** → `spec.md` (Architect) - **Read-Only**
3. **gate_path** → `plan.md` (Planner) - **Read-Only**
4. **gate_synthesis** → `walkthrough.md` (Craft) - **Write permissions from plan.md ACL**

### Key Security Features
- **Read-Open**: Full read access to codebase during planning
- **Write-Locked**: No write access until plan is approved
- **ACL Enforcement**: Kernel-level permission enforcement (not prompts)
- **Session Isolation**: All state in `.gap/` directory
- **Artifact Gravity**: Progress is cumulative and auditable

### The GAP Directory Structure
```
.gap/
├── gap.yaml              # Registry (active session, history)
└── sessions/
    └── 20260129_120000_software-development-v1/
        ├── intent.md
        ├── spec.md
        ├── plan.md
        └── walkthrough.md
```

---

## How This Changes Spec Manager Design

### Critical Realization

The Spec Manager is NOT just a task viewer. It must be a **GAP Harness** that:

1. **Enforces gate sequencing** (can't skip gates)
2. **Validates artifacts** (mandatory sections, traceability)
3. **Extracts and enforces ACLs** (security kernel)
4. **Manages sessions** (`.gap/` directory)
5. **Provides role-based UI** (different views per gate)

This is **much more complex** than the original design, but also **much more powerful**.


### New Design: GAP Harness for Nexus-Shell

The Spec Manager must integrate the **actual GAP Python library** and become a full harness.

#### Architecture

```
modules/spec_manager/
├── gap_integration/
│   ├── __init__.py
│   ├── harness.py              # Main GAP harness wrapper
│   ├── acl_enforcer.py         # Wraps gated_agent.security
│   ├── session_manager.py      # Wraps gated_agent.session
│   └── protocol_loader.py      # Wraps gated_agent.registry
├── ui/
│   ├── gate_dashboard.sh       # Current gate status (FZF)
│   ├── artifact_editor.sh      # Edit current gate artifact
│   ├── traceability_view.sh    # Show requirement → task links
│   └── acl_viewer.sh           # Show current ACL permissions
├── validators/
│   ├── intent_validator.py     # Validate intent.md structure
│   ├── spec_validator.py       # Validate spec.md structure
│   ├── plan_validator.py       # Validate plan.md + ACL
│   └── walkthrough_validator.py # Validate walkthrough.md
├── templates/
│   ├── intent.md.template
│   ├── spec.md.template
│   ├── plan.md.template
│   └── walkthrough.md.template
└── hooks/
    ├── on_gate_advance.sh      # Validate and advance
    ├── on_write_attempt.sh     # Check ACL before write
    └── on_exec_attempt.sh      # Check ACL before exec
```

---

## Core Features

### 1. GAP Harness Integration

**File**: `gap_integration/harness.py`

```python
from gated_agent.registry import Registry
from gated_agent.session import Session
from gated_agent.security import ACLEnforcer
from pathlib import Path
import yaml

class NexusGAPHarness:
    """
    Nexus-Shell integration with GAP.
    Manages the full lifecycle of a GAP session.
    """
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.gap_dir = self.project_root / ".gap"
        self.registry = Registry(root_dir="/path/to/gated-agent-protocol")
        self.session = None
        self.enforcer = None
        
    def init_session(self, protocol_id: str = "software-development-v1"):
        """Initialize a new GAP session"""
        self.session = Session(protocol_id)
        self.protocol = self.registry.get_manifest(protocol_id)
        return self.session.session_id
        
    def get_current_gate(self) -> str:
        """Return the current active gate"""
        state = self._load_state()
        return state.get("current_gate", "gate_intent")
        
    def can_advance_gate(self, gate_id: str) -> tuple[bool, str]:
        """Check if gate can be advanced"""
        gate = self._get_gate(gate_id)
        
        # Check if artifact exists
        for artifact in gate.output_artifacts:
            if not (self.gap_dir / "sessions" / self.session.session_id / artifact).exists():
                return False, f"Missing artifact: {artifact}"
        
        # Run gate-specific validation
        validator = self._get_validator(gate_id)
        is_valid, message = validator.validate()
        
        return is_valid, message
        
    def advance_gate(self, gate_id: str):
        """Advance to next gate after validation"""
        can_advance, message = self.can_advance_gate(gate_id)
        if not can_advance:
            raise ValueError(f"Cannot advance: {message}")
            
        # Find next gate
        next_gate = self._get_next_gate(gate_id)
        
        # Update state
        state = self._load_state()
        state["current_gate"] = next_gate.id
        state["gates"][gate_id]["status"] = "complete"
        state["gates"][next_gate.id]["status"] = "active"
        self._save_state(state)
        
    def load_acl(self, plan_path: str):
        """Load ACL from approved plan"""
        self.enforcer = ACLEnforcer(artifact_path=plan_path)
        
    def check_write_permission(self, file_path: str) -> bool:
        """Check if write is allowed by current ACL"""
        if not self.enforcer:
            return False  # No ACL loaded = read-only
        try:
            return self.enforcer.validate_write(file_path)
        except PermissionError:
            return False
            
    def check_exec_permission(self, command: str) -> bool:
        """Check if exec is allowed by current ACL"""
        if not self.enforcer:
            return False
        try:
            return self.enforcer.validate_exec(command)
        except PermissionError:
            return False
```

---

### 2. ACL Enforcement Hooks

**File**: `hooks/on_write_attempt.sh`

```bash
#!/bin/bash
# Intercept write attempts and check ACL

nxs-gap-write() {
    local target_file="$1"
    
    # Check if we're in a GAP session
    if [[ ! -d ".gap" ]]; then
        echo "Not in a GAP session. Write allowed."
        return 0
    fi
    
    # Check ACL via Python harness
    python3 <<EOF
from gap_integration.harness import NexusGAPHarness
harness = NexusGAPHarness(".")
if harness.check_write_permission("$target_file"):
    exit(0)
else:
    print("[GAP SECURITY] WRITE DENIED: '$target_file' not in ACL")
    exit(1)
EOF
    
    return $?
}

# Wrapper for common write commands
alias vim='nxs-gap-write-wrapper vim'
alias nvim='nxs-gap-write-wrapper nvim'
alias nano='nxs-gap-write-wrapper nano'

nxs-gap-write-wrapper() {
    local editor="$1"
    shift
    local file="$1"
    
    if nxs-gap-write "$file"; then
        command "$editor" "$@"
    else
        echo "Permission denied by GAP ACL"
        return 1
    fi
}
```

---

### 3. Gate Dashboard (Updated)

**File**: `ui/gate_dashboard.sh`

```bash
#!/bin/bash
# Interactive GAP gate status viewer

nxs-gap-dashboard() {
    # Get current state from Python harness
    local state=$(python3 -c "
from gap_integration.harness import NexusGAPHarness
import json
harness = NexusGAPHarness('.')
state = harness._load_state()
print(json.dumps(state))
")
    
    local current_gate=$(echo "$state" | jq -r '.current_gate')
    
    # Show gate pipeline with status indicators
    cat <<EOF
╔════════════════════════════════════════════════════════╗
║           GATED AGENT PROTOCOL - STATUS                ║
╠════════════════════════════════════════════════════════╣
║  Session: $(echo "$state" | jq -r '.session_id')
║  Protocol: software-development-v1                     ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  $(gate_status_line "gate_intent" "$current_gate")
║  $(gate_status_line "gate_invariant" "$current_gate")
║  $(gate_status_line "gate_path" "$current_gate")
║  $(gate_status_line "gate_synthesis" "$current_gate")
║                                                        ║
╠════════════════════════════════════════════════════════╣
║  Current Role: $(get_role "$current_gate")
║  Permissions: $(get_permissions "$current_gate")
║  ACL Status: $(get_acl_status)
╚════════════════════════════════════════════════════════╝

Actions:
  [e] Edit current artifact
  [v] View ACL permissions
  [t] Validate current gate
  [a] Advance gate (if valid)
  [s] Show session history
  [q] Quit
EOF
    
    # FZF menu for actions
    action=$(echo -e "Edit\nView ACL\nValidate\nAdvance\nHistory\nQuit" | fzf --prompt="Action> ")
    
    case "$action" in
        "Edit") nxs-gap-edit ;;
        "View ACL") nxs-gap-acl ;;
        "Validate") nxs-gap-validate ;;
        "Advance") nxs-gap-advance ;;
        "History") nxs-gap-history ;;
    esac
}

gate_status_line() {
    local gate="$1"
    local current="$2"
    
    if [[ "$gate" == "$current" ]]; then
        echo "[→] $gate (ACTIVE)"
    elif gate_is_complete "$gate"; then
        echo "[✓] $gate (COMPLETE)"
    else
        echo "[⊗] $gate (LOCKED)"
    fi
}
```

---

### 4. ACL Viewer

**File**: `ui/acl_viewer.sh`

```bash
#!/bin/bash
# Show current ACL permissions

nxs-gap-acl() {
    python3 <<EOF
from gap_integration.harness import NexusGAPHarness
harness = NexusGAPHarness(".")

if not harness.enforcer:
    print("No ACL loaded (Read-Only Mode)")
    exit(0)

acl = harness.enforcer.context

print("╔════════════════════════════════════════╗")
print("║     CURRENT ACL PERMISSIONS            ║")
print("╠════════════════════════════════════════╣")
print("║                                        ║")
print("║  ALLOWED WRITES:                       ║")
for path in acl.allowed_writes:
    print(f"║    • {path}")
print("║                                        ║")
print("║  ALLOWED EXECS:                        ║")
for cmd in acl.allowed_execs:
    print(f"║    • {cmd}")
print("║                                        ║")
print("╚════════════════════════════════════════╝")
EOF
}
```

---

### 5. Artifact Validators

**File**: `validators/plan_validator.py`

```python
import re
from pathlib import Path

class PlanValidator:
    def __init__(self, plan_path: Path):
        self.plan_path = plan_path
        self.content = plan_path.read_text()
        
    def validate(self) -> tuple[bool, str]:
        """Validate plan.md structure and ACL"""
        
        # Check mandatory sections
        if "## Implementation Steps" not in self.content:
            return False, "Missing 'Implementation Steps' section"
            
        # Check for ACL block
        if "## Access Control" not in self.content:
            return False, "Missing 'Access Control' section"
            
        # Validate ACL format
        acl_pattern = r"##\s+Access Control.*?\n```yaml\n(.*?)\n```"
        match = re.search(acl_pattern, self.content, re.DOTALL)
        
        if not match:
            return False, "ACL block not properly formatted (must be ```yaml block)"
            
        # Check traceability
        if not self._check_traceability():
            return False, "Tasks missing traceability metadata"
            
        return True, "Plan is valid"
        
    def _check_traceability(self) -> bool:
        """Check if tasks have traceability footers"""
        # Look for patterns like: — *Trace: G-01, P-02*
        trace_pattern = r"—\s*\*Trace:.*?\*"
        return bool(re.search(trace_pattern, self.content))
```

---

## Integration with Nexus-Shell

### Composition: `gap_workspace.json`

```json
{
  "name": "gap_workspace",
  "description": "Gated Agent Protocol development workspace",
  "layout": {
    "type": "hsplit",
    "panes": [
      {
        "id": "gap_dashboard",
        "size": 30,
        "command": "$WRAPPER watch -n 1 $SPEC_MANAGER/ui/gate_dashboard.sh"
      },
      {
        "type": "vsplit",
        "panes": [
          {
            "id": "editor",
            "command": "$EDITOR_CMD"
          },
          {
            "type": "vsplit",
            "panes": [
              {
                "id": "terminal",
                "command": "/bin/zsh -i"
              },
              {
                "id": "acl_monitor",
                "command": "$WRAPPER $SPEC_MANAGER/ui/acl_viewer.sh"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Shell Commands

```bash
# Session management
nxs-gap-init            # Initialize GAP session
nxs-gap-status          # Show current gate
nxs-gap-dashboard       # Open interactive dashboard

# Gate navigation
nxs-gap-advance         # Advance to next gate (with validation)
nxs-gap-validate        # Validate current gate
nxs-gap-history         # Show session history

# Artifact management
nxs-gap-edit            # Edit current gate artifact
nxs-gap-view <artifact> # View specific artifact

# Security
nxs-gap-acl             # Show current ACL permissions
nxs-gap-check-write <file>  # Check if write is allowed
nxs-gap-check-exec <cmd>    # Check if exec is allowed

# Workflow
nxs-intent              # Open intent.md
nxs-spec                # Open spec.md
nxs-plan                # Open plan.md
nxs-walkthrough         # Open walkthrough.md
```

---

## Event Bus Integration

The Spec Manager should publish GAP events to the Nexus Event Bus:

```bash
# Gate events
GAP_GATE_ADVANCED: { "from": "gate_intent", "to": "gate_invariant" }
GAP_GATE_BLOCKED: { "gate": "gate_path", "reason": "missing traceability" }
GAP_SESSION_STARTED: { "session_id": "20260129_120000", "protocol": "software-development-v1" }

# Security events
GAP_WRITE_DENIED: { "file": "src/main.py", "reason": "not in ACL" }
GAP_EXEC_DENIED: { "command": "rm -rf /", "reason": "not in ACL" }
GAP_ACL_LOADED: { "writes": 3, "execs": 2 }

# Validation events
GAP_VALIDATION_PASSED: { "gate": "gate_path", "artifact": "plan.md" }
GAP_VALIDATION_FAILED: { "gate": "gate_path", "reason": "missing ACL" }
```

---

## Comparison: Old vs New Design

| Feature | Original Design | GAP-Aware Design |
|---------|----------------|------------------|
| **Workflow** | Kiro (req → design → tasks) | GAP (4 gates, security-enforced) |
| **Enforcement** | None (manual) | Kernel-level ACL enforcement |
| **Traceability** | Basic (task → req) | Full (task → prop → goal) |
| **Security** | None | Read-Open / Write-Locked |
| **Testing** | Manual PBT | Integrated property runner |
| **Validation** | None | Gate-specific validators |
| **UI** | Simple task list | Gate dashboard + ACL viewer |
| **State** | tasks.md only | Full `.gap/` session management |
| **Roles** | None | Analyst/Architect/Planner/Craft |
| **Library** | Custom code | Uses official GAP Python SDK |

---

## Implementation Priority

### Phase 1: GAP Integration (Week 1)
1. Install GAP Python library
2. Create harness wrapper
3. Implement session management
4. Basic gate state machine

### Phase 2: Security Layer (Week 1-2)
1. ACL extraction and enforcement
2. Write/exec hooks
3. Permission checking
4. Security event publishing

### Phase 3: UI (Week 2)
1. Gate dashboard
2. ACL viewer
3. Artifact editor integration
4. Validation feedback

### Phase 4: Validators (Week 2-3)
1. Intent validator
2. Spec validator
3. Plan validator (with ACL check)
4. Walkthrough validator

---

## Impact on PHASE_0_TASKS.md

**Task 1.4: Spec Manager Module** needs to be **completely rewritten**:

### Old Task (3-4 days)
- Task list viewer
- Status updates
- Navigation commands

### New Task (7-10 days)
- GAP Python library integration
- Session management (`.gap/` directory)
- ACL enforcement hooks
- Gate state machine
- Artifact validators
- Gate dashboard
- ACL viewer
- Security event publishing

**Estimated effort increase**: +4-6 days (now 7-10 days total)

**Dependencies**: Requires GAP Python library to be installed/available

---

## Benefits of GAP Integration

1. **Real Security**: Kernel-level enforcement, not prompts
2. **Industry Standard**: Using official GAP protocol
3. **Session Management**: Clean `.gap/` directory structure
4. **ACL Transparency**: Users see exactly what's allowed
5. **Audit Trail**: Full session history
6. **Role Clarity**: Know what you should be doing at each stage
7. **Artifact Gravity**: Progress is cumulative and auditable
8. **Reusable**: Can work with other GAP-compliant tools

---

## Risks & Mitigations

### Risk 1: GAP Library Dependency
**Mitigation**: Bundle GAP library with Nexus-Shell, or make it optional

### Risk 2: Complexity
**Mitigation**: Start with basic integration, add features incrementally

### Risk 3: User Friction
**Mitigation**: Provide "quick mode" that bypasses gates for prototyping

### Risk 4: ACL Enforcement Overhead
**Mitigation**: Cache ACL checks, optimize hot paths

---

## Recommendation

**Implement full GAP integration** using the official Python library.

**Why**:
1. Uses proven, standardized protocol
2. Real security enforcement (not theater)
3. Aligns with your stated workflow
4. Makes Nexus-Shell a true "GAP Harness"
5. Enables collaboration with other GAP tools
6. Provides audit trail and session management

**Trade-off**: +4-6 days of implementation time, but **much higher value** and **real security**.

---

## Next Steps

1. **Install GAP library**: `pip install -e /path/to/gated-agent-protocol`
2. **Update PHASE_0_TASKS.md** with new Spec Manager tasks
3. **Create harness wrapper** (gap_integration/harness.py)
4. **Implement ACL hooks** (on_write_attempt.sh, on_exec_attempt.sh)
5. **Build gate dashboard** (ui/gate_dashboard.sh)
6. **Test with real workflow** (create a session, go through gates)

---

**End of Redesign Document**

#### Architecture

```
modules/spec_manager/
├── core/
│   ├── gate_engine.py          # Gate state machine
│   ├── role_validator.py       # Verify role permissions
│   ├── traceability.py         # Link tasks → properties → goals
│   └── artifact_validator.py   # Verify gate outputs
├── ui/
│   ├── gate_dashboard.sh       # Current gate status (FZF)
│   ├── artifact_editor.sh      # Edit current gate artifact
│   ├── traceability_view.sh    # Show requirement → task links
│   └── property_runner.sh      # Execute PBT tests
├── templates/
│   ├── intent.md.template
│   ├── spec.md.template
│   ├── plan.md.template
│   └── walkthrough.md.template
└── hooks/
    ├── on_gate_complete.sh     # Validate and advance
    ├── on_task_update.sh       # Check traceability
    └── on_test_run.sh          # Update property status
```

---

## Core Features

### 1. Gate State Machine

**File**: `core/gate_engine.py`

```python
class GateState:
    LOCKED = "locked"      # Not yet accessible
    ACTIVE = "active"      # Currently working on
    REVIEW = "review"      # Awaiting approval
    COMPLETE = "complete"  # Approved, gate passed

class GateEngine:
    def __init__(self, project_root):
        self.project_root = project_root
        self.state_file = f"{project_root}/.nexus/gap_state.json"
        
    def current_gate(self) -> str:
        """Return current active gate (intent, invariant, path, synthesis)"""
        
    def can_advance(self, gate: str) -> bool:
        """Check if gate can be advanced (all requirements met)"""
        
    def advance_gate(self, gate: str):
        """Move to next gate after validation"""
        
    def get_gate_status(self, gate: str) -> GateState:
        """Get current status of a gate"""
```

**State File** (`.nexus/gap_state.json`):
```json
{
  "current_gate": "gate_path",
  "gates": {
    "gate_intent": {
      "status": "complete",
      "artifact": "intent.md",
      "approved_by": "user",
      "approved_at": "2026-01-29T10:30:00Z"
    },
    "gate_invariant": {
      "status": "complete",
      "artifact": "spec.md",
      "approved_by": "user",
      "approved_at": "2026-01-29T11:45:00Z"
    },
    "gate_path": {
      "status": "active",
      "artifact": "plan.md",
      "started_at": "2026-01-29T12:00:00Z"
    },
    "gate_synthesis": {
      "status": "locked"
    }
  }
}
```

---

### 2. Traceability Engine

**File**: `core/traceability.py`

```python
class TraceabilityEngine:
    def parse_requirements(self, intent_md: str) -> List[Requirement]:
        """Extract goals and constraints from intent.md"""
        
    def parse_properties(self, spec_md: str) -> List[Property]:
        """Extract invariants from spec.md"""
        
    def parse_tasks(self, plan_md: str) -> List[Task]:
        """Extract implementation steps from plan.md"""
        
    def validate_coverage(self) -> CoverageReport:
        """Verify 100% coverage: all goals → properties → tasks"""
        
    def get_task_lineage(self, task_id: str) -> Lineage:
        """Show: Task → Property → Goal"""
```

**Traceability Format** (in `plan.md`):
```markdown
## Task 1.1: Implement Event Bus

**Traces to**:
- Goal: REQ-009 (Nexus Event Bus)
- Property: PROP-003 (Event delivery < 100ms)
- Constraint: WHEN event published, THEN subscribers SHALL receive within 100ms

### Subtasks
- [ ] 1.1.1: Create Unix socket server
  - Validates: PROP-003
- [ ] 1.1.2: Implement pub/sub API
  - Validates: REQ-009
```

---

### 3. Gate Dashboard (TUI)

**File**: `ui/gate_dashboard.sh`

```bash
#!/bin/bash
# Interactive gate status viewer

nxs-gap-dashboard() {
    local current_gate=$(python3 $SPEC_MANAGER/core/gate_engine.py current)
    
    # Show gate pipeline with status indicators
    cat <<EOF
╔════════════════════════════════════════════════════════╗
║           GATED AGENT PROTOCOL - STATUS                ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  [✓] gate_intent    → intent.md      (COMPLETE)       ║
║  [✓] gate_invariant → spec.md        (COMPLETE)       ║
║  [→] gate_path      → plan.md        (ACTIVE)         ║
║  [⊗] gate_synthesis → walkthrough.md (LOCKED)         ║
║                                                        ║
╠════════════════════════════════════════════════════════╣
║  Current Role: Planner                                 ║
║  Current Task: Define implementation steps             ║
║  Coverage: 85% (17/20 goals traced)                    ║
╚════════════════════════════════════════════════════════╝

Actions:
  [e] Edit current artifact (plan.md)
  [v] View traceability map
  [t] Run property tests
  [a] Advance gate (if complete)
  [q] Quit
EOF
    
    # FZF menu for actions
    action=$(echo -e "Edit\nView\nTest\nAdvance\nQuit" | fzf --prompt="Action> ")
    
    case "$action" in
        Edit) nxs-gap-edit ;;
        View) nxs-gap-trace ;;
        Test) nxs-gap-test ;;
        Advance) nxs-gap-advance ;;
    esac
}
```

---

### 4. Property-Based Test Integration

**File**: `ui/property_runner.sh`

```bash
#!/bin/bash
# Run property-based tests and update status

nxs-gap-test() {
    local spec_file="$PROJECT_ROOT/spec.md"
    
    # Extract properties from spec.md
    properties=$(python3 $SPEC_MANAGER/core/traceability.py list-properties)
    
    # For each property, find corresponding test
    for prop in $properties; do
        test_file=$(find tests/ -name "*${prop}*.py" -o -name "*${prop}*.sh")
        
        if [[ -n "$test_file" ]]; then
            echo "Running: $prop → $test_file"
            
            # Run test and capture result
            if bash "$test_file"; then
                # Update property status: PASSING
                python3 $SPEC_MANAGER/core/gate_engine.py set-property-status "$prop" "passing"
            else
                # Update property status: FAILING
                python3 $SPEC_MANAGER/core/gate_engine.py set-property-status "$prop" "failing"
            fi
        else
            echo "⚠️  No test found for $prop"
        fi
    done
    
    # Show summary
    python3 $SPEC_MANAGER/core/gate_engine.py property-summary
}
```

---

### 5. Gate Advancement with Validation

**File**: `hooks/on_gate_complete.sh`

```bash
#!/bin/bash
# Validate gate completion before advancing

nxs-gap-advance() {
    local current_gate=$(python3 $SPEC_MANAGER/core/gate_engine.py current)
    
    echo "Validating $current_gate..."
    
    # Run gate-specific validation
    case "$current_gate" in
        gate_intent)
            # Check: All goals have constraints
            python3 $SPEC_MANAGER/core/artifact_validator.py validate-intent
            ;;
        gate_invariant)
            # Check: All properties validate goals
            python3 $SPEC_MANAGER/core/artifact_validator.py validate-spec
            ;;
        gate_path)
            # Check: 100% coverage (goals → tasks)
            python3 $SPEC_MANAGER/core/traceability.py validate-coverage
            ;;
        gate_synthesis)
            # Check: All tasks complete, all tests passing
            python3 $SPEC_MANAGER/core/artifact_validator.py validate-walkthrough
            ;;
    esac
    
    if [[ $? -eq 0 ]]; then
        echo "✓ Validation passed"
        echo "Advance to next gate? (y/n)"
        read -r confirm
        
        if [[ "$confirm" == "y" ]]; then
            python3 $SPEC_MANAGER/core/gate_engine.py advance
            echo "✓ Gate advanced"
        fi
    else
        echo "✗ Validation failed. Fix issues before advancing."
    fi
}
```

---

## Integration with Nexus-Shell

### Composition: `gap_workspace.json`

```json
{
  "name": "gap_workspace",
  "description": "Gated Agent Protocol development workspace",
  "layout": {
    "type": "hsplit",
    "panes": [
      {
        "id": "gap_dashboard",
        "size": 25,
        "command": "$WRAPPER $SPEC_MANAGER/ui/gate_dashboard.sh"
      },
      {
        "type": "vsplit",
        "panes": [
          {
            "id": "editor",
            "command": "$EDITOR_CMD"
          },
          {
            "type": "vsplit",
            "panes": [
              {
                "id": "terminal",
                "command": "/bin/zsh -i"
              },
              {
                "id": "test_runner",
                "command": "$WRAPPER tail -f /tmp/nexus_test.log"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Shell Commands

```bash
# Gate management
nxs-gap              # Open gate dashboard
nxs-gap-status       # Show current gate
nxs-gap-edit         # Edit current artifact
nxs-gap-advance      # Advance to next gate
nxs-gap-trace        # Show traceability map

# Artifact navigation
nxs-intent           # Open intent.md
nxs-spec             # Open spec.md
nxs-plan             # Open plan.md
nxs-walkthrough      # Open walkthrough.md

# Testing
nxs-gap-test         # Run all property tests
nxs-gap-test <prop>  # Run specific property test
nxs-gap-coverage     # Show traceability coverage

# Workflow
nxs-gap-init         # Initialize GAP for project
nxs-gap-reset        # Reset to gate_intent
```

---

## Event Bus Integration

The Spec Manager should publish events to the Nexus Event Bus:

```bash
# Gate events
GATE_ADVANCED: { "from": "gate_intent", "to": "gate_invariant" }
GATE_FAILED: { "gate": "gate_path", "reason": "coverage < 100%" }

# Property events
PROPERTY_PASSING: { "property": "PROP-003", "test": "test_event_latency.py" }
PROPERTY_FAILING: { "property": "PROP-001", "test": "test_pane_survival.py" }

# Task events
TASK_STARTED: { "task": "1.1", "gate": "gate_synthesis" }
TASK_COMPLETED: { "task": "1.1", "gate": "gate_synthesis" }
```

These events can trigger:
- Visual feedback (flash panes)
- Notifications
- Automated actions (run tests on task complete)

---

## Comparison: Old vs New Design

| Feature | Original Design | GAP-Aware Design |
|---------|----------------|------------------|
| **Workflow** | Kiro (req → design → tasks) | GAP (4 gates, role-based) |
| **Enforcement** | None (manual) | Strict gate sequencing |
| **Traceability** | Basic (task → req) | Full (task → prop → goal) |
| **Testing** | Manual PBT | Integrated property runner |
| **Validation** | None | Gate-specific validators |
| **UI** | Simple task list | Gate dashboard + trace view |
| **State** | tasks.md only | Full gate state machine |
| **Roles** | None | Analyst/Architect/Planner/Craft |

---

## Implementation Priority

### Phase 1: Core Engine (Week 1)
1. Gate state machine
2. Traceability parser
3. Basic validation

### Phase 2: UI (Week 1-2)
1. Gate dashboard
2. Artifact editor integration
3. Traceability viewer

### Phase 3: Testing Integration (Week 2)
1. Property test runner
2. Coverage reporting
3. Event bus integration

### Phase 4: Polish (Week 2-3)
1. Templates
2. Documentation
3. Example workflows

---

## Impact on PHASE_0_TASKS.md

**Task 1.4: Spec Manager Module** needs to be **completely rewritten**:

### Old Task (3-4 days)
- Task list viewer
- Status updates
- Navigation commands

### New Task (5-7 days)
- Gate state machine
- Traceability engine
- Artifact validators
- Gate dashboard
- Property test integration
- Event bus integration

**Estimated effort increase**: +2-3 days (now 5-7 days total)

---

## Benefits of GAP Integration

1. **Enforced Discipline**: Can't skip gates or bypass validation
2. **Full Traceability**: Every line of code traces to a requirement
3. **Automated Validation**: Property tests verify correctness
4. **Clear Progress**: Visual gate pipeline shows status
5. **Role Clarity**: Know what you should be doing at each stage
6. **Artifact Gravity**: Progress is cumulative and auditable

---

## Risks & Mitigations

### Risk 1: Complexity
**Mitigation**: Start with minimal implementation, iterate

### Risk 2: Overhead
**Mitigation**: Make validation fast (<1s), automate where possible

### Risk 3: User Friction
**Mitigation**: Provide escape hatches for prototyping, enforce for production

---

## Recommendation

**Implement GAP-aware Spec Manager** instead of simple task viewer.

**Why**:
1. Aligns with your stated workflow (from chatlog)
2. Enforces discipline you want (artifact gravity)
3. Provides traceability Scriptum needs
4. Integrates with property-based testing
5. Makes Nexus-Shell a true "development station"

**Trade-off**: +2-3 days of implementation time, but **much higher value**.

---

## Next Steps

1. **Review this design** with user
2. **Update PHASE_0_TASKS.md** with new Spec Manager tasks
3. **Create gate templates** (intent.md, spec.md, plan.md)
4. **Implement gate engine** (core state machine)
5. **Build gate dashboard** (TUI)

---

**End of Redesign Document**
