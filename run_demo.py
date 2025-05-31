#!/usr/bin/env python3
"""
IntelliStore Demo Runner

This script runs a simplified version of IntelliStore for demonstration purposes.
It creates mock services and runs the API and frontend to show the system functionality.
"""

import asyncio
import os
import subprocess
import sys
import time
import threading
from pathlib import Path

# Mock services for demonstration
class MockVaultService:
    def __init__(self):
        self.data = {}
        
    async def initialize(self):
        print("✅ Mock Vault service initialized")
        
    async def close(self):
        pass
        
    def get_secret(self, path):
        return {"data": {"key": "mock-secret"}}

class MockKafkaService:
    def __init__(self, *args, **kwargs):
        pass
        
    async def initialize(self):
        print("✅ Mock Kafka service initialized")
        
    async def close(self):
        pass
        
    async def send_message(self, topic, message):
        print(f"📨 Kafka message sent to {topic}: {message}")

class MockRaftService:
    def __init__(self, *args, **kwargs):
        self.metadata = {}
        
    async def initialize(self):
        print("✅ Mock Raft metadata service initialized")
        
    async def close(self):
        pass
        
    async def get_metadata(self, key):
        return self.metadata.get(key, {})
        
    async def set_metadata(self, key, value):
        self.metadata[key] = value

def setup_environment():
    """Setup environment variables for the demo"""
    os.environ.update({
        "ENVIRONMENT": "development",
        "JWT_SECRET": "demo-secret-key-for-intellistore",
        "VAULT_ADDR": "http://localhost:8200",
        "VAULT_TOKEN": "demo-token",
        "RAFT_LEADER_ADDR": "localhost:5000",
        "STORAGE_NODES": "localhost:8080,localhost:8081,localhost:8082",
        "KAFKA_BROKERS": "localhost:9092",
        "DEBUG": "true"
    })

def patch_services():
    """Patch the real services with mock versions"""
    import sys
    sys.path.insert(0, '/workspace/intellistore/intellistore-api')
    
    # Import and patch the services
    from app.services import vault_service, kafka_service, raft_service
    
    vault_service.VaultService = MockVaultService
    kafka_service.KafkaService = MockKafkaService
    raft_service.RaftService = MockRaftService
    
    print("🔧 Services patched with mock implementations")

def run_api_server():
    """Run the FastAPI server"""
    try:
        setup_environment()
        patch_services()
        
        # Change to API directory
        os.chdir('/workspace/intellistore/intellistore-api')
        
        # Import and run the app
        import uvicorn
        from main import app
        
        print("🚀 Starting IntelliStore API server on http://localhost:8000")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ Error starting API server: {e}")
        import traceback
        traceback.print_exc()

def run_frontend_server():
    """Run the frontend development server"""
    try:
        # Change to frontend directory
        frontend_dir = '/workspace/intellistore/intellistore-frontend'
        os.chdir(frontend_dir)
        
        print("🎨 Starting IntelliStore Frontend on http://localhost:53641")
        
        # Run npm dev server
        subprocess.run([
            'npm', 'run', 'dev', '--', '--host', '0.0.0.0', '--port', '53641'
        ], check=True)
        
    except Exception as e:
        print(f"❌ Error starting frontend server: {e}")

def print_banner():
    """Print the IntelliStore banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ██╗███╗   ██╗████████╗███████╗██╗     ██╗     ██╗███████╗████████╗ ██████╗ ██████╗ ███████╗    ║
║    ██║████╗  ██║╚══██╔══╝██╔════╝██║     ██║     ██║██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗██╔════╝    ║
║    ██║██╔██╗ ██║   ██║   █████╗  ██║     ██║     ██║███████╗   ██║   ██║   ██║██████╔╝█████╗      ║
║    ██║██║╚██╗██║   ██║   ██╔══╝  ██║     ██║     ██║╚════██║   ██║   ██║   ██║██╔══██╗██╔══╝      ║
║    ██║██║ ╚████║   ██║   ███████╗███████╗███████╗██║███████║   ██║   ╚██████╔╝██║  ██║███████╗    ║
║    ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝    ║
║                                                                              ║
║                    AI-Driven Cloud-Native Distributed Object Storage        ║
║                                                                              ║
║                                  DEMO MODE                                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

🌟 Welcome to IntelliStore Demo!

This demonstration shows the key features of IntelliStore:
• 🔐 Authentication & Authorization
• 🪣 Bucket Management
• 📁 Object Storage Operations
• 📊 Real-time Monitoring
• 🤖 AI-Driven Tiering (simulated)
• 🔄 WebSocket Real-time Updates

Services Status:
• API Server: Starting on http://localhost:8000
• Frontend: Starting on http://localhost:53641
• Mock Services: Vault, Kafka, Raft (for demo purposes)

📖 Access the application at: http://localhost:53641
📚 API Documentation: http://localhost:8000/docs
📈 Health Check: http://localhost:8000/health

"""
    print(banner)

def main():
    """Main demo runner"""
    print_banner()
    
    # Start API server in a separate thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # Wait a bit for API to start
    print("⏳ Waiting for API server to start...")
    time.sleep(3)
    
    # Test API health
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is healthy!")
        else:
            print("⚠️  API server responded but may have issues")
    except Exception as e:
        print(f"⚠️  Could not verify API health: {e}")
    
    print("\n🎯 Starting frontend server...")
    print("📱 Once started, open http://localhost:53641 in your browser")
    print("🔑 Use any email/password to login (demo mode)")
    print("\n⌨️  Press Ctrl+C to stop all services\n")
    
    try:
        # Run frontend server (this will block)
        run_frontend_server()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down IntelliStore demo...")
        print("👋 Thank you for trying IntelliStore!")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()