//! .nexus.yaml configuration skeleton.

use serde::{Deserialize, Serialize};

/// Top-level Nexus Shell configuration (.nexus.yaml).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct NexusConfig {
    /// Workspace name override (default: directory name).
    pub workspace: Option<String>,
    /// Default shell (default: $SHELL).
    pub shell: Option<String>,
}

impl NexusConfig {
    pub fn default_config() -> Self {
        Self::default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_config_all_none() {
        let cfg = NexusConfig::default_config();
        assert!(cfg.workspace.is_none());
        assert!(cfg.shell.is_none());
    }

    #[test]
    fn config_roundtrips_json() {
        let cfg = NexusConfig {
            workspace: Some("my-project".into()),
            shell: Some("/bin/zsh".into()),
        };
        let json = serde_json::to_string(&cfg).unwrap();
        let back: NexusConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(back.workspace, cfg.workspace);
        assert_eq!(back.shell, cfg.shell);
    }
}
