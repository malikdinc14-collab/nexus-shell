# Idea: Composition Designer (Visual Layout Builder)

## Problem Statement
Creating workspace compositions requires manually writing YAML layout definitions. Users can't visually experiment with pane arrangements or see how a composition will look before committing to it.

## Proposed Solution
An interactive composition designer built into TextualSurface. Users drag/resize panes visually, assign capabilities, and save the result as a named composition in their pack or profile.

## Key Features
- **Visual pane manipulation**: Drag borders to resize, click to split, right-click to assign capability.
- **Live preview**: See the actual layout as you design it.
- **Save as composition**: Export to YAML for pack/profile inclusion.
- **Template library**: Start from existing compositions and modify.
- **Responsive awareness**: Preview how the composition adapts to different terminal sizes.
- **Keyboard-driven**: Full keyboard support (Alt+v/s for split, Alt+q to remove, arrow keys to resize).

## Target User
Users designing custom workspace layouts for their domain packs or personal profiles.
