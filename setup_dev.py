#!/usr/bin/env python3
"""
Development setup script for Farnsworth Fusor project.
This script sets up the development environment and installs dependencies.
"""

import os
import sys
import subprocess
import platform

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main setup function."""
    print("Farnsworth Fusor Development Setup")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required")
        sys.exit(1)
    
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        print("Failed to install dependencies")
        sys.exit(1)
    
    # Create necessary directories
    directories = ["logs", "data", "tests"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")
    
    # Set up pre-commit hooks if available
    if run_command("pre-commit install", "Setting up pre-commit hooks"):
        print("✓ Pre-commit hooks installed")
    else:
        print("⚠ Pre-commit not available, skipping hooks setup")
    
    print("\n" + "=" * 40)
    print("Development setup completed successfully!")
    print("\nNext steps:")
    print("1. Run tests: python -m pytest tests/")
    print("2. Start development: python src/Host_Codebase/ssh_datalink_host.py")
    print("3. Check code quality: pylint src/")

if __name__ == "__main__":
    main()
