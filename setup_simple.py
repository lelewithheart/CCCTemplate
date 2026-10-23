"""
Einfaches Setup für CCC Simple

Führe diese Datei einmal aus um alles zu installieren.
"""

import subprocess
import sys
from pathlib import Path


def install_pip_package(python_executable, package):
    """Installiert ein pip-Paket."""
    try:
        print(f"📦 Installiere {package}...")
        result = subprocess.run([str(python_executable), '-m', 'pip', 'install', package], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {package} installiert")
            return True
        else:
            print(f"❌ Fehler bei {package}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {package} Installation fehlgeschlagen: {e}")
        return False


def setup():
    """Setup durchführen."""
    print("🚀 CCC Simple Setup")
    print("=" * 30)
    
    # Python-Version prüfen
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 6):
        print("❌ Python 3.6+ erforderlich")
        return False
    
    print("✅ Python Version OK")
    
    # Basisordner erstellen; die Level-Unterordner legt der Runner an
    print("\n📁 Erstelle Ordner...")
    for folder in ['levels']:
        Path(folder).mkdir(exist_ok=True)
        print(f"✅ {folder}/")
    
    # Abhängigkeiten in einer projektlokalen Umgebung installieren
    print("\n📦 Installiere Abhängigkeiten...")
    venv_dir = Path('.venv')
    if not venv_dir.exists():
        print(f"🐍 Erstelle {venv_dir}/...")
        result = subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)])
        if result.returncode != 0:
            print("❌ Virtuelle Umgebung konnte nicht erstellt werden")
            return False

    venv_python = venv_dir / 'bin' / 'python'
    if not venv_python.exists():
        print(f"❌ Python in {venv_dir}/ nicht gefunden")
        return False

    if not install_pip_package(venv_python, 'pdfplumber'):
        return False
    
    print("\n🎉 Setup abgeschlossen!")
    print("\n📖 Verwendung:")
    print("  .venv/bin/python ccc_simple.py 5           # Interaktiv")
    print("  .venv/bin/python ccc_simple.py 5 --template # Template")
    
    return True


if __name__ == "__main__":
    setup()