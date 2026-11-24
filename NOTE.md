# Relier avis, classement et autorisation des AAP médico-sociaux : note de rendu

*Noé — cas métier Buddimm, stage « IA agentique et développement web ». Dépôt : `<lien git>`*

## 1. Angle, et pourquoi

Une procédure d'AAP laisse trois traces publiques : l'avis (R313-4-1), le classement de la
commission (R313-6-2) et l'autorisation (R313-7). Elles sont publiées à des dates différentes,
souvent au milieu de recueils des actes administratifs (RAA) de 100 à 200 pages. J'ai choisi
la **profondeur plutôt que la couverture** : une seule ARS (Auvergne-Rhône-Alpes), 3 AAP clos
retenus, et une chaîne **reliée et vérifiable de bout en bout** plutôt qu'un crawl large et peu fiable.

Trois choix techniques :

- **Jointure déterministe.** En ARA, chaque AAP porte un identifiant stable (`2021-69-ACT` :
  année, département, type) repris dans l'avis, le classement et souvent l'autorisation. C'est la
  clé principale. À défaut, on rapproche sur type + territoire + nombre de places. Tout est
  traçable : chaque valeur garde son URL et sa page.
- **Le RAA est découpé selon son sommaire.** Le sommaire donne, pour chaque acte, la page de
  début et le nombre de pages. On traite donc des actes, pas des pages isolées. Chaque acte est
  ensuite classé (avis, classement ou autorisation).
- **Le LLM est réservé à ce qui est flou.** Les dates, numéros et lauréats s'extraient bien par
  règles. Les critères de sélection sont le seul endroit où un LLM apporte quelque chose : ranger
  des libellés hétérogènes dans une grille commune. J'ai prévu un LLM local via Ollama (le plus
  proche d'un client qui utilise sa propre IA), avec repli sur des règles.

## 2. Ce qui marche

| AAP | Avis | Classement | Autorisation | Délai ≤ 6 mois | Fiabilité du lien |
|---|---|---|---|---|---|
| 2021-69-ACT — 40 places ACT, Métropole de Lyon | ✔ | ✔ | ✔ (lauréat = bénéficiaire) | ✔ | forte (1,0 / 1) |
| 2022-69-ACT — 20 places ACT, Rhône | ✔ | ✔ | ✔ (lauréat = bénéficiaire) | ✔ | forte (1,0 / 1) |
| 2024-15-EMSP — équipe mobile santé précarité, Cantal | ✘ | ✔ | citée seulement | non vérifiable | moyenne (0,6 / 1) |

- **Deux chaînes complètes et cohérentes.** Le contrôle « autorisation ≤ date limite + 6 mois »
  passe (23/09 pour une borne au 02/10/2021 ; 20/09 pour une borne au 04/10/2022).
- **Grille de critères lue par règles et auto-vérifiée.** La somme des coefficients lus égale le
  « TOTAL 60 /300 » imprimé dans l'avis.
- **Constat métier pour Buddimm.** Dans ces grilles ARA, la catégorie **implantation / immobilier**
  (localisation, descriptif des locaux) ne pèse que **10 points sur 300 (3,3 %)**. Le budget pèse
  20 % de la note et la qualité du projet 53 %. L'immobilier est peu noté au stade de l'AAP mais structurant
  ensuite : c'est un argument pour intervenir tôt.
- **Découvertes en passant.** Les RAA parcourus révèlent 8 autres AAP (ACT, LHSS, LAM), dont deux
  affichés en bonus avec leurs trous.
- **Règles du brief respectées :**
  - sources primaires seulement ;
  - au moins 2 s entre requêtes, User-Agent identifiable, cache (chaque PDF téléchargé une seule
    fois ; les lancements suivants lisent tout depuis le cache) ;
  - **personnes morales uniquement** : extraction en liste blanche (forme juridique + nom) et
    contrôle bloquant à l'export. Les signataires présents dans les PDF ne sont jamais stockés.

## 3. Ce qui bloque, ce qui est fragile

- **Les pages des AAP clos disparaissent du site de l'ARS** (« Accès refusé »). Les PDF restent
  servis, mais il faut connaître leur URL. Je n'ai donc pas retrouvé l'avis 2024-15-EMSP : la page
  est dépubliée et la recherche dans les RAA de février 2024 n'a rien donné.
- **Autorisation EMSP connue seulement indirectement.** L'acte original n'est pas dans les RAA de
  novembre et décembre 2024 que j'ai parcourus. Il n'est connu que par le « Vu l'arrêté
  n° 2024-04-0030… » d'un arrêté de tarification de 2025. Je l'affiche comme preuve indirecte.
- **Délai EMSP à vérifier.** Si la date limite (19/04/2024, lue dans un extrait de recherche web,
  donc non primaire) se confirme, la décision du 04/11/2024 dépasserait le délai de 6 mois
  d'environ 2 semaines. C'est un signal à vérifier, pas une conclusion.
