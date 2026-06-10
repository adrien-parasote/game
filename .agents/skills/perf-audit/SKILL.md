---
name: perf-audit
description: Audit de performance autonome du moteur de jeu pygame-ce. Produit un rapport de décision structuré couvrant tous les problèmes détectés, les pistes d'amélioration, et leur coût (effort, risque, gain estimé). Ce skill NE MODIFIE AUCUN FICHIER SOURCE. Il est conçu pour être exécuté en premier, et son rapport est transmis à un second agent (profile-game) pour l'exécution des corrections. Activer quand l'utilisateur dit "fais un audit des perfs", "donne-moi un rapport de performance", "qu'est-ce qui est lent dans le jeu", "je veux savoir où on en est sur les perfs", ou avant de lancer une session d'optimisation.
---

# Skill — Audit de Performance (Rapport de Décision)

> ⛔ **Ce skill ne modifie AUCUN fichier source.**
> Son seul output est un rapport markdown. Toute correction est déléguée
> à un second agent via le skill `profile-game`.

---

## Étape 0 — Résoudre le workspace root

```bash
WORKSPACE=$(git rev-parse --show-toplevel)
REPORT="$WORKSPACE/scripts/dev/perf_audit_$(date +%Y%m%d_%H%M).md"
echo "Workspace : $WORKSPACE"
echo "Rapport   : $REPORT"
```

---

## Étape 1 — Lire le guide d'interprétation

Lire en entier avant d'analyser quoi que ce soit :

```bash
cat "$WORKSPACE/.agents/skills/profile-game/references/profiling-agent-guide.md"
```

---

## Étape 2 — Lancer le profiling

```bash
cd "$WORKSPACE"
python scripts/dev/profile_game.py --output scripts/dev/perf_audit_raw.txt
```

- Durée : ~30 secondes. Attendre la fin complète.
- Si erreur → reporter l'erreur dans le rapport, section **Blockers**.

---

## Étape 3 — Lire le rapport brut

```bash
cat "$WORKSPACE/scripts/dev/perf_audit_raw.txt"
```

Extraire les données de chaque axe. Les consigner en mémoire avant de rédiger.

---

## Étape 4 — Construire le rapport de décision

Rédiger et sauvegarder le rapport au chemin `$REPORT` en respectant
**exactement** ce format markdown :

---

