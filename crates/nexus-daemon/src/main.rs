//! Nexus daemon — shared NexusCore over unix socket.
//!
//! Owns the engine. All surfaces connect here as JSON-RPC 2.0 clients.

use nexus_core::adapters::{ClaudeAdapter, FsExplorer, NotesAdapter, SystemInfoAdapter, TauriBrowserAdapter};
use nexus_core::capability::SystemContext;
use nexus_core::mux::Mux;
use nexus_engine::persistence;
use nexus_engine::{NexusCore, NullMux, TypedEvent};
use nexus_tmux::TmuxMux;
use std::sync::{Arc, Mutex as StdMutex};

async fn auto_save_loop(core: Arc<StdMutex<NexusCore>>) {
    let mut interval = tokio::time::interval(std::time::Duration::from_secs(30));
    loop {
        interval.tick().await;

        let snapshot = {
            let mut guard = match core.lock() {
                Ok(g) => g,
                Err(_) => continue,
            };
            if !guard.is_dirty() {
                continue;
            }
            let snap = guard.snapshot();
            guard.clear_dirty();
            snap
        };

        let session_name = snapshot.name.clone();
        let session_dir = persistence::nexus_home()
            .join("sessions")
            .join(&session_name);

        if let Err(e) = persistence::save_workspace(&session_dir, &snapshot) {
            eprintln!("auto-save failed: {e}");
        }
    }
}

#[tokio::main]
async fn main() {
    // -- Arg handling --
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("nexus-daemon — shared NexusCore over unix socket");
        println!();
        println!("Usage: nexus-daemon [--socket PATH] [--mux null|tmux]");
        println!();
        println!("Options:");
        println!("  --socket PATH    Command socket path override");
        println!("  --mux MODE       Mux backend: null (default) or tmux");
        println!("  --default        Skip session restore, start with fresh layout");
        println!("  -h, --help       Print this help");
        return;
    }

    // -- Bind listeners --
    #[cfg(unix)]
    let (cmd_listener, event_listener, cmd_socket_path, event_socket_path, pid_path) = {
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

        if let Some(parent) = cmd_socket.parent() {
            if let Err(e) = std::fs::create_dir_all(parent) {
                eprintln!("Cannot create socket directory {}: {e}", parent.display());
                std::process::exit(1);
            }
        }

        let _ = std::fs::remove_file(&cmd_socket);
        let _ = std::fs::remove_file(&event_socket);

        if let Err(e) = std::fs::write(&pid_file, std::process::id().to_string()) {
            eprintln!("Warning: could not write PID file: {e}");
        }

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

        (cmd_listener, event_listener, cmd_socket, event_socket, pid_file)
    };

    #[cfg(not(unix))]
    let (cmd_listener, event_listener, pid_path) = {
        let cmd_addr = nexus_core::constants::cmd_addr();
        let event_addr = nexus_core::constants::event_addr();
        let pid_file = nexus_core::constants::pid_path();
        
        if let Some(parent) = pid_file.parent() {
            let _ = std::fs::create_dir_all(parent);
        }

        if let Err(e) = std::fs::write(&pid_file, std::process::id().to_string()) {
            eprintln!("Warning: could not write PID file: {e}");
        }

        let cmd_listener = match tokio::net::TcpListener::bind(cmd_addr).await {
            Ok(l) => l,
            Err(e) => {
                eprintln!("Cannot bind command TCP socket {}: {}", cmd_addr, e);
                std::process::exit(1);
            }
        };

        let event_listener = match tokio::net::TcpListener::bind(event_addr).await {
            Ok(l) => l,
            Err(e) => {
                eprintln!("Cannot bind event TCP socket {}: {}", event_addr, e);
                std::process::exit(1);
            }
        };

        eprintln!("nexus-daemon listening:");
        eprintln!("  commands TCP: {}", cmd_addr);
        eprintln!("  events TCP:   {}", event_addr);
        eprintln!("  PID:          {}", std::process::id());

        (cmd_listener, event_listener, pid_file)
    };

    // -- Initialize engine --
    let mux_mode = args
        .windows(2)
        .find(|w| w[0] == "--mux")
        .map(|w| w[1].as_str())
        .unwrap_or("null");

    let ctx = SystemContext::from_login_shell();
    let claude = ClaudeAdapter::new(ctx.clone());
    let fs_explorer = FsExplorer::new();

    // Use --cwd arg if provided, otherwise current directory
    let cwd = args
        .windows(2)
        .find(|w| w[0] == "--cwd")
        .map(|w| w[1].clone())
        .unwrap_or_else(|| {
            std::env::current_dir()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_else(|_| "/tmp".into())
        });

    let mux: Box<dyn Mux> = match mux_mode {
        "tmux" => {
            eprintln!("  mux: tmux");
            Box::new(TmuxMux::new())
        }
        _ => {
            eprintln!("  mux: null (headless)");
            Box::new(NullMux::new())
        }
    };

    let claude = ClaudeAdapter::new(ctx.clone());
    let fs_explorer = FsExplorer::new();
    let tauri_browser = TauriBrowserAdapter::new();
    let notes = NotesAdapter::new();
    let sys_info = SystemInfoAdapter::new();
    
    // ...
    
    let mut core = NexusCore::with_registry(mux, ctx);
    if let Some(ref reg) = core.registry {
        let mut reg = reg.write().unwrap();
        reg.register_chat(Box::new(claude));
        reg.register_explorer(Box::new(fs_explorer));
        reg.register_browser(Box::new(tauri_browser));
        reg.register_richtext(Box::new(notes));
        reg.register_hud(Box::new(sys_info));
    }
    core.create_workspace("nexus", &cwd);

    // -- Attempt restore from previous session --
    let skip_restore = args.iter().any(|a| a == "--default");
    if skip_restore {
        eprintln!("  --default: starting with fresh layout");
    } else {
        let session_dir = persistence::session_dir("nexus");
        match persistence::load_workspace(&session_dir) {
            Ok(save) => {
                eprintln!("  restored session from {}", session_dir.display());
                core.layout = save.layout;
                core.stacks = save.stacks;
            }
            Err(_) => {
                // No previous session or corrupt — start fresh
            }
        }
    }

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
        _ = auto_save_loop(core.clone()) => {}
        _ = tokio::signal::ctrl_c() => {
            eprintln!("\nShutting down...");
        }
    }

    // -- Cleanup --
    #[cfg(unix)]
    {
        let _ = std::fs::remove_file(&cmd_socket_path);
        let _ = std::fs::remove_file(&event_socket_path);
    }
    let _ = std::fs::remove_file(&pid_path);
    eprintln!("Cleaned up socket and PID files");
}
