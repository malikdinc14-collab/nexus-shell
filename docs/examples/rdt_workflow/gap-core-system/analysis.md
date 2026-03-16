# Analysis: Current GAP Implementation vs Plan Layer Requirements

## Current Implementation Status

### ✅ Already Implemented
1. **Manifest System** (`manifest.py`)
   - YAML parsing with protocol inheritance
   - Phase definitions (requirements, design, tasks, implementation)
   - Step dependencies and gate configuration
   - Checkpoint strategy configuration

2. **Ledger System** (`ledger.py`)
   - Status tracking for steps
   - Hybrid reality check (file existence + dependencies)
   - Status persistence in `.gap/status.yaml`

3. **Gate System** (`gate.py`)
   - Proposal approval workflow
   - ACL extraction from proposals
   - File movement from proposals to live
   - Ledger status updates

4. **Security/ACL** (`security.py`)
   - ACL parsing from YAML blocks in artifacts
   - ACL storage for next gate
   - Basic ACL context model

5. **Checkpoint System** (`checkpoint.py`)
   - Runtime checkpoint verification
   - Strategy-based pause enforcement
   - Manual checkpoint approval

6. **CLI Structure**
   - `gap check status` - Current state
   - `gap scribe create` - Artifact generation
   - `gap gate list/approve` - Approval management
   - `gap checkpoint verify/approve` - Runtime gates

### 🔄 Partially Implemented (Needs Extension)
1. **Task Model**
   - Currently: Tasks are just files (`tasks.md`)
   - Needed: Structured Task model with traceability
   - Needed: Task YAML format with IDs and references

2. **Plan Layer**
   - Currently: ACL stored per-step in `.gap/acls/`
   - Needed: Unified Plan file with execution envelopes
   - Needed: Plan construction workflow
   - Needed: Plan validation and consistency checks

3. **Execution Envelopes**
   - Currently: Basic ACL (write/exec permissions)
   - Needed: Full envelope (ACL + model + locality + checkpoints)
   - Needed: Envelope approval workflow

## Gaps to Address

### 1. Task Structure (Req-2)
**Current**: Tasks are markdown files with checkboxes
**Required**: Dual-format approach:
- **Machine-readable**: `.gap/tasks.yaml` (structured YAML)
- **Human-readable**: `docs/tasks.md` (rendered markdown)
- Task IDs (T-1, T-2, etc.)
- Traceability to design/requirements
- Expected outputs
- No execution context

**Changes Needed**:
- New Task model in `models.py`
- Task YAML parser and serializer
- Task sync module for YAML ↔ Markdown conversion
- Traceability validation
- Integration with existing ledger

### 2. Plan File Structure (Req-3)
**Current**: ACL stored in separate files per step
**Required**: Unified `.gap/plan.yaml` with:
- Task-to-envelope mapping
- Complete execution envelopes
- Approval metadata

**Changes Needed**:
- New `plan.py` module
- Plan schema definition
- Plan validation
- Plan construction CLI

### 3. Enhanced Gate System (Req-4, Req-6)
**Current**: `gap gate approve` moves files and stores ACL
**Required**: `gap gate approve --edit-envelope` with:
- Interactive envelope builder
- Model selection
- Checkpoint configuration
- Plan file generation

**Changes Needed**:
- Extend `gate.py` for envelope editing
- Interactive form for envelope fields
- Plan file creation/update
- Ledger integration with envelope data

### 4. Drift Detection (Req-5)
**Current**: Basic dependency validation
**Required**: Full drift detection against Plan:
- ACL violation detection
- Model compliance checking
- Checkpoint enforcement
- Drift reporting and resolution

**Changes Needed**:
- Extend `auditor.py` for Plan validation
- Execution action logging
- Drift detection algorithms
- Drift resolution workflow

### 5. Enhanced CLI (Req-6)
**Current**: Basic commands
**Required**: Plan management commands:
- `gap plan show <task-id>`
- `gap plan edit <task-id>`
- `gap plan validate`
- `gap plan diff`

**Changes Needed**:
- New `plan.py` command module
- Plan inspection commands
- Plan validation commands
- Plan comparison tools

## Migration Strategy

### Phase 1: Backward Compatibility
1. Keep existing `.gap/acls/` structure for now
2. Add `.gap/plan.yaml` as optional enhancement
3. Support both old and new formats during transition

### Phase 2: Task Model Migration
1. Add Task YAML support alongside markdown
2. Provide migration tool for existing projects
3. Update templates to use new format

### Phase 3: Plan Layer Integration
1. Extend gate system for envelope editing
2. Update ledger to store envelope data
3. Enhance checkpoint system for Plan checkpoints

### Phase 4: Deprecation
1. Mark old ACL format as deprecated
2. Provide migration path to new Plan format
3. Remove old format in future version

## Risk Assessment

### High Risk
- **Breaking changes** to existing workflow
- **Data loss** during migration
- **Complexity** of new Plan system

### Mitigation Strategies
1. **Incremental rollout** - Add features without removing old ones
2. **Migration tools** - Automated conversion from old to new
3. **Compatibility mode** - Support both formats during transition
4. **Extensive testing** - Validate all migration paths

## Success Metrics
1. All existing tests pass with new system
2. Migration tools work for sample projects
3. Plan construction workflow is intuitive
4. Drift detection catches violations
5. Performance remains acceptable

## Next Steps
1. Review this analysis with stakeholders
2. Prioritize implementation phases
3. Create detailed design for each component
4. Implement with extensive testing
5. Document migration process