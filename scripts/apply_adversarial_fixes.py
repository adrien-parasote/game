import os

def append_to_file(filepath, text):
    with open(filepath, 'a') as f:
        f.write(text)

append_to_file('docs/game/specs/map-world-system.md', '\n## Error Handling - Map Loading\nIf a map chunk fails to load due to a missing tileset asset, render a magenta/black checkerboard tile as a fallback.\n')
append_to_file('docs/game/specs/save-system.md', '\n## Serialization Rules\nActive dialogue state is NOT serialized. Loading a game always spawns the player in the overworld, cancelling any active dialogue.\n')
append_to_file('docs/game/specs/entities-system.md', '\n## Z-Index Sorting\nIf Y-coordinates match, sort by Entity ID (lowest first) as a tie-breaker.\n')
append_to_file('docs/game/specs/lighting-system.md', '\n## Light Limits\nMaximum 16 dynamic lights per active chunk.\n')
append_to_file('docs/game/specs/dialogue-system.md', '\n## State Management\nStandard NPC speech bubbles are suppressed during Cutscene state.\n')

print("Applied adversarial fixes")
