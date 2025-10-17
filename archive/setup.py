"""
Setup script for Enhanced CCC Template

This script helps set up the environment and install optional dependencies.
"""

import subprocess
import sys
from pathlib import Path


def install_package(package_name: str) -> bool:
    """Install a Python package using pip."""
    try:
        print(f"Installing {package_name}...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', package_name], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {package_name} installed successfully")
            return True
        else:
            print(f"❌ Failed to install {package_name}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing {package_name}: {e}")
        return False


def check_gh_cli() -> bool:
    """Check if GitHub CLI is installed."""
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True)
        if result.returncode == 0:
            print("✅ GitHub CLI is installed")
            
            # Check for Copilot extension
            result = subprocess.run(['gh', 'extension', 'list'], 
                                  capture_output=True, text=True)
            
            if 'github/gh-copilot' in result.stdout:
                print("✅ GitHub Copilot CLI extension is installed")
            else:
                print("⚠️  GitHub Copilot CLI extension not found")
                print("   Install with: gh extension install github/gh-copilot")
            
            return True
        else:
            print("⚠️  GitHub CLI not installed (optional for enhanced AI features)")
            print("   Install from: https://cli.github.com/")
            return False
    except FileNotFoundError:
        print("⚠️  GitHub CLI not installed (optional for enhanced AI features)")
        return False


def main():
    print("🚀 Enhanced CCC Template Setup")
    print("=" * 40)
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 6):
        print("❌ Python 3.6+ required")
        return 1
    
    print("✅ Python version is compatible")
    
    # Install optional dependencies
    print("\n📦 Installing optional dependencies...")
    
    optional_packages = [
        'pdfplumber',  # For PDF text extraction
    ]
    
    for package in optional_packages:
        install_package(package)
    
    # Check GitHub CLI
    print("\n🔧 Checking GitHub CLI (optional)...")
    check_gh_cli()
    
    # Create directories
    print("\n📁 Creating directories...")
    directories = ['Inputs', 'Outputs', 'infos', 'prompts', 'levels']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created/verified: {directory}/")
    
    print("\n🎉 Setup complete!")
    print("\n📖 Next steps:")
    print("1. Place level ZIP files in Downloads folder")
    print("2. Run: python ccc_runner.py <level_number> --auto")
    print("3. See WORKFLOW_ENHANCED.md for detailed instructions")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())