"""Étape fetch : téléchargement poli avec cache local.

- un fichier par URL : cache/<sha1(url)[:16]>.pdf  -> jamais retéléchargé
- au moins 2 s entre deux requêtes réseau
- User-Agent identifiable
- chaque URL est journalisée dans cache/fetch_log.tsv
"""
import hashlib
import time
import urllib.request
from datetime import datetime
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "cache"
UA = "BuddimmAAP-etude-de-cas/0.1 (projet etudiant, cas metier Buddimm; usage non commercial)"
DELAY_S = 2.0
_last_request = 0.0


def key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _log(url: str, status: str, size: int) -> None:
    with open(CACHE / "fetch_log.tsv", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{status}\t{size}\t{url}\n")


def fetch(url: str) -> Path:
    """Renvoie le chemin local du PDF, en le téléchargeant seulement s'il n'est pas en cache."""
    global _last_request
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{key(url)}.pdf"
    if path.exists() and path.stat().st_size > 0:
        _log(url, "cache", path.stat().st_size)
        return path
    wait = DELAY_S - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            status = str(r.status)
    finally:
        _last_request = time.monotonic()
    if not data.startswith(b"%PDF"):
        _log(url, f"{status}-pas-un-pdf", len(data))
        raise ValueError(f"Réponse non PDF pour {url}")
    path.write_bytes(data)
    _log(url, status, len(data))
    return path
