#!/usr/bin/env python3
"""
IntelliStore Setup Script
Cross-platform setup for IntelliStore components
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """Run a command and handle errors"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Error: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def check_python():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version.split()[0]} found")

def check_node():
    """Check Node.js version"""
    try:
        result = run_command("node --version", check=False)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ Node.js {version} found")
            return True
    except:
        pass
    
    print("Error: Node.js is required but not found")
    print("Please install Node.js from https://nodejs.org/")
    return False

def check_go():
    """Check Go version"""
    try:
        result = run_command("go version", check=False)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ {version} found")
            return True
    except:
        pass
    
    print("Error: Go is required but not found")
    print("Please install Go from https://golang.org/")
    return False

def setup_python_venv(component_path, requirements_file="requirements.txt"):
    """Setup Python virtual environment for a component"""
    venv_path = component_path / "venv"
    
    print(f"Setting up Python environment for {component_path.name}...")
    
    # Create virtual environment
    if venv_path.exists():
        shutil.rmtree(venv_path)
    
    run_command(f'"{sys.executable}" -m venv venv', cwd=component_path)
    
    # Determine pip path based on OS
    if platform.system() == "Windows":
        pip_path = venv_path / "Scripts" / "pip"
        python_path = venv_path / "Scripts" / "python"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # Convert to absolute paths
    pip_path = pip_path.resolve()
    python_path = python_path.resolve()
    
    # Upgrade pip
    run_command(f'"{python_path}" -m pip install --upgrade pip', cwd=component_path)
    
    # Install requirements
    requirements_path = component_path / requirements_file
    if requirements_path.exists():
        run_command(f'"{pip_path}" install -r {requirements_file}', cwd=component_path)
    
    print(f"✓ Python environment setup complete for {component_path.name}")

def setup_go_component(component_path):
    """Setup Go component"""
    print(f"Setting up Go component {component_path.name}...")
    
    # Download dependencies
    run_command("go mod download", cwd=component_path)
    
    # Build the component
    run_command("go build -o bin/ ./cmd/...", cwd=component_path)
    
    print(f"✓ Go component {component_path.name} built successfully")

def setup_frontend():
    """Setup frontend component"""
    frontend_path = Path("intellistore-frontend")
    print(f"Setting up frontend...")
    
    # Install dependencies
    run_command("npm install", cwd=frontend_path)
    
    print("✓ Frontend setup complete")

def main():
    """Main setup function"""
    print("🚀 IntelliStore Setup")
    print("=" * 50)
    
    # Check prerequisites
    print("\n📋 Checking prerequisites...")
    check_python()
    
    if not check_node():
        sys.exit(1)
    
    if not check_go():
        sys.exit(1)
    
    print("\n✓ All prerequisites satisfied")
    
    # Setup components
    print("\n🔧 Setting up components...")
    
    # Setup Python components
    api_path = Path("intellistore-api")
    ml_path = Path("intellistore-ml")
    
    if api_path.exists():
        setup_python_venv(api_path)
    
    if ml_path.exists():
        setup_python_venv(ml_path)
    
    # Setup Go components
    core_path = Path("intellistore-core")
    tier_controller_path = Path("intellistore-tier-controller")
    
    if core_path.exists():
        setup_go_component(core_path)
    
    if tier_controller_path.exists():
        setup_go_component(tier_controller_path)
    
    # Setup frontend
    frontend_path = Path("intellistore-frontend")
    if frontend_path.exists():
        setup_frontend()
    
    print("\n🎉 Setup complete!")
    print("\nTo start IntelliStore, run:")
    if platform.system() == "Windows":
        print("  start.bat")
    else:
        print("  ./start.sh")

if __name__ == "__main__":
    main()