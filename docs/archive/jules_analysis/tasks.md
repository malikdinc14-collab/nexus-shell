# Nexus-Shell Phase 0 Completion Tasks

**Goal**: Complete Nexus-Shell to production-ready state with GAP integration  
**Timeline**: 3-4 weeks  
**Status**: Not Started

---

## Week 1: Critical Features

### Task 1.1: Event Bus Implementation (3-4 days)
**Priority**: CRITICAL  
**Validates**: Requirement 9 (Nexus Event Bus)

- [x] 1.1.1: Design event bus protocol
  - Define event types (FS_EVENT, TEST_EVENT, AI_EVENT, EDITOR_EVENT, GAP_EVENT)
  - Define message format (JSON)
  - Define socket location (`/tmp/nexus_$USER/$PROJECT/bus.sock`)
  - Document event schema

- [x] 1.1.2: Implement Unix socket server
  - Create `core/engine/bus/event_server.py`
  - Handle multiple client connections
  - Broadcast events to subscribers
  - Graceful shutdown on session end
  - Error handling and logging

- [x] 1.1.3: Create CLI client
  - Create `core/engine/bus/nxs-event` command
  - `nxs-event publish <type> <data>`
  - `nxs-event subscribe <type> <handler>`
  - `nxs-event list` (show active subscriptions)

- [x] 1.1.4: Integrate with station manager
  - Auto-start event bus on station init
  - Auto-stop on station cleanup
  - Add bus socket path to station state

- [ ] 1.1.5: Create example integrations
  - File watcher → FS_EVENT
  - Test runner → TEST_EVENT
  - Editor → EDITOR_EVENT (file opened, line changed)

**Acceptance Criteria**:
- Event bus starts automatically with station
- Multiple panes can publish/subscribe
- Events delivered within 100ms
- No memory leaks after 1000+ events

---

### Task 1.2: Fix Cross-Pane File Dispatch (2-3 days)
**Priority**: CRITICAL  
**Validates**: Requirement 2 (Composable Modularity)

- [ ] 1.2.1: Audit Neovim RPC reliability
  - Test current `--listen` pipe setup
  - Identify failure modes
  - Document workarounds
  - Test on macOS and Linux

- [ ] 1.2.2: Create robust RPC wrapper
  - Create `lib/nvim_rpc.sh`
  - Retry logic for pipe connection (3 attempts, 1s delay)
  - Timeout handling (5s max)
  - Clear error messages
  - Fallback to opening in new nvim instance

- [ ] 1.2.3: Integrate with Yazi
  - Configure Yazi to use RPC wrapper
  - Test file opening from Yazi
  - Handle edge cases (file not found, nvim not running, pipe missing)
  - Add visual feedback (flash border)

- [ ] 1.2.4: Create terminal dispatch command
  - Create `edit` command in shell_hooks.zsh
  - `edit file.txt` opens in editor pane
  - `view file.md` opens in render mode (glow)
  - Works from any pane
  - Publishes EDITOR_EVENT to bus

- [ ] 1.2.5: Add visual feedback
  - Flash editor pane border on file open
  - Show notification in status line
  - Log dispatch events to station log

**Acceptance Criteria**:
- `edit file.txt` works 100% of the time
- Yazi file selection opens in editor
- Clear error messages on failure
- Works across all compositions
- Visual feedback on success

---

### Task 1.3: AI Chat Auto-Launch (1-2 days)
**Priority**: HIGH  
**Validates**: Scriptum Requirement 12 (AI Tutor Integration)

- [ ] 1.3.1: Create chat tool detector
  - Check for opencode, aider, gptme in PATH
  - Check for API keys if needed (OPENAI_API_KEY, etc.)
  - Return best available tool
  - Fallback order: opencode → aider → gptme → none

- [ ] 1.3.2: Update pane wrapper for chat
  - Detect if pane is designated "chat"
  - Auto-launch detected tool
  - Fallback to shell if no tool available
  - Show helpful message if no tool found

- [ ] 1.3.3: Add chat tool configuration
  - Add `NEXUS_CHAT_TOOL` to tools.conf
  - Support "auto", "opencode", "aider", "gptme", "none"
  - Document configuration options in README
  - Add examples to tools.conf.example

