# Multi-stage build for IntelliStore Tier Controller
FROM golang:1.21 AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y git ca-certificates && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy go mod files and source code
COPY go.mod ./
COPY . .

# Download dependencies and create go.sum
RUN go mod tidy && go mod download

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o tier-controller ./cmd/main.go

# Final stage
FROM debian:bullseye-slim

# Install ca-certificates for HTTPS requests
RUN apt-get update && apt-get install -y ca-certificates wget && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1001 intellistore && \
    useradd -r -u 1001 -g intellistore intellistore

# Set working directory
WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/tier-controller .

# Change ownership
RUN chown intellistore:intellistore /app/tier-controller

# Switch to non-root user
USER intellistore

# Expose metrics port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:9090/health || exit 1

# Default command
CMD ["./tier-controller"]