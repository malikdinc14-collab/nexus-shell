use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use nexus_core::NexusError;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrowserSession {
    pub pane_id: String,
    pub url: String,
    pub title: String,
}

pub struct Browser {
    sessions: HashMap<String, BrowserSession>,
}

impl Browser {
    pub fn new() -> Self {
        Self {
            sessions: HashMap::new(),
        }
    }

    pub fn open(&mut self, pane_id: &str, url: &str) -> Result<BrowserSession, NexusError> {
        let session = BrowserSession {
            pane_id: pane_id.to_string(),
            url: url.to_string(),
            title: "Browser".into(), // Will be updated by surface events
        };
        self.sessions.insert(pane_id.to_string(), session.clone());
        Ok(session)
    }

    pub fn navigate(&mut self, pane_id: &str, url: &str) -> Result<(), NexusError> {
        if let Some(session) = self.sessions.get_mut(pane_id) {
            session.url = url.to_string();
            Ok(())
        } else {
            Err(NexusError::NotFound(format!("no browser session for pane: {pane_id}")))
        }
    }

    pub fn get_session(&self, pane_id: &str) -> Option<&BrowserSession> {
        self.sessions.get(pane_id)
    }

    pub fn remove_session(&mut self, pane_id: &str) -> bool {
        self.sessions.remove(pane_id).is_some()
    }

    pub fn state(&self) -> HashMap<String, BrowserSession> {
        self.sessions.clone()
    }
}

impl Default for Browser {
    fn default() -> Self {
        Self::new()
    }
}
