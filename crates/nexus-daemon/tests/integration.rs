//! Integration test: start daemon, connect client, verify round-trip.

use nexus_client::{JsonRpcRequest, JsonRpcResponse};
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixStream;
use std::path::PathBuf;

/// Start a daemon on a temp socket, return socket paths and child process.
fn start_test_daemon() -> (PathBuf, PathBuf, std::process::Child) {
    let dir = std::env::temp_dir().join(format!("nexus-test-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();

    let cmd_socket = dir.join("nexus.sock");
    let event_socket = dir.join("nexus-events.sock");

    // Clean up any stale sockets
    let _ = std::fs::remove_file(&cmd_socket);
    let _ = std::fs::remove_file(&event_socket);

    // Find the daemon binary — it should be built by cargo before running tests
    // Use CARGO_BIN_EXE_nexus-daemon if available (cargo test sets this for integration tests
    // of the same package), otherwise look next to the test binary.
    let daemon = option_env!("CARGO_BIN_EXE_nexus-daemon")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            std::env::current_exe().unwrap()
                .parent().unwrap()
                .parent().unwrap()
                .join("nexus-daemon")
        });

    let child = std::process::Command::new(&daemon)
        .arg("--socket")
        .arg(&cmd_socket)
        .spawn()
        .expect("Failed to start daemon");

    // Wait for socket to appear
    for _ in 0..60 {
        if cmd_socket.exists() {
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
    assert!(cmd_socket.exists(), "Daemon socket did not appear within 3s");

    (cmd_socket, event_socket, child)
}

fn send_request(
    reader: &mut BufReader<UnixStream>,
    writer: &mut UnixStream,
    method: &str,
    params: serde_json::Value,
) -> JsonRpcResponse {
    let req = JsonRpcRequest::new(1, method, params);
    let mut line = serde_json::to_string(&req).unwrap();
    line.push('\n');
    writer.write_all(line.as_bytes()).unwrap();

    let mut buf = String::new();
    reader.read_line(&mut buf).unwrap();
    serde_json::from_str(&buf).unwrap()
}

#[test]
fn daemon_hello_roundtrip() {
    let (cmd_socket, _event_socket, mut child) = start_test_daemon();

    let stream = UnixStream::connect(&cmd_socket).unwrap();
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut writer = stream;

    let resp = send_request(&mut reader, &mut writer, "nexus.hello", serde_json::Value::Null);
    assert!(resp.error.is_none(), "hello failed: {:?}", resp.error);
    let result = resp.result.unwrap();
    assert!(result.get("version").is_some());
    assert!(result.get("protocol").is_some());

    child.kill().unwrap();
    let _ = child.wait();
    let _ = std::fs::remove_dir_all(cmd_socket.parent().unwrap());
}

#[test]
fn daemon_layout_operations() {
    let (cmd_socket, _event_socket, mut child) = start_test_daemon();

    let stream = UnixStream::connect(&cmd_socket).unwrap();
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut writer = stream;

    // Get layout
    let resp = send_request(&mut reader, &mut writer, "layout.show", serde_json::Value::Null);
    assert!(resp.error.is_none(), "layout.show failed: {:?}", resp.error);

    // Navigate
    let resp = send_request(&mut reader, &mut writer, "navigate.left", serde_json::Value::Null);
    assert!(resp.error.is_none(), "navigate.left failed: {:?}", resp.error);

    child.kill().unwrap();
    let _ = child.wait();
    let _ = std::fs::remove_dir_all(cmd_socket.parent().unwrap());
}

#[test]
fn daemon_session_operations() {
    let (cmd_socket, _event_socket, mut child) = start_test_daemon();

    let stream = UnixStream::connect(&cmd_socket).unwrap();
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut writer = stream;

    // Session info
    let resp = send_request(&mut reader, &mut writer, "session.info", serde_json::Value::Null);
    assert!(resp.error.is_none(), "session.info failed: {:?}", resp.error);

    // Session list
    let resp = send_request(&mut reader, &mut writer, "session.list", serde_json::Value::Null);
    assert!(resp.error.is_none(), "session.list failed: {:?}", resp.error);

    child.kill().unwrap();
    let _ = child.wait();
    let _ = std::fs::remove_dir_all(cmd_socket.parent().unwrap());
}

#[test]
fn daemon_unknown_command_returns_error() {
    let (cmd_socket, _event_socket, mut child) = start_test_daemon();

    let stream = UnixStream::connect(&cmd_socket).unwrap();
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut writer = stream;

    let resp = send_request(&mut reader, &mut writer, "bogus.command", serde_json::Value::Null);
    assert!(resp.error.is_some(), "expected error for unknown command");

    child.kill().unwrap();
    let _ = child.wait();
    let _ = std::fs::remove_dir_all(cmd_socket.parent().unwrap());
}
