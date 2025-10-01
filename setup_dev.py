#!/usr/bin/env python3
"""
Development setup script for Farnsworth Fusor project.
This script helps set up the development environment with pre-commit hooks.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Farnsworth Fusor development environment...")
    print("=" * 60)
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: You don't appear to be in a virtual environment.")
        print("   It's recommended to activate your virtual environment first.")
        response = input("   Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("   Setup cancelled.")
            return False
    
    # Install development dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return False
    
    # Install pre-commit hooks
    if not run_command("pre-commit install", "Installing pre-commit hooks"):
        return False
    
    # Run pre-commit on all files to set up the environment
    if not run_command("pre-commit run --all-files", "Running pre-commit on all files"):
        print("⚠️  Some pre-commit checks failed. This is normal for the first run.")
        print("   The hooks are now installed and will run on future commits.")
    
    print("\n" + "=" * 60)
    print("🎉 Development environment setup complete!")
    print("\nNext steps:")
    print("1. Make your changes to the code")
    print("2. Commit your changes - pre-commit hooks will run automatically")
    print("3. If hooks fail, fix the issues and commit again")
    print("\nManual commands:")
    print("• Run linting: pylint src/")
    print("• Format code: black src/")
    print("• Run pre-commit: pre-commit run --all-files")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
