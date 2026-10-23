#!/usr/bin/env python3
"""
ccc_api.py - Direkter Client fuer die Cloudflight-CCC-Plattform (Tasks holen, Loesungen abgeben).

Kein Browser, keine Dependencies (nur stdlib). Zwei Auth-Wege:

  1) Token-Datei (Standard):  ~/.config/ccc/token  (oder $CCC_TOKEN)
     Token im Browser holen: auf https://codingcontest.org eingeloggt sein, DevTools-Konsole:
       fetch('/api/game-token',{method:'POST',headers:{'Content-Type':'application/json'},
         body:JSON.stringify({contestSlug:'<slug>'})}).then(r=>r.json()).then(j=>console.log(j.token))
     Der Slug kommt aus:  python3 ccc_api.py contests --running

  2) Playwright (optional):   python3 ccc_api.py login
     Braucht `pip install playwright` + `playwright install chromium` und Zugangsdaten in
     ~/.config/ccc/env  (CCC_EMAIL=..., CCC_PASSWORD=...).

Befehle:
  contests [--running]         alle Contests / den laufenden (slug, status, gameBaseUrl)
  resolve                      slug + gameBaseUrl des laufenden Contests
  state                        eigener Fortschritt (Level, passedFiles, Cooldowns)
  download N [--out DIR]       level-N.zip holen (Default: ~/Downloads fuer ccc_simple.py)
  inputs N [--out DIR]         Input-Dateien von Level N einzeln holen
  sandbox N [--out FILE]       echten Pruefcode (HTML) von Level N
  submit N -i IDX -f FILE      Loesung fuer Level N, Output-Index IDX hochladen
  leaderboard [--scope X]      Leaderboard
  login                        Token via Playwright holen und nach ~/.config/ccc/token schreiben

Plattform-API (reverse-engineered aus dem Game-Bundle):
  POST https://codingcontest.org/api/game-token  {contestSlug}   -> {token}   (braucht Login-Cookie)
  GET  <gameBaseUrl>/api/contestant/contestant-info
  GET  <gameBaseUrl>/api/contestant/level/{N}/files              -> ZIP
  GET  <gameBaseUrl>/api/contestant/level/{N}/input/{idx}
  GET  <gameBaseUrl>/api/contestant/level/{N}/sandbox            -> HTML
  POST <gameBaseUrl>/api/contestant/submit-{N}-{idx}             multipart Feld "solution"
  GET  <gameBaseUrl>/api/game-engine/leaderboard?scope=...
Header: Authorization: <game-token>, X-CCC-SLUG: <contest-slug>, Referer: https://codingcontest.org/
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

PLATFORM = "https://codingcontest.org"
CONFIG_DIR = Path.home() / ".config" / "ccc"
TOKEN_FILE = CONFIG_DIR / "token"
CONFIG_FILE = CONFIG_DIR / "config.json"
ENV_FILE = CONFIG_DIR / "env"
REFERER = PLATFORM + "/"
UA = "ccc-api/1.0 (+local script)"
_LIVE_CACHE: dict | None = None


class ApiError(Exception):
    def __init__(self, status: int, message: str, payload=None):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message
        self.payload = payload


# ---------------------------------------------------------------- HTTP-Basis

def _request(url: str, *, method: str = "GET", headers: dict | None = None,
             data: bytes | None = None, timeout: int = 20):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", UA)
    req.add_header("Referer", REFERER)
    req.add_header("Accept", "application/json, */*")
    for k, v in (headers or {}).items():
        if v:
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        body = e.read()
        ctype = e.headers.get("Content-Type", "")
        msg = body.decode("utf-8", "replace")[:400]
        payload = None
        if "json" in ctype:
            try:
                payload = json.loads(body)
                msg = payload.get("error") or payload.get("message") or msg
            except ValueError:
                pass
        raise ApiError(e.code, msg, payload) from None
    except urllib.error.URLError as e:
        raise ApiError(0, f"Netzwerkfehler: {e.reason}") from None
    except (TimeoutError, socket.timeout):
        raise ApiError(0, f"keine Antwort nach {timeout}s (0 Bytes) - API antwortet nicht; "
                          "entweder kurzzeitig ausgefallen oder gedrosselt. Spaeter erneut versuchen.") from None


def _json(url: str, **kw):
    status, headers, body = _request(url, **kw)
    if not body:
        return None
    try:
        return json.loads(body)
    except ValueError:
        raise ApiError(status, f"keine JSON-Antwort von {url}", body[:200].decode("utf-8", "replace")) from None


# ---------------------------------------------------------------- Konfiguration

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except ValueError:
            print(f"WARN: {CONFIG_FILE} ist kein gueltiges JSON - wird ignoriert", file=sys.stderr)
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    CONFIG_FILE.chmod(0o600)


def get_token(required: bool = True) -> str | None:
    token = os.environ.get("CCC_TOKEN")
    if not token and TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token and required:
        raise SystemExit(
            "Kein Game-Token gefunden.\n"
            f"  Lege {TOKEN_FILE} an (chmod 600) oder setze $CCC_TOKEN.\n"
            "  Token im Browser holen (eingeloggt auf codingcontest.org, DevTools-Konsole):\n"
            "    fetch('/api/game-token',{method:'POST',headers:{'Content-Type':'application/json'},\n"
            "      body:JSON.stringify({contestSlug:'<slug>'})}).then(r=>r.json()).then(j=>console.log(j.token))\n"
            "  Oder: python3 ccc_api.py login   (Playwright + ~/.config/ccc/env)"
        )
    return token


def current_live() -> dict:
    """Laufenden Contest (status RUNNING/STARTED/LIVE) liefern - gecacht pro Prozess.

    Wichtig fuer den Contest-Tag: die API setzt `status` und `gameBaseUrl` erst beim
    Start. Eine veraltete ~/.config/ccc/config.json (z.B. vom letzten Contest) darf
    diese Erkennung nicht ueberstimmen, sonst laeuft alles gegen den alten Game-Host.
    """
    global _LIVE_CACHE
    if _LIVE_CACHE is not None:
        return _LIVE_CACHE
    _LIVE_CACHE = {}
    try:
        contests = list_contests()
    except ApiError:
        return _LIVE_CACHE
    running = [c for c in contests if c.get("status") in ("RUNNING", "STARTED", "LIVE")]
    if running:
        chosen = sorted(running, key=lambda c: c.get("startTime") or "")[-1]
        if chosen.get("gameBaseUrl"):
            cfg = load_config()
            cfg.update({"slug": chosen["slug"], "game_base_url": chosen["gameBaseUrl"],
                        "contest": chosen.get("name")})
            save_config(cfg)
        _LIVE_CACHE = chosen
    return _LIVE_CACHE


def contest_slug(cli_slug: str | None) -> str:
    if cli_slug:
        return cli_slug
    slug = os.environ.get("CCC_SLUG")
    if slug:
        return slug
    live = current_live()
    if live.get("slug"):
        return live["slug"]
    cfg = load_config()
    return cfg.get("slug") or resolve_running()["slug"]


def game_base(cli_base: str | None) -> str:
    if cli_base:
        return cli_base.rstrip("/")
    base = os.environ.get("CCC_GAME_BASE")
    if base:
        return base.rstrip("/")
    live = current_live()
    if live.get("gameBaseUrl"):
        return live["gameBaseUrl"].rstrip("/")
    cfg = load_config()
    base = cfg.get("game_base_url")
    if not base and not cfg.get("slug"):
        base = resolve_running().get("gameBaseUrl") or ""
    if not base:
        raise SystemExit("gameBaseUrl ist (noch) leer - der Contest laeuft vermutlich noch nicht. "
                         "Nutze --base oder trage ihn in ~/.config/ccc/config.json ein.")
    return base.rstrip("/")


def _game_headers(slug: str) -> dict:
    return {"Authorization": get_token(), "X-CCC-SLUG": slug}


# ---------------------------------------------------------------- Plattform

def list_contests() -> list[dict]:
    data = _json(f"{PLATFORM}/api/contests?page=0&size=100")
    return data.get("content", [])


def resolve_running() -> dict:
    """Laufenden Contest (status RUNNING, sonst letzter mit gameBaseUrl) finden."""
    contests = list_contests()
    running = [c for c in contests if c.get("status") in ("RUNNING", "STARTED", "LIVE")]
    pool = running or [c for c in contests if c.get("gameBaseUrl")]
    if not pool:
        raise SystemExit("Kein Contest mit gameBaseUrl gefunden.")
    chosen = sorted(pool, key=lambda c: c.get("startTime") or "")[-1]
    cfg = load_config()
    cfg.update({"slug": chosen["slug"], "game_base_url": chosen.get("gameBaseUrl", ""),
                "contest": chosen.get("name")})
    save_config(cfg)
    return chosen


def game_token_via_cookies(contest_slug_value: str, cookie_header: str) -> str:
    """Game-Token mit einer bereits vorhandenen Login-Cookiesitzung holen.

    Wichtig: der Endpunkt ist POST und damit CSRF-geschuetzt. Spring/Angular
    erwarten den XSRF-Token doppelt: als Cookie `XSRF-TOKEN` UND als Header
    `X-XSRF-TOKEN` (Angular-Default). Ohne Header antwortet der Server 403
    "Forbidden" - noch bevor die Authentifizierung geprueft wird.
    """
    cookie_header = cookie_header.strip()
    body = json.dumps({"contestSlug": contest_slug_value}).encode()
    headers = {"Content-Type": "application/json", "Cookie": cookie_header}
    m = re.search(r"(?:^|;\s*)XSRF-TOKEN=([^;]+)", cookie_header)
    if m:
        headers["X-XSRF-TOKEN"] = urllib.parse.unquote(m.group(1))
    else:
        print("WARN: kein XSRF-TOKEN im Cookie-String - der POST wird vermutlich 403 liefern", file=sys.stderr)
    data = _json(f"{PLATFORM}/api/game-token", method="POST", data=body, headers=headers)
    token = (data or {}).get("token")
    if not token:
        raise SystemExit(f"Kein Token in der Antwort: {data}")
    return token


# ---------------------------------------------------------------- Contestant-API

def cmd_token(a) -> int:
    """Game-Token aus einem Login-Cookie holen (Alternative zum DevTools-Snippet)."""
    slug = contest_slug(a.slug)
    cookie = a.cookie or ""
    if a.cookie_file:
        cookie = Path(a.cookie_file).expanduser().read_text(encoding="utf-8")
    cookie = cookie.strip().removeprefix("Cookie:").strip()
    if not cookie:
        raise SystemExit("Cookie fehlt:  --cookie 'name=wert; name2=wert2'  oder  --cookie-file datei\n"
                         "Cookie im Browser holen: DevTools -> Network -> beliebige /api-Anfrage ->\n"
                         "Rechtsklick -> Copy as cURL, daraus den 'Cookie:'-Teil kopieren.")

    # Kein Vorab-Check auf /api/registrations/me: der Pfad existiert nicht (404 fuer
    # eingeloggte Nutzer); unauthentifiziert liefert Spring auf JEDEN /api-Pfad 401.
    # Der game-token-POST selbst ist die verlaessliche Probe - Status wird unten gemappt.
    try:
        token = game_token_via_cookies(slug, cookie)
    except ApiError as e:
        hint = {
            400: "Slug falsch geschrieben?",
            401: "Cookie tot oder unvollstaendig - im Browser neu einloggen und Cookie neu kopieren.",
            403: "CSRF: im Cookie-String fehlt XSRF-TOKEN (oder du bist fuer diesen Contest nicht registriert).",
        }.get(e.status, "")
        raise SystemExit(f"Token-Abruf fehlgeschlagen: {e}\n  {hint}") from None
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token, encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    print(f"Slug : {slug}")
    print(f"Token: {token[:18]}... ({len(token)} Zeichen)")
    print(f"gespeichert in {TOKEN_FILE}")
    return 0

def cmd_state(a) -> int:
    slug, base = contest_slug(a.slug), game_base(a.base)
    info = _json(f"{base}/api/contestant/contestant-info", headers=_game_headers(slug)) or {}
    if a.json:
        print(json.dumps(info, indent=2))
        return 0
    score = info.get("score") or {}
    game = score.get("gameScore") or {}
    levels = info.get("levelsInfo") or {}
    print(f"Contestant-ID : {info.get('id')}   dev={info.get('dev')}")
    print(f"Level erreicht: {game.get('level')} / {levels.get('count')}   Zeit: {game.get('timeMs')} ms")
    print(f"Score         : {game.get('score')}")
    for name, lvl in sorted((score.get("state") or {}).items()):
        passed = lvl.get("passedFiles") or {}
        ok = [k for k, v in passed.items() if v is not None]
        subs = lvl.get("submissions") or []
        scores = lvl.get("scoresPerFile") or {}
        print(f"  {name}: passed={sorted(ok)} submissions={len(subs)} scores={scores}")
    for cd in info.get("cooldowns") or []:
        print(f"  Cooldown Level {cd.get('level')} Datei {cd.get('fileId')}: {cd.get('remainingMs')} ms")
    return 0


def cmd_download(a) -> int:
    slug, base = contest_slug(a.slug), game_base(a.base)
    out_dir = Path(a.out).expanduser() if a.out else Path.home() / "Downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    status, headers, body = _request(f"{base}/api/contestant/level/{a.level}/files",
                                     headers=_game_headers(slug))
    ctype = (headers.get("Content-Type") or "").lower()
    if "json" in ctype:  # Server liefert gelegentlich nur eine URL
        url = (json.loads(body) or {}).get("url")
        if not url:
            raise SystemExit(f"Kein Download-Link in der Antwort: {body[:200]}")
        status, headers, body = _request(url)
        ctype = (headers.get("Content-Type") or "").lower()
    if "zip" not in ctype and not body[:2] == b"PK":
        raise SystemExit(f"Antwort ist kein ZIP (Content-Type: {ctype}, {len(body)} Bytes)")
    target = out_dir / f"level-{a.level}.zip"
    target.write_bytes(body)
    print(f"{target}  ({len(body)} Bytes)")
    print(f"Naechster Schritt: python3 ccc_simple.py {a.level}   (aus dem CCCTemplate-Ordner)")
    return 0


def cmd_inputs(a) -> int:
    slug, base = contest_slug(a.slug), game_base(a.base)
    out_dir = Path(a.out).expanduser() if a.out else Path("Inputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    got = 0
    for idx in range(1, 13):
        try:
            _, _, body = _request(f"{base}/api/contestant/level/{a.level}/input/{idx}",
                                  headers=_game_headers(slug))
        except ApiError as e:
            if e.status in (400, 401, 403, 404):
                break
            raise
        target = out_dir / f"in_level-{a.level}_{idx}.txt"
        target.write_bytes(body)
        got += 1
        print(f"{target}  ({len(body)} Bytes)")
    if not got:
        print("Keine Inputs geladen (Index 1 nicht vorhanden oder Level nicht freigeschaltet).")
        return 1
    return 0


def cmd_sandbox(a) -> int:
    slug, base = contest_slug(a.slug), game_base(a.base)
    _, _, body = _request(f"{base}/api/contestant/level/{a.level}/sandbox",
                          headers=_game_headers(slug))
    target = Path(a.out) if a.out else Path(f"sandbox-level-{a.level}.html")
    target.write_bytes(body)
    print(f"{target}  ({len(body)} Bytes)  -> enthaelt den echten Pruefcode")
    return 0


def _multipart(field: str, filename: str, blob: bytes) -> tuple[bytes, str]:
    boundary = "----cccapi" + uuid.uuid4().hex
    ctype = mimetypes.guess_type(filename)[0] or "text/plain"
    chunks = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {ctype}\r\n\r\n".encode(),
        blob,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def cmd_submit(a) -> int:
    slug, base = contest_slug(a.slug), game_base(a.base)
    path = Path(a.file).expanduser()
    if not path.exists():
        raise SystemExit(f"Datei nicht gefunden: {path}")
    blob = path.read_bytes()
    body, ctype = _multipart("solution", a.filename or path.name, blob)
    url = f"{base}/api/contestant/submit-{a.level}-{a.index}"
    try:
        result = _json(url, method="POST", data=body,
                       headers={**_game_headers(slug), "Content-Type": ctype})
    except ApiError as e:
        if e.status == 429:
            cool = (e.payload or {}).get("cooldownSec") if isinstance(e.payload, dict) else None
            raise SystemExit(f"Rate-Limit: noch {cool} s warten, dann erneut hochladen.") from None
        raise
    evaluation = (result or {}).get("evaluation") or {}
    print(f"Upload Level {a.level} / Index {a.index}: {path.name} ({len(blob)} Bytes)")
    print("Evaluation:")
    print(json.dumps(evaluation, indent=2) if a.json else _compact_evaluation(evaluation))
    cool = (result or {}).get("cooldownSec")
    if cool:
        print(f"Cooldown: {cool} s bis zum naechsten Upload dieses Outputs")
    score = (result or {}).get("score") or {}
    print(f"Level jetzt: {((score.get('gameScore') or {}).get('level'))}  Score: {((score.get('gameScore') or {}).get('score'))}")
    return 0


def _compact_evaluation(ev: dict) -> str:
    if not ev:
        return "  (leer)"
    lines = []
    for k, v in ev.items():
        if isinstance(v, list):
            lines.append(f"  {k}: {len(v)} Eintraege, ok={sum(1 for x in v if isinstance(x, dict) and x.get('correct'))}")
        else:
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def cmd_leaderboard(a) -> int:
    slug, base = contest_slug(a.slug), game_base(a.base)
    data = _json(f"{base}/api/game-engine/leaderboard?scope={a.scope}", headers=_game_headers(slug))
    print(json.dumps(data, indent=2)[:4000])
    return 0


def cmd_contests(a) -> int:
    contests = list_contests()
    rows = [c for c in contests if (not a.running or c.get("status") in ("RUNNING", "STARTED", "LIVE"))]
    print(f"{len(rows)} von {len(contests)} Contests")
    for c in rows:
        print(f"  {c.get('status','?'):18} {c.get('slug','?'):42} "
              f"{c.get('gameBaseUrl','') or '-'}  [{c.get('name')}]")
    return 0


def cmd_resolve(a) -> int:
    c = resolve_running()
    print(f"Contest : {c.get('name')} ({c.get('status')})")
    print(f"Slug    : {c.get('slug')}")
    print(f"Game-URL: {c.get('gameBaseUrl') or '(noch leer)'}")
    print(f"Levels  : {c.get('totalLevels')}")
    print(f"gespeichert in {CONFIG_FILE}")
    return 0


# ---------------------------------------------------------------- Playwright-Login

def cmd_login(a) -> int:
    """Token via Playwright holen (optionaler Weg, braucht einen Browser)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "Playwright ist nicht installiert. Entweder Token manuell holen (siehe Hilfe oben)\n"
            "oder: python3 -m venv ~/.venvs/ccc && ~/.venvs/ccc/bin/pip install playwright\n"
            "      ~/.venvs/ccc/bin/playwright install chromium"
        ) from None

    creds = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip().strip('"').strip("'")
    email = os.environ.get("CCC_EMAIL") or creds.get("CCC_EMAIL")
    password = os.environ.get("CCC_PASSWORD") or creds.get("CCC_PASSWORD")
    if not email or not password:
        raise SystemExit(f"Zugangsdaten fehlen. Lege {ENV_FILE} an (chmod 600):\n"
                         "  CCC_EMAIL=...\n  CCC_PASSWORD=...")

    slug = contest_slug(a.slug)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{PLATFORM}/login", wait_until="networkidle")
        page.fill('input[type="email"], input[name="username"], input[name="email"]', email)
        page.fill('input[type="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        token = page.evaluate(
            """async (slug) => {
                 const r = await fetch('/api/game-token', {method:'POST',
                   headers:{'Content-Type':'application/json'},
                   body: JSON.stringify({contestSlug: slug})});
                 if (!r.ok) return {error: r.status + ' ' + (await r.text()).slice(0,200)};
                 return await r.json();
               }""", slug)
        browser.close()
    if not isinstance(token, dict) or not token.get("token"):
        raise SystemExit(f"Token-Abruf fehlgeschlagen: {token}")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token["token"], encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    print(f"Token gespeichert: {TOKEN_FILE}")
    return 0


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CCC-Plattform-Client (Tasks holen, Loesungen abgeben)",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--slug", help="contestSlug (Default: ~/.config/ccc/config.json / laufender Contest)")
    p.add_argument("--base", help="gameBaseUrl (Default: automatisch)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("contests", help="Contests auflisten")
    s.add_argument("--running", action="store_true", help="nur laufende")
    s.set_defaults(func=cmd_contests)

    s = sub.add_parser("resolve", help="laufenden Contest ermitteln und merken")
    s.set_defaults(func=cmd_resolve)

    s = sub.add_parser("state", help="eigenen Fortschritt zeigen")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_state)

    s = sub.add_parser("download", help="level-N.zip holen")
    s.add_argument("level", type=int)
    s.add_argument("--out", help="Zielordner (Default ~/Downloads)")
    s.set_defaults(func=cmd_download)

    s = sub.add_parser("inputs", help="Inputs eines Levels einzeln holen")
    s.add_argument("level", type=int)
    s.add_argument("--out", help="Zielordner (Default ./Inputs)")
    s.set_defaults(func=cmd_inputs)

    s = sub.add_parser("sandbox", help="Pruefcode-HTML eines Levels holen")
    s.add_argument("level", type=int)
    s.add_argument("--out", help="Zieldatei")
    s.set_defaults(func=cmd_sandbox)

    s = sub.add_parser("submit", help="Loesung hochladen")
    s.add_argument("level", type=int)
    s.add_argument("-i", "--index", required=True, help="Output-Index (z.B. 1 fuer _1-small)")
    s.add_argument("-f", "--file", required=True, help="Loesungsdatei")
    s.add_argument("--filename", help="Dateiname im Upload (Default: Name der Datei)")
    s.add_argument("--json", action="store_true", help="Evaluation roh ausgeben")
    s.set_defaults(func=cmd_submit)

    s = sub.add_parser("leaderboard", help="Leaderboard abrufen")
    s.add_argument("--scope", default="GLOBAL")
    s.set_defaults(func=cmd_leaderboard)

    s = sub.add_parser("login", help="Token via Playwright holen")
    s.set_defaults(func=cmd_login)

    s = sub.add_parser("token", help="Game-Token aus Browser-Cookie holen (ohne Playwright)")
    s.add_argument("--cookie", help="Cookie-String (aus DevTools, 'Copy as cURL')")
    s.add_argument("--cookie-file", help="Datei mit dem Cookie-String")
    s.set_defaults(func=cmd_token)
    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except ApiError as e:
        print(f"FEHLER {e}", file=sys.stderr)
        if e.status == 401:
            print("  -> Token ungueltig/abgelaufen: neu holen (Browser-Snippet oder `ccc_api.py login`).",
                  file=sys.stderr)
        elif e.status == 403:
            print("  -> Zugriff verweigert (Level nicht freigeschaltet oder Contest nicht aktiv).", file=sys.stderr)
        elif e.status == 503:
            print("  -> Backend der Plattform ist gerade nicht erreichbar ('no healthy upstream'). "
                  "Spaeter erneut versuchen.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
