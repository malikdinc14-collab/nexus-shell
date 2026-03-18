# Nexus Shell Installation Rules

## Foundational Principle: User Consent and Preference
Nexus Shell is a deeply integrated terminal environment. As such, it must never mutate the user's system without explicit, interactive consent.

1. **Strict User Preference**: The `profile.yaml` file is the ultimate source of truth. If a capability (Editor, Explorer, Menu) is explicitly configured there, the `CapabilityRegistry` must select that adapter.
2. **Interactive Prompts for Missing Tools**: If a user selects a tool (e.g., `textual` or `yazi`) that is **not currently installed** on their machine, Nexus Shell **MUST ASK** the user if they want the system to install it for them.
3. **No Auto-Install**: Nexus Shell will **NEVER** automatically install system packages or tools in the background without the user pressing `Y` or explicitly confirming the installation step.
4. **Lean Core Dependencies**: The core Python package must rely ONLY on absolute essentials (`pyyaml`, `requests`). All other functionality (Textual menus, LLM parsers) is relegated to isolated, opt-in submodules.
