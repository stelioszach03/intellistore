#!/bin/bash

# IntelliStore Startup Script for Unix/Linux/macOS
# This script starts all IntelliStore components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1
    else
        return 0
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within timeout"
    return 1
}

# Function to start a component in background
start_component() {
    local component=$1
    local command=$2
    local port=$3
    local log_file="logs/${component}.log"
    
    print_status "Starting $component..."
    
    # Check if port is available
    if ! check_port $port; then
        print_warning "Port $port is already in use. $component may already be running."
        return 1
    fi
    
    # Create logs directory
    mkdir -p logs
    
    # Start the component
    eval "$command" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "logs/${component}.pid"
    
    print_success "$component started (PID: $pid, Port: $port)"
    return 0
}

# Function to stop all components
stop_all() {
    print_status "Stopping all IntelliStore components..."
    
    # Kill processes by PID files
    for pid_file in logs/*.pid; do
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            local component=$(basename "$pid_file" .pid)
            
            if kill -0 $pid 2>/dev/null; then
                print_status "Stopping $component (PID: $pid)..."
                kill $pid
                rm -f "$pid_file"
            fi
        fi
    done
    
    # Also kill by process name patterns
    pkill -f "intellistore-server" 2>/dev/null || true
    pkill -f "intellistore-client" 2>/dev/null || true
    pkill -f "tier-controller" 2>/dev/null || true
    pkill -f "uvicorn.*main:app" 2>/dev/null || true
    pkill -f "vite.*--port.*51017" 2>/dev/null || true
    
    print_success "All components stopped"
}

# Function to show status
show_status() {
    print_status "IntelliStore Component Status:"
    echo
    
    # Check each component
    local components=(
        "Core Server:8001"
        "API Server:8000"
        "ML Service:8002"
        "Frontend:51017"
        "Tier Controller:8003"
    )
    
    for component_info in "${components[@]}"; do
        local name=$(echo $component_info | cut -d: -f1)
        local port=$(echo $component_info | cut -d: -f2)
        
        if check_port $port; then
            echo -e "  $name: ${RED}STOPPED${NC}"
        else
            echo -e "  $name: ${GREEN}RUNNING${NC} (port $port)"
        fi
    done
    echo
}

# Main script logic
case "${1:-start}" in
    "start")
        print_status "🚀 Starting IntelliStore..."
        echo
        
        # Check if setup was run
        if [ ! -d "intellistore-api/venv" ] || [ ! -d "intellistore-ml/venv" ] || [ ! -d "intellistore-frontend/node_modules" ]; then
            print_warning "Setup not detected. Running setup first..."
            python3 setup.py
            echo
        fi
        
        # Start Core Server
        if [ -d "intellistore-core" ]; then
            start_component "core-server" "cd intellistore-core && ./bin/server" 8001
        fi
        
        # Start API Server
        if [ -d "intellistore-api" ]; then
            start_component "api-server" "cd intellistore-api && ./venv/bin/python main.py" 8000
        fi
        
        # Start ML Service
        if [ -d "intellistore-ml" ]; then
            start_component "ml-service" "cd intellistore-ml && ./venv/bin/python simple_main.py" 8002
        fi
        
        # Start Tier Controller
        if [ -d "intellistore-tier-controller" ]; then
            start_component "tier-controller" "cd intellistore-tier-controller && ./bin/tier-controller" 8003
        fi
        
        # Wait a bit for backend services to start
        sleep 5
        
        # Start Frontend
        if [ -d "intellistore-frontend" ]; then
            start_component "frontend" "cd intellistore-frontend && npm run dev" 51017
        fi
        
        echo
        print_success "🎉 IntelliStore started successfully!"
        echo
        print_status "Access points:"
        echo "  • Frontend: http://localhost:51017"
        echo "  • API: http://localhost:8000"
        echo "  • API Docs: http://localhost:8000/docs"
        echo
        print_status "Logs are available in the 'logs/' directory"
        print_status "Use './start.sh stop' to stop all services"
        print_status "Use './start.sh status' to check service status"
        ;;
        
    "stop")
        stop_all
        ;;
        
    "restart")
        stop_all
        sleep 2
        $0 start
        ;;
        
    "status")
        show_status
        ;;
        
    "logs")
        if [ -n "$2" ]; then
            tail -f "logs/$2.log"
        else
            print_status "Available log files:"
            ls -1 logs/*.log 2>/dev/null | sed 's/logs\///g' | sed 's/\.log//g' || echo "No log files found"
            echo
            print_status "Usage: $0 logs <component-name>"
        fi
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [component]}"
        echo
        echo "Commands:"
        echo "  start    - Start all IntelliStore components"
        echo "  stop     - Stop all IntelliStore components"
        echo "  restart  - Restart all IntelliStore components"
        echo "  status   - Show status of all components"
        echo "  logs     - Show available log files or tail a specific component log"
        exit 1
        ;;
esac