```markdown
# Rapport d'Audit de Performance — Moteur de Jeu
> Généré le : [DATE]
> Durée du profiling : [N] frames (~[N/60] secondes)
> Fichier source : scripts/dev/perf_audit_raw.txt

---

## 1. Résumé Exécutif

**Score global : [🟢 Bon / 🟡 Dégradé / 🔴 Critique]**

| Axe | État | Problème principal |
|---|---|---|
| Frame timing | 🟢/🟡/🔴 | [résumé en 1 ligne] |
| CPU | 🟢/🟡/🔴 | [résumé en 1 ligne] |
| Mémoire | 🟢/🟡/🔴 | [résumé en 1 ligne] |
| GC Pressure | 🟢/🟡/🔴 | [résumé en 1 ligne] |

**Métriques clés :**
- FPS moyen : [X] fps
- avg frame : [X] ms (seuil : 16.7 ms)
- p95 : [X] ms (seuil confort : 20 ms)
- p99 : [X] ms (seuil critique : 33 ms)
- Mémoire delta : [X] KB/frame (seuil : 10 KB/frame)
- GC gen0 : [X] collections / 30 s (seuil : 100)

---

## 2. Problèmes Détectés

> Classés par sévérité décroissante.

### P-001 — [Nom court du problème]

| Champ | Valeur |
|---|---|
| **Sévérité** | 🔴 Critique / 🟠 Élevé / 🟡 Moyen / 🟢 Faible |
| **Axe** | CPU / Mémoire / GC / Frame timing |
| **Localisation** | `game/src/[fichier.py]:[ligne]` |
| **Métrique impactée** | [ex : tottime = 0.84 s, soit 35 % du budget frame] |
| **Description** | [Ce qui se passe exactement, sans jargon inutile] |
| **Preuve** | [Ligne exacte du rapport brut qui l'atteste] |

### P-002 — [...]
[répéter le bloc pour chaque problème]

---

## 3. Pistes d'Amélioration

> Tableau de décision. Chaque ligne correspond à un problème P-NNN.

| ID | Amélioration | Sévérité | Gain estimé | Effort | Risque | Priorité |
|---|---|---|---|---|---|---|
| P-001 | [description courte] | 🔴 | [ex: -40% tottime render] | 🟢 Faible | 🟢 Faible | ⭐⭐⭐ |
| P-002 | [description courte] | 🟠 | [ex: -15 KB/frame] | 🟡 Moyen | 🟡 Moyen | ⭐⭐ |
| P-003 | [description courte] | 🟡 | [ex: -3 gen0 coll/30s] | 🔴 Élevé | 🟡 Moyen | ⭐ |

**Légende Effort :**
- 🟢 Faible : < 1h, 1 fichier, pattern connu, tests existants
- 🟡 Moyen : 1–4h, 2–3 fichiers, refactoring localisé
- 🔴 Élevé : > 4h, plusieurs modules, tests à écrire

**Légende Risque :**
- 🟢 Faible : changement localisé, tests unitaires couvrent la zone
- 🟡 Moyen : impact possible sur d'autres composants
- 🔴 Élevé : touche un hot-path critique, forte chance de régression

---

## 4. Ordre de Traitement Recommandé

Séquence recommandée basée sur le ratio gain/effort/risque :

1. **[P-NNN]** — [raison : gain maximal, risque minimal]
2. **[P-NNN]** — [raison]
3. **[P-NNN]** — [raison]

> Chaque correction doit être exécutée indépendamment avec re-profilage
> entre chaque étape. Ne jamais grouper plusieurs P-NNN dans un même fix.

---

## 5. Blockers

> Problèmes qui empêchent l'audit ou la correction. Vide si aucun.

| Blocker | Description | Action requise |
|---|---|---|
| [ex: ImportError] | [description] | [ce qu'il faut faire] |

---

## 6. Données Brutes

**Rapport source :** `scripts/dev/perf_audit_raw.txt`

Extraits pertinents (top 5 tottime, delta mémoire, GC) :

\`\`\`
[coller ici les lignes clés du rapport brut]
\`\`\`

---

## Instructions pour le second agent

Pour exécuter les corrections, lancer le skill `profile-game` en lui passant
ce rapport comme contexte. Appliquer UN problème à la fois dans l'ordre de la
section 4. Re-profiler entre chaque correction.

\`\`\`
Skill à activer : profile-game
Rapport d'entrée : [chemin absolu de ce fichier]
Premier problème à traiter : P-[NNN]
\`\`\`
```

---

## Étape 5 — Afficher le résumé à l'utilisateur

Après avoir sauvegardé le rapport, afficher dans le chat :

```
AUDIT DE PERFORMANCE TERMINÉ
=============================
Rapport complet : scripts/dev/perf_audit_YYYYMMDD_HHMM.md

Résumé :
  [Score global] | [N] problèmes détectés

  Top 3 priorités :
  1. P-NNN — [nom] | Gain: [X] | Effort: 🟢/🟡/🔴 | Risque: 🟢/🟡/🔴
  2. P-NNN — [nom] | Gain: [X] | Effort: 🟢/🟡/🔴 | Risque: 🟢/🟡/🔴
  3. P-NNN — [nom] | Gain: [X] | Effort: 🟢/🟡/🔴 | Risque: 🟢/🟡/🔴

→ Dis-moi quels P-NNN tu veux corriger et dans quel ordre.
  Le skill profile-game prendra la main pour l'exécution.
```

---

## Règles d'or

- **Zéro modification de code source.** Ce skill est en lecture seule.
- **Zéro spéculation.** Chaque problème doit être attesté par une ligne du rapport brut.
- **Gain estimé ≠ gain garanti.** Toujours indiquer "estimé" et le baser sur les patterns connus du guide.
- **Jamais de chemin absolu.** Toujours `$WORKSPACE` résolu via `git rev-parse --show-toplevel`.
- **Un problème = un bloc P-NNN.** Ne jamais fusionner deux problèmes distincts.
