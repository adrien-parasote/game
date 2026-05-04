# 🗺️ Roadmap — L'Éveil de l'Héritier v0.5+

> **Évolutif** — rien n'est définitif. Vision complète : `docs/strategic/game_vision.md`  
> Dernière mise à jour : 2026-05-04

---

## 📦 Audit Assets Existants

| Catégorie | Fichiers | Statut |
|---|---|---|
| Maps | `00-spawn.tmj`, `01-castel.tmj` | ⚠️ À refaire |
| Maps | `99-debug_room.tmj` | ✅ Référence technique |
| Sprites | `01-character.png`, `02-butler.png` | ✅ |
| Sprites interactifs | portes, coffres, torches, leviers, emotes | ✅ |
| Tilesets | sol, murs, fenêtres, mobilier intérieur | ✅ (intérieur uniquement) |
| BGM | `00-castel.ogg` | ✅ 1 piste |
| SFX | porte, levier, coffre, emote, footstep ×2, feu | ✅ 6 effets |

**Manque :** tilesets extérieurs · sprites ennemis/NPCs/familiers · BGM zones · SFX météo/cuisine/nature

---

## 🎯 Vision

**Solo v1.0 :** Cozy RPG sans fin. Saisons, météo, amitié, familiers, ville vivante.  
**Co-op local v2.0 :** 2-3 joueurs. Trésor partagé. Synergies amplifiées.

### Boucle de synergie complète
```
🪓 Bûcherons + ⛏️ Mineurs + 🏹 Chasseurs
          ↓ ressources brutes
🔨 Artisans  → armes, armures, mobilier, ornements
🌾 Semeurs   → récoltes + monstres cuisinés → festins
⚙️ Ingénieurs → Gardien Méca, automatisation
          ↓
💰 Commerce + 🔮 Éthéristes → sphérier, enchantements
          ↓
🏰 Château → gestion ville, familiers, amitié PNJs
```

---

## ✅ Phase 1 — Game Flow & Persistance `v0.5` TERMINÉE

GameStateManager · Save/Load 3 slots · TitleScreen · PauseScreen · SaveMenuOverlay

---

## 🌿 Phase 2 — Fondations du Monde `v0.5→0.6`

### Développement
- **`gameplay.json`** : items (ressources, ingrédients, drops monstres, équipements météo, mobilier, `gold`, `ether_crystal`)
- **Stats joueur** : `hp, max_hp, attack, defense, speed`
- **Customisation personnage** : silhouette, couleur, tenue · équipements visibles sur sprite
- **Saisons** : `TimeSystem` étendu → 4 saisons · durée jour/nuit variable
- **PNJs multi-races** : `race`, `guild`, `home_tile`, `work_tile`, `leisure_spots[]`
- **Routine IA PNJ** : lever (6h) · déjeuner (8h) · travail (9h-18h) · taverne (18-21h) · sommeil (23h)
- **Races disponibles** : Humains · Elfes · Nains · Hommes-bêtes · Méca

### 🎨 Assets à produire
**Maps (construites ensemble) :**
| Map | Zone | Tilesets |
|---|---|---|
| `01-chateau_chambre.tmj` | Chambre du joueur (hub respawn) | mobilier intérieur ✅ |
| `02-chateau_salon.tmj` | Grande salle, bâtiments ruinés | murs/sol pierre ✅ |
| `03-jardin.tmj` | Jardin extérieur, parcelles agricoles | **tileset-exterieur** ❌ |

**Sprites :** NPCs 4 races · 4 directions · emotes étendues  
**Tilesets :** `tileset-exterieur.png` (herbe, chemin, haies, fleurs, murs pierre)  
**Audio :** BGM `01-jardin.ogg` · BGM `02-village.ogg` · SFX footstep herbe/terre · ambiance jardin

**Livrable :** Château jouable, jardin accessible, monde saisonnier et peuplé.

---

## 🌧️ Phase 3 — Météo & Équipement Contextuel `v0.6→0.7`

### Développement
`WeatherSystem` : 6 états · malus/bonus · items équipés annulent les malus · `requires_item` dans Tiled

| Météo | Malus | Annulé par |
|---|---|---|
| Pluie | Marche -20% · Agriculture +10% | `parapluie` |
| Orage | Marche -40% | `manteau_tempête` |
| Neige | Marche -15% | `manteau_hiver` |
| Brouillard | Vision -50% | `lunettes_ether` |
| Zone aquatique | Nage lente / accès bloqué | `tuba` |

`requires_item` dans Tiled : `08-sous_eau` → `tuba` · `09-montagne` → `manteau_hiver`

