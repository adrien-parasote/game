import sys
from PIL import Image, ImageDraw
import math

def create_mech_tree_image(size=18):
    """Creates a mechanical tree pixel art image with alpha."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Golden colors
    gold_base = (218, 165, 32, 255)
    gold_light = (255, 215, 0, 255)
    gold_dark = (184, 134, 11, 255)
    gold_border = (139, 101, 8, 255)
    
    cx = size // 2
    cy = 6
    r_outer = 5
    r_inner = 3
    
    # 1. Canopy (Gear)
    # Teeth
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x = int(cx + r_outer * math.cos(rad))
        y = int(cy + r_outer * math.sin(rad))
        draw.rectangle([x-1, y-1, x+1, y+1], fill=gold_base)
        
    # Gear body
    draw.ellipse([cx - r_outer + 1, cy - r_outer + 1, cx + r_outer - 1, cy + r_outer - 1], fill=gold_base)
    # Inner hole
    draw.ellipse([cx - r_inner + 1, cy - r_inner + 1, cx + r_inner - 1, cy + r_inner - 1], fill=(0,0,0,0))
    
    # Branches inside gear
    draw.line([cx, cy-r_inner, cx, cy+r_inner], fill=gold_base, width=1)
    draw.line([cx-r_inner, cy, cx+r_inner, cy], fill=gold_base, width=1)
    draw.line([cx-2, cy-2, cx+2, cy+2], fill=gold_base, width=1)
    draw.line([cx-2, cy+2, cx+2, cy-2], fill=gold_base, width=1)
    
    # 2. Trunk
    # A sturdy mechanical trunk
    draw.rectangle([cx - 1, cy + r_inner, cx + 1, size - 4], fill=gold_base)
    
    # 3. Mechanical Roots / Base
    # Little gears or pipes at the bottom
    draw.rectangle([cx - 4, size - 4, cx - 2, size - 3], fill=gold_base)
    draw.rectangle([cx + 2, size - 4, cx + 4, size - 3], fill=gold_base)
    
    # Base pedestal
    draw.rectangle([cx - 5, size - 3, cx + 5, size - 2], fill=gold_base)
    
    # Add some shading (brodé effect)
    pixels = img.load()
    for y in range(size):
        for x in range(size):
            r, g, b, a = pixels[x, y]
            if a > 0:
                # Add highlight top-left, shadow bottom-right
                if x + y < size + 1:
                    pixels[x, y] = gold_light
                else:
                    pixels[x, y] = gold_dark
                
                # Border outline (simple)
                is_border = False
                for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < size and 0 <= ny < size:
                        if img.getpixel((nx, ny))[3] == 0:
                            is_border = True
                            break
                if is_border:
                    pixels[x, y] = gold_border

    return img

def apply_gear_to_banners(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    
    width, height = img.size
    banner_width = width // 12
    
    gear = create_mech_tree_image(18)
    gw, gh = gear.size
    gear_pixels = gear.load()
    img_pixels = img.load()
    
    for i in range(12):
        bx = i * banner_width + 16  # Center X for a 32-pixel wide banner
        by = 31                     # Center Y of the fabric in the 64-pixel high banner
        
        patch_x1 = bx - gw // 2
        patch_y1 = by - gh // 2
        
        # Calculate base luminosity
        lums = []
        for y in range(gh):
            for x in range(gw):
                px, py = patch_x1 + x, patch_y1 + y
                if 0 <= px < width and 0 <= py < height:
                    bg_r, bg_g, bg_b, _ = img_pixels[px, py]
                    lum = 0.299 * bg_r + 0.587 * bg_g + 0.114 * bg_b
                    lums.append(lum)
        
        lums.sort()
        base_lum = lums[len(lums)//2] if lums else 1
        if base_lum == 0: base_lum = 1
        
        for y in range(gh):
            for x in range(gw):
                px, py = patch_x1 + x, patch_y1 + y
                if 0 <= px < width and 0 <= py < height:
                    gr, gg, gb, ga = gear_pixels[x, y]
                    if ga > 0:
                        bg_r, bg_g, bg_b, bg_a = img_pixels[px, py]
                        
                        lum = 0.299 * bg_r + 0.587 * bg_g + 0.114 * bg_b
                        factor = lum / base_lum
                        factor = 0.6 + (factor * 0.4)
                        
                        nr = min(255, int(gr * factor))
                        ng = min(255, int(gg * factor))
                        nb = min(255, int(gb * factor))
                        
                        alpha = ga / 255.0
                        out_r = int(nr * alpha + bg_r * (1 - alpha))
                        out_g = int(ng * alpha + bg_g * (1 - alpha))
                        out_b = int(nb * alpha + bg_b * (1 - alpha))
                        
                        img_pixels[px, py] = (out_r, out_g, out_b, 255)

    img.save(output_path)

if __name__ == "__main__":
    apply_gear_to_banners("/Users/adrien.parasote/Documents/perso/game/assets/images/sprites/banners.png", "/Users/adrien.parasote/Documents/perso/game/assets/images/sprites/banners_mech_tree.png")
