#!/usr/bin/env python3
"""
CCC Simple - Einfacher All-in-One Contest Runner

Ein einziges Skript für den kompletten CCC Workflow mit AI-Integration.

Verwendung:
    python ccc_simple.py <level_nummer> [optionen]
    
Optionen:
    --auto          Vollautomatik mit AI
    --template      Nur Template erstellen
    --help          Hilfe anzeigen

Beispiele:
    python ccc_simple.py 5           # Interaktiv mit AI-Hilfe
    python ccc_simple.py 5 --auto    # Vollautomatisch
    python ccc_simple.py 5 --template # Nur Template
"""

import os
import sys
import zipfile
import shutil
import subprocess
from pathlib import Path
import argparse

# Versuche pdfplumber zu importieren
try:
    import pdfplumber
    PDF_OK = True
except ImportError:
    PDF_OK = False


class CCCSimple:
    """Einfacher CCC Runner - alles in einer Klasse."""
    
    def __init__(self, level: int):
        self.level = level
        self.level_dir = Path("levels") / f"level-{level}"
        self.source_dir = self.level_dir / "source"
        self.input_dir = self.level_dir / "Inputs"
        self.output_dir = self.level_dir / "Outputs"
        self.setup_dirs()
    
    def setup_dirs(self):
        """Erstelle benötigte Ordner."""
        for folder in [self.source_dir, self.input_dir, self.output_dir]:
            folder.mkdir(parents=True, exist_ok=True)

    def prepare_run(self):
        """Entferne alte Laufdaten dieses Levels vor einem neuen Lauf."""
        if self.source_dir.exists():
            shutil.rmtree(self.source_dir)

        for folder in [self.input_dir, self.output_dir]:
            if folder.exists():
                shutil.rmtree(folder)

        for filename in [
            f"level{self.level}_prompt.txt",
            f"level{self.level}_workflow.md",
            f"level{self.level}_ai_request.md",
        ]:
            file_path = self.level_dir / filename
            if file_path.exists():
                file_path.unlink()

        self.setup_dirs()
        self.log(f"Alte Laufdaten gelöscht: {self.level_dir}", "OK")
    
    def log(self, msg: str, typ: str = "INFO"):
        """Einfaches Logging mit Icons."""
        icons = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "AI": "🤖"}
        print(f"{icons.get(typ, '•')} {msg}")
    
    def header(self, title: str):
        """Titel ausgeben."""
        print(f"\n{'='*60}\n{title}\n{'='*60}")
    
    def find_zip(self) -> Path:
        """Finde ZIP-Datei."""
        zip_name = f"level-{self.level}.zip"
        
        # Downloads-Ordner prüfen
        downloads = Path.home() / "Downloads" / zip_name
        if downloads.exists():
            self.log(f"ZIP gefunden: {downloads}")
            return downloads
            
        # Aktueller Ordner
        local = Path(zip_name)
        if local.exists():
            self.log(f"ZIP gefunden: {local}")
            return local
            
        raise FileNotFoundError(f"❌ {zip_name} nicht gefunden!")
    
    def extract_zip(self):
        """ZIP extrahieren."""
        zip_path = self.find_zip()
        self.log("Extrahiere ZIP...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.source_dir)
        
        self.log("ZIP extrahiert", "OK")
    
    def find_pdf(self) -> Path:
        """Finde PDF-Datei."""
        patterns = [
            f"Level {self.level}.pdf",
            f"level{self.level}.pdf", 
            f"Level{self.level}.pdf",
            f"level-{self.level}.pdf"
        ]
        
        # Downloads prüfen
        for pattern in patterns:
            pdf_path = Path.home() / "Downloads" / pattern
            if pdf_path.exists():
                return pdf_path
        
        # infos Ordner prüfen
        for pattern in patterns:
            pdf_path = self.source_dir / pattern
            if pdf_path.exists():
                return pdf_path
        
        # Irgendein PDF in infos
        pdfs = list(self.source_dir.glob("*.pdf"))
        if pdfs:
            return pdfs[0]
            
        raise FileNotFoundError("❌ Keine PDF gefunden!")
    
    def extract_pdf_text(self) -> str:
        """PDF-Text extrahieren."""
        try:
            pdf_path = self.find_pdf()
        except FileNotFoundError as e:
            self.log(str(e), "WARN")
            return ""

        self.log(f"PDF gefunden: {pdf_path}", "OK")

        if not PDF_OK:
            self.log(
                "pdfplumber nicht installiert - PDF-Text kann nicht extrahiert werden. "
                "Installiere es mit: python3 -m pip install pdfplumber",
                "WARN",
            )
            return ""
        
        try:
            self.log(f"Extrahiere Text aus: {pdf_path.name}")
            
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            self.log(f"PDF-Text extrahiert ({len(text)} Zeichen)", "OK")
            return text
            
        except Exception as e:
            self.log(f"PDF-Extraktion fehlgeschlagen: {e}", "WARN")
            return ""
    
    def create_ai_prompt(self, pdf_text: str) -> str:
        """AI-Prompt erstellen."""
        level_path = self.level_dir.resolve()
        prompt = f"""# Coding Challenge - Level {self.level}

    ## Verbindliche Dateipfade
    Arbeitsordner dieses Levels: `{level_path}`
    Eingabedateien: `{level_path / "Inputs"}`
    Ausgabedateien: `{level_path / "Outputs"}`
    Lösungsdatei: `{level_path / f"level{self.level}.py"}`

    WICHTIG:
    - Verwende ausschließlich diese Pfade für dieses Level.
    - Die Lösung muss die Verzeichnisse relativ zu ihrer eigenen Datei bestimmen.
    - Verwende dafür `Path(__file__).resolve().parent`, nicht den aktuellen Terminalordner.
    - Suche Eingaben mit `BASE_DIR / "Inputs" / "in_*"`.
    - Schreibe Ausgaben mit `BASE_DIR / "Outputs"`.
    - Speichere die Lösung exakt unter `{level_path / f"level{self.level}.py"}`.

## Problembeschreibung:
            {pdf_text if pdf_text else "[PDF gefunden, aber der Text konnte nicht extrahiert werden - Problem manuell eingeben]"}

## Aufgabe:
Erstelle eine vollständige Python-Lösung die:
1. Input-Dateien aus Inputs/ liest
2. Jede Eingabe gemäß Problembeschreibung verarbeitet  
3. Output-Dateien nach Outputs/ schreibt
4. Optimisierung ist wichtig (sei so schnell wie möglich), aber opfere möglichst wenig qualität)

## Input-Dateien:
- Pfad: Inputs/
- Format: in_*

## Output-Dateien:
- Pfad: Outputs/
- Format: out_*

## Template:
```python
from pathlib import Path

def solve(input_data):
    # Deine Lösung hier
    lines = input_data.strip().split('\\n')
    # ... Verarbeitung ...
    return "result"

def main():
    base_dir = Path(__file__).resolve().parent
    input_folder = base_dir / "Inputs"
    output_folder = base_dir / "Outputs"
    output_folder.mkdir(exist_ok=True)
    
    for input_file in sorted(input_folder.glob("in_*")):
        with open(input_file, 'r', encoding='utf-8') as f:
            data = f.read()
        
        result = solve(data)
        
        output_file = output_folder / input_file.name.replace('in_', 'out_', 1)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(result))
        print(f"Generiert: {{output_file.name}}")

if __name__ == "__main__":
    main()
```

Überlegter Lüsungsweg:

(Hier Lösungsweg einfügen)

Bitte erstelle eine vollständige Lösung und speichere sie als level{self.level}.py
"""
        
        # Prompt-Datei speichern
        prompt_file = self.level_dir / f"level{self.level}_prompt.txt"
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        
        self.log(f"AI-Prompt gespeichert: {prompt_file}", "OK")
        return prompt
    
    def organize_files(self):
        """Dateien organisieren."""
        self.log("Organisiere Dateien...")
        
        # Eingabedateien nach Inputs/
        in_files = [
            file_path for file_path in self.source_dir.rglob("in_*")
            if file_path.is_file()
        ]
        for in_file in in_files:
            dest = self.input_dir / in_file.name
            shutil.move(str(in_file), str(dest))
        
        # Referenzausgaben nach Outputs/ (falls vorhanden)
        out_files = [
            file_path for file_path in self.source_dir.rglob("out_*")
            if file_path.is_file()
        ]
        for out_file in out_files:
            dest = self.output_dir / out_file.name
            shutil.move(str(out_file), str(dest))
        
        self.log(f"Dateien organisiert: {len(in_files)} .in, {len(out_files)} .out", "OK")
    
    def generate_template(self):
        """Template-Lösung generieren."""
        template = f'''"""
Level {self.level} - Auto-generiertes Template

TODO: Implementiere die solve() Funktion!
"""

from pathlib import Path


def solve(input_data):
    """
    Löse das Problem für die gegebenen Input-Daten.
    
    Args:
        input_data (str): Die Input-Daten als String
        
    Returns:
        str: Die Lösung
    """
    lines = input_data.strip().split('\\n')
    
    # TODO: Hier deine Lösung implementieren
    # Beispiel:
    # first_line = lines[0]
    # numbers = [int(x) for x in first_line.split()]
    # result = sum(numbers)
    
    result = "0"  # Platzhalter-Ergebnis
    return result


def main():
    """Haupt-Funktion zum Verarbeiten aller Input-Dateien."""
    input_folder = Path("Inputs")
    output_folder = Path("Outputs")
    output_folder.mkdir(exist_ok=True)
    
    # Alle Input-Dateien für dieses Level finden
    pattern = f"level{self.level}_*.in"
    input_files = sorted(input_folder.glob(pattern))
    
    if not input_files:
        print(f"❌ Keine Input-Dateien gefunden: {{pattern}}")
        return
    
    print(f"📁 Verarbeite {{len(input_files)}} Input-Dateien...")
    
    for input_file in input_files:
        print(f"📄 Verarbeite {{input_file.name}}...")
        
        # Input lesen
        with open(input_file, 'r', encoding='utf-8') as f:
            input_data = f.read()
        
        # Problem lösen
        result = solve(input_data)
        
        # Output schreiben
        output_file = output_folder / input_file.name.replace('.in', '.out')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(result))
        
        print(f"✅ Generiert: {{output_file.name}}")
    
    print("🎉 Alle Input-Dateien verarbeitet!")


if __name__ == "__main__":
    main()
'''
        
        solution_file = self.level_dir / f"level{self.level}.py"
        with open(solution_file, 'w', encoding='utf-8') as f:
            f.write(template)
        
        self.log(f"Template erstellt: {solution_file}", "OK")
        self.log("⚠️  Bitte implementiere die solve() Funktion!", "WARN")
    
    def run_solution(self) -> bool:
        """Lösung ausführen."""
        solution_file = self.level_dir / f"level{self.level}.py"
        
        if not Path(solution_file).exists():
            self.log(f"{solution_file} nicht gefunden!", "ERROR")
            return False
        
        self.log(f"Führe {solution_file} aus...")
        
        try:
            result = subprocess.run(
                [sys.executable, solution_file.name],
                cwd=self.level_dir,
                capture_output=False,
            )
            
            if result.returncode == 0:
                self.log("Lösung erfolgreich ausgeführt", "OK")
                
                # Output-Dateien zählen
                out_files = list(self.output_dir.glob("*.out"))
                self.log(f"Generiert: {len(out_files)} Output-Dateien", "OK")
                return True
            else:
                self.log(f"Lösung fehlgeschlagen (Code: {result.returncode})", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Fehler beim Ausführen: {e}", "ERROR")
            return False
    
    def cleanup(self):
        """Aufräumen."""
        self.log("Räume auf...")
        
        if self.source_dir.exists():
            shutil.rmtree(self.source_dir)
        
        self.log("Aufgeräumt", "OK")
    
    def create_ai_workflow(self):
        """AI-Workflow-Anleitung erstellen."""
        workflow = f"""# Level {self.level} - AI Workflow

## Schritt 1: Prompt kopieren
Kopiere den Inhalt aus: `levels/level-{self.level}/level{self.level}_prompt.txt`

## Schritt 2: AI verwenden
Füge den Prompt ein in:
- GitHub Copilot Chat (VS Code)
- ChatGPT / Claude / beliebige AI
- Beliebigen Code-Assistenten

## Schritt 3: Lösung generieren
Bitte die AI:
1. Vollständige Python-Lösung zu erstellen
2. Als `levels/level-{self.level}/level{self.level}.py` zu speichern
3. Sicherstellen dass sie aus `Inputs/` liest und nach `Outputs/` schreibt

## Schritt 4: Testen
Führe die Lösung aus dem Level-Ordner aus: `python levels/level-{self.level}/level{self.level}.py`

## Schritt 5: Fertigstellen
Führe aus dem Projektordner aus: `python ccc_simple.py {self.level}` um einen neuen Lauf zu starten
"""
        
        workflow_file = self.level_dir / f"level{self.level}_workflow.md"
        with open(workflow_file, 'w', encoding='utf-8') as f:
            f.write(workflow)
        
        self.log(f"AI-Workflow erstellt: {workflow_file}", "AI")
        return workflow_file
    
    def run_interactive(self):
        """Interaktiver Modus."""
        self.header(f"🎯 CCC Level {self.level} - Interaktiver Modus")
        
        # Schritt 1: Dateien verarbeiten
        try:
            self.prepare_run()
            self.extract_zip()
            pdf_text = self.extract_pdf_text()
            self.create_ai_prompt(pdf_text)
            self.organize_files()
        except Exception as e:
            self.log(f"Verarbeitung fehlgeschlagen: {e}", "ERROR")
            return 1
        
        # Schritt 2: AI-Workflow erstellen
        workflow_file = self.create_ai_workflow()
        
        # Schritt 3: Pause für manuelle Arbeit
        self.header(f"⏸️  PAUSE - Erstelle level{self.level}.py")
        print(f"📋 AI-Prompt: {self.level_dir / f'level{self.level}_prompt.txt'}")
        print(f"📖 Workflow: {workflow_file}")
        print(f"📁 Input-Dateien: {self.input_dir}/")
        print(f"🎯 Erstelle: {self.level_dir / f'level{self.level}.py'}")
        print(f"\nDrücke ENTER wenn level{self.level}.py fertig ist...")
        input()

        if self.run_solution():
            self.cleanup()
            self.header(f"🎉 Level {self.level} erfolgreich abgeschlossen!")
            return 0
        else:
            return 1
    
    def run_auto(self):
        """Automatischer Modus mit AI."""
        self.header(f"🤖 CCC Level {self.level} - Automatischer Modus")
        
        # Schritt 1: Dateien verarbeiten
        try:
            self.prepare_run()
            self.extract_zip()
            pdf_text = self.extract_pdf_text()
            prompt = self.create_ai_prompt(pdf_text)
            self.organize_files()
        except Exception as e:
            self.log(f"Verarbeitung fehlgeschlagen: {e}", "ERROR")
            return 1
        
        self.log("Versuche AI-Automatisierung...", "AI")
        
        # Erstelle Anweisungsdatei für manuelle AI-Nutzung
        ai_file = self.level_dir / f"level{self.level}_ai_request.md"
        with open(ai_file, 'w', encoding='utf-8') as f:
            f.write(f"""# AI Request für Level {self.level}

Bitte generiere eine vollständige Python-Lösung für diese Coding Challenge.

{prompt}
- Stelle sicher dass es aus Inputs/ liest und nach Outputs/ schreibt
- Füge Fehlerbehandlung hinzu
""")
        
        # Manuelle AI-Anweisung
        self.header("🤖 AI-AUTOMATISIERUNG - MANUELLER SCHRITT")
        print(f"1. Öffne: {ai_file}")
        print("2. Kopiere den kompletten Inhalt")
        print("3. Füge ihn in GitHub Copilot Chat ein")
        print(f"4. Speichere die generierte Lösung als: {self.level_dir / f'level{self.level}.py'}")
        print("5. Drücke ENTER wenn die Lösung bereit ist...")
        input()
        
        # Schritt 3: Lösung ausführen
        if self.run_solution():
            self.cleanup()
            self.header(f"🎉 Level {self.level} automatisch abgeschlossen!")
            return 0
        else:
            return 1
    
    def run_template_only(self):
        """Nur Template erstellen."""
        self.header(f"📝 CCC Level {self.level} - Template-Modus")
        
        try:
            self.prepare_run()
            self.extract_zip()
            self.extract_pdf_text()  # Für Kontext, auch wenn nicht verwendet
            self.organize_files()
            self.generate_template()
            
            self.header("Template erstellt!")
            print(f"📝 Template: {self.level_dir / f'level{self.level}.py'}")
            print("⚠️  Implementiere die solve() Funktion")
            print(f"\nLösung testen? [j/N]: ", end="")
            
            if input().lower() in ['j', 'ja', 'y', 'yes']:
                if self.run_solution():
                    self.cleanup()
                    return 0
            
            return 0
            
        except Exception as e:
            self.log(f"Template-Erstellung fehlgeschlagen: {e}", "ERROR")
            return 1


def main():
    """Haupt-Funktion."""
    parser = argparse.ArgumentParser(
        description="CCC Simple - Einfacher All-in-One Contest Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python ccc_simple.py 5           # Level 5 Zip wird verarbeitet
  python ccc_simple.py 5 --template # Nur Template erstellen
        """
    )
    
    parser.add_argument('level', type=int, help='Level-Nummer')
    parser.add_argument('--auto', action='store_true', help='Vollautomatik mit AI')
    parser.add_argument('--template', action='store_true', help='Nur Template erstellen')
    
    args = parser.parse_args()
    
    # Abhängigkeiten prüfen
    if not PDF_OK:
        print("⚠️  pdfplumber nicht installiert. Installiere mit: pip install pdfplumber")
    
    # Runner erstellen
    runner = CCCSimple(args.level)
    
    # Modus bestimmen
    try:
        if args.template:
            return runner.run_template_only()
        elif args.auto:
            return runner.run_auto()
        else:
            return runner.run_interactive()
    except KeyboardInterrupt:
        print("\n❌ Abgebrochen")
        return 1
    except Exception as e:
        print(f"❌ Unerwarteter Fehler: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())