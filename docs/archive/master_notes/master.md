# 🗺️ Nexus Shell: The Exhaustive Sovereign Index (Zero-Trust Map)

> [!CAUTION]
> **AUDIT STATUS**: `100% Visible Scanned | 0% Verified`
> I have performed a deep-drill audit of 630+ files. This map now captures the exhaustive geometry of the system.
> **DARK ZONES Identified**: Some directories (e.g., `external/`, `node_modules/`) are permission-locked or ignored.

---

## 🏛️ Layer 0: The Soul (Ideology, Standards & Roots)
*The fundamental invariants and strategic guidance.*

- [ ] `docs/vision.md`: Modeless Sovereignty & Philosophy.
- [ ] `ROADMAP.md`: Strategic Evolution (Foundations → AI Sovereignty).
- [ ] `LICENSE`: MIT Sovereign Permissive License.
- [ ] `install.sh` / `uninstall.sh`: The entry/exit lifecycle.

---

## 🏗️ Layer 1: The Matrix (The Intelligence Nervous System)
*The core logic, event bus, and bridge services that enable the "Live Shell".*

### 📡 Event Bus & Mesh (`core/bus/`)
- [ ] `core/bus/event_server.py`: Unix Domain Socket Pub/Sub.
- [ ] `core/bus/test_event_bus.sh`: Mesh verification logic.
- [ ] `scripts/verify_bus.sh`: Standalone diagnostic.

### 🛡️ Governance & GAP (`core/services/`, `.gap/`)
- [ ] `core/services/gap_service.sh`: GAP Mission polling and alignment.
- [ ] `core/services/gap_bridge.sh`: The isolated bridge to the GAP protocol.
- [ ] `core/exec/nxs-gap-spec.sh`: Multi-tab mission spec renderer.
- [ ] `.gap/features/`: Active mission definitions & status gaging.

### 🧠 Logic & Execution Flow (`core/boot/`, `core/exec/`)
- [ ] `core/boot/launcher.sh`: Master boot orchestrator.
- [ ] `core/boot/onboarding.sh` / `setup_wizard.sh`: UX initialization.
- [ ] `core/exec/router.sh`: Global command dispatcher.
- [ ] `core/exec/nxs-tab.sh`: Sovereign tab life-cycle management.
- [ ] `core/exec/dap_handler.sh`: Headless Debug Adapter Protocol.

---

## 🦾 Layer 2: The Body (Physical Geometry & Artifacts)
*The modules, binaries, compositions, and configurations that render the workspace.*

### 🛠️ The Binaries (`bin/`)
- [ ] `bin/nxs`: Core entry point.
- [ ] `bin/nxs-view`: The Sovereign Renderer.
- [ ] `bin/nxs-agent-boot.sh`: Universal Agent dispatcher.
- [ ] `bin/nxs-keys.sh`: macOS Keychain Security Shield.

### 🧩 The Modules (46 Logical Units)
- [ ] `modules/agents`, `modules/agent-zero`, `modules/bandwhich`, `modules/bottom`, `modules/btop`, `modules/cava`, `modules/coding-agent`, `modules/dive`, `modules/editor`, `modules/fzf`, `modules/gh-dash`, `modules/glances`, `modules/glow`, `modules/gptme`, `modules/gum`, `modules/harlequin`, `modules/k9s`, `modules/lazydocker`, `modules/lazygit`, `modules/lazysql`, `modules/menu`, `modules/micro`, `modules/ncspot`, `modules/nmap`, `modules/nvim`, `modules/opencode`, `modules/openevolve`, `modules/optillm`, `modules/pi`, `modules/posting`, `modules/presenterm`, `modules/process-compose`, `modules/render`, `modules/sc-im`, `modules/serie`, `modules/slumber`, `modules/spotify-player`, `modules/taskwarrior-tui`, `modules/television`, `modules/termscp`, `modules/termshark`, `modules/trippy`, `modules/visidata`, `modules/web`, `modules/yazi`, `modules/zellij`.

### 🎭 Compositions (`compositions/`)
- [ ] `ai-pair.json`, `ascent.json`, `conflict_matrix.json`, `data-eng.json`, `debug_tools.json`, `devops.json`, `gap-mission.json`, `git-review.json`, `minimal.json`, `music.json`, `music-studio.json`, `network.json`, `onboarding.json`, `quad.json`, `quad_parallax.json`, `school.json`, `simple.json`, `sovereign-control.json`, `sre.json`, `terminal.json`, `vscodelike.json`, `writer.json`.

### 🎚️ Profiles & Config (`config/`)
- [ ] `config/profiles/`: `agent-stream.yaml`, `ascent.yaml`, `focus.yaml`, `music.yaml`, `school.yaml`, `sovereign.yaml`, `swarm.yaml`.
- [ ] `config/keybinds/`: `default.conf`, `minimal.conf`, `user.conf`, `vim.conf`.

---

## 🚀 Layer 3: The Vector (Momentum, Debt & The Horizon)
*Active missions, technical debt, and planned evolution.*

### 📍 Tech Debt & Pending Invariants (Audit Findings)
- [ ] **State Sync**: `core/state/state_engine.sh` → TODO: Cloud/Remote sync.
- [ ] **Agent Zero**: `services/agent-zero/agent.py` → TODO: Message range/topic/history.
- [ ] **Browser Integration**: `services/agent-zero/python/tools/browser_agent.py` → TODO: Timeout cleanup.

### 🌌 Dark Zones (Visible but Locked/Ignored)
- [ ] `external/`: OptiLLM, Agency-Agents, OpenEvolve, Pi-Mono (Security locked).
- [ ] `node_modules/`: (Ignored by default, but present in `opencode`).

---

**Map Version**: `1.1.0 (Exhaustive)`
**Audit ID**: `NX-DRIL-630`
**Timestamp**: 2026-03-14 12:45
**Integrity**: `VERIFICATION_REQUIRED`
