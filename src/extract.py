"""Étape extract : texte page par page -> actes -> champs {valeur, url, page}.

Un RAA est un gros PDF dont le sommaire donne, pour chaque acte, sa page de début
et son nombre de pages : on s'en sert pour découper. Un PDF ARS isolé = un seul acte.
Aucun texte libre n'est stocké : seulement des champs typés et des personnes morales.
"""
import json
import re
from datetime import date
from pathlib import Path

from pypdf import PdfReader

import privacy

MONTHS = {m: i for i, m in enumerate(
    "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split(), 1)}
DATE_RX = r"(\d{1,2})(?:er)?\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+(20\d\d)"
AAP_ID_RX = re.compile(r"\b(20\d\d-\d{1,2}-(?:ACT|EMSP|LHSS|LAM|CSAPA|CAARUD|SSIAD|EHPAD|IME|MAS|FAM|SESSAD|[A-Z]{2,6}))\b")


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t.replace("’", "'")).strip()


def to_iso(d, mois, an) -> str:
    mois = mois.lower().replace("fevrier", "février").replace("aout", "août").replace("decembre", "décembre")
    return date(int(an), MONTHS[mois], int(d)).isoformat()


def find_date(rx: str, text: str):
    # jusqu'à 4 mots entre le libellé et la date (« : au plus tard le 3 février 2022 », « : Vendredi 2 avril 2021 »)
    m = re.search(r"(?:" + rx + r")\s*:?\s*(?:[\w']+\s+){0,4}?" + DATE_RX, text, re.I)
    return to_iso(*m.groups()[-3:]) if m else None


# ---------------------------------------------------------------- PDF -> pages
def pdf_pages(path: Path) -> list[str]:
    """Texte de chaque page, mis en cache à côté du PDF (cache/<clé>.pages.json)."""
    cached = path.with_suffix(".pages.json")
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    pages = [(p.extract_text() or "") for p in PdfReader(path).pages]
    cached.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


def split_acts(pages: list[str]) -> list[dict]:
    """Découpe un RAA selon son sommaire ; sinon le document entier est un acte."""
    head = "\n".join(pages[:6])
    if "Sommaire" in head:
        rx = re.compile(r"(84-\d{4}-\d\d-\d\d-\d{3,5})\s*-\s*(.+?)\((\d+)\s*pages?\)\s*Page\s*(\d+)", re.S)
        acts = [{"titre": norm(t), "debut": int(p), "nb": int(n)} for _, t, n, p in rx.findall(head)]
        if acts:
            return acts
    return [{"titre": norm(pages[0][:300]) if pages else "", "debut": 1, "nb": len(pages)}]


# ---------------------------------------------------------------- classification
def classify(title: str, text: str) -> str:
    t, start = title.lower(), text[:2500].lower()
    if "le classement est le suivant" in text.lower():
        return "classement"
    if re.search(r"portant autorisation|autorisant la cr[ée]ation", t + " " + start):
        return "autorisation"
    if re.search(r"avis d.appel [àa] projets?|cahier des charges", t + " " + start):
        return "avis"
    return "autre"


def field(value, url, page):
    return {"valeur": value, "url": url, "page": page} if value not in (None, "", []) else None


def first_page(pages, start, rx):
    """Numéro de page (1-based dans le PDF) où `rx` apparaît pour la première fois."""
    for i, t in enumerate(pages):
        if re.search(rx, norm(t), re.I):
            return start + i
    return None


def search(pages, start, rx, group=1, flags=re.I):
    for i, t in enumerate(pages):
        m = re.search(rx, norm(t), flags)
        if m:
            return m, start + i
    return None, None


# ---------------------------------------------------------------- champs communs
def common_fields(pages, start, url):
    out = {}
    ids = [m for t in pages for m in AAP_ID_RX.findall(t)]
    if ids:
        best = max(set(ids), key=ids.count)
        out["aap_id"] = field(best, url, first_page(pages, start, re.escape(best)))
    m, p = search(pages, start, r"cr[ée]ation (?:d'une? |de |d')(.{10,160}?)(?:\.| - |Les projets| Vu | Avis)")
    if m:
        out["objet"] = field(m.group(1).strip(" ,;"), url, p)
    m, p = search(pages, start, r"(\d+)\s+(?:places?|appartements?|lits?)\b")
    if m:
        out["places"] = field(int(m.group(1)), url, p)
    m, p = search(pages, start, r"(M[ée]tropole de Lyon|d[ée]partement (?:du|de la|de l'|de|des) ?[A-ZÉ][\w\-ôéèû]+)")
    if m:
        out["territoire"] = field(re.sub(r"^d[ée]partement (?:du |de la |de l'|des |de )?", "", m.group(1), flags=re.I).strip(), url, p)
    m, p = search(pages, start, r"[ée]quipe mobile sant[ée] pr[ée]carit[ée]|appartements? de coordination th[ée]rapeutique|lits? halte soins sant[ée]")
    if m:
        out["type"] = field(m.group(0).lower(), url, p)
    return out


# ---------------------------------------------------------------- par type d'acte
def avis_fields(pages, start, url):
    out = {}
    for name, rx in [
        ("date_publication", r"Date de publication"),
        ("date_limite_depot", r"Date limite de (?:r[ée]ception|transmission) des dossiers(?: de candidature)?|date limite de d[ée]p[ôo]t des (?:dossiers|candidatures)"),
    ]:
        for i, t in enumerate(pages):
            d = find_date(rx, norm(t))
            if d:
                out[name] = field(d, url, start + i)
                break
    return out


def classement_fields(pages, start, url):
    out = {}
    text = norm("\n".join(pages))
    m, p = search(pages, start, r"(\w+) projets ont [ée]t[ée] re[çc]us")
    if m:
        out["nb_projets_recus"] = field(m.group(1).lower(), url, p)
    for i, t in enumerate(pages):
        d = find_date(r"commission d'information et de s[ée]lection[^.]{0,80}?du", norm(t))
        if d:
            out["date_commission"] = field(d, url, start + i)
            break
    for i, t in enumerate(pages):
        d = find_date(r"Fait [àa] Lyon, le", norm(t))
        if d:
            out["date_avis_classement"] = field(d, url, start + i)
            break
    # bloc entre « Le classement est le suivant » et « Conformément »
    blk = re.search(r"Le classement est le suivant\s*:?(.*?)Conform[ée]ment", text, re.S | re.I)
    if blk:
        p = first_page(pages, start, r"Le classement est le suivant")
        ranking = []
        for rank, rest in re.findall(r"(\d+)\s*-\s*(.*?)(?=\s\d+\s*-\s|$)", blk.group(1)):
            for ent in privacy.entities(rest):
                ranking.append({"rang": int(rank), **ent, "ex_aequo": "aequo" in rest.lower()})
        out["classement"] = field(ranking, url, p)
    return out


def autorisation_fields(pages, start, url):
    out = {}
    m, p = search(pages, start, r"(?:Arr[êe]t[ée]|D[ée]cision) n°\s*(\d{4}-\d{2}-\s?\d{4})")
    if m:
        out["numero_acte"] = field(m.group(1).replace(" ", ""), url, p)
    for i, t in enumerate(pages):
        d = find_date(r"Fait [àa] Lyon,? le", norm(t))
        if d:
            out["date_autorisation"] = field(d, url, start + i)
            break
    # tous les « N places » de la 1re page, sans les additionner (« 16 places … et 24 places » ≠ « 20 places dont 10 »)
    nums = list(dict.fromkeys(int(n) for n in re.findall(r"(\d+)\s+places", norm(pages[0]) if pages else "")))
    if nums:
        out["places_mentionnees"] = field(nums, url, start)
    m, p = search(pages, start, r"(?:g[ée]r[ée]e? par|retenu le projet pr[ée]sent[ée] par|accord[ée]e? [àa]) l'\s*(.{0,90})")
    if m:
        ents = privacy.entities(m.group(0)) or privacy.entities_until_address(m.group(0))
        if ents:
            out["beneficiaire"] = field(ents[0], url, p)
    for i, t in enumerate(pages):
        d = find_date(r"Vu l'avis d'appel [àa] projets?.{0,400}?publi[ée] au recueil des actes administratifs.{0,120}?le", norm(t))
        if d:
            out["avis_publie_le"] = field(d, url, start + i)
            break
    return out


def citations(pages, start, url):
    """Autorisations citées par un acte ultérieur (« Vu l'arrêté n° X du JJ mois AAAA autorisant… »)."""
    out = []
    for i, t in enumerate(pages):
        for m in re.finditer(r"n°\s*(\d{4}-\d{2}-\s?\d{4}) du " + DATE_RX + r"\s*autorisant(.{0,300}?)(?:;|Vu|Consid)", norm(t), re.I):
            ents = privacy.entities(m.group(5)) or privacy.entities_unquoted(m.group(5))
            out.append({
                "numero_acte": m.group(1).replace(" ", ""), "date": to_iso(*m.group(2, 3, 4)),
                "texte_type": re.sub(r"g[ée]r[ée]e? par.*", "", m.group(5)).strip()[:160],
                "beneficiaire": ents[0] if ents else None, "url": url, "page": start + i,
            })
    return out


def extract_document(url: str, path: Path) -> list[dict]:
    pages = pdf_pages(path)
    records = []
    for act in split_acts(pages):
        a, b = act["debut"], act["debut"] + act["nb"] - 1
        sub = pages[a - 1:b]
        kind = classify(act["titre"], "\n".join(sub))
        rec = {"type_doc": kind, "url": url, "pages": [a, b], "nb_pages_pdf": len(pages),
               "texte_vide": sum(1 for t in sub if len(t.strip()) < 50)}
        cites = citations(sub, a, url)
        if kind == "autre" and not cites:
            continue
        rec["champs"] = common_fields(sub, a, url)
        rec["champs"].update({"avis": avis_fields, "classement": classement_fields,
                              "autorisation": autorisation_fields}.get(kind, lambda *x: {})(sub, a, url))
        rec["champs"] = {k: v for k, v in rec["champs"].items() if v}
        rec["citations"] = cites
        records.append(rec)
    return records
