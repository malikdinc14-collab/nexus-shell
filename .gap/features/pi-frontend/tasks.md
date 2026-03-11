# Tasks: Pi Frontend Integration

## Phase 1: Infrastructure
- [ ] **1.1: Agent Zero Endpoint Audit**
    - [ ] Determine exactly what WS/HTTP port and protocol Agent Zero exposes its chat UI over.
- [ ] **1.2: Pi CLI Configuration**
    - [ ] Install or configure `pi` locally in the Nexus Shell footprint.
    - [ ] Draft the YAML/JSON config allowing `pi` to talk to the local background process instead of an external API.

## Phase 2: Integration
- [ ] **2.1: The Custom Wrapper**
    - [ ] Write `bin/nxs-chat` to initialize the `pi` process with the custom config file forcefully.
- [ ] **2.2: Composition Update**
    - [ ] Edit `compositions/ai-pair.json` to swap the generic `echo` or `agent-zero` command with the new `nxs-chat` wrapper.

## Success Criteria
- [ ] Running `nxs -c ai-pair` seamlessly boots the Daemon Agent (if stopped) and drops the user directly into a fully-functional `pi` TUI connected to the agent.
