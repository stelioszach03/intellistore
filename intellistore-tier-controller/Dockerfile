# Multi-stage build for IntelliStore Tier Controller
FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates

# Set working directory
WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o tier-controller ./cmd/main.go

# Final stage
FROM alpine:latest

# Install ca-certificates for HTTPS requests
RUN apk --no-cache add ca-certificates

# Create non-root user
RUN addgroup -g 1001 intellistore && \
    adduser -D -u 1001 -G intellistore intellistore

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