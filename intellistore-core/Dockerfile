# Multi-stage build for IntelliStore Core
FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates tzdata

# Set working directory
WORKDIR /app

# Copy go mod files
COPY go.mod ./

# Download dependencies and create go.sum
RUN go mod tidy && go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o intellistore-server ./cmd/server
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o intellistore-client ./cmd/client

# Final stage
FROM alpine:3.18

# Install runtime dependencies
RUN apk --no-cache add ca-certificates tzdata

# Create non-root user
RUN addgroup -g 1001 intellistore && \
    adduser -D -u 1001 -G intellistore intellistore

# Set working directory
WORKDIR /app

# Copy binaries from builder
COPY --from=builder /app/intellistore-server .
COPY --from=builder /app/intellistore-client .

# Create data directory
RUN mkdir -p /var/lib/intellistore && \
    chown -R intellistore:intellistore /var/lib/intellistore

# Switch to non-root user
USER intellistore

# Expose ports
EXPOSE 5000 8080 9100

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Default command
CMD ["./intellistore-server"]