### 🎨 Assets à produire
**Maps :** `04-village.tmj` · `05-foret.tmj`  
**Sprites :** overlays météo (pluie, neige, brouillard) · équipements visibles (parapluie, manteau)  
**Tilesets :** `tileset-foret.png` (arbres, sous-bois, racines, clairière)  
**Audio :** BGM `03-foret.ogg` · BGM `04-orage.ogg` · SFX pluie/orage/vent neige

**Livrable :** Météo dynamique, équipement contextuel, zone forêt jouable.

---

## 🏗️ Phase 4 — Château, Bâtiments & Guildes `v0.7→0.8`

### Développement
- `BuildingSystem` : 4 niveaux (ruiné→reconstruit→décoré→restauré)
- `FurnitureSystem` : placement libre, grille tile-based, effets passifs optionnels
- `GuildSystem` : 6 guildes · rangs (Apprenti→Grand Maître) · contrats journaliers
- Chambre extensible : 4×4 → 6×6 → 8×8 → suite royale (selon `KingdomState`)
- Mobilier acheté **exclusivement aux guildes**
- Gestion de la ville depuis le **Bureau du Seigneur** (château, pas de mairie)

**Pièces du château :**
| Pièce | Fonction | Extensible |
|---|---|---|
| Bureau du Seigneur | Gestion ville, contrats guildes | Non |
| Chambre | Lit de respawn, aménageable | ✅ |
| Grande salle | Festins, festivals intérieurs | Selon KingdomState |
| Salle du trésor | Stock partagé (co-op) | Selon reconstruction |
| Bibliothèque | Sphérier, lore, quêtes | Selon reconstruction |
| Enclos des familiers | Héberge les animaux apprivoisés | ✅ |

**Guildes & Bâtiments :**
| Guilde | Bâtiments | Mobilier vendu |
|---|---|---|
| ⚔️ Aventuriers | Taverne · Armurerie · Salle d'entraînement | Trophées, armures déco |
| 💰 Commerce | Comptoir · Entrepôt · Marché couvert | Comptoirs, coffres décorés |
| 🔮 Éthéristes | Tour de Magie · Cristallerie · Labo | Cristaux lumineux, tapis runiques |
| 🌾 Semeurs | Grange · Serre · Cuisine communale | Jardinières, râteliers |
| 🔨 Artisans | Atelier · Forge · Couture · Menuiserie | Meubles artisanaux, outils déco |
| ⚙️ Ingénieurs | Atelier Méca · Fonderie · Dépôt | Automates déco, engrenages muraux |

### 🎨 Assets à produire
**Maps :** `06-mines.tmj` · `07-marais.tmj`  
**Sprites :** bâtiments 4 états visuels par guilde  
**Tilesets :** `tileset-village.png` · `tileset-mines.png`  
**Audio :** BGM `05-village-jour.ogg` · BGM `06-village-nuit.ogg` · BGM `07-mines.ogg` · SFX forge/couture/mécanismes

**Livrable :** La ville se reconstruit guilde par guilde. Le château s'aménage.

---

## 🌾 Phase 5 — Agriculture, Cuisine & Monstres `v0.8→0.9` ⭐

### Développement
- `Harvestable` : 4 états `seed→sprout→grown→ripe` · piloté par `TimeSystem`
- **Gardien Méca** : ordres simples → coffre `jardin_stock` · extensible avec niveau Jardin
- **Chasseurs** : animaux dans `05-foret` → viande, peaux, captures de familiers
- **Bûcherons** : arbres abattables → bois · **Mineurs** : veines minerai → pierre, métal
- `CraftingSystem` : `recipes.json` unifié cuisine + artisanat · filtré par station + niveau bâtiment
- **Monstres cuisinables** (Dungeon Meshi) : Bestiaire Culinaire in-game

| Monstre | Drop cuisinable | Effet plat |
|---|---|---|
| Créature végétale | Filaments, spores | +HP regen 3j |
| Gardien méca hostile | Huile, acier cristal | +defense 2j |
| Loup des glaces | Viande de givre | +speed |
| Boss de zone | Cœur éthéré | Buff permanent mineur |

**Festivals saisonniers :**
| Saison | Festival | Déclencheur |
|---|---|---|
| Printemps | Festival des Semailles | Festin aux herbes sauvages |
| Été | Festival du Soleil | Festin aux fruits d'éther |
| Automne | Festival de la Moisson | Festin de monstre |
| Hiver | Festival des Lumières | Festin chaud (ragoût) |

