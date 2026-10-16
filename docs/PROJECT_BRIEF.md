# frda-mito-signatures — Brief de démarrage Claude Code

Oct 16, 2026 · @Clément Peponnet

## Mode d'emploi

Ce brief donne à Claude Code le contexte, les règles et le premier objectif du projet. L'architecture n'y est volontairement pas fixée : elle se décide avec Claude Code pendant la session.

1. Cloner le repo vide `neuroevidence-lab/frda-mito-signatures` et lancer Claude Code à sa racine.
2. Exporter ce doc en Markdown et le déposer à la racine sous `docs/PROJECT_BRIEF.md`, ou le coller directement en premier message.
3. Coller le prompt de la section « Premier prompt de session ».
4. Valider le plan proposé par Claude Code avant toute écriture de code (mode plan).
5. En fin de session, demander à Claude Code de générer le `CLAUDE.md` à partir des règles de ce brief et des décisions prises.

## Contexte et mission

Projet personnel mené le week-end, en open source : produire une analyse reproductible et utile à des chercheurs sur l'ataxie de Friedreich (FRDA), à partir de données publiques uniquement.

- **Maladie :** ataxie de Friedreich. Elle est causée par un déficit en frataxine (gène FXN), ce qui perturbe la formation des clusters fer-soufre et la fonction mitochondriale.
- **Pourquoi FRDA plutôt que Parkinson :** l'ancrage causal est net (FXN), il existe des données d'intervention publiques et la communauté est accessible (FARA, AFAF). Parkinson reste prévu en phase 2, pour une extension transversale sur les mitochondries.
- **Livrable cible :** une signature transcriptomique mitochondriale reproductible, accompagnée d'un dossier de preuves traçable. Ce n'est pas une plateforme, et aucune interface n'est prévue avant un premier résultat validé.
- **Utilisateur final :** un chercheur FRDA, qui doit comprendre ce qui est reproduit, ce qui est nouveau et ce qui n'est pas démontré.
- **Vision long terme :** l'organisation GitHub `neuroevidence-lab`, avec un repo par question scientifique.

## Question scientifique et périmètre phase 1

La phase 1 répond à une seule question, en deux temps.

1. Quelles signatures biologiques liées à la mitochondrie se reproduisent entre jeux de données FRDA indépendants ?
2. Les interventions de GSE145115 font-elles bouger ces signatures dans la direction attendue ?

**Premier jalon :** reproduire un résultat publié (une figure ou un tableau) et documenter l'écart obtenu. Aucune analyse « nouvelle » avant cela.

**Hors périmètre en phase 1 :**

- Parkinson et les autres maladies
- Données sous accès restreint (DUA)
- Interface web, agents LLM, graphe de preuves
- Single-cell