- [ ] 1.3.4: Create chat commands
  - `tutor` command to focus chat pane
  - `ask <question>` to send to chat
  - Integration with event bus (AI_EVENT)
  - Keybinding to toggle chat pane

**Acceptance Criteria**:
- Chat tool auto-launches on station start
- Graceful fallback if tool not available
- User can configure preferred tool
- Works in all compositions with chat pane
- Clear error messages if misconfigured

---

### Task 1.4: GAP Integration - Core (5-7 days)
**Priority**: HIGH  
**Validates**: Requirement 7 (Integrated Agentic Workflow)

- [ ] 1.4.1: Install and configure GAP library
  - Clone/install Gated Agent Protocol repo
  - Add to Nexus-Shell dependencies
  - Test import in Python
  - Document installation in README

- [ ] 1.4.2: Create GAP harness wrapper
  - Create `modules/spec_manager/gap_integration/harness.py`
  - Wrap `gated_agent.registry.Registry`
  - Wrap `gated_agent.session.Session`
  - Wrap `gated_agent.security.ACLEnforcer`
  - Implement `NexusGAPHarness` class

- [ ] 1.4.3: Implement session management
  - Initialize `.gap/` directory structure
  - Create/load `gap.yaml` registry
  - Start new sessions
  - Archive artifacts
  - Load session history

- [ ] 1.4.4: Implement gate state machine
  - Track current gate (intent → invariant → path → synthesis)
  - Validate gate completion
  - Advance to next gate
  - Prevent gate skipping
  - Save/load state from `.gap/gap.yaml`

- [ ] 1.4.5: Create artifact validators
  - `validators/intent_validator.py` (check EARS syntax, goals, constraints)
  - `validators/spec_validator.py` (check architecture, properties, data models)
  - `validators/plan_validator.py` (check steps, traceability, ACL format)
  - `validators/walkthrough_validator.py` (check changes, tests, validation)

- [ ] 1.4.6: Implement ACL enforcement
  - Extract ACL from plan.md
  - Parse YAML block
  - Validate write permissions
  - Validate exec permissions
  - Raise PermissionError on denial

- [ ] 1.4.7: Create enforcement hooks
  - `hooks/on_write_attempt.sh` (intercept writes)
  - `hooks/on_exec_attempt.sh` (intercept execs)
  - Wrapper functions for vim/nvim/nano
  - Wrapper functions for common commands
  - Integration with shell_hooks.zsh

**Acceptance Criteria**:
- GAP library successfully integrated
- Can create and manage sessions
- Gate state machine works correctly
- Validators catch malformed artifacts
- ACL enforcement blocks unauthorized writes/execs
- Hooks intercept file operations

---

## Week 2: Testing & UI

### Task 2.1: GAP Integration - UI (3-4 days)
**Priority**: HIGH  
**Depends on**: Task 1.4

- [ ] 2.1.1: Create gate dashboard
  - `ui/gate_dashboard.sh` (FZF-based TUI)
  - Show current gate status
  - Show session info
  - Show ACL permissions
  - Show validation status
  - Interactive menu (edit, validate, advance, quit)

- [ ] 2.1.2: Create ACL viewer
  - `ui/acl_viewer.sh`
  - Show allowed writes
  - Show allowed execs
  - Highlight current permissions
  - Update in real-time

- [ ] 2.1.3: Create artifact editor integration
  - `ui/artifact_editor.sh`
  - Open current gate artifact in editor
  - Validate on save
  - Show validation errors
  - Prevent advancing if invalid

- [ ] 2.1.4: Create traceability viewer
  - `ui/traceability_view.sh`
  - Show goal → property → task links
  - Highlight missing links
  - Interactive navigation
  - Export to diagram

- [ ] 2.1.5: Create shell commands
  - `nxs-gap-init` (initialize session)
  - `nxs-gap-status` (show current gate)
  - `nxs-gap-dashboard` (open dashboard)
  - `nxs-gap-advance` (advance gate)
  - `nxs-gap-validate` (validate current gate)
  - `nxs-gap-acl` (show ACL)
  - `nxs-gap-history` (show session history)

