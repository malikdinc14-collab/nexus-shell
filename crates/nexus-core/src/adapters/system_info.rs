use crate::capability::{AdapterManifest, Capability, CapabilityType, HUDCapability, HUDFrame, HUDPart};
use crate::error::NexusError;
use sysinfo::System;
use std::collections::HashMap;

pub struct SystemInfoAdapter {
    manifest: AdapterManifest,
    sys: System,
}

impl SystemInfoAdapter {
    pub fn new() -> Self {
        let mut sys = System::new_all();
        sys.refresh_all();
        Self {
            manifest: AdapterManifest {
                name: "system-monitor",
                capability_type: CapabilityType::HUD,
                priority: 10,
                binary: "",
            },
            sys,
        }
    }
}

impl Default for SystemInfoAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl Capability for SystemInfoAdapter {
    fn manifest(&self) -> &AdapterManifest {
        &self.manifest
    }

    fn is_available(&self) -> bool {
        true
    }
}

impl HUDCapability for SystemInfoAdapter {
    fn get_frame(&self) -> Result<HUDFrame, NexusError> {
        let mut sys = System::new_all();
        sys.refresh_all();

        let cpu_usage = sys.global_cpu_info().cpu_usage();
        let total_mem = sys.total_memory();
        let used_mem = sys.used_memory();
        let mem_usage = (used_mem as f32 / total_mem as f32) * 100.0;

        let parts = vec![
            HUDPart {
                id: "cpu_load".into(),
                part_type: "Gauge".into(),
                label: "CPU Usage".into(),
                value: serde_json::json!(cpu_usage),
                metadata: HashMap::from([("unit".into(), "%".into())]),
            },
            HUDPart {
                id: "mem_load".into(),
                part_type: "Gauge".into(),
                label: "RAM Usage".into(),
                value: serde_json::json!(mem_usage),
                metadata: HashMap::from([("unit".into(), "%".into())]),
            },
        ];

        Ok(HUDFrame {
            source: "system".into(),
            parts,
            timestamp: chrono::Utc::now().to_rfc3339(),
        })
    }
}
