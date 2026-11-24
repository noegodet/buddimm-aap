"""Étape link : relier avis -> classement -> autorisation pour chaque AAP.

1. jointure exacte sur le n° d'AAP (clé stable en ARA, ex. 2021-69-ACT) ;
2. à défaut, correspondance approchée : même type + même territoire + même nb de places ;
3. contrôles : bénéficiaire = rang 1 du classement ; date d'autorisation ≤ date limite + 6 mois (CASF R313-7).
Le score de fiabilité du lien additionne ces indices ; il n'est pas une probabilité.
"""
from datetime import date

import privacy


def plus_6_mois(iso: str) -> str:
    d = date.fromisoformat(iso)
    m = d.month + 6
    y, m = d.year + (m - 1) // 12, (m - 1) % 12 + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day).isoformat()
        except ValueError:
            continue


def v(rec, name):
    f = rec and rec["champs"].get(name)
    return f["valeur"] if f else None


def approx_match(a, b) -> bool:
    keys = ["type", "territoire", "places"]
    return all(v(a, k) is not None and v(a, k) == v(b, k) for k in keys)


def pick(records, kind, aap_id, ref):
    """Document de type `kind` pour cet AAP : par n° d'abord, sinon par ressemblance avec `ref`."""
    exact = [r for r in records if r["type_doc"] == kind and v(r, "aap_id") == aap_id]
    if exact:
        return exact[0], "n° AAP"
    if ref:
        approx = [r for r in records if r["type_doc"] == kind and not v(r, "aap_id") and approx_match(r, ref)]
        if approx:
            return approx[0], "type + territoire + places"
    return None, None


def build(aap_id, records, notes):
    avis, m_avis = pick(records, "avis", aap_id, None)
    clas, m_clas = pick(records, "classement", aap_id, avis)
    auto, m_auto = pick(records, "autorisation", aap_id, avis or clas)
    ref = avis or clas

    # autorisation seulement citée par un acte ultérieur (preuve indirecte)
    # garde-fous : même lauréat, même type d'établissement (un gestionnaire a souvent plusieurs
    # dispositifs : ACT, LHSS, EMSP…), et date postérieure à la commission
    cite = None
    if not auto and clas and v(clas, "classement"):
        laureat = v(clas, "classement")[0]["nom"]
        typ = (v(clas, "type") or "").lower()
        for r in records:
            for c in r.get("citations", []):
                if (c["beneficiaire"] and privacy.same_entity(laureat.split()[0], c["beneficiaire"]["nom"])
                        and typ and typ in c["texte_type"].lower()
                        and c["date"] >= (v(clas, "date_commission") or "")):
                    cite = c

    score, controles = 0.0, []
    score += {"n° AAP": 0.3, None: 0}.get(m_clas, 0.15) if clas else 0
    score += {"n° AAP": 0.3, None: 0}.get(m_auto, 0.15) if auto else (0.1 if cite else 0)

    laureat = v(clas, "classement")[0] if clas and v(clas, "classement") else None
    benef = v(auto, "beneficiaire") or (cite and cite["beneficiaire"])
    if laureat and benef:
        ok = privacy.same_entity(laureat["nom"], benef["nom"])
        controles.append({"regle": "bénéficiaire = rang 1 du classement", "statut": "ok" if ok else "écart"})
        score += 0.2 if ok else 0

    limite = v(avis, "date_limite_depot")
    d_auto = v(auto, "date_autorisation") or (cite and cite["date"])
    if limite and d_auto:
        borne = plus_6_mois(limite)
        ok = d_auto <= borne
        controles.append({"regle": "autorisation ≤ date limite + 6 mois (R313-7)", "borne": borne,
                          "date_autorisation": d_auto, "statut": "ok" if ok else "dépassé"})
        score += 0.2 if ok else 0
    else:
        controles.append({"regle": "autorisation ≤ date limite + 6 mois (R313-7)", "statut": "non vérifiable",
                          "raison": "date limite inconnue" if not limite else "date d'autorisation inconnue"})

    score = round(min(score, 1.0), 2)
    return {
        "aap_id": aap_id,
        "objet": v(ref, "objet") or v(auto, "objet"),
        "type": v(ref, "type") or v(auto, "type"),
        "territoire": v(ref, "territoire") or v(auto, "territoire"),
        "places": v(ref, "places") or v(auto, "places"),
        "avis": avis and {**avis, "jointure": m_avis},
        "classement": clas and {**clas, "jointure": m_clas},
        "autorisation": auto and {**auto, "jointure": m_auto},
        "autorisation_citee": cite,
        "controles": controles,
        "confiance": {"score": score, "niveau": "forte" if score >= 0.8 else "moyenne" if score >= 0.5 else "faible"},
        "non_trouve": {k: notes.get(k, ["Aucun document correspondant dans les sources parcourues."])
                       for k, doc in [("avis", avis), ("classement", clas), ("autorisation", auto)] if not doc},
    }