- [ ] 2.1.6: Create GAP composition
  - `compositions/gap_workspace.json`
  - Gate dashboard pane (top)
  - Editor pane (center)
  - Terminal pane (bottom left)
  - ACL monitor pane (bottom right)
  - Test with real workflow

**Acceptance Criteria**:
- Dashboard shows accurate gate status
- ACL viewer shows current permissions
- Can edit and validate artifacts
- Traceability viewer shows links
- All commands work correctly
- Composition loads and functions

---

### Task 2.2: Property-Based Tests (3-4 days)
**Priority**: HIGH  
**Validates**: Design correctness properties

- [ ] 2.2.1: Set up test framework
  - Choose PBT library (Hypothesis for Python)
  - Create `tests/` directory structure
  - Add test runner script
  - Configure CI integration

- [ ] 2.2.2: Implement Property 1: Pane Indestructibility
  - Test: Kill random tools, pane survives
  - Test: Crash tools with SIGSEGV, pane survives
  - Test: Hub menu always appears
  - Test: No zombie processes

- [ ] 2.2.3: Implement Property 2: Path Zero-Entropy
  - Test: Clone repo to random location, still works
  - Test: Symlink launcher, still works
  - Test: All paths resolve correctly
  - Test: No hardcoded paths

- [ ] 2.2.4: Implement Property 3: Environment Hermeticity
  - Test: Modules don't leak variables
  - Test: Station variables available in all panes
  - Test: Clean environment after unload
  - Test: No conflicts between sessions

- [ ] 2.2.5: Implement Property 4: Session Interoperability
  - Test: Multiple windows share state
  - Test: State updates propagate
  - Test: No race conditions
  - Test: Concurrent access safe

- [ ] 2.2.6: Implement Property 5: Deterministic Layout
  - Test: Same composition → same layout
  - Test: Layout survives resize
  - Test: Pane IDs stable
  - Test: No layout drift

- [ ] 2.2.7: Implement Property 6: ACL Enforcement
  - Test: Unauthorized writes blocked
  - Test: Unauthorized execs blocked
  - Test: Authorized operations allowed
  - Test: ACL changes take effect immediately

**Acceptance Criteria**:
- All 6 properties have passing tests
- Tests run in CI
- Test coverage > 80% for core/
- No false positives/negatives

---

### Task 2.3: User Acceptance Testing (4-5 days)
**Priority**: HIGH  
**Depends on**: All Week 1 tasks

- [ ] 2.3.1: Daily usage test (1 week)
  - Use Nexus-Shell for all development work
  - Log issues and friction points
  - Measure boot time, responsiveness
  - Test all compositions
  - Test all commands

- [ ] 2.3.2: Stress testing
  - Open 10+ panes
  - Open 5+ windows
  - Run for 8+ hours
  - Monitor memory/CPU
  - Check for leaks

- [ ] 2.3.3: Tool crash recovery
  - Intentionally crash each tool
  - Verify pane survival
  - Verify state recovery
  - Test hub menu
  - Test restart

- [ ] 2.3.4: Performance profiling
  - Measure boot time (target: <2s)
  - Measure event latency (target: <100ms)
  - Measure memory usage (target: <500MB)
  - Identify bottlenecks
  - Optimize hot paths

- [ ] 2.3.5: Raspberry Pi testing
  - Install on Pi 4
  - Test all features
  - Identify performance issues
  - Optimize if needed
  - Document Pi-specific setup

**Acceptance Criteria**:
- No critical bugs found
- Performance meets targets
- Works reliably on Pi
- User satisfaction high
- All features functional

---

## Week 3: Polish & Documentation

### Task 3.1: Documentation (2-3 days)
**Priority**: MEDIUM  
**Depends on**: All features complete

- [ ] 3.1.1: User guide
  - Getting started
  - Installation (macOS, Linux, Pi)
  - Core workflows
  - Keybindings reference
  - Troubleshooting
  - FAQ

- [ ] 3.1.2: GAP workflow guide
  - What is GAP
  - How to use gates
  - Understanding ACLs
  - Session management
  - Best practices
  - Examples

