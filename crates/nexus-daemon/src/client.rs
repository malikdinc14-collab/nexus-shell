//! Daemon client — connect to nexus-daemon and send commands.

use crate::protocol::{Request, Response};
use std::collections::HashMap;
use std::path::Path;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixStream;

/// A connection to the nexus daemon.
pub struct DaemonClient {
    reader: BufReader<tokio::net::unix::OwnedReadHalf>,
    writer: tokio::net::unix::OwnedWriteHalf,
}

impl DaemonClient {
    /// Connect to the daemon at the given socket path.
    pub async fn connect(path: &Path) -> Result<Self, std::io::Error> {
        let stream = UnixStream::connect(path).await?;
        let (read, write) = stream.into_split();
        Ok(Self {
            reader: BufReader::new(read),
            writer: write,
        })
    }

    /// Connect to the daemon at the default socket path.
    pub async fn connect_default() -> Result<Self, std::io::Error> {
        Self::connect(&crate::server::socket_path()).await
    }

    /// Send a command and receive the response.
    pub async fn request(
        &mut self,
        cmd: &str,
        args: HashMap<String, serde_json::Value>,
    ) -> Result<Response, std::io::Error> {
        let req = Request {
            cmd: cmd.to_string(),
            args,
        };
        let mut line = serde_json::to_string(&req)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        line.push('\n');
        self.writer.write_all(line.as_bytes()).await?;

        let mut buf = String::new();
        self.reader.read_line(&mut buf).await?;
        let response: Response = serde_json::from_str(&buf)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        Ok(response)
    }

    /// Convenience: send a command with no args.
    pub async fn cmd(&mut self, cmd: &str) -> Result<Response, std::io::Error> {
        self.request(cmd, HashMap::new()).await
    }
}
