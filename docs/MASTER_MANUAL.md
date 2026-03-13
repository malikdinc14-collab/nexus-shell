# 📕 Nexus Shell: The Master Manual

This is the definitive guide to the Nexus Shell "Intelligence OS". Use this document to master the navigation, orchestration, and autonomous capabilities of your workstation.

---

## 1. Getting Started
Nexus Shell is a self-contained, high-performance development environment.

### **Launching the Station**
```bash
# Basic launch
./bin/nxs

# Launch with profile and layout
./bin/nxs --profile sovereign --layout sovereign-control

# List all available options
./bin/nxs --list
```

---

## 2. Core Navigation
Mastering the interface is about speed and muscle memory.

### **The Multi-Slot System**
Nexus supports up to 10 independent **Window Slots** per project.
- **`Alt + 1` to `Alt + 9`**: Switch between active slots instantly.
- **`Alt + 0`**: Jump to the primary Window 0.

### **Pane Management**
- **`Alt + h/j/k/l`**: Move focus between panes (Vim-style).
- **`Alt + Esc`**: Enter **NORMAL MODE** for resizing (`H/J/K/L`) and navigation.
- **`Alt + z`**: Maximize the current pane (Toggle Zoom).

---

## 3. The Nervous System (Event Bus & AI)
Nexus is a coordinated intelligence environment, powered by the **Event Bus**.

### **Real-time Interaction**
- **`nxs-ask "[mission]"`**: Send a task to the background AI daemon (SID).
- **`nxs-ai-stream`**: View the real-time thought stream and reasoning of the agent.
- **`nxs-event subscribe [TYPE]`**: Listen to specific signals on the bus.

### **SID (Sovereign Intelligence Daemon)**
The SID bridges your activity and the agent's logic. It monitors logs and broadcasts signals (like File Open events) to keep your workspace in sync.

---

## 4. Workflows & Profiles
Nexus adapts to your current task via **Profiles**.

### **Switching Contexts**
Use the command palette (`Ctrl + \`) or the CLI flag (`--profile`) to swap:
- **`sovereign`**: Full AI integration with GAP briefing.
- **`focus`**: Minimalist layout with distraction-free defaults.
- **`swarm`**: Multi-agent orchestration layout.

### **The RDT Cycle**
Manage complex features through **Requirements**, **Design**, and **Tasks**. 
- Access the **Workflow (`Alt + W`)** tab to browse and audit project specs.

---

## 5. Maintenance & Safety
Keep your 48GB Mac stable and secure.

### **Vitals Check**
- **`Alt + M`**: Monitor GPU load and RAM pressure.
- **`scripts/verify_bus.sh`**: Verify Event Bus health.
- **`scripts/verify_sid.sh`**: Verify AI Daemon status.

### **The Resource Guard**
Located in `Brains > 🛡️ Resource Guard`. Automatically shuts down local models (`:down`) if RAM usage exceeds **44GB** to prevent system locks.

---
**Index**: [SOVEREIGN_INDEX.md](../SOVEREIGN_INDEX.md)
