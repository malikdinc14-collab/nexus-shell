//! Nexus daemon — shared NexusCore over unix socket.
//!
//! Owns the engine. All surfaces connect here as JSON-RPC 2.0 clients.

use nexus_core::adapters::{ClaudeAdapter, FsExplorer};
use nexus_core::capability::SystemContext;
use nexus_engine::{NexusCore, NullMux, TypedEvent};
use std::sync::{Arc, Mutex as StdMutex};

#[tokio::main]
async fn main() {
    // -- Arg handling --
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("nexus-daemon — shared NexusCore over unix socket");
        println!();
        println!("Usage: nexus-daemon [--socket PATH]");
        println!();
        println!("Options:");
        println!("  --socket PATH    Command socket path override");
        println!("  -h, --help       Print this help");
        return;
    }

    let cmd_socket = args
        .windows(2)
        .find(|w| w[0] == "--socket")
        .map(|w| std::path::PathBuf::from(&w[1]))
        .unwrap_or_else(nexus_core::constants::socket_path);

    let event_socket = {
        let mut p = cmd_socket.clone();
        p.set_file_name("nexus-events.sock");
        p
    };

    let pid_file = {
        let mut p = cmd_socket.clone();
        p.set_file_name("nexus.pid");
        p
    };

    // -- Directory setup --
    if let Some(parent) = cmd_socket.parent() {
        if let Err(e) = std::fs::create_dir_all(parent) {
            eprintln!("Cannot create socket directory {}: {e}", parent.display());
            std::process::exit(1);
        }
    }

    // Remove stale sockets
    let _ = std::fs::remove_file(&cmd_socket);
    let _ = std::fs::remove_file(&event_socket);

    // Write PID file
    if let Err(e) = std::fs::write(&pid_file, std::process::id().to_string()) {
        eprintln!("Warning: could not write PID file: {e}");
    }

    // -- Bind listeners --
    let cmd_listener = match tokio::net::UnixListener::bind(&cmd_socket) {
        Ok(l) => l,
        Err(e) => {
            eprintln!("Cannot bind command socket {}: {e}", cmd_socket.display());
            std::process::exit(1);
        }
    };

    let event_listener = match tokio::net::UnixListener::bind(&event_socket) {
        Ok(l) => l,
        Err(e) => {
            eprintln!("Cannot bind event socket {}: {e}", event_socket.display());
            std::process::exit(1);
        }
    };

    eprintln!("nexus-daemon listening:");
    eprintln!("  commands: {}", cmd_socket.display());
    eprintln!("  events:   {}", event_socket.display());
    eprintln!("  PID:      {}", std::process::id());

    // -- Initialize engine --
    let ctx = SystemContext::from_login_shell();
    let claude = ClaudeAdapter::new(ctx.clone());
    let fs_explorer = FsExplorer::new();

    let cwd = std::env::current_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| "/tmp".into());

    let mut core = NexusCore::with_registry(Box::new(NullMux::new()), ctx);
    if let Some(ref mut reg) = core.registry {
        reg.register_chat(Box::new(claude));
        reg.register_explorer(Box::new(fs_explorer));
    }
    core.create_workspace("nexus", &cwd);

    // -- Event bridge --
    let (event_tx, event_rx) = tokio::sync::mpsc::unbounded_channel::<TypedEvent>();
    {
        let mut bus = core.bus.lock().unwrap();
        bus.subscribe("*.*", move |event: &TypedEvent| {
            let _ = event_tx.send(event.clone());
        });
    }

    let connections = nexus_daemon::event_bridge::SharedConnections::default();
    let _fanout = nexus_daemon::event_bridge::spawn_fanout(event_rx, connections.clone());

    // -- Shared state --
    let core = Arc::new(StdMutex::new(core));
    let client_count = nexus_daemon::server::ClientCount::default();

    // -- Shutdown channel --
    let (shutdown_tx, shutdown_rx) = tokio::sync::watch::channel(false);

    // -- Run --
    let cmd_socket_path = cmd_socket.clone();
    let event_socket_path = event_socket.clone();
    let pid_path = pid_file.clone();

    tokio::select! {
        _ = nexus_daemon::server::run_command_listener(
            cmd_listener, core.clone(), client_count.clone(), shutdown_rx.clone()
        ) => {}
        _ = nexus_daemon::server::run_event_listener(
            event_listener, connections, shutdown_rx.clone()
        ) => {}
        _ = nexus_daemon::server::idle_shutdown_monitor(
            core.clone(), client_count, shutdown_tx
        ) => {}
        _ = tokio::signal::ctrl_c() => {
            eprintln!("\nShutting down...");
        }
    }

    // -- Cleanup --
    let _ = std::fs::remove_file(&cmd_socket_path);
    let _ = std::fs::remove_file(&event_socket_path);
    let _ = std::fs::remove_file(&pid_path);
    eprintln!("Cleaned up socket and PID files");
}
