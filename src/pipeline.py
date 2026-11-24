"""Point d'entrée : python src/pipeline.py [--no-llm]

discover (seeds) -> fetch (cache) -> extract (actes, champs) -> criteria -> link -> export web/data.js
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import criteria
import extract
import link
import privacy
from fetch import fetch
from seeds import BONUS, SEARCH_NOTES, SEEDS, TARGETS

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # console Windows


def main(use_llm=True):
    t0 = time.time()
    records, sources = [], []
    for url in SEEDS:
        try:
            path = fetch(url)
        except Exception as e:
            sources.append({"url": url, "statut": f"échec : {e}"})
            continue
        recs = extract.extract_document(url, path)
        pages = extract.pdf_pages(path)
        for r in recs:
            if r["type_doc"] == "avis":
                a, b = r["pages"]
                r["criteres"] = criteria.extract(pages[a - 1:b], a, url, use_llm)
        records += recs
        sources.append({"url": url, "statut": "ok", "pages": len(pages),
                        "actes_retenus": [f'{r["type_doc"]} {link.v(r, "aap_id") or "?"} p.{r["pages"][0]}-{r["pages"][1]}' for r in recs]})
        print(f"[{len(recs)} acte(s)] {url[-90:]}")

    ids = sorted({link.v(r, "aap_id") for r in records if link.v(r, "aap_id")})
    fiches = [{**link.build(i, records, SEARCH_NOTES.get(i, {})), "bonus": i in BONUS} for i in TARGETS + BONUS]
    autres = [i for i in ids if i not in TARGETS + BONUS]
    data = {"genere_le": datetime.now().isoformat(timespec="seconds"), "duree_s": round(time.time() - t0, 1),
            "fiches": fiches, "autres_aap_detectes": autres, "sources": sources}
    privacy.check(data)  # échoue si un indice de personne physique subsiste
    out = ROOT / "web" / "data.js"
    out.write_text("window.DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    (ROOT / "web" / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in fiches:
        print(f'{f["aap_id"]:14} confiance {f["confiance"]["niveau"]:8} ({f["confiance"]["score"]})  '
              f'avis={"✓" if f["avis"] else "✗"} classement={"✓" if f["classement"] else "✗"} '
              f'autorisation={"✓" if f["autorisation"] else ("~ citée" if f["autorisation_citee"] else "✗")}')
    print("Autres n° d'AAP détectés en passant :", ", ".join(autres) or "aucun")
    print(f"-> {out}  ({data['duree_s']} s)")


if __name__ == "__main__":
    main(use_llm="--no-llm" not in sys.argv)
