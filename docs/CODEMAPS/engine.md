<!-- Generated: 2026-04-24 | Files scanned: 10 | Token estimate: ~350 -->

# Engine Logic & Data Flow

## Map Loading Flow
Game._load_map(name) → TmjParser.load_map() → TileProperty Resolver → Game._spawn_entities()
Game._spawn_entities() → WorldState.get_state() → InteractiveEntity Init → Game.interactived.add()

## Interaction Chain
Input (E) → Game._handle_interactions() → Player.get_target_rect() → Entity.interact()
Entity.interact() → DialogueManager.start_dialogue() OR Toggle State → Target ID Check
Target ID Check → Game.find_entity(target_id) → Target.interact()

## Collision Logic
Entity.move() → Game._is_collidable() → Obstacles Group + Interactives + NPCs
If collide → move cancelled → move_timer reset

## UI State Machine
Dialogue.is_active=True → Game.update() stops Player movement input
Dialogue.advance() → Typing Skip → Next Page → Close → Dialogue.is_active=False
Dialogue.is_active=False → Player input restored
