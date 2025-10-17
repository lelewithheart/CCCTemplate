# Archive - Erweiterte CCC-Systeme

Dieser Ordner enthält die erweiterten, modularen Versionen des CCC-Systems.

## 📁 Was ist hier?

### Haupt-Komponenten
- `ccc_runner.py` - Erweiterter Haupt-Runner mit vielen Optionen
- `ccc_core.py` - Modulare Kern-Funktionalität
- `ccc_ai_automation.py` - Erweiterte AI-Integration
- `run_level.py` - Optimierte Version des Original-Runners

### Dokumentation
- `README.md` - Vollständige Dokumentation des erweiterten Systems
- `WORKFLOW_ENHANCED.md` - Detaillierte Workflow-Beschreibungen
- `setup.py` - Setup für das modulare System

### Original-Dateien
- `general/` - Verarbeitungsscripts
  - `process_level.py` - Optimierte Version
  - `process_level_original.py` - Original-Backup

## 🤔 Wann verwenden?

**Verwende die Dateien hier wenn:**
- Du das CCC-System erweitern willst
- Du mit mehreren Projekten gleichzeitig arbeitest  
- Du die modulare Architektur brauchst
- Du verstehen willst, wie komplexe Systeme aufgebaut sind

**Für normale Contest-Verwendung:**
Verwende `ccc_simple.py` im Hauptordner - das ist viel einfacher!

## 🚀 Verwendung des erweiterten Systems

Falls du doch das erweiterte System verwenden willst:

```powershell
# Setup (einmalig)
python archive/setup.py

# Erweiterte Verwendung
python archive/ccc_runner.py 5 --auto        # Vollautomatik
python archive/ccc_runner.py 5 --interactive # Interaktiv
python archive/ccc_runner.py 5 --process-only # Nur verarbeiten
python archive/ccc_runner.py 5 --template    # Template

# Original-optimiert
python archive/run_level.py 5 --auto         # Automatisch
python archive/run_level.py 5                # Interaktiv
```

## 📊 Simple vs. Erweitert

| Aspekt | Simple (Hauptordner) | Erweitert (Archive) |
|--------|---------------------|---------------------|
| **Dateien** | 1 | 6+ |
| **Komplexität** | Niedrig | Hoch |
| **Funktionen** | Alle wichtigen | Alle + Extras |
| **Lernkurve** | Minimal | Steil |
| **Wartung** | Einfach | Komplex |
| **Erweiterbarkeit** | Basic | Hoch |

## 💡 Empfehlung

**Für 99% der Fälle:** Verwende `ccc_simple.py` im Hauptordner

**Nur für Entwickler/Erweiterer:** Verwende das System hier im Archive

---

*Die Dateien hier sind vollständig funktional und getestet, aber für normale Verwendung unnötig komplex.*