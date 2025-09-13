FROM python:3.13-alpine

# Create non-root user for security
RUN addgroup -g 10001 -S appgroup && \
    adduser -u 10001 -S appuser -G appgroup

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY --chown=10001:10001 requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt && \
    python -c "import mcp; print(dir(mcp))"

# Copy the rest of the application with proper ownership
COPY --chown=10001:10001 . .

# Switch to non-root user
USER 10001

# Default environment variables (will be overridden at runtime)
ENV MCP_SERVER_NAME="youtrack-mcp"
ENV MCP_SERVER_DESCRIPTION="YouTrack MCP Server"
ENV MCP_DEBUG="false"
ENV YOUTRACK_VERIFY_SSL="true"

# Run the MCP server in stdio mode for Claude integration by default
CMD ["python", "main.py", "--transport", "stdio"]