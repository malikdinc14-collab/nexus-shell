# Requirements: Nexus Shell Integrations & Spec Manager

## 1. Spec Manager Functional Requirements (GAP Harness)
- **R-01: Deterministic Gate Sequencing**: The Spec Manager must enforce a non-skippable pipeline (Intent → Invariant → Path → Synthesis).
- **R-02: Artifact-Linked Permissions**: Access Control Lists (ACLs) must be derived from approved `plan.md` artifacts.
- **R-03: Multi-Tab Rendering**: The Spec Manager must support simultaneous high-fidelity rendering of all 4 mission artifacts across terminal tabs.
- **R-04: Automated Traceability**: The system must verify links between Requirements (Audit-Analyst), Invariants (Audit-Architect), and Tasks (Audit-Planner).

## 2. Platform Integration Requirements
- **R-05: Modeless Navigation**: Key integration commands (e.g., `nxs-gap-status`) must be available globally via the Nexus modifier (`Alt`).
- **R-06: Unified Render Engine**: All spec management UI must delegate to `nxs-view` for Mermaid diagram and high-fidelity text display.
- **R-07: Event Bus Propagation**: Every state change (Gate Advance, ACL load, Permission Denied) must be broadcast to the Nexus Event Bus.

## 3. Security Requirements
- **R-08: Write-Lock Isolation**: Any terminal pane associated with a GAP mission must be locked into read-only mode until a plan is approved.
- **R-09: Secure Key Management**: Integrations must use `nxs-keys.sh` (macOS Keychain) for all AI model authentication.
