# ADR-002 — Format de sauvegarde : JSON sur disque

**Date :** 2026-05-02  
**Status :** ✅ Accepté

## Contexte

Il faut choisir comment sérialiser et stocker l'état du jeu (3 slots).

## Options évaluées

| Option | Pros | Cons |
|---|---|---|
| **JSON (retenu)** | Lisible, natif Python, pas de dépendance, inspecable en debug | Légèrement plus lent que binaire (négligeable pour 3 slots) |
| pickle | Rapide, natif | Sécurité (exécute du code), fragile aux refactors de classes, non lisible |
| SQLite | Robuste pour données relationnelles | Surengineering, aucune relation ici |

## Décision

JSON. Fichiers stockés dans `saves/` à la racine du projet. Répertoire dans `.gitignore`.

## Structure du fichier `saves/slot_N.json`

```json
{
  "version": "0.4.0",
  "saved_at": "2026-05-02T14:30:00",
  "playtime_seconds": 3600,
  "player": {
    "map_name": "01-castle_hall.tmj",
    "x": 320,
    "y": 480,
    "facing": "down"
  },
  "time_system": {
    "elapsed_seconds": 7200.0,
    "season_index": 0
  },
  "inventory": {
    "slots": [
      {"item_id": "sword_iron", "quantity": 1},
      null,
      {"item_id": "potion_health", "quantity": 3}
    ],
    "equipment": {
      "HEAD": null,
      "LEFT_HAND": {"item_id": "sword_iron", "quantity": 1},
      "RIGHT_HAND": null,
      "UPPER_BODY": null,
      "LOWER_BODY": null,
      "SHOES": null,
      "BAG": null,
      "BELT": null
    }
  },
  "world_state": {
    "castle_hall_chest_01": {"is_on": true, "loot_items": []},
    "forest_lever_03": {"is_on": false, "loot_items": null}
  }
}
```

## Conséquences

- `SaveManager` est responsable de la sérialisation/désérialisation
- `Item` doit exposer `to_dict() -> dict` et `from_dict(d: dict) -> Item`
- `Inventory` doit exposer `to_dict()` et `from_dict()`
- `TimeSystem` doit exposer `to_dict()` et `from_dict()`
- Version du schéma (`version`) incluse pour migrations futures
