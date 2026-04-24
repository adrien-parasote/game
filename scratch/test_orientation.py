import pygame
from pygame.math import Vector2

class DummyObj:
    def __init__(self, pos, d_str):
        self.pos = pos
        self.direction_str = d_str
        self.sub_type = 'chest'

def _verify_orientation(obj, p_state: str, p_pos: Vector2) -> bool:
    o_dir = getattr(obj, "direction_str", "down")
    o_pos = obj.pos
    
    x_aligned = abs(p_pos.x - o_pos.x) < 20
    y_aligned = abs(p_pos.y - o_pos.y) < 20
    
    print(f"o_dir={o_dir}, p_state={p_state}")
    print(f"p_pos={p_pos}, o_pos={o_pos}")
    print(f"x_aligned={x_aligned}, y_aligned={y_aligned}")
    
    if o_dir == 'up' and p_state == 'down' and p_pos.y < o_pos.y and x_aligned: return True
    if o_dir == 'down' and p_state == 'up' and p_pos.y > o_pos.y and x_aligned: return True
    if o_dir == 'left' and p_state == 'right' and p_pos.x < o_pos.x and y_aligned: return True
    if o_dir == 'right' and p_state == 'left' and p_pos.x > o_pos.x and y_aligned: return True
    
    return False

# Chest facing RIGHT
chest = DummyObj(Vector2(368, 464), 'right')

# Player approaches from RIGHT
p_pos = Vector2(400, 464)
p_state = 'left'

print("Test RIGHT:")
res = _verify_orientation(chest, p_state, p_pos)
print(f"Result: {res}\n")

