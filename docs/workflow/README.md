# RDT Workflow: Requirements -> Design -> Tasks

This directory manages the lifecycle of your engineering projects within Nexus-Shell.

## 📁 Structure
- **`requirements/`**: High-level functional and technical goals (`REQ-001.md`).
- **`design/`**: Architectural specs and logic flow (`DSN-001.md`).
- **`tasks/`**: Concrete implementation items (`TSK-001.md`).
- **`flight_recorder/`**: (Automated) Transaction logs of every agent-applied code edit.

## 🔗 Traceability
Every task should be interlinked back to a design and a requirement. 
Use the following markdown format for automatic parsing in the Parallax UI:
`[REQ-001](../requirements/REQ-001.md)`

## 🤖 Agentic Control
Your agents (like the Resident Engineer) are instructed to follow this workflow. They will:
1.  Read requirements first.
2.  Propose or update design docs.
3.  Break down work into tasks.
4.  Stage transactions only when a task is active.

## ⌨️ Command Line Utility
Use `px-workflow` to manage links and status from the shell:
- `px-workflow list`: Show all docs.
- `px-workflow link REQ-001 DSN-001`: Establish a two-way link.
- `px-workflow status TSK-001 "Completed"`: Update task progress.
