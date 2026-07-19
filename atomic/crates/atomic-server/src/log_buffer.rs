//! In-memory ring buffer for capturing tracing log lines.
//!
//! Used to let users export recent logs for bug reports.

use std::collections::VecDeque;
use std::io::Write;
use std::sync::{Arc, Mutex};

/// Thread-safe ring buffer that stores the last N log lines.
#[derive(Clone)]
pub struct LogBuffer {
    inner: Arc<Mutex<VecDeque<String>>>,
    capacity: usize,
}

impl LogBuffer {
    pub fn new(capacity: usize) -> Self {
        Self {
            inner: Arc::new(Mutex::new(VecDeque::with_capacity(capacity))),
            capacity,
        }
    }

    /// Push a log line, dropping the oldest if at capacity.
    pub fn push(&self, line: String) {
        if let Ok(mut buf) = self.inner.lock() {
            if buf.len() >= self.capacity {
                buf.pop_front();
            }
            buf.push_back(line);
        }
    }

    /// Return all buffered lines joined with newlines.
    pub fn dump(&self) -> String {
        match self.inner.lock() {
            Ok(buf) => buf.iter().cloned().collect::<Vec<_>>().join("\n"),
            Err(_) => String::from("(failed to acquire log buffer lock)"),
        }
    }

    /// Create a `MakeWriter` adapter for use with `tracing_subscriber::fmt::layer()`.
    pub fn make_writer(&self) -> LogBufferMakeWriter {
        LogBufferMakeWriter {
            buffer: self.clone(),
        }
    }
}

/// Adapter that implements `MakeWriter` for tracing integration.
#[derive(Clone)]
pub struct LogBufferMakeWriter {
    buffer: LogBuffer,
}

/// Per-write instance that buffers bytes until a newline, then pushes to the ring buffer.
pub struct LogBufferWriteHandle {
    buffer: LogBuffer,
    line_buf: Vec<u8>,
}

impl<'a> tracing_subscriber::fmt::MakeWriter<'a> for LogBufferMakeWriter {
    type Writer = LogBufferWriteHandle;

    fn make_writer(&'a self) -> Self::Writer {
        LogBufferWriteHandle {
            buffer: self.buffer.clone(),
            line_buf: Vec::with_capacity(256),
        }
    }
}

impl Write for LogBufferWriteHandle {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        self.line_buf.extend_from_slice(buf);
        // Flush complete lines to the ring buffer
        while let Some(pos) = self.line_buf.iter().position(|&b| b == b'\n') {
            let line = String::from_utf8_lossy(&self.line_buf[..pos]).to_string();
            if !line.is_empty() {
                self.buffer.push(line);
            }
            self.line_buf.drain(..=pos);
        }
        Ok(buf.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        // Flush any remaining partial line
        if !self.line_buf.is_empty() {
            let line = String::from_utf8_lossy(&self.line_buf).to_string();
            if !line.is_empty() {
                self.buffer.push(line);
            }
            self.line_buf.clear();
        }
        Ok(())
    }
}

impl Drop for LogBufferWriteHandle {
    fn drop(&mut self) {
        let _ = self.flush();
    }
}
