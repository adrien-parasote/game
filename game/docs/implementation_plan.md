# Implementation Plan: Workspace Restructure & Wiki Separation

Ce document fait office de spécification technique (SPEC) finale pour la restructuration du workspace.

## 1. Le challenge de l'architecture

Vous souhaitez :
1. Avoir `GEMINI.md` et `.agents/` à la racine (visuellement).
2. Conserver le versioning Git sur `GEMINI.md` et `.agents/`.
3. Avoir un dossier `game-wiki` séparé pour la documentation utilisateur/lore.

**La solution technique (Le "Faux Sous-Dossier") :**
Puisque `GEMINI.md` doit être versionné par votre repo `game`, le dossier racine de votre workspace **doit rester le repo `game`**. 
Pour intégrer le wiki de manière transparente, nous allons cloner `game.wiki` **à l'intérieur** de ce dossier racine, mais nous allons demander à Git de l'ignorer complètement (via `.gitignore`).

**Résultat visuel dans VSCode :**
```text
/Users/.../game/                <-- Ceci est votre repo principal "game"
  ├── .git/                     (Git du jeu)
  ├── .gitignore                (Ignore "game-wiki/")
  ├── GEMINI.md                 (Versionné dans "game")
  ├── .agents/                  (Versionnés dans "game")
  ├── game/                     (Votre code source actuel)
  └── game-wiki/                <-- Clone du wiki
        ├── .git/               (Git indépendant du wiki)
        └── Home.md             (Lore, GDD)
```

> **Pourquoi c'est la meilleure solution :** L'agent IA et vous voyez tout au même endroit. Vos fichiers de configuration IA restent versionnés en toute sécurité dans le repo du jeu. Git gère les deux dépôts de manière totalement indépendante (aucun conflit de "nested repository" grâce au `.gitignore`).

## 2. Proposed Changes (Modifications)

### Configuration Git
- Mettre à jour le `.gitignore` à la racine pour ignorer le dossier du wiki.
#### [MODIFY] [.gitignore](file:///Users/adrien.parasote/Documents/perso/game/.gitignore)

### Création du Wiki local
- Cloner le repository wiki (ou l'initialiser localement si distant inexistant).
- Créer la page d'accueil du wiki pour valider l'architecture.
#### [NEW] [game-wiki/Home.md](file:///Users/adrien.parasote/Documents/perso/game/game-wiki/Home.md)

### Nettoyage de `game/docs/`
- Le dossier actuel `game/docs/` ne contient que des documents d'architecture, des ADRs et des spécifications IA. Nous les laissons tels quels dans le repo principal.

## 3. Mandatory Spec Sections (Stream Coding)

### Anti-patterns
- **Anti-pattern 1 :** Créer un super-repo avec Git Submodules. *Pourquoi :* Les submodules sont complexes à maintenir au quotidien et sources d'erreurs fréquentes.
- **Anti-pattern 2 :** Déplacer `GEMINI.md` hors du repo. *Pourquoi :* Perte de versioning des instructions IA.
- **Anti-pattern 3 :** Ne pas ignorer `game-wiki/` dans le `.gitignore`. *Pourquoi :* Git tentera d'indexer un repo dans un repo, créant un submodule corrompu.

### Test Cases
- **Test 1 : Git Isolation.** Un `git status` dans le repo principal ne doit PAS voir les modifications faites dans `game-wiki`.
- **Test 2 : Wiki Commit.** Un `git status` dans le dossier `game-wiki` doit fonctionner indépendamment.

### Error Handling
- Si le clone distant échoue, nous initialiserons un repo git vierge (`git init`) dans `game-wiki`, que vous pourrez relier au wiki GitHub plus tard.

## User Review Required

> [!IMPORTANT]
> Cette architecture répond exactement à vos 3 critères (Fichiers globaux à la racine, Versioning conservé, et Wiki séparé).
>
> Si vous validez cette architecture définitive, je lance l'exécution (BUILD) pour configurer le `.gitignore` et initialiser `game-wiki`.
