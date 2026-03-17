# Phase 0: Nexus-Shell Completion Tasks

**Timeline**: 2-3 weeks  
**Goal**: Complete Nexus-Shell to production-ready state for Scriptum integration

---

## Week 1: Critical Features

### Task 1.1: Implement Event Bus (3-4 days)
**Priority**: CRITICAL  
**Dependencies**: None  
**Validates**: Requirement 9 (Nexus Event Bus)

#### Subtasks:
- [ ] 1.1.1: Design event bus protocol
  - Define event types (FS_EVENT, TEST_EVENT, AI_EVENT, EDITOR_EVENT)
  - Define message format (JSON)
  - Define socket location (`/tmp/nexus_$USER/$PROJECT/bus.sock`)

- [ ] 1.1.2: Implement Unix socket server
  - Create `core/engine/bus/event_server.py`
  - Handle multiple client connections
  - Broadcast events to subscribers
  - Graceful shutdown on session end

- [ ] 1.1.3: Create CLI client
  - Create `core/engine/bus/nxs-event` command
  - `nxs-event publish <type> <data>`
  - `nxs-event subscribe <type> <handler>`
  - `nxs-event list` (show active subscriptions)

- [ ] 1.1.4: Integrate with station manager
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
**Dependencies**: None  
**Validates**: Requirement 2 (Composable Modularity)

#### Subtasks:
- [ ] 1.2.1: Audit Neovim RPC reliability
  - Test current `--listen` pipe setup
  - Identify failure modes
  - Document workarounds

- [ ] 1.2.2: Create robust RPC wrapper
  - Create `lib/nvim_rpc.sh`
  - Retry logic for pipe connection
  - Timeout handling
  - Error messages

- [ ] 1.2.3: Integrate with Yazi
  - Configure Yazi to use RPC wrapper
  - Test file opening from Yazi
  - Handle edge cases (file not found, nvim not running)

- [ ] 1.2.4: Create terminal dispatch command
  - Create `edit` command in shell_hooks.zsh
  - `edit file.txt` opens in editor pane
  - `view file.md` opens in render mode
  - Works from any pane

- [ ] 1.2.5: Add visual feedback
  - Flash editor pane border on file open
  - Show notification in status line
  - Log dispatch events

**Acceptance Criteria**:
- `edit file.txt` works 100% of the time
- Yazi file selection opens in editor
- Clear error messages on failure
- Works across all compositions

---

### Task 1.3: AI Chat Auto-Launch (1-2 days)
**Priority**: HIGH  
**Dependencies**: None  
**Validates**: Requirement 12 (AI Tutor Integration - Scriptum)

#### Subtasks:
- [ ] 1.3.1: Create chat tool detector
  - Check for opencode, aider, gptme in PATH
  - Check for API keys if needed
  - Return best available tool

- [ ] 1.3.2: Update pane wrapper for chat
  - Detect if pane is designated "chat"
  - Auto-launch detected tool
  - Fallback to shell if no tool available

- [ ] 1.3.3: Add chat tool configuration
  - Add `NEXUS_CHAT_TOOL` to tools.conf
  - Support "auto", "opencode", "aider", "gptme", "none"
  - Document configuration options

- [ ] 1.3.4: Create chat commands
  - `tutor` command to focus chat pane
  - `ask <question>` to send to chat
  - Integration with event bus

**Acceptance Criteria**:
- Chat tool auto-launches on station start
- Graceful fallback if tool not available
- User can configure preferred tool
- Works in all compositions with chat pane

---

### Task 1.4: Spec Manager Module (MVP) (3-4 days)
**Priority**: HIGH  
**Dependencies**: Event Bus (optional)  
**Validates**: Requirement 7 (Integrated Agentic Workflow)

#### Subtasks:
- [ ] 1.4.1: Create module structure
  - Create `modules/spec_manager/`
  - Add manifest.json
  - Add install.sh, init.zsh

- [ ] 1.4.2: Implement task list viewer
  - Parse tasks.md (markdown checkbox format)
  - Display in FZF with status indicators
  - Color coding (not started, in progress, complete)

- [ ] 1.4.3: Implement task status updates
  - Select task → mark in progress
  - Select task → mark complete
  - Update tasks.md file atomically

- [ ] 1.4.4: Add navigation commands
  - `nxs-tasks` - open task viewer
  - `nxs-req` - open requirements.md
  - `nxs-design` - open design.md
  - `nxs-spec` - open all spec files in splits

- [ ] 1.4.5: Create composition with spec pane
  - Add "spec_manager" composition
  - Dedicated pane for task tracking
  - Auto-refresh on file changes

**Acceptance Criteria**:
- Can view and update task status
- Changes persist to tasks.md
- Works with Kiro task format
- Accessible from any pane

---

