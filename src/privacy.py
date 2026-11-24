"""Garde-fou « personnes morales uniquement ».

Deux niveaux :
1. liste blanche : on ne stocke une entité que si elle porte une forme juridique
   (association, fondation, GCSMS…). Aucun texte libre n'est conservé.
2. filet de sécurité : toute valeur texte passe par `check()` avant export ;
   l'export échoue si un motif typique d'une personne physique subsiste
   (« Signé », civilités, fonctions de signataire).
"""
import re

LEGAL_FORMS = (
    r"association|fondation|gcsms|gcs|groupement|mutuelle|mutualit[ée]|soci[ée]t[ée]|sas|sarl|scic|"
    r"centre hospitalier|ccas|cias|union|f[ée]d[ée]ration|congr[ée]gation|[ée]tablissement public"
)
# forme juridique + nom entre guillemets droits, typographiques ou chevrons
ENTITY_RE = re.compile(
    rf"\b({LEGAL_FORMS})\s*[\"«“]\s*([^\"»”]{{2,80}}?)\s*[\"»”]", re.I
)

PERSON_HINTS = re.compile(
    r"\b(sign[ée]e?|M\.|Mme|Mlle|Monsieur|Madame|Dr|Docteur|Pr[ée]sidente?|"
    r"Directeur|Directrice|D[ée]l[ée]gu[ée]e?)\b"
)


def entities(text: str) -> list[dict]:
    """Extrait les personnes morales citées sous la forme `Association "NOM"`."""
    out = []
    for form, name in ENTITY_RE.findall(text):
        name = re.sub(r"\s+", " ", name).strip()
        if PERSON_HINTS.search(name):
            continue  # par prudence : on jette plutôt que de risquer un nom
        out.append({"forme": form.lower(), "nom": name.upper()})
    return out


UNQUOTED_RE = re.compile(rf"\b({LEGAL_FORMS})\s+((?:[A-ZÉÈ][\w'\-]*\s?){{1,5}})")


def entities_unquoted(text: str) -> list[dict]:
    """Variante plus fragile : `l'association ANEF Cantal` (mots à majuscule, sans guillemets)."""
    out = []
    for form, name in UNQUOTED_RE.findall(text):
        name = name.strip()
        if name and not PERSON_HINTS.search(name):
            out.append({"forme": form.lower(), "nom": name.upper()})
    return out


def entities_until_address(text: str) -> list[dict]:
    """Dernier recours : `l'Association lyonnaise … (A.L.Y.N.E.A.) sise 53, rue…` -> nom jusqu'à « sise »/virgule."""
    m = re.search(rf"\b({LEGAL_FORMS})\s+(.{{3,120}}?)\s*(?:,|;|\bsise\b|\bdont\b|$)", text, re.I)
    if m and not PERSON_HINTS.search(m.group(2)):
        return [{"forme": m.group(1).lower(), "nom": m.group(2).strip().upper()}]
    return []


def same_entity(a: str, b: str) -> bool:
    """`ALYNEA` ~ `LYONNAISE … (A.L.Y.N.E.A.)` : on compare les lettres seules, par inclusion."""
    sa, sb = re.sub(r"[^A-Z]", "", a.upper()), re.sub(r"[^A-Z]", "", b.upper())
    return bool(sa and sb) and (sa in sb or sb in sa)


def check(obj, path="data") -> None:
    """Parcourt récursivement l'objet exporté ; lève une erreur au moindre indice de personne physique."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            check(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check(v, f"{path}[{i}]")
    elif isinstance(obj, str) and not obj.startswith("http") and PERSON_HINTS.search(obj):
        raise ValueError(f"Indice de personne physique dans {path} : {obj[:80]!r}")
