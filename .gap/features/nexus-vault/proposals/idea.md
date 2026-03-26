# Idea: Nexus Vault (Encrypted Project Secrets)

## Problem Statement
Boot lists and project configs will inevitably need API keys, tokens, and credentials. Without a secrets solution, developers either hardcode them (insecure) or manage env files outside nexus-shell (fragmented).

## Proposed Solution
A `nexus vault` CLI that manages encrypted secrets per project using age/sops. Secrets stored in `.nexus/secrets.yaml` (encrypted, safe to commit) and auto-injected as environment variables during boot.

## Key Features
- **Encrypt/decrypt**: `nexus vault set KEY=value`, `nexus vault get KEY`.
- **Auto-injection**: Boot list processes inherit decrypted env vars.
- **age/sops backend**: Industry-standard encryption, supports multiple recipients.
- **Committable**: `.nexus/secrets.yaml` is safe to check into version control.
- **Key management**: `nexus vault init` generates age keypair, stored in `~/.nexus/keys/`.

## Target User
Developers who want project secrets managed alongside their workspace config.
