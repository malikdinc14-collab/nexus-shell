"""Project-local configuration system.

Discovers and loads `.nexus/` directories in project roots, providing:
  - Boot lists: ordered startup actions (`.nexus/boot.yaml`)
  - Project menus: workspace-layer Command Graph nodes (`.nexus/menu.yaml`)
  - Profile overrides: preferred profile/theme/composition (`.nexus/profile.yaml`)
  - Connectors: project-specific event-to-action rules (`.nexus/connectors.yaml`)
"""
