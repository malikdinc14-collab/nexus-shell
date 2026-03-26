use crate::registry::CapabilityRegistry;
use nexus_core::capability::{HUDFrame, HUDCapability};
use nexus_core::error::NexusError;
use std::sync::{Arc, RwLock};

pub struct HUDManager {
    pub registry: Arc<RwLock<CapabilityRegistry>>,
}

impl HUDManager {
    pub fn new(registry: Arc<RwLock<CapabilityRegistry>>) -> Self {
        Self { registry }
    }

    /// Aggregate frames from all available HUD adapters
    pub fn get_combined_frame(&self) -> Result<Vec<HUDFrame>, NexusError> {
        let reg = self.registry.read().unwrap();
        let mut frames = Vec::new();

        for adapter in &reg.huds {
            if adapter.is_available() {
                if let Ok(frame) = adapter.get_frame() {
                    frames.push(frame);
                }
            }
        }

        Ok(frames)
    }

    /// Get a frame from the best (highest priority) HUD adapter
    pub fn get_best_frame(&self) -> Result<HUDFrame, NexusError> {
        let reg = self.registry.read().unwrap();
        let adapter = reg.best_hud()
            .ok_or_else(|| NexusError::NotFound("no HUD adapter available".into()))?;
        
        adapter.get_frame()
    }
}
