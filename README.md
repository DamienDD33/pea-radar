# PEA Radar

Classement des actions et ETF éligibles au PEA, avec les **vrais cours de clôture** mis à jour automatiquement chaque soir de semaine.

- `index.html` : l'application.
- `data/tickers.json` : la liste des actifs et leur code Yahoo Finance.
- `scripts/update_data.py` : le script qui télécharge les cours et crée `data/prices.json`.
- `.github/workflows/update.yml` : l'automatisation qui lance le script chaque soir et publie le site.

---

## Installation pas à pas (15 minutes environ)

### 1. Créer un compte GitHub
Allez sur <https://github.com/signup> et créez un compte gratuit. Votre **pseudo** fera partie de l'adresse du site.

### 2. Créer le dépôt
1. Une fois connecté, cliquez sur **+** en haut à droite, puis sur **New repository**.
2. Dans **Repository name**, tapez `pea-radar`.
3. Cochez **Public**. GitHub Pages est gratuit uniquement pour les dépôts publics, et le dépôt ne contient aucune donnée personnelle.
4. Cliquez sur **Create repository**.

### 3. Envoyer les fichiers
1. Sur la page du dépôt, cliquez sur le lien **uploading an existing file**.
2. Décompressez le zip sur votre ordinateur, puis faites glisser dans la page **le contenu** du dossier `pea-radar` : `index.html`, `README.md`, `requirements.txt` et les dossiers `data` et `scripts`.
3. Cliquez sur **Commit changes**.

### 4. Activer le site (GitHub Pages)
1. Dans le dépôt, ouvrez **Settings**, puis **Pages** dans le menu de gauche.
2. Sous **Build and deployment**, dans **Source**, choisissez **GitHub Actions**.

### 5. Autoriser l'automatisation à enregistrer les données
1. Toujours dans **Settings**, ouvrez **Actions**, puis **General**.
2. En bas de la page, sous **Workflow permissions**, cochez **Read and write permissions**.
3. Cliquez sur **Save**.

### 6. Créer le fichier d'automatisation
Le dossier `.github` commence par un point. Il est souvent masqué par Windows et macOS et ne part pas toujours par glisser-déposer. Le plus sûr est de créer le fichier à la main :
1. Cliquez sur **Add file**, puis **Create new file**.
2. Dans le nom du fichier, tapez exactement `.github/workflows/update.yml`. Les `/` créent les dossiers automatiquement.
3. Ouvrez le fichier `update.yml` du zip (il se trouve dans `.github/workflows/`) avec le Bloc-notes, copiez tout son contenu et collez-le dans GitHub.
4. Cliquez sur **Commit changes**, puis encore sur **Commit changes**.

> Pour afficher le dossier caché : sous Windows, menu **Affichage**, puis **Éléments masqués**. Sous macOS, appuyez sur `Cmd + Maj + .` dans le Finder.

### 7. Vérifier la première mise à jour
L'enregistrement du fichier d'automatisation **lance tout seul** une première mise à jour.
1. Ouvrez l'onglet **Actions** du dépôt et cliquez sur la ligne en cours (rond orange 🟠).
2. Attendez 2 à 4 minutes, jusqu'à ce qu'une coche verte ✅ apparaisse.
3. Rien ne démarre ? Cliquez sur **Mise à jour des cours** à gauche, puis sur **Run workflow**, et encore sur le bouton vert **Run workflow**.

### 8. Ouvrir l'application
Votre site est à l'adresse :

```
https://VOTRE-PSEUDO.github.io/pea-radar/
```

Ajoutez-la à vos favoris. Elle fonctionne aussi sur téléphone.

À partir de là, **tout est automatique** : chaque soir de semaine vers 18 h 20 (19 h 20 en été), GitHub télécharge les cours de clôture et republie le site.

---

## En cas de problème

| Symptôme | Solution |
|---|---|
| Le site affiche « Impossible de charger les cours » | Relancez la mise à jour (étape 7, point 3) et vérifiez que la coche est verte. |
| Message « Vous avez ouvert le fichier directement » | Ouvrez l'adresse `github.io` et non le fichier `index.html` de votre ordinateur. |
| Croix rouge ❌ dans l'onglet Actions | Cliquez dessus pour lire le journal. Si c'est l'étape « Télécharger les cours », Yahoo est peut-être momentanément indisponible : le lendemain, cela repart souvent tout seul. |
| Erreur `Permission denied` ou `403` au moment d'enregistrer | Refaites l'étape 5. |
| Erreur lors de la publication sur Pages | Vérifiez l'étape 4 (Source = **GitHub Actions**). |
| « X actifs sans données » dans l'application | Le code Yahoo de ces actifs est peut-être erroné. Le journal des Actions indique lesquels. Corrigez-les dans `data/tickers.json` (cherchez le bon code sur finance.yahoo.com, par exemple `MC.PA`). |
| Badge orange « Données anciennes » | La mise à jour automatique échoue depuis plusieurs jours : consultez l'onglet Actions. |

**Bon à savoir**
- GitHub peut retarder les tâches planifiées de quelques minutes, parfois plus.
- Si un actif échoue un soir, ses données de la veille sont conservées et l'application l'indique (« non actualisé »).
- La bibliothèque yfinance n'est pas une interface officielle de Yahoo. Elle est réinstallée dans sa dernière version à chaque exécution, ce qui corrige automatiquement la plupart des pannes.

---

## Ajouter ou retirer un actif
1. Dans `data/tickers.json`, ajoutez une ligne `"TICKER": "CODE.YAHOO"`.
2. Dans `index.html`, ajoutez une fiche dans `PEA_DB.assets` (même `ticker`, avec nom, type, secteur et description).
3. Enregistrez (**Commit changes**) : le site se met à jour tout seul en quelques minutes.

---

*Les données proviennent de Yahoo Finance et peuvent comporter des erreurs. Les frais des ETF affichés sont indicatifs. Ceci n'est pas un conseil en investissement.*
