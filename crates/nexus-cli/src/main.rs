//! Nexus CLI — thin client for the Nexus daemon.
//!
//! Every subcommand connects to the daemon via NexusClient and sends
//! a single JSON-RPC request. The daemon owns the engine.

use clap::{Parser, Subcommand};
use nexus_client::NexusClient;
use std::collections::HashMap;

#[derive(Parser)]
#[command(name = "nexus", about = "Nexus Shell CLI")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Stack operations (push, switch, close, list, tag, rename)
    Stack {
        #[command(subcommand)]
        action: StackAction,
    },
    /// Layout operations (show, split, navigate, focus, zoom)
    Layout {
        #[command(subcommand)]
        action: LayoutAction,
    },
    /// Session operations
    Session {
        #[command(subcommand)]
        action: SessionAction,
    },
    /// Pane operations
    Pane {
        #[command(subcommand)]
        action: PaneAction,
    },
    /// Show daemon info
    Hello,
}

#[derive(Subcommand)]
enum StackAction {
    Push {
        #[arg(short, long)]
        identity: String,
        #[arg(short, long)]
        pane_id: String,
        #[arg(short, long, default_value = "Shell")]
        name: String,
    },
    Switch {
        #[arg(short, long)]
        identity: String,
        #[arg(short = 'x', long)]
        index: usize,
    },
    Close {
        #[arg(short, long)]
        identity: String,
    },
    Tag {
        #[arg(short, long)]
        identity: String,
        #[arg(short, long)]
        tag: String,
    },
    Rename {
        #[arg(short, long)]
        identity: String,
        #[arg(short, long)]
        name: String,
    },
}

#[derive(Subcommand)]
enum LayoutAction {
    Show,
    Split {
        #[arg(short, long, default_value = "vertical")]
        direction: String,
        #[arg(short, long, default_value = "terminal")]
        pane_type: String,
    },
    Navigate { direction: String },
    Focus { pane_id: String },
    Zoom,
}

#[derive(Subcommand)]
enum SessionAction {
    Create {
        #[arg(short, long, default_value = "nexus")]
        name: String,
        #[arg(short, long)]
        cwd: Option<String>,
    },
    Info,
    List,
}

#[derive(Subcommand)]
enum PaneAction {
    List,
    Close {
        #[arg(short, long)]
        pane_id: String,
    },
}

fn main() {
    let cli = Cli::parse();

    let mut client = match NexusClient::connect() {
        Ok(c) => c,
        Err(e) => {
            eprintln!("Failed to connect to daemon: {e}");
            std::process::exit(1);
        }
    };

    let result = match cli.command {
        Commands::Stack { action } => handle_stack(&mut client, action),
        Commands::Layout { action } => handle_layout(&mut client, action),
        Commands::Session { action } => handle_session(&mut client, action),
        Commands::Pane { action } => handle_pane(&mut client, action),
        Commands::Hello => client.hello(),
    };

    match result {
        Ok(val) => {
            if !val.is_null() {
                println!("{}", serde_json::to_string_pretty(&val).unwrap_or_default());
            } else {
                println!("ok");
            }
        }
        Err(e) => {
            eprintln!("error: {e}");
            std::process::exit(1);
        }
    }
}

fn handle_stack(client: &mut NexusClient, action: StackAction) -> Result<serde_json::Value, nexus_core::NexusError> {
    match action {
        StackAction::Push { identity, pane_id, name } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
                ("pane_id".into(), pane_id),
                ("name".into(), name),
            ].into_iter().collect();
            client.stack_op("push", &payload)
        }
        StackAction::Switch { identity, index } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
                ("index".into(), index.to_string()),
            ].into_iter().collect();
            client.stack_op("switch", &payload)
        }
        StackAction::Close { identity } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
            ].into_iter().collect();
            client.stack_op("close", &payload)
        }
        StackAction::Tag { identity, tag } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
                ("tag".into(), tag),
            ].into_iter().collect();
            client.stack_op("tag", &payload)
        }
        StackAction::Rename { identity, name } => {
            let payload: HashMap<String, String> = [
                ("identity".into(), identity),
                ("name".into(), name),
            ].into_iter().collect();
            client.stack_op("rename", &payload)
        }
    }
}

fn handle_layout(client: &mut NexusClient, action: LayoutAction) -> Result<serde_json::Value, nexus_core::NexusError> {
    match action {
        LayoutAction::Show => client.layout(),
        LayoutAction::Split { direction, pane_type } => {
            client.request("pane.split", serde_json::json!({
                "direction": direction,
                "pane_type": pane_type,
            }))
        }
        LayoutAction::Navigate { direction } => client.navigate(&direction),
        LayoutAction::Focus { pane_id } => client.focus(&pane_id),
        LayoutAction::Zoom => client.zoom(),
    }
}

fn handle_session(client: &mut NexusClient, action: SessionAction) -> Result<serde_json::Value, nexus_core::NexusError> {
    let cwd = std::env::current_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| "/tmp".into());

    match action {
        SessionAction::Create { name, cwd: explicit_cwd } => {
            let dir = explicit_cwd.as_deref().unwrap_or(&cwd);
            client.session_create(&name, dir)
        }
        SessionAction::Info => client.session_info(),
        SessionAction::List => client.request("session.list", serde_json::Value::Null),
    }
}

fn handle_pane(client: &mut NexusClient, action: PaneAction) -> Result<serde_json::Value, nexus_core::NexusError> {
    match action {
        PaneAction::List => client.pane_list(),
        PaneAction::Close { pane_id } => client.close_pane(&pane_id),
    }
}
