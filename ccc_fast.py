#!/usr/bin/env python3
"""ccc_fast.py - Ein-Befehl-Pipeline fuer einen CCC-Level-Lauf.

Ziel: so wenig Wanduhr wie moeglich zwischen "Level ist da" und "Loesung ist
hochgeladen". Keine input()-Pausen, kein Copy-Paste in einen Chat, kein
manueller Upload.

    python3 ccc_fast.py prep 3          # Task holen + Level-Ordner aufbauen + BRIEF.md
    python3 ccc_fast.py check 3         # level3.py laufen lassen, Outputs vs. Referenz, Laufzeiten
    python3 ccc_fast.py submit 3        # Outputs hochladen (Score/Evaluation)
    python3 ccc_fast.py go 3 --watch    # prep -> warten bis level3.py da ist -> check -> submit

Dateien im Level-Ordner (levels/level-N/):
    Inputs/in_*            Eingaben
    Outputs/out_*          eigene Ausgaben
    .ref/ref_*             Sicherung der mitgelieferten Referenzausgaben (ueberlebt Laeufe)
    source/<Level N>.pdf   Original-PDF
    source/sandbox-level-N.html
    BRIEF.md               PDF-Text (pdftotext -layout) + Pfade + Referenz-Info: das liest der Agent
    levelN.py              Loesung (schreibt der Agent)
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = Path(os.environ.get("CCC_PROJECT") or SCRIPT_DIR).resolve()
sys.path.insert(0, str(SCRIPT_DIR))
import ccc_api  # noqa: E402  (gleicher Ordner: HTTP + Auth an einer Stelle)


# ------------------------------------------------------------------ Helpers

def log(msg: str, kind: str = "info") -> None:
    icon = {"info": "..", "ok": "OK", "warn": "!!", "err": "XX"}.get(kind, "..")
    print(f"[{icon}] {msg}", flush=True)


def level_dir(n: int) -> Path:
    return BASE / "levels" / f"level-{n}"


def index_of(path: Path) -> int | None:
    """out_level-3_1-small.txt -> 1 ; out_level-3_0-example.txt -> 0"""
    parts = path.stem.split("_")
    for p in parts[1:]:
        head = p.split("-")[0]
        if head.isdigit():
            return int(head)
    return None


def pdf_text(pdf: Path) -> str:
    """pdftotext -layout (schnell, mit Layout). Fallback: pdfplumber."""
    if shutil.which("pdftotext"):
        try:
            t0 = time.perf_counter()
            res = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                                 capture_output=True, text=True, timeout=60)
            if res.returncode == 0 and res.stdout.strip():
                log(f"PDF-Text per pdftotext ({time.perf_counter()-t0:.2f}s, {len(res.stdout)} Zeichen)", "ok")
                return res.stdout
        except (subprocess.SubprocessError, OSError) as e:
            log(f"pdftotext fehlgeschlagen: {e}", "warn")
    try:
        import pdfplumber
    except ImportError:
        log("weder pdftotext noch pdfplumber verfuegbar - kein PDF-Text", "warn")
        return ""
    t0 = time.perf_counter()
    with pdfplumber.open(pdf) as doc:
        text = "\n".join((p.extract_text() or "") for p in doc.pages)
    log(f"PDF-Text per pdfplumber ({time.perf_counter()-t0:.2f}s, {len(text)} Zeichen)", "ok")
    return text


def fetch_zip(n: int, from_zip: str | None, no_api: bool) -> Path | None:
    target = Path.home() / "Downloads" / f"level-{n}.zip"
    if from_zip:
        p = Path(from_zip).expanduser()
        if not p.exists():
            raise SystemExit(f"ZIP nicht gefunden: {p}")
        return p
    if no_api:
        return target if target.exists() else None
    try:
        token = ccc_api.get_token(required=False)
        if not token:
            raise ccc_api.ApiError(0, "kein Token")
        slug = ccc_api.contest_slug(None)
        base = ccc_api.game_base(None)
        t0 = time.perf_counter()
        status, headers, body = ccc_api._request(
            f"{base}/api/contestant/level/{n}/files", headers={"Authorization": token, "X-CCC-SLUG": slug})
        ctype = (headers.get("Content-Type") or "").lower()
        if "json" in ctype:
            url = (json.loads(body) or {}).get("url")
            if not url:
                raise SystemExit(f"Kein Download-Link: {body[:200]}")
            _, _, body = ccc_api._request(url)
        if body[:2] != b"PK":
            raise SystemExit(f"kein ZIP ({ctype}, {len(body)} Bytes)")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        log(f"ZIP via API ({len(body)} Bytes in {time.perf_counter()-t0:.2f}s): {target}", "ok")
        return target
    except (ccc_api.ApiError, SystemExit) as e:
        log(f"API-Download nicht moeglich ({e}) - nutze lokales ZIP", "warn")
    return target if target.exists() else None


# ------------------------------------------------------------------ prep

def cmd_prep(a) -> int:
    t_start = time.perf_counter()
    n = a.level
    d = level_dir(n)
    for sub in ("source", "Inputs", "Outputs", ".ref"):
        (d / sub).mkdir(parents=True, exist_ok=True)

    zip_path = fetch_zip(n, a.zip, a.no_api)
    if zip_path is None:
        raise SystemExit(f"Kein ZIP fuer Level {n} (weder API noch ~/Downloads/level-{n}.zip)")

    t0 = time.perf_counter()
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(d / "source")
    log(f"ZIP entpackt ({time.perf_counter()-t0:.2f}s)", "ok")

    src = d / "source"
    n_in = n_out = 0
    for f in sorted(src.rglob("in_*")):
        if f.is_file():
            shutil.copy2(f, d / "Inputs" / f.name)
            n_in += 1
    for f in sorted(src.rglob("out_*")):
        if f.is_file():
            target = d / "Outputs" / f.name
            (d / ".ref" / f"ref_{f.name}").write_bytes(f.read_bytes())   # Referenz immer sichern
            if not target.exists():                                      # eigene Ausgabe nie ueberschreiben
                shutil.copy2(f, target)
            n_out += 1
    for f in sorted(src.rglob("sandbox*.html")):
        shutil.copy2(f, d / "source" / f.name)
    log(f"{n_in} Inputs, {n_out} Referenz-Outputs (gesichert in .ref/)", "ok")

    pdfs = sorted(src.glob("*.pdf"))
    text = pdf_text(pdfs[0]) if pdfs else ""
    refs = sorted((d / ".ref").glob("ref_*"))

    brief = [f"# Level {n} - Brief", "",
             f"Arbeitsordner: {d}",
             f"Eingaben:      {d/'Inputs'}   (in_*)",
             f"Ausgaben:      {d/'Outputs'}  (out_*, Index aus Dateiname: out_level-{n}_<idx>-<name>.txt)",
             f"Loesung:       {d/f'level{n}.py'}",
             f"Referenzen:    {d/'.ref'}   (NICHT ueberschreiben - Kopie der Original-Outputs)", ""]
    if pdfs:
        brief += [f"Original-PDF: {pdfs[0]}", ""]
    sandboxes = sorted(src.rglob("sandbox*.html"))
    if sandboxes:
        brief += [f"Sandbox (echter Pruefcode): {sandboxes[0]}", ""]
    if refs:
        brief += ["Referenz-Outputs:"] + [f"  {r.name}  ({r.stat().st_size} B)" for r in refs] + [""]
    brief += ["", "## Aufgabenstellung (PDF-Text)", "", text or "[kein Text extrahiert]"]
    (d / "BRIEF.md").write_text("\n".join(brief), encoding="utf-8")
    log(f"BRIEF.md geschrieben ({len(text)} Zeichen Aufgabenstellung)", "ok")
    log(f"prep fertig in {time.perf_counter()-t_start:.2f}s -> {d}", "ok")
    print(f"\nNaechster Schritt: {d/f'level{n}.py'} schreiben, dann  python3 ccc_fast.py check {n}")
    return 0


# ------------------------------------------------------------------ check

def run_solution(n: int, python: str | None = None) -> tuple[bool, float]:
    d = level_dir(n)
    script = d / f"level{n}.py"
    if not script.exists():
        log(f"{script} fehlt", "err")
        return False, 0.0
    t0 = time.perf_counter()
    res = subprocess.run([python or sys.executable, script.name], cwd=d)
    dt = time.perf_counter() - t0
    if res.returncode != 0:
        log(f"level{n}.py exit {res.returncode} nach {dt:.2f}s", "err")
        return False, dt
    log(f"level{n}.py gelaufen in {dt:.2f}s ({Path(python or sys.executable).name})", "ok")
    return True, dt


def diff_references(n: int) -> list[tuple[str, bool, str]]:
    d = level_dir(n)
    rows = []
    for ref in sorted((d / ".ref").glob("ref_out_*")):
        name = ref.name[len("ref_"):]
        mine = d / "Outputs" / name
        if not mine.exists():
            rows.append((name, False, "fehlt"))
            continue
        a, b = ref.read_bytes(), mine.read_bytes()
        if a == b:
            rows.append((name, True, f"identisch ({len(b)} B)"))
        else:
            rows.append((name, False, f"{len(a)} B Referenz vs {len(b)} B eigen ({len(b)-len(a):+d})"))
    return rows


def cmd_check(a) -> int:
    n = a.level
    ok, dt = run_solution(n, a.python)
    d = level_dir(n)
    outs = sorted((d / "Outputs").glob("out_*"))
    ins = sorted((d / "Inputs").glob("in_*"))
    log(f"{len(outs)} Output-Dateien", "ok" if outs else "warn")
    if len(outs) != len(ins):
        log(f"{len(ins)} Inputs, aber {len(outs)} Outputs - fehlt eine Ausgabe?", "warn")
    for o in outs:
        print(f"     {o.name:38} {o.stat().st_size:>9} B  idx={index_of(o)}")
    rows = diff_references(n)
    if rows:
        print("\nReferenz-Vergleich:")
        clean = True
        for name, same, info in rows:
            print(f"  {'PASS' if same else 'FAIL'}  {name:34} {info}")
            clean &= same
        print(f"\nErgebnis: {'alle Referenzen byte-identisch' if clean else 'Abweichung(en)'}   (Laufzeit {dt:.2f}s)")
        return 0 if clean else 2
    log("keine Referenz gesichert (.ref/ leer) - Vergleich uebersprungen", "warn")
    return 0


# ------------------------------------------------------------------ submit

def _headers_or_empty() -> dict:
    """Auth-Header, falls vorhanden - fuer dry-run ohne Token."""
    try:
        return {"Authorization": ccc_api.get_token(), "X-CCC-SLUG": ccc_api.contest_slug(None)}
    except SystemExit:
        return {}


def level_file_ids(n: int, base: str, headers: dict) -> list:
    """inputFiles/fileIds des Levels aus contestant-info holen (Struktur defensiv)."""
    try:
        info = ccc_api._json(f"{base}/api/contestant/contestant-info", headers=headers) or {}
        levels = (info.get("levelsInfo") or {}).get("levels") or []
        if 0 <= n - 1 < len(levels):
            lvl = levels[n - 1] or {}
            return lvl.get("inputFiles") or lvl.get("files") or []
    except ccc_api.ApiError as e:
        log(f"contestant-info nicht abrufbar ({e}) - nutze Index aus Dateiname", "warn")
    return []


def match_id(output: Path, ids: list) -> str | None:
    """fileId fuer eine Output-Datei bestimmen: erst ueber die API-Liste, sonst Zahlenindex."""
    name = output.name
    for entry in ids:
        candidate = entry if isinstance(entry, str) else (
            entry.get("fileId") or entry.get("id") or entry.get("name") if isinstance(entry, dict) else None)
        if candidate is None:
            continue
        cand = str(candidate)
        if cand and (cand in name or name.replace("out_level-", "").startswith(cand)):
            return cand
    idx = index_of(output)
    return str(idx) if idx is not None else None


def upload_all(n: int, a) -> list[dict]:
    """Alle Outputs hochladen. Rueckgabe je Datei: {file, fileId, correct, eval, error}."""
    d = level_dir(n)
    outs = sorted((d / "Outputs").glob("out_*"))
    slug, base = ccc_api.contest_slug(None), ccc_api.game_base(None)
    headers = {"Authorization": ccc_api.get_token(), "X-CCC-SLUG": slug}
    ids = level_file_ids(n, base, headers)
    if ids:
        log(f"inputFiles laut API: {ids}", "info")

    results = []
    for o in outs:
        if a.only is not None and index_of(o) != a.only:
            continue
        if "example" in o.name and not a.with_example:
            continue
        fid = match_id(o, ids)
        if not fid:
            log(f"keine fileId fuer {o.name} - uebersprungen", "warn")
            continue
        for attempt in (1, 2):
            body, ctype = ccc_api._multipart("solution", o.name, o.read_bytes())
            try:
                t0 = time.perf_counter()
                res = ccc_api._json(f"{base}/api/contestant/submit-{n}-{fid}", method="POST", data=body,
                                    headers={**headers, "Content-Type": ctype}) or {}
                dt = time.perf_counter() - t0
            except ccc_api.ApiError as e:
                if e.status == 429 and attempt == 1:
                    cool = (e.payload or {}).get("cooldownSec") if isinstance(e.payload, dict) else 10
                    try:
                        wait_s = min(float(cool), 180)
                    except (TypeError, ValueError):
                        wait_s = 10
                    log(f"Rate-Limit bei idx {fid}: {wait_s:.0f}s warten, dann erneut", "warn")
                    time.sleep(wait_s)
                    continue
                log(f"idx {fid} fehlgeschlagen: {e}", "err")
                results.append({"file": o.name, "fileId": fid, "correct": None, "error": str(e)})
                break
            ev = res.get("evaluation") or {}
            results.append({"file": o.name, "fileId": fid, "correct": ev.get("correct"),
                            "eval": ev, "level": (((res.get("score") or {}).get("gameScore") or {}).get("level"))})
            log(f"idx {fid} hochgeladen in {dt:.2f}s -> correct={ev.get('correct')} "
                f"cooldown={res.get('cooldownSec')}s", "ok" if ev.get("correct") else "warn")
            if ev and not a.quiet:
                print(json.dumps(ev, indent=2)[:1200])
            lvl = (((res.get("score") or {}).get("gameScore") or {}).get("level"))
            if lvl:
                log(f"Level laut Server jetzt: {lvl}", "ok")
            break
    return results


def cmd_submit(a) -> int:
    n = a.level
    d = level_dir(n)
    outs = sorted((d / "Outputs").glob("out_*"))
    if a.dry_run:
        ids = []
        try:
            ids = level_file_ids(n, ccc_api.game_base(None), _headers_or_empty())
        except SystemExit:
            log("kein Game-Host aktiv - dry-run nutzt IDs aus den Dateinamen", "warn")
        for o in outs:
            if "example" in o.name and not a.with_example:
                continue
            print(f"  [dry-run] submit-{n}-{match_id(o, ids)}  <-  {o.name} ({o.stat().st_size} B)")
        if not ids:
            log("keine inputFiles von der API (dry-run ohne Token?) - IDs aus Dateinamen", "warn")
        return 0
    if not outs:
        raise SystemExit("nichts zu submitten")
    results = upload_all(n, a)
    if not results:
        raise SystemExit("nichts zu submitten")
    bad = [r for r in results if r.get("correct") is False or r.get("error")]
    ok = [r for r in results if r.get("correct")]
    log(f"{len(ok)}/{len(results)} Outputs korrekt bewertet", "ok" if not bad else "warn")
    return 0 if not bad else 1


# ------------------------------------------------------------------ go

def cmd_go(a) -> int:
    t0 = time.perf_counter()
    rc = cmd_prep(a)
    if rc != 0:
        return rc
    n = a.level
    script = level_dir(n) / f"level{n}.py"
    if a.watch:
        log(f"warte auf {script} (Abbruch mit Strg-C)", "info")
        while not script.exists():
            time.sleep(0.2)
        # stabile Groesse abwarten (Agent schreibt evtl. in Haeppchen)
        last = -1
        while True:
            size = script.stat().st_size
            if size == last and size > 0:
                break
            last = size
            time.sleep(0.2)
        log("Loesung erkannt", "ok")
    if getattr(a, "blitz", False):
        cmd_blitz(a)          # prueft selbst, faellt bei --auto auf den Agenten-Modus zurueck
    elif a.auto:
        rc_solve = cmd_solve(a)
        if rc_solve != 0:
            log("Hermes hat keine (neue) Loesung erzeugt - check laeuft trotzdem", "warn")
    rc = cmd_check(a)
    if rc != 0:
        log("check nicht sauber - kein Submit (mit --force-submit trotzdem hochladen)", "warn")
        if not a.force_submit:
            return rc
    if a.submit or a.force_submit:
        rc2 = cmd_submit(a)
        log(f"go komplett in {time.perf_counter()-t0:.2f}s", "ok")
        return max(rc, rc2)
    log(f"go bis check fertig in {time.perf_counter()-t0:.2f}s (ohne Submit)", "ok")
    return rc


# ------------------------------------------------------------------ blitz (schnellster Pfad)

BLITZ_PROMPT = """Du bist Senior-Wettbewerbsprogrammierer. Loese die folgende Aufgabe in EINEM Schritt.

