# Parallax V3 User Guide 📖

## The Dashboard
The Parallax Dashboard is your control center. It overlays your work without interrupting it.

### 🎮 Controls
| Key | Action | Description |
| :--- | :--- | :--- |
| `Enter` | **Execute** | Run the selected Action, Navigate to Folder, or Select Context. |
| `Esc` | **Back** | Go back up one level in the context stack, or clear the search query. |
| `Ctrl+D` | **Directories** | Open the interactive Directory Navigator (`cdr`) in the Stage pane. |
| `Ctrl+N` | **Notes** | Open your persistent scratchpad in the Stage pane. |
| `Ctrl+I` | **Intel** | Open the Intelligence Registry to manage AI providers. |
| `Ctrl+W` | **Save Surface** | Capture the current Tmux layout and save it as a named Surface. |
| `Ctrl+Y` | **Verbose** | Toggle Verbosity (show detailed logs/output). |
| `?` | **Legend** | Toggle the keybind legend at the top/bottom. |
| `Settings` | **Configure** | Navigate to the Settings plane to change layouts. |

## ⚙️ Settings Dashboard
Parallax allows you to configure your experience without editing files.
- **Layout Style**:
    - **Default (Classic)**: `[List] -> [Prompt] -> [Legend]`. The prompt floats at the bottom.
    - **Reverse (App-Like)**: `[Legend] -> [Prompt] -> [List]`. Top-down flow.
- **Verbosity & Legend**: Toggle startup defaults.

*Changes to Layout Style apply immediately via Hot-Reload.*

## ✈️ Planes
Parallax organizes capabilities into "Planes":
1.  **Actions**: Executable scripts and flows.
2.  **Agents**: AI personas (Claude, Ollama, OpenAI).
3.  **Surfaces**: Saved Tmux layouts (IDE, Monitor, Chat).
4.  **Places**: Bookmarked directories and project roots.
5.  **Docs**: Project documentation (including this guide!).
6.  **Intel**: AI Provider registry and status.

## 🧱 The Stage & The Negative Space
When you run an action, the Dashboard may close. This is **Negative Space Persistence**.
- The Dashboard gets out of your way.
- Results appear in your main shell (The Stage).
- You are never "trapped" inside Parallax.
