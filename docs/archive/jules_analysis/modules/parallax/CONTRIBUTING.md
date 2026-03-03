# Contributing to Parallax

Thank you for your interest in contributing to Parallax!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/parallax.git`
3. Install in dev mode: `./install.sh --dev`
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## Development Setup

Dev mode creates symlinks instead of copies, so changes are reflected immediately:

```bash
./install.sh --dev
```

## Code Style

- Shell scripts: Follow [Google's Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
- Python: Use [Black](https://black.readthedocs.io/) formatter
- Use meaningful variable names
- Comment complex logic

## Testing

Before submitting:

1. Test the dashboard: `parallax`
2. Test shell integration: open new terminal, verify px-link works
3. Test any actions you modified

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Write clear commit messages
4. Push to your fork
5. Open a PR with a clear description

## Reporting Issues

When reporting issues, please include:

- OS version
- Shell version (`zsh --version`)
- tmux version (`tmux -V`)
- Steps to reproduce
- Expected vs actual behavior

## Adding New Actions

Actions go in `content/actions/<category>/`:

```bash
#!/bin/bash
# @parallax-action
# @name: Action Name
# @id: category:action-id
# @description: What this action does
# @icon: emoji-name
# @param PARAM_NAME: Description

# Your code here
```

## Questions?

Open an issue with the `question` label.
