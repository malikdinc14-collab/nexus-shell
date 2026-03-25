//! Nexus daemon entry point.
//!
//! Starts NexusCore, binds a unix socket, handles signals for cleanup.

use nexus_engine::{NexusCore, NullMux};
use std::sync::Arc;
use tokio::sync::Mutex;

#[tokio::main]
async fn main() {
    // Simple arg handling (no clap — keep deps minimal)
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("nexus-daemon — shared NexusCore over unix socket");
        println!();
        println!("Usage: nexus-daemon [--socket PATH]");
        println!();
        println!("Options:");
        println!("  --socket PATH    Socket path (default: $XDG_RUNTIME_DIR/nexus/nexus.sock)");
        println!("  -h, --help       Print this help");
        return;
    }

    let socket_path = args
        .windows(2)
        .find(|w| w[0] == "--socket")
        .map(|w| std::path::PathBuf::from(&w[1]))
        .unwrap_or_else(nexus_daemon::server::socket_path);

    // Ensure parent directory exists
    if let Some(parent) = socket_path.parent() {
        if let Err(e) = std::fs::create_dir_all(parent) {
            eprintln!("Cannot create socket directory {}: {e}", parent.display());
            std::process::exit(1);
        }
    }

    // Remove stale socket
    if socket_path.exists() {
        let _ = std::fs::remove_file(&socket_path);
    }

    // Write PID file
    let pid_path = socket_path.with_extension("pid");
    if let Err(e) = std::fs::write(&pid_path, std::process::id().to_string()) {
        eprintln!("Warning: could not write PID file: {e}");
    }

    // Bind listener
    let listener = match tokio::net::UnixListener::bind(&socket_path) {
        Ok(l) => l,
        Err(e) => {
            eprintln!("Cannot bind {}: {e}", socket_path.display());
            std::process::exit(1);
        }
    };

    eprintln!("nexus-daemon listening on {}", socket_path.display());
    eprintln!("PID {}", std::process::id());

    // Initialize engine
    let cwd = std::env::current_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| "/tmp".into());
    let mut core = NexusCore::new(Box::new(NullMux::new()));
    core.create_workspace("nexus", &cwd);
    let core = Arc::new(Mutex::new(core));

    // Run server with signal handling for cleanup
    let sock = socket_path.clone();
    let pid = pid_path.clone();
    tokio::select! {
        _ = nexus_daemon::server::run(listener, core) => {}
        _ = tokio::signal::ctrl_c() => {
            eprintln!("\nShutting down...");
        }
    }

    // Cleanup
    let _ = std::fs::remove_file(&sock);
    let _ = std::fs::remove_file(&pid);
    eprintln!("Cleaned up socket and PID file");
}
