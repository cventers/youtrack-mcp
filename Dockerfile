FROM python:3.13-alpine

# Install security updates and required packages
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
        ca-certificates \
        tzdata && \
    rm -rf /var/cache/apk/*

# Create non-root user for security
RUN addgroup -g 10001 -S appgroup && \
    adduser -u 10001 -S appuser -G appgroup -h /app -s /sbin/nologin

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY --chown=10001:10001 requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt && \
    python -c "import mcp; print(dir(mcp))" && \
    pip cache purge

# Copy the rest of the application with proper ownership
COPY --chown=10001:10001 . .

# Set proper permissions on application files
RUN chmod -R 755 /app && \
    find /app -type f -name "*.py" -exec chmod 644 {} \; && \
    find /app -type f -name "*.sh" -exec chmod 755 {} \;

# Switch to non-root user
USER 10001

# Default environment variables (will be overridden at runtime)
ENV MCP_SERVER_NAME="youtrack-mcp"
ENV MCP_SERVER_DESCRIPTION="YouTrack MCP Server"
ENV MCP_DEBUG="false"
ENV YOUTRACK_VERIFY_SSL="true"

# Security hardening
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Set secure umask
RUN umask 0027

# Run the MCP server in stdio mode for Claude integration by default
CMD ["python", "main.py", "--transport", "stdio"]