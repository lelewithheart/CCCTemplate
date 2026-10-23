# 🎯 Was sollst du verwenden?

## 🚀 **EMPFOHLEN: CCC Simple** (Neu, einfach, alles-in-einem)

```powershell
python3 setup_simple.py                # Einmal ausführen
.venv/bin/python ccc_simple.py 5       # Level 5 interaktiv
.venv/bin/python ccc_simple.py 5 --auto # Level 5 vollautomatisch
```

**Warum Simple?**
- ✅ **Nur 1 Datei** statt 6+ Module
- ✅ **3 einfache Befehle** für alles
- ✅ **Gleiche Funktionen** wie das komplexe System
- ✅ **Einfacher zu verstehen** und zu verwenden
- ✅ **Schneller** - kein Modul-Loading

---

## 🔧 **Erweitert: Vollständiges System** (Komplex, aber mächtig)

```powershell  
python setup.py                       # Setup
python ccc_runner.py 5 --auto         # Hauptrunner
python run_level.py 5 --auto          # Optimierter Original
```

**Wann verwenden?**
- 🔧 Du willst das System erweitern/anpassen
- 📚 Du arbeitest an mehreren Projekten gleichzeitig
- ⚙️ Du brauchst die modulare Architektur
- 🎓 Du willst verstehen wie komplexe Systeme aufgebaut sind

---

## 📊 Vergleich

| Feature | CCC Simple | Vollsystem |
|---------|------------|------------|
| **Dateien** | 1 | 6+ |
| **Setup** | `setup_simple.py` | `setup.py` |
| **Befehle** | 3 einfache | 10+ Optionen |
| **AI-Integration** | ✅ | ✅ |
| **Automatisierung** | ✅ | ✅ |
| **Erweiterbarkeit** | Basic | Hoch |
| **Lernkurve** | Niedrig | Hoch |

---

## 🎯 **Empfehlung**

### Für 99% der Fälle:
```powershell
# Verwende CCC Simple
.venv/bin/python ccc_simple.py 5
```

### Nur wenn du das System erweitern willst:
```powershell  
# Verwende das Vollsystem
python ccc_runner.py 5 --auto
```

---

## 📁 Dateiübersicht

```
CCCTemplate/
├── 🌟 ccc_simple.py           # ← DAS HIER VERWENDEN
├── 🌟 setup_simple.py         # ← Einmaliges Setup  
├── 🌟 README_SIMPLE.md        # ← Einfache Anleitung
├── 
├── 📖 WAS_VERWENDEN.md         # ← Diese Datei
├── 
└── [Vollsystem - Optional]
    ├── ccc_runner.py           # Erweiterter Runner
    ├── ccc_core.py             # Core-Module  
    ├── ccc_ai_automation.py    # AI-System
    ├── run_level.py            # Optimierter Original
    ├── setup.py                # Vollsystem-Setup
    ├── README.md               # Vollsystem-Doku
    └── WORKFLOW_ENHANCED.md    # Erweiterte Workflows
```

### Ordnerstruktur der Levels

Jedes Level wird getrennt verwaltet:

```
levels/
└── level-5/
    ├── Inputs/       # Eingabedateien
    ├── Outputs/      # erzeugte Ausgaben und Referenzausgaben
    ├── source/       # PDF aus dem ZIP
    ├── level5.py     # deine Lösung
    ├── level5_prompt.txt
    └── level5_workflow.md
```

Beim nächsten Lauf desselben Levels werden alte Inputs, Outputs, Prompt-,
Workflow- und Quelldateien automatisch ersetzt. Die vorhandene Lösung bleibt erhalten.

---

## 🚀 Schnellstart

**Neu hier? Fang mit Simple an:**

1. **Setup** (einmalig): `python3 setup_simple.py`
2. **Verwenden**: `.venv/bin/python ccc_simple.py 5`
3. **Fertig!** 🎉

**Das wars!** Keine komplexen Entscheidungen, keine Verwirrung.

---

**💡 Tipp**: Das Vollsystem ist immer noch da falls du es später brauchst, aber für Contests ist Simple perfekt!