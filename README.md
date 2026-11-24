# AAP médico-sociaux : avis → classement → autorisation (ARS Auvergne-Rhône-Alpes)

Prototype pour le cas métier Buddimm. Pour quelques appels à projets (AAP) clos de l'ARS
Auvergne-Rhône-Alpes, il retrouve les 3 traces publiques prévues par le CASF, les relie et
affiche une fiche par AAP. Chaque valeur renvoie à son PDF source et à sa page.

| Trace | Texte | Où on la trouve |
|---|---|---|
| Avis d'appel à projets (critères, cahier des charges) | CASF R313-4-1 | RAA de la préfecture de région, site ARS |
| Classement de la commission | CASF R313-6-2 | RAA, site ARS (PDF « avis de la commission ») |
| Autorisation (≤ date limite + 6 mois) | CASF R313-7 | RAA |

## Lancer

```bash
pip install -r requirements.txt      # pypdf, et c'est tout
python src/pipeline.py               # ou : python src/pipeline.py --no-llm
```

Ouvrir ensuite `web/index.html` dans un navigateur. Les données sont dans `web/data.js`,
ce qui permet d'ouvrir la page directement depuis le disque, sans serveur. Une copie se
trouve dans `web/data.json`.

La page comporte quatre parties :
- **Synthèse :** quelques chiffres clés et un tableau d'état par AAP (trouvé, citée, non trouvé ; délai légal ; fiabilité du lien, notée de 0 à 1).
- **Fiches :** une frise chronologique par AAP (dates à l'échelle et fenêtre légale de 6 mois), les documents sources, et les critères en barres avec l'immobilier mis en évidence.
- **Prospection :** les lauréats autorisés (prospects en aval) et les candidats classés non retenus.
- **Sources :** les PDF parcourus.

Le premier lancement télécharge environ 12 PDF (60 Mo) et dure environ 3 minutes avec
la cadence imposée et l'extraction de texte. Les lancements suivants lisent tout depuis
`cache/` et prennent moins d'une minute.

## Pipeline (`src/`)

| Étape | Fichier | Ce qu'elle fait |
|---|---|---|
| discover | `seeds.py` | URL de départ en dur (RAA et PDF ARS), trouvées à la main. Pas de crawl. |
| fetch | `fetch.py` | Cache `cache/<sha1(url)>.pdf` (jamais retéléchargé), au moins 2 s entre requêtes, User-Agent identifiable, journal `cache/fetch_log.tsv`. |
| extract | `extract.py` | `pypdf` page par page. Découpe les RAA selon leur **sommaire** (page de début et nombre de pages de chaque acte). Classe chaque acte (avis / classement / autorisation). Extrait des champs `{valeur, url, page}` par regex. |
| privacy | `privacy.py` | Personnes morales uniquement. Liste blanche (forme juridique + nom). Contrôle bloquant à l'export contre tout indice de personne physique. |
| criteria | `criteria.py` | Lit la grille de notation de l'avis par règles et ramène chaque critère à une grille commune. Auto-contrôle : la somme des coefficients doit égaler le « TOTAL » imprimé. LLM local (Ollama) en option. |
| link | `link.py` | Jointure par n° d'AAP (ex. `2021-69-ACT`), sinon par type + territoire + places. Contrôles : lauréat = bénéficiaire, règle des 6 mois. Calcule un score de fiabilité du lien (0 à 1). |
| export | `pipeline.py` | Écrit `web/data.js` et `web/data.json`. |

## LLM local (optionnel)

```bash
ollama pull qwen2.5:1.5b    # tient dans 2 Go de VRAM
python src/pipeline.py
```

Si Ollama répond sur `localhost:11434`, chaque grille de critères est aussi extraite par
le modèle (JSON imposé, température 0), puis comparée à l'extraction par règles. Sinon,
l'étape est sautée sans erreur.

> ⚠️ Ollama n'était pas installé sur la machine de développement : ce chemin est codé mais **n'a pas été exécuté**.

## Garde-fous

- Sources primaires uniquement : `auvergne-rhone-alpes.ars.sante.fr` et `prefectures-regions.gouv.fr`.
- Aucun nom de personne physique n'est stocké. Les PDF bruts (qui contiennent les signataires) restent dans `cache/`, exclu de git.
- Un document introuvable est affiché « non trouvé », avec les endroits où on l'a cherché. Rien n'est inventé.