## Aufgabe (Originaltext der Aufgabenstellung)
{task}

## Eingabedateien (vollstaendig, aus {inputs})
{inputs_dump}

## Referenzausgaben (byte-genau - Format-Wahrheit, aus {refs})
{refs_dump}

## Regeln
- Schreibe EIN Python-Programm, das alle Dateien `in_*` aus dem Ordner `Inputs` liest und
  fuer jede eine Datei `out_*` in `Outputs` schreibt (Name: `in_` -> `out_`, Rest identisch).
- Pfade immer ueber `Path(__file__).resolve().parent`, niemals ueber das Arbeitsverzeichnis.
- Ausgabeformat exakt wie die Referenz (Leerzeilen, trailing newline, Reihenfolge, Zahlformat).
- Keine externen Pakete, nur Standardbibliothek. Schnell: die grossen Eingaben muessen in
  wenigen Sekunden laufen (O(n log n) oder besser, keine quadratischen Schleifen).
- Keine Kommentare, keine Prints, ausser einer kurzen Zeile pro geschriebener Datei.

## Antwortformat
Antworte AUSSCHLIESSLICH mit dem vollstaendigen Python-Code. Kein Markdown, keine ```-Zaeune,
keine Erklaerung davor oder danach. Die erste Zeile muss Python-Code sein.
"""


def _inline(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n[... gekuerzt, {len(text)} Zeichen gesamt ...]"


def cmd_blitz(a) -> int:
    """Ein einziger Modellaufruf, ohne Tools/Skill: Code kommt als Antwort, lokal geprueft."""
    n = a.level
    d = level_dir(n)
    brief = d / "BRIEF.md"
    if not brief.exists():
        raise SystemExit(f"{brief} fehlt - erst 'prep {n}' laufen lassen")
    task_text = brief.read_text(encoding="utf-8")

    ins = []
    for f in sorted((d / "Inputs").glob("in_*")):
        ins.append(f"### {f.name}  ({f.stat().st_size} B)\n```\n{_inline(f.read_text(encoding='utf-8', errors='replace'), a.max_inline)}\n```")
    refs = []
    for f in sorted((d / ".ref").glob("ref_out_*")):
        refs.append(f"### {f.name[len('ref_'):]}  ({f.stat().st_size} B)\n```\n{_inline(f.read_text(encoding='utf-8', errors='replace'), 4000)}\n```")

    prompt = BLITZ_PROMPT.format(task=task_text, inputs=d / "Inputs",
                                 inputs_dump="\n\n".join(ins) or "(keine)",
                                 refs=d / ".ref", refs_dump="\n\n".join(refs) or "(keine)")

    model = a.model or "deepseek-v4-flash"
    cmd = ["hermes", "-z", prompt, "--yolo", "-m", model]
    if a.toolsets:
        cmd += ["-t", a.toolsets]
    log(f"Blitz: 1 Modellaufruf ({model}, Prompt {len(prompt)} Zeichen, keine Tools) ...", "info")
    t0 = time.perf_counter()
    try:
        res = subprocess.run(cmd, cwd=str(BASE), capture_output=True, text=True, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        log(f"Blitz-Timeout nach {a.timeout}s", "err")
        return 1
    t_model = time.perf_counter() - t0
    code = (res.stdout or "").strip()
    if res.returncode != 0 or not code:
        log(f"Blitz fehlgeschlagen ({t_model:.1f}s): {(res.stderr or '')[-300:]}", "err")
        return 1

    # Fences und Vorrede wegschneiden, falls das Modell sie doch liefert
    if "```" in code:
        parts = code.split("```")
        code = max(parts, key=len)
        code = code.split("\n", 1)[1] if code.lstrip().startswith(("python", "py")) else code
    start = code.find("from ")
    if start < 0:
        start = code.find("import ")
    if start > 0:
        code = code[start:]

    script = d / f"level{n}.py"
    script.write_text(code.rstrip() + "\n", encoding="utf-8")
    log(f"Code geschrieben ({len(code)} Zeichen) nach {t_model:.1f}s Modellzeit", "ok")

    rc = cmd_check(a)
    log(f"Blitz gesamt: {t_model:.1f}s Modell + Check", "ok" if rc == 0 else "warn")
    if rc != 0 and a.auto:
        log("Blitz traf die Referenz nicht - Fallback auf Agenten-Modus (solve)", "warn")
        return cmd_solve(a)
    return rc


