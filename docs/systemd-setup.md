# Systemd User Service Setup for YouTrack MCP

This guide explains how to set up the YouTrack MCP server as a systemd user service for automatic startup and management.

## Prerequisites

- systemd user service support (most modern Linux distributions)
- Podman or Docker installed
- YouTrack MCP Docker image built and available

## Installation

1. **Copy the service file:**
   ```bash
   mkdir -p ~/.config/systemd/user/
   cp docs/youtrack-mcp-user.service ~/.config/systemd/user/
   ```

2. **Configure environment variables:**
   Edit the service file and update the environment variables:
   ```bash
   # Replace with your actual YouTrack instance
   Environment=YOUTRACK_URL=https://your.youtrack.cloud

   # Replace with your actual API token
   Environment=YOUTRACK_API_TOKEN=perm:your-actual-token-here

   # Update Docker image reference
   docker.io/yourrepo/youtrack-mcp:latest
   ```

3. **Create configuration directory:**
   ```bash
   mkdir -p ~/.config/youtrack-mcp/
   mkdir -p ~/.local/share/youtrack-mcp/
   ```

4. **Reload systemd and enable the service:**
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable youtrack-mcp-user.service
   ```

## Usage

### Start the service
```bash
systemctl --user start youtrack-mcp-user.service
```

### Stop the service
```bash
systemctl --user stop youtrack-mcp-user.service
```

### Check status
```bash
systemctl --user status youtrack-mcp-user.service
```

### View logs
```bash
journalctl --user -u youtrack-mcp-user.service -f
```

### Restart the service
```bash
systemctl --user restart youtrack-mcp-user.service
```

## Security Features

The systemd service includes several security hardening measures:

- **Non-root container execution** (`--user 10001:10001`)
- **Read-only filesystem** with isolated tmp directory
- **Dropped capabilities** (`--cap-drop ALL`)
- **No new privileges** (`--security-opt no-new-privileges`)
- **Resource limits** (512MB memory, 50% CPU)
- **Isolated networking** with controlled host access

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `YOUTRACK_URL` | Your YouTrack instance URL | Required |
| `YOUTRACK_API_TOKEN` | API token with appropriate permissions | Required |
| `MCP_TIMEOUT` | MCP operation timeout in milliseconds | 15000 |
| `MCP_DEBUG` | Enable debug logging | false |
| `YOUTRACK_VERIFY_SSL` | Verify SSL certificates | true |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FILE` | Log file path | ~/.local/share/youtrack-mcp/youtrack-mcp.log |

### Log Files

Logs are written to:
- **Systemd journal**: `journalctl --user -u youtrack-mcp-user.service`
- **File**: `~/.local/share/youtrack-mcp/youtrack-mcp.log` (if configured)

## Troubleshooting

### Service fails to start
Check the systemd journal:
```bash
journalctl --user -u youtrack-mcp-user.service --no-pager -n 50
```

### Permission issues
Ensure the Docker/Podman socket is accessible:
```bash
# For Podman
systemctl --user enable podman.socket
systemctl --user start podman.socket
```

### Network connectivity
Test connectivity to your YouTrack instance:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://your.youtrack.cloud/api/admin/projects
```

## Alternative: Direct Python Execution

For development or simpler deployments, you can modify the service to run Python directly:

1. Comment out the Podman `ExecStart` line
2. Uncomment the Python `ExecStart` line:
   ```bash
   ExecStart=%h/.local/bin/youtrack-mcp --transport stdio
   ```

3. Install the package locally:
   ```bash
   pip install -e .
   ```

**Note:** Direct Python execution is less secure than containerized deployment.

## Integration with Claude Desktop

Once the service is running, configure Claude Desktop to connect to the MCP server:

```json
{
  "mcpServers": {
    "youtrack": {
      "command": "systemctl",
      "args": ["--user", "start", "youtrack-mcp-user.service"],
      "env": {}
    }
  }
}
```

This setup ensures the MCP server starts automatically when Claude Desktop needs it.