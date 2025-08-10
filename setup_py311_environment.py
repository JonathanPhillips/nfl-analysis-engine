#!/usr/bin/env python3
"""Script to set up Python 3.11 environment for NFL data."""

import subprocess
import sys
from pathlib import Path

def setup_python311_environment():
    """Set up Python 3.11 environment with nfl_data_py."""
    
    print("=" * 60)
    print("PYTHON 3.11 ENVIRONMENT SETUP")
    print("=" * 60)
    
    # Check if pyenv is available
    try:
        result = subprocess.run(['pyenv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ pyenv available")
            
            # Install Python 3.11.9 (stable version)
            print("\n1. Installing Python 3.11.9...")
            subprocess.run(['pyenv', 'install', '3.11.9'], check=False)
            
            # Create project-specific environment
            env_path = Path.cwd() / "nfl_data_env311"
            print(f"\n2. Creating environment at {env_path}")
            
            subprocess.run([
                'pyenv', 'exec', 'python3.11', '-m', 'venv', str(env_path)
            ], check=False)
            
            # Install packages
            pip_path = env_path / "bin" / "pip"
            print("\n3. Installing NFL data packages...")
            
            packages = [
                'nfl_data_py',
                'pandas', 
                'numpy',
                'requests',
                'pyarrow'  # For parquet support
            ]
            
            for package in packages:
                print(f"   Installing {package}...")
                subprocess.run([str(pip_path), 'install', package], check=False)
            
            print("\n✅ Python 3.11 environment setup complete!")
            print(f"To use: source {env_path}/bin/activate")
            
            # Create activation script
            activation_script = """#!/bin/bash
# NFL Data Environment Activation
source nfl_data_env311/bin/activate
echo "✅ NFL Data environment activated (Python 3.11)"
python3 --version
"""
            
            with open("activate_nfl_env.sh", "w") as f:
                f.write(activation_script)
            
            subprocess.run(['chmod', '+x', 'activate_nfl_env.sh'])
            print("Created activation script: ./activate_nfl_env.sh")
            
        else:
            print("❌ pyenv not available")
            print("Install with: brew install pyenv")
            
    except FileNotFoundError:
        print("❌ pyenv not found")
        print("Install pyenv first: brew install pyenv")
        
        # Alternative: use conda/mamba
        try:
            result = subprocess.run(['conda', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("\n✅ conda available as alternative")
                print("Run: conda create -n nfl_data python=3.11 pandas numpy")
        except FileNotFoundError:
            print("❌ conda also not available")

if __name__ == "__main__":
    setup_python311_environment()