# ------------------------------------------------------------------ solve (Hermes)

SOLVE_PROMPT = """Du loest Level {n} der Cloudflight CCC komplett selbststaendig. Keine Rueckfragen.

Arbeitsordner: {d}
Aufgabenstellung + Pfade: {brief}      <- zuerst vollstaendig lesen
Eingaben:            {inputs}
Ausgaben:            {outputs}
Referenzausgaben (byte-genau, NICHT aendern): {refs}
Sandbox/Pruefcode (falls vorhanden, hoechste Autoritaet fuer die Regeln): {sandbox}

Vorgehen:
1. Problem aus BRIEF.md verstehen; bei Unklarheiten die Sandbox-JS gegenlesen (dort steht der echte Pruefcode).
2. {script} schreiben. Rahmen: main() mit Path(__file__).resolve().parent, liest Inputs/in_*,
   schreibt Outputs/out_* (Dateiname in_ -> out_), solve(input_text) -> output_text.
3. Selbst verifizieren mit:  python3 {runner} check {n}
   Es muss "alle Referenzen byte-identisch" erscheinen. Bei Abweichung Ursache finden
   (Format, trailing newline, Reihenfolge, Leerzeilen) und fixen - nicht raten, sondern
   Referenzdatei byte-genau vergleichen.
4. Laufzeit beachten: die grossen Eingaben sollen in wenigen Sekunden durch sein.

Antworte am Ende in maximal 3 Zeilen: geschriebene Datei, Referenz-Diff-Ergebnis, Laufzeit der grossen Datei.
"""


