use crate::capability::{AdapterManifest, BrowserCapability, Capability, CapabilityType};
use crate::error::NexusError;

/// A stub adapter for the Tauri WebView.
/// 
/// This adapter lives in the engine/daemon. It tracks the browser's state (URL)
/// but does not perform any actual rendering. Commands sent to this adapter
/// are typically broadcast to the UI surface.
pub struct TauriBrowserAdapter {
    manifest: AdapterManifest,
    current_url: Option<String>,
}

impl TauriBrowserAdapter {
    pub fn new() -> Self {
        Self {
            manifest: AdapterManifest {
                name: "tauri-webview",
                capability_type: CapabilityType::Browser,
                priority: 100,
                binary: "", // Native to the Tauri surface
            },
            current_url: None,
        }
    }
}

impl Default for TauriBrowserAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl Capability for TauriBrowserAdapter {
    fn manifest(&self) -> &AdapterManifest {
        &self.manifest
    }

    fn is_available(&self) -> bool {
        // This adapter is always available when running within a Tauri surface.
        // The engine assumes the surface will handle the rendering.
        true
    }
}

impl BrowserCapability for TauriBrowserAdapter {
    fn load_url(&mut self, url: &str) -> Result<(), NexusError> {
        self.current_url = Some(url.to_string());
        // In a real implementation, this would emit an event to the bus
        // or be picked up by the UI surface during the next sync.
        Ok(())
    }

    fn get_current_url(&self) -> Option<String> {
        self.current_url.clone()
    }

    fn query_selector(&self, _selector: &str) -> Result<String, NexusError> {
        Err(NexusError::Unimplemented("query_selector is not supported in the stub adapter"))
    }

    fn is_alive(&self) -> bool {
        true
    }

    fn get_launch_command(&self) -> Option<String> {
        None
    }
}
