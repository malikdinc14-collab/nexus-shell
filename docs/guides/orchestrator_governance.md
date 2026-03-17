# Orchestrator Governance Guide

This guide explains how to configure and use the **Orchestrator** capability in Nexus Shell to manage hierarchical agent missions.

## 1. Profile Configuration

An Orchestrator is defined by a `governance` block in its `.yaml` profile (e.g., `config/profiles/sovereign.yaml`).

```yaml
# config/profiles/sovereign.yaml
env:
  NEXUS_ROLE: "sovereign"

governance:
  can_spawn: true
  role: "orchestrator"  # Elevates the kernel to Orchestrator mode
  max_depth: 2          # Limits how many agents can be spawned in a chain
  allowed_sub_profiles: # Whitelist of agents this orchestrator can manage
    - praxis
    - distiller
    - researcher
```

## 2. Creating an Orchestrator Mission

When you start an agent with the `sovereign` profile, it initializes a Permissioned Kernel. This kernel unlocks the `spawn_agent` tool.

### Hierarchical Resource Tracking
All sub-agents spawned by an orchestrator inherit the `group_id` of the mission. This ensures that:
1. You can see the entire fleet status in the HUD.
2. You can perform an **Emergency Kill** on the whole group at once.
3. Resource budgets (tokens/cost) are aggregated across the group.

## 3. Safety Constraints

- **No New Profiles**: Agents cannot "hallucinate" new roles. They are strictly limited to the YAML profiles pre-defined in your `~/.nexus/profiles` directory.
- **VFS Isolation**: Child agents are sandboxed into sub-directories, preventing them from interfering with the Orchestrator's internal reasoning files.
- **Immutable Roots**: Sub-agents cannot re-spawn another Orchestrator, preventing "Agent Fork Bombs."

## 4. Troubleshooting

If an agent reports `Permission Denied: Profile is not authorized to spawn agents`, check:
1. That `NEXUS_ROLE` or a governance flag is correctly set in the profile.
2. That the agent was provisioned via the `agent_cli.py` which supports the new Recursive Agency protocol.