- [ ] 3.1.3: Module development guide
  - Module structure
  - Manifest format
  - Integration patterns
  - Testing
  - Publishing

- [ ] 3.1.4: Composition creation guide
  - JSON format
  - Layout syntax
  - Tool configuration
  - Examples
  - Best practices

- [ ] 3.1.5: Video tutorials
  - Installation (5 min)
  - Basic usage (10 min)
  - GAP workflow (15 min)
  - Advanced features (20 min)

**Acceptance Criteria**:
- New user can install and use without help
- All features documented
- Examples for common tasks
- Videos clear and concise

---

### Task 3.2: Module Ecosystem (2-3 days)
**Priority**: LOW  
**Depends on**: Core features complete

- [ ] 3.2.1: Add essential modules
  - ripgrep (search)
  - bat (previews)
  - delta (git diffs)
  - eza (better ls)
  - btop (system monitor)

- [ ] 3.2.2: Wire up existing modules
  - lazygit keybinding
  - gptme integration
  - opencode integration
  - micro as alternative editor

- [ ] 3.2.3: Create module marketplace
  - List available modules
  - One-command install
  - Dependency management
  - Update mechanism

- [ ] 3.2.4: Module templates
  - Template for new modules
  - Example module
  - Testing template
  - Documentation template

**Acceptance Criteria**:
- All recommended modules available
- Easy to discover and install
- No conflicts or issues
- Clear documentation

---

### Task 3.3: Final Polish (2-3 days)
**Priority**: MEDIUM  
**Depends on**: All features complete

- [ ] 3.3.1: Error handling improvements
  - Better error messages
  - Helpful suggestions
  - Recovery instructions
  - Logging improvements

- [ ] 3.3.2: Performance optimizations
  - Reduce boot time
  - Optimize event bus
  - Cache ACL checks
  - Reduce memory usage

- [ ] 3.3.3: UX improvements
  - Better visual feedback
  - Smoother animations
  - Clearer status indicators
  - Keyboard shortcuts

- [ ] 3.3.4: Bug fixes
  - Fix known issues
  - Address user feedback
  - Edge case handling
  - Stability improvements

- [ ] 3.3.5: Release preparation
  - Version bump
  - Changelog
  - Release notes
  - Tag release

**Acceptance Criteria**:
- No known critical bugs
- Performance targets met
- UX polished
- Ready for release

---

## Optional: Future Features (Defer to Post-Hardware)

### Task 4.1: Tabbed Interfaces
- [ ] Shell tabs (tmux sub-windows)
- [ ] Parallax tabbed views
- [ ] Tab navigation keybindings

### Task 4.2: Follower Mode
- [ ] Leader/follower protocol
- [ ] Context mirroring
- [ ] Multi-screen support

### Task 4.3: Headless Daemon
- [ ] Background persistence
- [ ] Resume capability
- [ ] Remote attachment

---

## Success Metrics

### Completion Criteria
- [ ] All Week 1 tasks complete
- [ ] All Week 2 tests passing
- [ ] Documentation complete
- [ ] 1 week of stable daily usage
- [ ] Works on Raspberry Pi
- [ ] Ready for Scriptum integration

### Performance Targets
- Boot time: <2 seconds
- Event latency: <100ms
- Memory usage: <500MB
- CPU usage: <10% idle

### Quality Targets
- Test coverage: >80%
- No critical bugs
- No memory leaks
- No crashes in 1 week

---

## Risk Mitigation

### High Risk Items
1. **Event Bus complexity**
   - Mitigation: Start with simple implementation, iterate
   - Fallback: Use file-based events if sockets fail

2. **Neovim RPC reliability**
   - Mitigation: Extensive testing, retry logic
   - Fallback: Use file-based dispatch if RPC fails

3. **GAP library integration**
   - Mitigation: Test early, document issues
   - Fallback: Simplified GAP-inspired implementation

4. **Pi performance**
   - Mitigation: Profile early, optimize critical paths
   - Fallback: Reduce features if needed

---

## Notes

- Tasks are ordered by priority and dependencies
- Estimated times are for focused work
- Some tasks can be parallelized
- Testing should be continuous, not just Week 2
- User feedback should inform all tasks

---

**End of Tasks**
