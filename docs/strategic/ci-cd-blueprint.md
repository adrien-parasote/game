# Strategic Blueprint: CI/CD Pipeline

## 1. Success Metrics
- **Zero Broken Merges**: No Pull Request can be merged if tests, linting, or typing checks fail.
- **100% Automated Release Notes**: Release notes are generated automatically via labels without manual sorting.
- **Zero Maintenance Overhead**: Dependencies update themselves via PRs.

## 2. Constraint Mapping (The 0€ Budget)
- **Infrastructure**: GitHub Actions.
- **Cost Rule**: GitHub Actions est gratuit pour les dépôts publics (minutes illimitées). Pour les dépôts **privés**, GitHub offre 2000 minutes gratuites par mois. 
- **⚠️ Contrainte macOS** : Sur les dépôts privés, 1 minute d'exécution sur un serveur macOS "coûte" l'équivalent de 10 minutes Linux. Pour garantir un budget strictement à 0€ sans risque d'épuiser le quota gratuit, **la CI tournera exclusivement sur Linux (`ubuntu-latest`)**.

## 3. Architecture Direction (GitHub Actions)
L'usine logicielle sera composée de 4 briques indépendantes :

1. **La Quality Gate** (`ci.yml`) :
   - Déclencheur : Toute PR et tout Push sur `main`.
   - Étapes : Checkout -> Setup Python -> Install dependencies -> `ruff format` -> `ruff check` -> `pyright` -> `pytest`.
2. **L'Auto-Labeler** (`labeler.yml`) :
   - Déclencheur : Création d'une PR.
   - Règle : `feat/*` = label `enhancement` | `bug/*` = label `bug` | `refactor/*` = label `refactor`.
3. **Le Release Manager** (`release.yml`) :
   - Déclencheur : Au moment de la création d'un Tag (`v*`).
   - Action : Génère la Release Note en triant les PRs mergées selon leurs labels.
4. **Dependabot** (`dependabot.yml`) :
   - Déclencheur : Hebdomadaire (cron).
   - Action : Ouvre une PR automatique si `pygame-ce`, `pytest` ou `ruff` ont des mises à jour.

## 4. Exclusions & Boundaries
- **Pas de compilation** : On ne génère pas de `.app` ou `.exe` pour le moment, la release contiendra uniquement le code source propre et packagé.
- **Pas de test macOS en CI** : Pour protéger le quota gratuit (voir section 2).
