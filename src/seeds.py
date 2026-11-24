"""Étape discover : URL de départ en dur (pas de crawl général, assumé).

Chaque URL a été trouvée à la main (recherche web restreinte aux domaines
ARS / préfecture) puis vérifiée. Le pipeline ne sait PAS d'avance ce que contient
chaque PDF : il découpe les RAA par leur sommaire, classe chaque acte
(avis / classement / autorisation) et en extrait le n° d'AAP lui-même.
"""

ARS = "https://www.auvergne-rhone-alpes.ars.sante.fr"
PREF = "https://www.prefectures-regions.gouv.fr"

SEEDS = [
    # --- 2021-69-ACT (ACT, Métropole de Lyon)
    PREF + "/auvergne-rhone-alpes/content/download/77557/501248/file/1fevrier2021_n%C2%B0%201_recueil-84-2021-019-recueil-des-actes-administratifs-special(1).pdf",
    ARS + "/index.php/media/79849/download",
    PREF + "/content/download/86817/558379/file/30septembre2021_recueil-84-2021-174-recueil-des-actes-administratifs-special.pdf",
    # --- 2022-69-ACT (ACT, Rhône)
    PREF + "/content/download/91653/586983/file/31janvier2022_recueil-84-2022-021-recueil-des-actes-administratifs-special.pdf",
    "https://auvergne-rhone-alpes.ars.sante.fr/media/90066/download?inline=",
    PREF + "/auvergne-rhone-alpes/content/download/96848/618277/file/11juillet2022_n%C2%B02_recueil-84-2022-148-recueil-des-actes-administratifs-special.pdf",
    PREF + "/auvergne-rhone-alpes/irecontenu/telechargement/98987/630905/file/4octobre2022_recueil-84-2022-218-recueil-des-actes-administratifs-special.pdf",
    # --- 2024-15-EMSP (équipe mobile santé précarité, Cantal)
    ARS + "/media/129968/download",
    PREF + "/irecontenu/telechargement/121721/903077/file/6novembre2024_recueil-84-2024-327-recueil-des-actes-administratifs-special.pdf",
    PREF + "/irecontenu/telechargement/122292/907170/file/25novembre2024_n%C2%B0-1_recueil-84-2024-345-recueil-des-actes-administratifs-special.pdf",
    PREF + "/auvergne-rhone-alpes/irecontenu/telechargement/122565/909314/file/2d%C3%A9cembre2024_recueil-84-2024-350-recueil-des-actes-administratifs-special.pdf",
    PREF + "/auvergne-rhone-alpes/irecontenu/telechargement/133043/975986/file/20251127_recueil-84-2025-334-recueil-des-actes-administratifs-special.pdf",
]

# AAP retenus pour la démo (les autres n° détectés en passant sont listés à part).
TARGETS = ["2021-69-ACT", "2022-69-ACT", "2024-15-EMSP"]
# Bonus : repérés en passant dans les mêmes RAA, aucune URL ajoutée pour eux.
BONUS = ["2022-03-ACT", "2022-42-ACT"]

# Où l'on a cherché à la main ce qui manque (affiché quand un document est « non trouvé »).
SEARCH_NOTES = {
    "2024-15-EMSP": {
        "avis": [
            "Page ARS de l'AAP : « Accès refusé » (page dépubliée après clôture).",
            "Recherche web sur le domaine prefectures-regions.gouv.fr (RAA février 2024) : aucun avis EMSP Cantal identifié.",
        ],
        "autorisation": [
            "RAA 84-2024-327 (6/11/2024), 84-2024-345 (25/11/2024), 84-2024-350 (2/12/2024) parcourus par le pipeline.",
            "Décision citée (« Vu… ») dans un acte de tarification du RAA 84-2025-334 : preuve indirecte seulement.",
        ],
    },
}
