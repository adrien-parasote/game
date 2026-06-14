---
name: Feature Request
about: Suggest an idea for this project
title: '[FEAT] '
labels: enhancement
assignees: ''
---
# 📝 Feature Request Template

> **Usage Note:** Replace the text in brackets `[ ]` with your feature details. Remove the italicized examples before submitting the request.

---

## 1. Feature Name
**[Clear name of the feature]**

*Example: "Character Sprint System", "House to Outdoor Transition", "Quick Inventory"*

---

## 2. Goal (The Why)
**[Why are we doing this?]**

*Examples:*
*- "The player needs to cross the map faster when there are no enemies."*
*- "Connect the basement map to the ground floor map for exploration."*

---

## 3. Game Mechanic (The What)
**[Precise description of the expected behavior]**

*Example for Sprint:*
*- Assigned key: Hold left 'Shift'.*
*- Behavior: Movement speed increases from 150 to 300 pixels per second.*
*- Animation: The walking animation speeds up (or play a specific `run_down`, `run_up` animation).*

---

## 4. Interactions with Existing Systems
Check or detail the existing systems that will be impacted by this feature:

- [ ] **Movement / Physics:** *Ex: Modifies base speed.*
- [ ] **Collisions / Navigation:** *Ex: The player can now pass through certain obstacles.*
- [ ] **Animations:** *Ex: Requires loading new running frames.*
- [ ] **User Interface (UI / HUD):** *Ex: Adds a progress or stamina bar to the screen.*
- [ ] **Map / Tile Management:** *Ex: Interacts with special tiles (stairs layers, triggers).*
- [ ] **Camera:** *Ex: The camera detaches or zooms out slightly.*
- [ ] **Game State / Save:** *Ex: Remember if this specific door has been unlocked.*

**Additional Details:**
**[Specify here how the checked systems are impacted]**

---

## 5. Assets (Visuals and Audio)
**[Required graphical or sound resources]**

*Examples:*
*- "Use tile ID 16 from the `01-stairs.tsx` tileset."*
*- "Generate a blue square placeholder sprite for testing."*
*- "The run sprites are already in `assets/characters/player_run.png`."*

---

## 6. Edge Cases
**[Boundary behaviors or non-standard situations to prevent]**

*Examples:*
*- "What happens if we release the movement key but keep holding Shift?" -> The character stops running.*
*- "Can we sprint diagonally?" -> Yes, speed must be normalized to prevent moving faster diagonally.*
*- "Is the movement cancelled if we hit a wall?" -> Yes, the player slides against the wall.*

---

## 7. Out of Scope
**[What is NOT part of this request for now]**

*Examples:*
*- "No stamina system for now (unlimited sprint)."*
*- "No dust particles behind the character."*
*- "No sound integration for footsteps."*
