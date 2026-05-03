# 🗺️ Master Strategic Roadmap: RPG Engine v0.5+

## 🎯 Current State Analysis (v0.4.x)
L'engine actuel est extrêmement solide et riche en fonctionnalités :
- **Architecture de Rendu** : Y-Sorting, Caméra dynamique, Culling optimisé.
- **Interactions** : Système d'UI robuste (Drag & Drop, Chests, Équipement), Dialogue dynamique (Speech Bubbles, Signboards), Système d'Emotes.
- **Environnement** : Cycle Jour/Nuit, Lumières dynamiques (torches, fenêtres), Audio spatial et Footsteps dynamiques basés sur le terrain.
- **État & Données** : `WorldState` pour la persistance entre les maps, `LootTables` pour la génération.
- **Qualité** : 92% de couverture de test, architecture propre (Stream Coding v6.0).

L'engine a tous les fondements d'un jeu d'exploration. La prochaine étape logique est d'ajouter les **systèmes de progression**, le **cycle de vie du jeu (Game Flow)**, et les **boucles de gameplay (Combat/Economie)**.

---

## 🚀 Roadmap des Prochaines Phases

### Phase 1 : Game Flow & Persistance (Save/Load)
*Avant d'ajouter plus de complexité, il faut pouvoir sauvegarder et structurer les états du jeu.*

1. **Serialization & Disk I/O**
   - Exporter le `WorldState`, l' `Inventory` (avec l'équipement), le `TimeSystem` (jour/saison) et l'état du `Player` (position, map courante) en JSON/binaire.
   - Gérer les slots de sauvegarde (ex: Save 1, Save 2, Autosave).
2. **Game State Machine (Menu Principal & Pause)**
   - Remplacer le lancement direct par un `GameStateManager` (`TITLE_SCREEN`, `PLAYING`, `PAUSED`, `GAME_OVER`).
   - Créer un Menu Principal (Nouvelle Partie, Charger, Options, Quitter).
   - Créer un Menu Échap (Pause) en jeu.

### Phase 2 : Fondations du Combat & Stats
*Donner une utilité aux armes et armures présentes dans l'inventaire.*

1. **Stat System (Entities)**
   - Ajouter un composant `Stats` (HP, Max HP, Attack, Defense, Speed) aux entités (Player, Enemies).
   - Lier les stats de l'inventaire (bonus d'armes/armures) au composant `Stats` du joueur.
2. **Système de Dégâts & Hitboxes**
   - Implémenter des actions d'attaque (ex: coup d'épée) générant des hitboxes temporaires.
   - Système de "Hurtbox" et calcul de dégâts (Attaque vs Défense).
   - Feedback visuel : Knockback (recul), Flash rouge, Floating Damage Numbers.
3. **Hostile AI (Enemies)**
   - Créer la classe `Enemy` héritant de `BaseEntity`.
   - AI de base : Patrol (comme les NPCs actuels), Chase (quand joueur dans un certain rayon), Attack.
   - Loot à la mort (intégration avec le système de `LootTable`).

### Phase 3 : Économie & Marchands
*Créer une boucle de ressources pour le joueur.*

1. **Currency System**
   - Ajouter la monnaie (ex: `gold`) dans l'inventaire.
   - Items avec un attribut `value` dans `gameplay.json`.
2. **Shop UI**
   - Nouvelle interface `ShopUI` (dérivée de la logique de `ChestUI` ou `InventoryUI`).
   - Interaction avec des NPCs marchands spécifiques.
   - Logique d'Achat (vérification du gold) et de Vente (transfert d'item contre du gold).

### Phase 4 : Quêtes & Progression
*Donner un but au joueur.*

1. **Quest System**
   - Moteur de quêtes stocké dans le `WorldState`.
   - Objectifs basés sur des événements (ex: `kill_x_enemies`, `collect_y_items`, `talk_to_z`).
2. **Dialogue Conditionnel**
   - Étendre le `DialogueManager` et le `SpeechBubble` pour lire des branches de dialogue différentes selon l'état du `WorldState` (ex: dialogue différent si la quête est en cours ou terminée).
3. **Quest Log UI**
   - Un nouvel onglet dans l'UI (peut-être à côté de l'inventaire) pour afficher les quêtes actives et accomplies.