def cmd_solve(a) -> int:
    n = a.level
    d = level_dir(n)
    brief = d / "BRIEF.md"
    if not brief.exists():
        raise SystemExit(f"{brief} fehlt - erst 'prep {n}' laufen lassen")
    script = d / f"level{n}.py"
    before = script.stat().st_mtime if script.exists() else 0

    sandboxes = sorted((d / "source").rglob("sandbox*.html"))
    prompt = SOLVE_PROMPT.format(
        n=n, d=d, brief=brief, inputs=d / "Inputs", outputs=d / "Outputs",
        refs=d / ".ref", sandbox=sandboxes[0] if sandboxes else "(keine Sandbox mitgeliefert)",
        script=script, runner=SCRIPT_DIR / "ccc_fast.py")

    cmd = ["hermes", "-z", prompt, "--yolo", "-t", "file,terminal",
           "-s", "coding-challenge-levels"]
    if a.model:
        cmd += ["-m", a.model]
    log(f"Hermes loest Level {n} (oneshot) ...", "info")
    t0 = time.perf_counter()
    try:
        res = subprocess.run(cmd, cwd=str(BASE), capture_output=True, text=True, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        log(f"Hermes-Timeout nach {a.timeout}s", "err")
        return 1
    dt = time.perf_counter() - t0
    out = (res.stdout or "").strip()
    if out:
        print(out)
    if res.returncode != 0:
        log(f"hermes exit {res.returncode} nach {dt:.0f}s: {(res.stderr or '')[-400:]}", "err")
    changed = script.exists() and script.stat().st_mtime != before
    log(f"Hermes fertig in {dt:.0f}s - level{n}.py {'geschrieben/aktualisiert' if changed else 'NICHT geaendert'}",
        "ok" if changed else "warn")
    return 0 if changed else 1


# ------------------------------------------------------------------ loop

def cmd_loop(a) -> int:
    """Alle Levels vollautomatisch: prep -> loesen -> pruefen -> abgeben -> naechstes.

    Kein Abbruch bei falscher Abgabe (es gibt keine Strafe): der Server bewertet,
    wir verbessern und geben erneut ab. Gesperrte Levels fuehren zurueck zum
    vorherigen Level, statt den ganzen Lauf zu beenden.
    """
    n = a.level
    tries = {i: 0 for i in range(a.level, a.max_level + 1)}
    while n <= a.max_level:
        if tries.get(n, 0) >= a.max_tries:
            log(f"Level {n}: {a.max_tries} Versuche erschoepft - weiter", "warn")
            n += 1
            continue
        tries[n] = tries.get(n, 0) + 1
        log(f"===== Level {n}  (Versuch {tries[n]}/{a.max_tries}) =====", "info")

        # 1) Task holen (Level ist evtl. noch gesperrt, weil das vorige nicht durch ist)
        ok_prep = False
        for attempt in range(1, a.retries + 1):
            try:
                if cmd_prep(a) == 0:
                    ok_prep = True
                    break
            except SystemExit as e:
                log(f"prep: {e}", "warn")
            log(f"Level {n} noch gesperrt (Versuch {attempt}/{a.retries})", "warn")
            time.sleep(a.retry_wait)
        if not ok_prep:
            if n > a.level:
                log(f"Level {n} bleibt gesperrt -> zurueck zu Level {n-1}", "warn")
                n -= 1
                continue
            log(f"Level {n} nicht abrufbar - Stop", "err")
            return 1

        # 2) Loesen: erster Versuch Blitz (1 Modellaufruf, schnell), danach Agenten-Modus (stark)
        if getattr(a, "blitz", False) and tries[n] == 1:
            cmd_blitz(a)
        else:
            if getattr(a, "model_solve", None):
                a.model = a.model_solve
            cmd_solve(a)

        # 3) Lokal pruefen
        local_ok = cmd_check(a) == 0
        log(f"lokaler Referenz-Diff: {'PASS' if local_ok else 'FAIL'}", "ok" if local_ok else "warn")

        # 4) Abgeben - auch bei lokalem FAIL, die Bewertung ist gratis
        if a.submit or a.force_submit:
            results = upload_all(n, a)
            verdicts = [r.get("correct") for r in results if r.get("correct") is not None]
            correct = any(verdicts) if verdicts else None
            log(f"Server-Bewertung Level {n}: {correct}", "ok" if correct else "warn")
            if correct is True:
                n += 1
                continue
            if correct is False:
                log("Server sagt falsch - naechster Versuch mit Agenten-Modus", "warn")
                continue
            if correct is None and local_ok:
                log("keine Server-Bewertung, aber Referenz byte-identisch - weiter", "ok")
                n += 1
                continue
        elif local_ok:
            n += 1
            continue
        else:
            continue
    log(f"Loop fertig (Level {a.level} bis {a.max_level} durchlaufen)", "ok")
    return 0


# ------------------------------------------------------------------ wait

def cmd_wait(a) -> int:
    """Auf den Contest-Start warten (bis gameBaseUrl gesetzt ist) und Level holen."""
    start = time.time()
    deadline = start + a.timeout
    last_status = None
    attempt = 0
    while time.time() < deadline:
        ccc_api._LIVE_CACHE = None          # pro Runde frisch fragen
        try:
            contests = ccc_api.list_contests()
        except ccc_api.ApiError as e:
            log(f"API nicht erreichbar ({e}) - neuer Versuch in {a.interval}s", "warn")
            time.sleep(a.interval)
            continue
        mine = next((c for c in contests if c.get("slug") == a.slug), None)
        running = [c for c in contests if c.get("status") in ("RUNNING", "STARTED", "LIVE")]
        cand = mine or (sorted(running, key=lambda c: c.get("startTime") or "")[-1] if running else None)
        if not cand and not a.slug:
            # noch niemand laeuft: den naechsten anstehenden Contest nehmen (frueheste startTime)
            upcoming = sorted((c for c in contests if c.get("status") == "OPEN_REGISTRATION"),
                              key=lambda c: c.get("startTime") or "")
            cand = upcoming[0] if upcoming else None
        if not cand:
            log("Contest nicht gefunden", "err")
            return 1
        status = f"{cand.get('status')} base={cand.get('gameBaseUrl') or '-'}"
        if status != last_status:
            left = ""
            try:
                st = datetime.datetime.fromisoformat(cand["startTime"].replace("Z", "+00:00"))
                mins = (st - datetime.datetime.now(datetime.timezone.utc)).total_seconds() / 60
                left = f"  Start in {mins:.0f} min" if mins > 0 else "  Start war"
            except (KeyError, ValueError):
                pass
            log(f"{cand['slug']}: {status}{left}", "info")
            last_status = status
        if cand.get("gameBaseUrl"):
            log(f"Game-Host steht: {cand['gameBaseUrl']}", "ok")
            cfg = ccc_api.load_config()
            cfg.update({"slug": cand["slug"], "game_base_url": cand["gameBaseUrl"],
                        "contest": cand.get("name")})
            ccc_api.save_config(cfg)
            if getattr(a, "loop", False):
                return cmd_loop(a)
            attempt += 1
            try:
                rc = cmd_prep(a)
            except SystemExit as e:      # ZIP-Endpunkt evtl. noch nicht offen
                log(f"prep noch nicht moeglich: {e}", "warn")
                rc = 1
            if rc == 0:
                log(f"Level {a.level} bereit nach {time.time()-start:.0f}s Wartezeit", "ok")
                return 0
            if attempt >= 30:
                return rc
            log("prep fehlgeschlagen - neuer Versuch", "warn")
        time.sleep(a.interval)
    log("Timeout: Contest hat nicht rechtzeitig gestartet", "err")
    return 1


# ------------------------------------------------------------------ CLI

def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="CCC-Ein-Befehl-Pipeline (prep/check/submit/go)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("level", type=int)
        sp.add_argument("--only", type=int, help="nur diesen Output-Index")
        sp.add_argument("--with-example", action="store_true", help="auch *_0-example hochladen")
        sp.add_argument("--dry-run", action="store_true", help="nur zeigen, was hochgeladen wuerde")
        sp.add_argument("--zip", help="lokales ZIP statt API")
        sp.add_argument("--no-api", action="store_true", help="API komplett aus (nur lokales ZIP)")
        sp.add_argument("--submit", action="store_true", help="nach dem Check hochladen")
        sp.add_argument("--force-submit", action="store_true", help="auch bei Abweichung hochladen")
        sp.add_argument("--watch", action="store_true", help="warten bis levelN.py existiert")
        sp.add_argument("--python", help="Interpreter fuer levelN.py (Default: dieser; z.B. ~/.venvs/ccc/bin/python fuer scipy)")
        sp.add_argument("--auto", action="store_true", help="Hermes (oneshot) die Loesung schreiben lassen")
        sp.add_argument("--model", help="Modell fuer den Hermes-Aufruf (Default: Hermes-Standard)")
        sp.add_argument("--timeout", type=int, default=1200, help="Timeout fuer den Hermes-Aufruf in s (Default 1200)")
        sp.add_argument("--max-level", type=int, default=6, help="hoechstes Level fuer 'loop' (Default 6)")
        sp.add_argument("--retries", type=int, default=12, help="prep-Wiederholungen wenn Level noch gesperrt (Default 12)")
        sp.add_argument("--retry-wait", type=int, default=10, help="Sekunden zwischen prep-Wiederholungen (Default 10)")
        sp.add_argument("--blitz", action="store_true", help="schneller Pfad: EIN Modellaufruf ohne Tools/Skill")
        sp.add_argument("--max-inline", type=int, default=20000, help="max. Zeichen pro Input im Blitz-Prompt (Default 20000)")
        sp.add_argument("--toolsets", default=None, help="Toolsets fuer den Blitz-Aufruf (Default: keine)")
        sp.add_argument("--max-tries", type=int, default=3, help="Loeseversuche pro Level (Default 3)")
        sp.add_argument("--model-solve", default=None, help="Modell fuer den Agenten-Fallback (z.B. deepseek-v4-pro)")
        sp.add_argument("--quiet", action="store_true", help="keine rohen Evaluation-JSONs ausgeben")

    for name, func in (("prep", cmd_prep), ("check", cmd_check), ("submit", cmd_submit),
                       ("solve", cmd_solve), ("blitz", cmd_blitz), ("go", cmd_go), ("loop", cmd_loop)):
        sp = sub.add_parser(name)
        common(sp)
        sp.set_defaults(func=func)

    s = sub.add_parser("wait", help="auf Contest-Start warten und Level automatisch holen")
    s.add_argument("level", nargs="?", type=int, default=1)
    s.add_argument("--slug", default=None, help="contestSlug (Default: laufender Contest)")
    s.add_argument("--interval", type=int, default=10, help="Sekunden zwischen Abfragen (Default 10)")
    s.add_argument("--timeout", type=int, default=7200, help="max. Wartezeit in Sekunden (Default 7200)")
    s.add_argument("--zip", default=None)
    s.add_argument("--no-api", action="store_true")
    s.add_argument("--loop", action="store_true", help="nach dem Start die ganze Level-Schleife fahren")
    s.add_argument("--submit", action="store_true", help="Loesungen hochladen (mit --loop)")
    s.add_argument("--model", default=None)
    s.add_argument("--max-level", type=int, default=6)
    s.add_argument("--retries", type=int, default=12)
    s.add_argument("--retry-wait", type=int, default=10)
    s.add_argument("--blitz", action="store_true", help="schnellen Pfad (1 Modellaufruf) benutzen")
    s.add_argument("--auto", action="store_true", help="Fallback auf Agenten-Modus wenn Blitz die Referenz verfehlt")
    s.add_argument("--max-inline", type=int, default=20000)
    s.add_argument("--toolsets", default=None)
    s.add_argument("--max-tries", type=int, default=3)
    s.add_argument("--model-solve", default=None)
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(func=cmd_wait, only=None, with_example=False, dry_run=False, python=None,
                  auto=False, force_submit=False, watch=False)

    a = p.parse_args()
    try:
        return a.func(a)
    except ccc_api.ApiError as e:
        log(f"{e}", "err")
        if e.status == 401:
            log("Token ungueltig/abgelaufen - neu holen (Browser-Snippet oder ccc_api.py login)", "warn")
        elif e.status == 503:
            log("Backend der Plattform nicht erreichbar - spaeter erneut", "warn")
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
