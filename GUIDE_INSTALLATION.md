# Guide d'installation — Blasons des communes de France

Ce guide explique comment installer et utiliser le projet **blasons**, qui permet de télécharger automatiquement les blasons (armoiries) des ~35 000 communes de France depuis Wikimedia Commons.

---

## Prérequis

Deux outils sont nécessaires :

1. **Git** — pour récupérer le code source
2. **uv** — le gestionnaire de projet Python (il installe Python et les dépendances automatiquement)

### Installer Git

#### Sur Mac

Ouvrir le **Terminal** (chercher "Terminal" dans Spotlight avec `Cmd + Espace`), puis taper :

```bash
xcode-select --install
```

Une fenêtre apparaît pour installer les outils en ligne de commande Apple, qui incluent Git. Cliquer sur **Installer**.

#### Sur Windows

Télécharger Git depuis <https://git-scm.com/download/win> et lancer l'installateur. Garder toutes les options par défaut.

Une fois installé, ouvrir **Git Bash** (chercher "Git Bash" dans le menu Démarrer). C'est dans cette fenêtre que les commandes suivantes seront tapées.

### Installer uv

`uv` est un outil qui gère Python et les dépendances du projet. Il s'installe en une seule commande.

#### Sur Mac (dans le Terminal)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Fermer et rouvrir le Terminal après l'installation.

#### Sur Windows (dans Git Bash)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Fermer et rouvrir Git Bash après l'installation.

> **Vérification** : taper `uv --version` — si un numéro de version s'affiche, l'installation a fonctionné.

---

## Récupérer le projet

Dans le Terminal (Mac) ou Git Bash (Windows), se placer dans le dossier où l'on souhaite stocker le projet, puis taper :

```bash
git clone https://github.com/arthursw/blasons.git
cd blasons
```

Cela crée un dossier `blasons` contenant tout le code source.

---

## Installer les dépendances

Toujours dans le dossier `blasons` :

```bash
uv sync
```

Cette commande s'occupe de tout : elle installe la bonne version de Python et toutes les bibliothèques nécessaires. Rien d'autre à faire.

---

## Configuration

### Fichier CSV des communes

Le projet a besoin du fichier `communes-france-2025.csv` contenant la liste des communes. S'il n'est pas déjà inclus dans le dépôt, le placer à la racine du dossier `blasons/`.

### Fichier .env (optionnel)

Créer un fichier `.env` à la racine du projet pour personnaliser les paramètres. On peut le créer avec un éditeur de texte (Bloc-notes sur Windows, TextEdit sur Mac) et y mettre :

```env
USER_AGENT=BlasonBot/1.0 (votre@email.com)
```

> **Important** : la politique de Wikimedia demande que le User-Agent contienne une adresse de contact.

---

## Lancer le téléchargement

### Commande de base

```bash
uv run blasons
```

Le programme va :
1. Charger la liste des communes depuis le CSV
2. Interroger Wikidata pour trouver les blasons (résultats mis en cache)
3. Interroger PetScan pour les communes non trouvées (résultats mis en cache)
4. Résoudre les URLs de téléchargement sur Wikimedia Commons
5. Télécharger les fichiers SVG dans des dossiers organisés par région et département

### Options utiles

| Commande | Description |
|---|---|
| `uv run blasons` | Lancement standard |
| `uv run blasons --limit 50` | Limiter à 50 communes (pour tester) |
| `uv run blasons --force` | Re-télécharger les fichiers déjà existants |
| `uv run blasons --refresh` | Ignorer le cache et re-interroger Wikidata/PetScan |

### Reprendre un téléchargement interrompu

Le programme est conçu pour reprendre là où il s'est arrêté :
- Les résultats des requêtes Wikidata et PetScan sont sauvegardés dans `data/cache/`
- Les URLs déjà résolues sont aussi mises en cache
- Les fichiers déjà téléchargés ne sont pas re-téléchargés

Il suffit de relancer `uv run blasons` pour continuer.

---

## Résultat

Les blasons sont organisés dans le dossier `blasons/` :

```
blasons/
  AUVERGNE_RHONE_ALPES/
    _AUVERGNE_RHONE_ALPES.svg          ← blason de la région
    01_AIN/
      _AIN.svg                          ← blason du département
      STKBL01_01400_L_ABERGEMENT_CLEMENCIAT_01.svg
      STKBL01_01500_AMBERIEU_EN_BUGEY_01.svg
      ...
  ILE_DE_FRANCE/
    _ILE_DE_FRANCE.svg
    75_PARIS/
      _PARIS.svg
      STKBL75_75000_PARIS_01.svg
  ...
```

Les rapports sont dans le dossier `data/` :
- `download_log.csv` — journal de tous les téléchargements
- `communes_sans_blason.csv` — communes pour lesquelles aucun blason n'a été trouvé

---

## En cas de problème

| Problème | Solution |
|---|---|
| `uv: command not found` | Fermer et rouvrir le Terminal / Git Bash |
| `git: command not found` | Réinstaller Git (voir section Prérequis) |
| Le téléchargement est très lent | C'est normal — le programme respecte les limites de Wikimedia (1 requête/seconde). ~20 000 fichiers prennent environ 6 heures. |
| Le script a planté en cours de route | Relancer `uv run blasons`, il reprendra automatiquement |
