Nice stack 🙂 you’re basically building a **modern terminal-first, local-AI-friendly workflow**.

Here’s a **curated map of notable open-source TUIs** you might want to add, grouped by purpose. I’ll skip basics and focus on *interesting / powerful / actively used* tools.

---

## 🧠 AI / Coding Assistants (TUI)

You already mentioned:

* **opencode**
* **aider**

### Worth adding

* **continue (TUI mode)**
  Local-first AI coding assistant, works well with Ollama / LM Studio.
  More “IDE brain” than chat.

* **gptme**
  Very Unix-y AI agent. Reads/writes files, runs commands, explains diffs.
  Feels like a shell-native coding partner.

* **llm** (Simon Willison)
  Small, composable CLI/TUI for local & remote models.
  Great glue tool: `cat file | llm "summarize"`.

* **fabric**
  Prompt-driven workflows (“summarize”, “refactor”, “explain”)
  Excellent for chaining with shell tools.

---

## 📁 Files / Navigation / Search

You have **yazi** (excellent choice).

### Also interesting

* **lf** – minimal, vim-like file manager
* **nnn** – ultra-fast, scriptable, extensible
* **fd** – better `find`
* **ripgrep (rg)** – essential for everything
* **fzf** – fuzzy selection glue for *everything*

💡 yazi + fzf + rg is a god-tier combo.

---

## 🌳 Git / VCS (beyond LazyGit)

You already have:

* **Lazygit**

Also:

* **gitui** – keyboard-heavy, vim-like
* **tig** – classic, scriptable, pager-style
* **gh** (GitHub CLI) – not pure TUI, but essential

---

## 🖥️ System / Process / Resource TUIs

* **btop** – modern `htop` replacement (CPU/GPU/disk/network)
* **htop** – still useful
* **glances** – system overview
* **dust** – better `du`
* **duf** – better `df`

---

## 📦 Containers / Infra

* **lazydocker** – LazyGit-style Docker TUI
* **k9s** – Kubernetes TUI (fantastic)
* **ctop** – container metrics
* **terraform-tui** (early but promising)

---

## 📝 Writing / Docs / Knowledge

You mentioned:

* **doxx-go**

Also consider:

* **Glow** – render Markdown beautifully in terminal
* **mdcat** – fast markdown renderer
* **zk** – Zettelkasten note system
* **nb** – notes, bookmarks, todos in git
* **obsidian-cli** (community tools) – if you like Obsidian + terminal

---

## 🧭 Shell / Environment Enhancers

* **zellij** – modern tmux alternative (layout-aware)
* **tmux** – still king in some workflows
* **starship** – prompt, but makes TUIs nicer
* **direnv** – auto-env per project
* **just** – better `make` for commands

---

## 🔐 Secrets / Security

* **gopass** – password manager TUI
* **age + agebox** – modern encryption
* **pass** – classic, simple

---

## 🌐 Networking / APIs

* **xh** – better `httpie` / curl
* **curlie** – curl + httpie style
* **grpcurl** – gRPC debugging
* **trippy** – network path visualization TUI

---

## 🧪 Databases / Data

* **lazysql** – DB TUI
* **usql** – universal SQL CLI
* **pgcli / mycli** – autocomplete SQL
* **jq / yq** – non-negotiable

---

## 🎨 Terminal UX / Fun but Useful

* **bat** – better `cat`
* **eza** – better `ls`
* **delta** – better git diff
* **slides** – terminal presentations
* **termshark** – Wireshark in terminal

---

## 🧩 Meta Tools (Glue Everything Together)

These are what turn TUIs into a *system*:

* **fzf**
* **ripgrep**
* **entr** – run on file change
* **watchexec**
* **taskwarrior**
* **timewarrior**

---

## If I had to add just 5 to your list

Given your choices, I’d strongly recommend:

1. **zellij**
2. **fzf**
3. **ripgrep**
4. **btop**
5. **fabric** or **gptme**

---

If you want, I can:

* Design a **cohesive TUI + local-AI workflow**
* Suggest a **minimal but powerful toolset**
* Help wire **doxx-go + nvim + aider/opencode**
* Or tailor this list for **writing vs coding vs ops**

Just tell me your main focus.