## Week 2: Testing & Validation

### Task 2.1: Property-Based Tests (3-4 days)
**Priority**: HIGH  
**Dependencies**: All Week 1 tasks  
**Validates**: Design correctness properties

#### Subtasks:
- [ ] 2.1.1: Set up test framework
  - Choose PBT library (Hypothesis for Python, or shell-based)
  - Create `tests/` directory structure
  - Add test runner script

- [ ] 2.1.2: Implement Property 1: Pane Indestructibility
  - Test: Kill random tools, pane survives
  - Test: Crash tools with SIGSEGV, pane survives
  - Test: Hub menu always appears

- [ ] 2.1.3: Implement Property 2: Path Zero-Entropy
  - Test: Clone repo to random location, still works
  - Test: Symlink launcher, still works
  - Test: All paths resolve correctly

- [ ] 2.1.4: Implement Property 3: Environment Hermeticity
  - Test: Modules don't leak variables
  - Test: Station variables available in all panes
  - Test: Clean environment after unload

- [ ] 2.1.5: Implement Property 4: Session Interoperability
  - Test: Multiple windows share state
  - Test: State updates propagate
  - Test: No race conditions

- [ ] 2.1.6: Implement Property 5: Deterministic Layout
  - Test: Same composition → same layout
  - Test: Layout survives resize
  - Test: Pane IDs stable

**Acceptance Criteria**:
- All 5 properties have passing tests
- Tests run in CI
- Test coverage > 80% for core/

---

### Task 2.2: User Acceptance Testing (4-5 days)
**Priority**: HIGH  
**Dependencies**: All Week 1 tasks  
**Validates**: Real-world usability

#### Subtasks:
- [ ] 2.2.1: Daily usage test (1 week)
  - Use Nexus-Shell for all development work
  - Log issues and friction points
  - Measure boot time, responsiveness

- [ ] 2.2.2: Stress testing
  - Open 10+ panes
  - Open 5+ windows
  - Run for 8+ hours
  - Monitor memory/CPU

- [ ] 2.2.3: Tool crash recovery
  - Intentionally crash each tool
  - Verify pane survival
  - Verify state recovery

- [ ] 2.2.4: Performance profiling
  - Measure boot time (target: <2s)
  - Measure event latency (target: <100ms)
  - Measure memory usage (target: <500MB)

- [ ] 2.2.5: Raspberry Pi testing
  - Install on Pi 4
  - Test all features
  - Identify performance issues
  - Optimize if needed

**Acceptance Criteria**:
- No critical bugs found
- Performance meets targets
- Works reliably on Pi
- User satisfaction high

---

## Week 3: Polish & Documentation

### Task 3.1: Documentation (2-3 days)
**Priority**: MEDIUM  
**Dependencies**: All features complete  
**Validates**: Usability for new users

#### Subtasks:
- [ ] 3.1.1: User guide
  - Getting started
  - Core workflows
  - Keybindings reference
  - Troubleshooting

- [ ] 3.1.2: Module development guide
  - Module structure
  - Manifest format
  - Integration patterns
  - Testing

- [ ] 3.1.3: Composition creation guide
  - JSON format
  - Layout syntax
  - Tool configuration
  - Examples

- [ ] 3.1.4: Video tutorials
  - Installation (5 min)
  - Basic usage (10 min)
  - Advanced workflows (15 min)

**Acceptance Criteria**:
- New user can install and use without help
- All features documented
- Examples for common tasks

---

### Task 3.2: Module Ecosystem (2-3 days)
**Priority**: LOW  
**Dependencies**: None  
**Validates**: Completeness

#### Subtasks:
- [ ] 3.2.1: Add essential modules
  - ripgrep (search)
  - bat (previews)
  - delta (git diffs)

- [ ] 3.2.2: Wire up existing modules
  - lazygit keybinding
  - gptme integration
  - opencode integration

- [ ] 3.2.3: Create module marketplace
  - List available modules
  - One-command install
  - Dependency management

**Acceptance Criteria**:
- All recommended modules available
- Easy to discover and install
- No conflicts or issues

---

## Optional: Future Features (Defer to Post-Hardware)

### Task 4.1: Tabbed Interfaces
- Shell tabs
- Parallax tabs
- Tab navigation

### Task 4.2: Follower Mode
- Leader/follower protocol
- Context mirroring
- Multi-screen support

### Task 4.3: Headless Daemon
- Background persistence
- Resume capability
- Remote attachment

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

3. **Pi performance**
   - Mitigation: Profile early, optimize critical paths
   - Fallback: Reduce features if needed

---

## Next Actions

1. Review this plan with user
2. Set up development environment
3. Create feature branches for each task
4. Begin with Task 1.1 (Event Bus)
5. Daily standups to track progress

---

**End of Phase 0 Tasks**
