"""Étape criteria : grille de notation de l'avis -> grille commune.

Les avis ARA suivent un gabarit : blocs « I - APPRECIATION … (50%) 150 points »,
puis des critères suivis d'un coefficient (cotation 0 à 5, donc points = coef × 5).
1. règles (toujours) : on lit les coefficients ligne à ligne ;
2. LLM local (optionnel, si Ollama répond) : même tâche en JSON imposé, pour comparer.
Puis normalisation dans une grille commune, avec une catégorie « implantation / immobilier ».
"""
import json
import re
import urllib.request

import privacy
from fetch import CACHE, key

COMMON = {  # l'ordre compte : « budget … en investissement » est du financement, pas de l'immobilier
    "cout_financement": r"budget|enveloppe|efficience|financ|co[ûu]t|[ée]conomi",
    "implantation_immobilier": r"localisation|locaux|accessibilit|implantation|immobili|foncier|b[âa]ti",
    "delai_mise_en_oeuvre": r"calendrier du projet|d[ée]lai|r[ée]alisation",
    "partenariats": r"partenai|r[ée]seau|co-construit|collaboration",
    "experience_porteur": r"capacit[ée] [àa] faire|exp[ée]rience|connaissance du territoire",
}


def categorize(label: str, bloc: str) -> str:
    if bloc == "IV":  # évaluation : rattaché à la qualité du projet
        return "qualite_projet"
    for cat, rx in COMMON.items():
        if re.search(rx, label, re.I):
            return cat
    return "qualite_projet"


def grid_pages(pages: list[str], start: int):
    """Pages de la grille : de « MODALITE DE NOTATION » (ou « Coefficient ») jusqu'à « TOTAL … /300 »."""
    i0 = next((i for i, t in enumerate(pages) if re.search(r"MODALIT[ÉE] DE NOTATION|Coeffi\s*cient", t)), None)
    if i0 is None:
        return None
    i1 = next((i for i in range(i0, len(pages)) if re.search(r"TOTAL\s+\d*\s*/\s*\d+", pages[i])), len(pages) - 1)
    return i0, i1


def rules(pages: list[str], start: int, url: str) -> list[dict]:
    g = grid_pages(pages, start)
    if not g:
        return []
    out, bloc, buf = [], None, []
    for pi in range(g[0], g[1] + 1):
        lines = [l.strip() for l in pages[pi].splitlines() if l.strip()]
        # en-tête : n° de page seul ; pied RAA : « 84_ARS_… » + ligne de titre de l'acte
        while lines and re.fullmatch(r"\d{1,3}", lines[0]):
            lines.pop(0)
        if any(l.startswith("84_ARS") for l in lines):
            lines = lines[:next(i for i, l in enumerate(lines) if l.startswith("84_ARS"))]
        for line in lines:
            mb = re.match(r"^(I{1,3}|IV|V)\s*-", line)
            if mb:
                bloc, buf = mb.group(1), []
                continue
            if re.search(r"\(\d+\s*%\)|^\d+ points|^APPRECIATION|^DE (LA|L')|^[A-ZÉ' ]{4,}$", line):
                buf = []  # suite du titre de bloc en majuscules
                continue
            # coefficient = petit entier isolé, suivi de 2 espaces ou fin de ligne (≠ « loi du 2 janvier »)
            m = re.match(r"^(.*?)(?:^|\s)(\d{1,2})(?:\s{2,}(.*)|\s*)$", line)
            if m and bloc and 0 < int(m.group(2)) <= 20 and (m.group(1) or buf) and ":" not in m.group(1):
                cand = [l for l in buf + [m.group(1)] if l]
                # le libellé commence à la dernière ligne à majuscule (avant : fin de la description précédente)
                j = max([i for i, l in enumerate(cand) if re.match(r"^[A-ZÉÈÀ]", l)] or [0])
                label = re.sub(r"\s+", " ", " ".join(cand[j:])).strip(" :")
                label = re.sub(r"(\w)- (\w)", r"\1\2", label.replace("accompagne ments", "accompagnements"))
                if label:
                    out.append({"bloc": bloc, "critere": label, "coef": int(m.group(2)),
                                "points_max": int(m.group(2)) * 5, "url": url, "page": start + pi})
                buf = []
                continue
            if line.endswith(":") or ":" in line:
                buf = []
            else:
                buf.append(line)
    return out


def summarize(items: list[dict]) -> dict:
    total = sum(i["points_max"] for i in items) or 1
    agg = {c: 0 for c in ["qualite_projet", *COMMON]}
    for i in items:
        i["categorie"] = categorize(i["critere"], i["bloc"])
        agg[i["categorie"]] += i["points_max"]
    return {"total_points": total, "par_categorie": {c: {"points": p, "pct": round(100 * p / total, 1)} for c, p in agg.items()}}


# ---------------------------------------------------------------- LLM local (optionnel)
OLLAMA = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"
SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "bloc": {"type": "string"}, "critere": {"type": "string"}, "coef": {"type": "integer"}},
    "required": ["bloc", "critere", "coef"]}}
PROMPT = ("Voici la grille de notation d'un avis d'appel à projets médico-social. "
          "Liste chaque critère avec son bloc (I, II, III ou IV) et son coefficient pondérateur (entier). "
          "N'invente rien : uniquement ce qui figure dans le texte. Réponds en JSON.\n\n")


def llm(pages: list[str], start: int, url: str):
    """Renvoie la liste des critères selon le LLM, ou None si Ollama n'est pas disponible."""
    g = grid_pages(pages, start)
    if not g:
        return None
    text = "\n".join(pages[g[0]:g[1] + 1])
    text = "\n".join(l for l in text.splitlines() if not privacy.PERSON_HINTS.search(l))  # rien de personnel au modèle
    cache = CACHE / f"llm_{key(url + MODEL + str(start))}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    body = json.dumps({"model": MODEL, "prompt": PROMPT + text, "format": SCHEMA, "stream": False,
                       "options": {"temperature": 0, "num_ctx": 8192}}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"}), timeout=600) as r:
            items = json.loads(json.loads(r.read())["response"])
    except Exception:
        return None
    items = [{**i, "points_max": int(i["coef"]) * 5} for i in items if isinstance(i, dict) and str(i.get("coef", "")).isdigit()]
    cache.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return items


def extract(pages: list[str], start: int, url: str, use_llm: bool = True) -> dict | None:
    items = rules(pages, start, url)
    if not items:
        return None
    res = {"methode": "regles", "criteres": items, **summarize(items)}
    # auto-contrôle : la grille imprime « TOTAL 60 /300 » -> somme des coefficients attendue
    g = grid_pages(pages, start)
    m = re.search(r"TOTAL\s+(\d+)\s*/\s*(\d+)", pages[g[1]])
    if m:
        lu = sum(i["coef"] for i in items)
        res["controle_total"] = {"coef_annonce": int(m.group(1)), "coef_lus": lu,
                                 "points_annonces": int(m.group(2)), "statut": "ok" if lu == int(m.group(1)) else "écart"}
    if use_llm:
        li = llm(pages, start, url)
        if li is not None:
            res["llm"] = {"modele": MODEL, "criteres": li, **summarize(li),
                          "accord_coef_total": sum(i["coef"] for i in li) == sum(i["coef"] for i in items)}
    return res
