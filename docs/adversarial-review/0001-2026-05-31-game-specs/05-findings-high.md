[HIGH] — Missing Z-Index Resolution for Entities
Location: entities-system.md / Rendering
Problem: When two entities have the exact same Y-coordinate, their Z-index order is undefined. This leads to z-fighting or inconsistent rendering frame-to-frame.
Fix: Explicitly define a tie-breaker: "If Y-coordinates match, sort by Entity ID (lowest first)."

[HIGH] — Maximum Light Source Threshold Unspecified
Location: lighting-system.md / Light Limits
Problem: Spec mentions 'many' lights but no concrete cap. AI will likely hardcode an arbitrary max limit array (like 8 or 16) or allow infinite lights causing severe FPS drops.
Fix: Define explicit limit: "Maximum 16 dynamic lights per active chunk."
