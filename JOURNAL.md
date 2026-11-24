# Journal de bord

Les heures viennent des horodatages de la session Claude Code (23/11/2026). Elles ne comptent
pas mon temps de lecture et de décision entre deux échanges.

## 10:40 – 11:20 · Machine et repérage (≈ 40 min)

- **Machine.** Python 3.14 et `pypdf` déjà installés ; ni `pdftotext` ni Ollama. 8,9 Go de RAM (1,1 Go libre), Ryzen 5 2500U, GTX 1050 (2 Go).
  - Décision : un modèle 1.5B si Ollama est installé, sinon on s'en passe.
- **Pages des AAP clos inaccessibles.**
  - Les pages ARS de chaque AAP clos répondent « Accès refusé » (dépubliées), alors que d'autres pages ARS répondent 200 avec le même User-Agent.
  - Les PDF `/media/<id>/download` restent servis.
  - J'ai voulu tester un User-Agent de navigateur : le garde-fou de Claude Code a bloqué la requête, et c'est cohérent avec le brief (User-Agent identifiable). Je n'ai pas insisté.
- **Le listing ARS des appels est filtré côté client.** On n'en tire rien sans JavaScript.
- **La recherche web (restreinte aux 2 domaines) a été plus efficace :**
  - elle a donné les RAA candidats ;
  - un script de balayage (n° d'AAP, n° d'arrêté par page) a confirmé les pages.
- **Le sommaire des RAA donne la page de début et le nombre de pages de chaque acte.** C'est la clé pour découper un RAA de 200 pages.

## 11:25 – 11:45 · Pipeline (≈ 20 min)

- **Bugs corrigés en route :**
  - regex de date avalée par une alternation `|` ;
  - libellés de critères tronqués ;
  - faux coefficients : n° de page, et « loi du **2** janvier 2002 » lu comme un coefficient de 2 ;
  - catégorie : « budget… en **investissement** » rangé à tort dans l'immobilier.
- **Auto-contrôle ajouté.** La somme des coefficients extraits doit égaler le « TOTAL 60 /300 » imprimé. ✔ sur les 3 grilles lues.
- **Exécution.** Premier lancement environ 160 s (extraction de texte d'environ 700 pages), puis environ 40 s. Le pipeline a téléchargé 3 PDF, et 70 accès sont venus du cache.

## Refonte visuelle de la page (≈ 20 min)

- **Choix (validés avec moi) :** une synthèse en tête (chiffres clés et tableau d'état), une frise chronologique par AAP avec la fenêtre légale de 6 mois, les critères en barres horizontales classées, une vue prospection.
- **Couleurs :** neutres, avec un seul bleu d'accent (l'immobilier). Les couleurs d'état sont toujours doublées d'une icône et d'un libellé. Le validateur de palette fait passer la paire bleu/gris sur la séparation pour les daltoniens ; le contraste faible du gris est compensé par une valeur écrite sur chaque barre.
- **Vérifié dans Chrome :** pas d'erreur JS de la page. Deux défauts corrigés : des dates de la frise posées sur l'axe, et un conflit de classe CSS qui déformait les pastilles rouges.
- **Pas vérifié :** le rendu sur téléphone (la fenêtre ne s'est pas redimensionnée).

## Recentrage du bonus prospection (24/11)

- Après relecture du brief (agents « orientés marketing », recherche d'insights), la prospection
  ne se limite plus aux lauréats.
- Chaîne retenue : besoin (PRS, schémas, taux d'équipement) → annonce (calendrier prévisionnel)
  → AAP → locaux, avec un horizon de prospection par maillon.
- Écarté : la presse locale, exclue par la règle des sources primaires. Hôpitaux également hors
  champ (sanitaire, pas d'AAP médico-social).
- Rien de nouveau n'est codé : seuls la NOTE (§5) et le texte de la vue Prospection changent.

## État par AAP

| AAP | Avis | Classement | Autorisation | Contrôle 6 mois | Fiabilité du lien |
|---|---|---|---|---|---|
| 2021-69-ACT | ✔ RAA 84-2021-019 p.68-96 | ✔ ARS media 79849 p.1 | ✔ RAA 84-2021-174 p.7-11 | ✔ 23/09/2021 ≤ 02/10/2021 | forte (1,0 / 1) |
| 2022-69-ACT | ✔ RAA 84-2022-021 p.168-197 | ✔ RAA 84-2022-148 p.31 | ✔ RAA 84-2022-218 p.12-15 | ✔ 20/09/2022 ≤ 04/10/2022 | forte (1,0 / 1) |
| 2024-15-EMSP | ✘ non trouvé | ✔ ARS media 129968 p.1 | ~ seulement **citée** (RAA 84-2025-334 p.33) | ? non vérifiable | moyenne (0,6 / 1) |
| 2022-03-ACT (bonus) | ✔ RAA 84-2022-021 | ✘ | ✘ | ? | faible (0,0 / 1) |
| 2022-42-ACT (bonus) | ✘ | ✔ RAA 84-2022-148 p.34 | ✘ | ? | faible (0,3 / 1) |

Les deux AAP bonus ont été repérés en passant dans les mêmes RAA. Je n'ai fait aucune recherche dédiée pour eux.

## Documents introuvables, et où j'ai cherché

- **Avis 2024-15-EMSP.**
  - La page ARS est dépubliée.
  - La recherche web sur prefectures-regions.gouv.fr (RAA de février 2024) n'a rien donné.
  - La date limite (19/04/2024) n'est connue que par un extrait de recherche web, pas par une source primaire. Je ne l'ai donc pas utilisée : la règle des 6 mois reste « non vérifiable ».
  - Si cette date se confirme, l'autorisation du 04/11/2024 dépasserait la borne (19/10/2024) d'environ 2 semaines. Ce serait à vérifier, pas à conclure.
- **Décision 2024-04-0030 (EMSP), acte original.**
  - Absente des RAA 84-2024-327, -345 et -350.
  - Seulement citée dans le « Vu… » d'un arrêté de tarification 2025 (RAA 84-2025-334).

## Ce qui est fragile

- **URL de départ trouvées à la main.** Sans elles, rien n'est découvert.
- **Regex calées sur le gabarit ARA :**
  - « Le classement est le suivant », « Fait à Lyon, le », grille « (50%) 150 points » ;
  - une autre ARS ou un département demandera d'autres règles.
- **Noms de bénéficiaires hétérogènes :**
  - « Association "OPPELIA" » face à « l'Association lyonnaise nouvelle d'écoute et d'accompagnement (A.L.Y.N.E.A.) » ;
  - le rapprochement par lettres (`ALYNEA` ⊂ `…ALYNEA`) peut produire des faux positifs sur des noms courts.
- **Un gestionnaire porte plusieurs dispositifs** (ANEF Cantal : ACT, LHSS, EMSP). Une citation n'est retenue que si elle porte le même type d'établissement.
- **Nombre de places :** « 16 places … et 24 places » face à « 20 places dont 10 hors les murs ». On affiche les nombres lus, sans les additionner.
- **Score de fiabilité du lien :** une somme d'indices. Ce n'est pas une probabilité calibrée.
- **Le texte est extrait avec `pypdf` uniquement.** Un acte scanné sans couche texte serait vu comme vide (aucun cas bloquant ici).
- **LLM : codé, jamais exécuté** (Ollama absent).
