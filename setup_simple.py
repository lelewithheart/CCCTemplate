"""
Einfaches Setup für CCC Simple

Führe diese Datei einmal aus um alles zu installieren.
"""

import subprocess
import sys
from pathlib import Path


def install_pip_package(package):
    """Installiert ein pip-Paket."""
    try:
        print(f"📦 Installiere {package}...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
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
    
    # Ordner erstellen
    print("\n📁 Erstelle Ordner...")
    for folder in ['Inputs', 'Outputs', 'infos']:
        Path(folder).mkdir(exist_ok=True)
        print(f"✅ {folder}/")
    
    # Abhängigkeiten installieren
    print("\n📦 Installiere Abhängigkeiten...")
    install_pip_package('pdfplumber')
    
    print("\n🎉 Setup abgeschlossen!")
    print("\n📖 Verwendung:")
    print("  python ccc_simple.py 5           # Interaktiv")
    print("  python ccc_simple.py 5 --template # Template")
    
    return True


if __name__ == "__main__":
    setup()