### 🎨 Assets à produire
**Maps :** `08-sous_eau.tmj` (tuba requis) · `09-montagne.tmj` (manteau requis)  
**Sprites :** 4-6 ennemis (attaque, dégâts, mort) · plantes 4 stades · effets cuisine  
**Tilesets :** `tileset-aquatique.png` · `tileset-montagne.png`  
**Audio :** BGM `08-combat.ogg` · BGM `09-festival.ogg` · BGM `10-sous_eau.ogg` · BGM `11-montagne.ogg` · SFX récolte/cuisine/festival/combat

**Livrable :** Cuisiner un monstre, déclencher un festival, voir la ville fêter.

---

## 🐾 Phase 6 — Familiers & Amitié `v0.9→1.0`

### Développement
- `FamiliarSystem` : apprivoisement (nourrir un animal affaibli) · 5 niveaux d'amitié
- `FriendshipSystem` : 5 niveaux avec PNJs · cadeaux · accès progressif

**Familiers :**
| Familier | Capacité (niv. 4) |
|---|---|
| Renard des bois | Révèle items cachés |
| Louveteau méca | Alerte intrusions château |
| Fée champignon | Accélère croissance parcelle |
| Dragon de poche | Flamme 1×/jour |
| Poisson lanterne | Navigation zones aquatiques |

**Amitié PNJ :** Inconnu → Connaissance → Ami → Proche → Confiant  
Niv. 5 : PNJ rejoint ponctuellement l'aventure + bonus passif permanent.

### 🎨 Assets à produire
**Sprites :** 5-8 familiers (idle, suivi, capacité, affection)  
**Audio :** SFX par familier · BGM `12-enclos.ogg`

---

## 🔮 Phase 7 — Sphérier & Combat `v1.0→1.1`

### Développement
- `SphereGrid` : **Éther Cristallisé** comme monnaie unique · nœuds libres (pas de voie verrouillée)
- Tout débloquable en solo · Bibliothèque du château déverrouille les nœuds
- Sources d'éther : quêtes (+3-15) · craft (+1) · recette (+2) · festival (+5) · boss (+10) · bâtiment (+5)
- `Enemy` : Patrol→Chase→Attack · **mort douce** : Majordome nous ramène au lit

**Structure sphérier (nœuds libres) :**
```
🌱 Récolte ×1.5    🏗️ -30% coûts     🗡️ +15% dégâts
🍳 Buffs 2 jours   📚 +éther ×1.2    🛡️ -20% dégâts
🎉 +festivals      🌍 +maps cachées   💨 +drops monstres
🤝 Synergiste*     ⚖️ +XP ×1.5       🔥 Berserker
```
*Synergiste : bonus en solo, ×2 en co-op*

**Audio :** BGM `13-boss.ogg` · SFX sphérier (cristal qui s'active)

---

## 💰 Phase 8 — Économie, Quêtes & Jeu Sans Fin `v1.1→1.5`

- `ShopUI` (dérivée `ChestUI`) · rang guilde → items exclusifs
- Quêtes : `collect` · `cook` · `build` · `tame` · `befriend` · `festival` · `weather_challenge` · `serve_monster_dish`
- Dialogue conditionnel (WorldState + saison + météo + amitié)
- **Pas d'endgame forcé** — saisons infinies, nouveaux PNJs, `KingdomState` croissant

**Audio :** BGM variations saisonnières · SFX commerce/quête/amitié

---

## 👥 Phase 9 — Co-op Local `v1.5→2.0`

- 2-3 joueurs · WorldState + KingdomState + **Salle du trésor** partagés
- Sphérier indépendant par joueur · Familiers indépendants
- Festival déclenché par un joueur → bonus pour tous
- Save solo compatible avec l'arrivée de nouveaux joueurs

---

## 📐 Versions

| Version | Dev | Assets prioritaires |
|---|---|---|
| `0.5.x` | Hardening ← **maintenant** | — |
| `0.6.0` | Monde + Saisons + PNJs + Customisation | Château maps · NPCs · tileset extérieur · BGM jardin/village |
| `0.7.0` | Météo + Équipement contextuel | Overlays météo · tileset forêt · BGM forêt/orage |
| `0.8.0` | Château + Guildes + Bâtiments + Mobilier | Bâtiments sprites · tileset village/mines · BGM mines |
| `0.9.0` | Agriculture + Cuisine + Monstres ⭐ | Ennemis · tilesets aquatique/montagne · BGM combat/festival |
| `1.0.0` | Familiers + Amitié PNJ | Familiers sprites · SFX animaux |
| `1.1.0` | Sphérier + Combat doux | BGM boss · SFX sphérier |
| `1.5.0` | Économie + Quêtes + Jeu sans fin | BGM saisonnières |
| `2.0.0` | Co-op Local 👥 | — |