- **La découverte est manuelle.** Les URL de départ ont été trouvées par recherche web ciblée. Je
  n'ai pas fait de crawl, par manque de temps et parce que le listing ARS est rendu en JavaScript.
- **Règles calées sur le gabarit ARA.** Une autre ARS, et surtout les départements, demanderont
  d'autres motifs.
- **Fragilités de détail.** Les noms de bénéficiaires sont hétérogènes (« OPPELIA » face à
  « Association lyonnaise … (A.L.Y.N.E.A.) »). Un même gestionnaire porte plusieurs dispositifs, il
  faut donc filtrer aussi sur le type. Les « 16 + 24 places » ne s'additionnent pas comme
  « 20 dont 10 ». Le score de fiabilité du lien additionne des indices et n'est pas calibré.
- **LLM non exécuté.** Ollama n'était pas installé sur ma machine (8 Go de RAM, GTX 1050 avec
  2 Go). L'étape est codée (JSON imposé, cache, comparaison avec les règles) mais **n'a pas tourné**.

## 4. La suite

1. **Découverte automatique.** Indexer chaque nouveau RAA (sommaire seul, quelques Ko utiles)
   plutôt que des URL en dur. Sur les RAA testés, le titre de l'acte dans le sommaire distinguait
   déjà « Avis d'appel à projet » et « portant autorisation ». Le classement, lui, se reconnaît à
   son texte, pas à son titre.
2. **Passage à l'échelle multi-ARS et départements :**
   - une fiche de règles par émetteur ;
   - le LLM local pour les formats inconnus, validé par les auto-contrôles (total des
     coefficients, dates cohérentes) ;
   - les appels conjoints ARS/département sont publiés à deux endroits : il faut dédoublonner
     sur l'objet, le territoire et les dates.
3. **OCR des actes scannés,** au moins pour les arrêtés de tarification, souvent numérisés.
4. **Veille des calendriers prévisionnels.** L'avis cite l'arrêté annuel qui fixe le calendrier
   (ex. ARS n° 2022-14-0002) : c'est la source pour anticiper les AAP.
5. **Évaluation.** Constituer un petit jeu de vérité terrain (environ 20 AAP vérifiés à la main)
   pour mesurer précision et rappel, et calibrer le score de fiabilité.

## 5. Bonus : brancher le résultat sur la prospection

Un AAP médico-social ne surgit pas d'un fait divers : il **exécute une programmation publique**.
La chaîne complète va du besoin aux locaux, et le prototype n'en couvre que le milieu :

```
Besoin      PRS de l'ARS, schémas départementaux, taux d'équipement (DREES), démographie (INSEE)
  → Annonce   calendrier prévisionnel annuel des AAP (arrêté de l'ARS)
  → AAP       avis → classement → autorisation          ← ce que relie le prototype
  → Locaux    recherche, travaux, visite de conformité (L313-6)
```

Chaque maillon donne un horizon de prospection :

- **Tendance (1 à 3 ans avant).** L'agent agrège les AAP collectés par type, territoire et année
  (places autorisées). Il extrait aussi des PRS et des schémas les objectifs chiffrés de création
  de places. Objectif moins places déjà autorisées : on obtient les territoires et les types
  d'établissement où un prochain AAP est probable. On approche alors tôt les gestionnaires du
  secteur, avec une étude foncière à l'appui.
- **Annonce (2 à 12 mois avant).** Le calendrier prévisionnel (ex. arrêté ARS n° 2022-14-0002)
  désigne le type et le territoire. Les associations concernées auront environ 2 mois pour produire
  un volet « locaux », que la grille ne note qu'à 3 % mais qui structure la suite.
- **Aval (après l'autorisation).** Ce volet est **déjà livré** : les lauréats (ALYNEA, OPPELIA,
  ANEF Cantal) ont des locaux à trouver ou à mettre en conformité. Les candidats classés 2ᵉ ou 3ᵉ ont
  un projet prêt et le représenteront souvent.

**Non fait.** Les horizons tendance et annonce ne sont pas codés, et 5 AAP ne suffisent pas à
dégager une tendance. La presse locale est exclue par le brief (sources primaires uniquement) : au
mieux un signal lu par un humain, jamais stocké.

## 6. Outils et temps

- **Outils :**
  - Claude Code (modèle Claude Opus 5.5) pour le repérage des sources (recherche web restreinte
    aux domaines ARS et préfecture), le code et les brouillons ;
  - Python 3.14 et `pypdf`, curl ;
  - Ollama et `qwen2.5:1.5b` prévus mais non installés, donc non utilisés.
- **Temps :** environ 1 h 15 de session (repérage environ 40 min, pipeline et app environ 20 min,
  rédaction environ 15 min), plus mon temps de relecture et de décision. *[à compléter et ajuster]*
