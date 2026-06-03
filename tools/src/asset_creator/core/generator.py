import numpy as np


def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def lerp(a, b, t):
    return a + t * (b - a)

def noise_4d_value(x, y, z, w, rng, grid_size=8):
    """4D Value noise evaluating coordinates mapped onto a grid."""
    # Normalize coordinates to positive space and scale by grid_size
    x = (x - x.min()) / (x.max() - x.min() + 1e-6) * grid_size
    y = (y - y.min()) / (y.max() - y.min() + 1e-6) * grid_size
    z = (z - z.min()) / (z.max() - z.min() + 1e-6) * grid_size
    w = (w - w.min()) / (w.max() - w.min() + 1e-6) * grid_size

    xi = x.astype(int) % grid_size
    yi = y.astype(int) % grid_size
    zi = z.astype(int) % grid_size
    wi = w.astype(int) % grid_size

    xf = x - np.floor(x)
    yf = y - np.floor(y)
    zf = z - np.floor(z)
    wf = w - np.floor(w)

    u = fade(xf)
    v = fade(yf)
    t1 = fade(zf)
    t2 = fade(wf)

    grid = rng.uniform(0, 1, (grid_size, grid_size, grid_size, grid_size))

    def get_val(ix, iy, iz, iw):
        return grid[ix % grid_size, iy % grid_size, iz % grid_size, iw % grid_size]

    val_000 = lerp(get_val(xi, yi, zi, wi), get_val(xi+1, yi, zi, wi), u)
    val_010 = lerp(get_val(xi, yi+1, zi, wi), get_val(xi+1, yi+1, zi, wi), u)
    val_100 = lerp(get_val(xi, yi, zi+1, wi), get_val(xi+1, yi, zi+1, wi), u)
    val_110 = lerp(get_val(xi, yi+1, zi+1, wi), get_val(xi+1, yi+1, zi+1, wi), u)
    val_001 = lerp(get_val(xi, yi, zi, wi+1), get_val(xi+1, yi, zi, wi+1), u)
    val_011 = lerp(get_val(xi, yi+1, zi, wi+1), get_val(xi+1, yi+1, zi, wi+1), u)
    val_101 = lerp(get_val(xi, yi, zi+1, wi+1), get_val(xi+1, yi, zi+1, wi+1), u)
    val_111 = lerp(get_val(xi, yi+1, zi+1, wi+1), get_val(xi+1, yi+1, zi+1, wi+1), u)

    val_00 = lerp(val_000, val_010, v)
    val_10 = lerp(val_100, val_110, v)
    val_01 = lerp(val_001, val_011, v)
    val_11 = lerp(val_101, val_111, v)

    val_0 = lerp(val_00, val_10, t1)
    val_1 = lerp(val_01, val_11, t1)

    return lerp(val_0, val_1, t2)

def fractal_noise_4d(x, y, z, w, rng, octaves=4, persistence=0.5, lacunarity=2.0):
    """Fractal Brownian Motion (fBm) using 4D Value Noise."""
    total = np.zeros_like(x)
    amplitude = 1.0
    max_value = 0.0
    for i in range(octaves):
        # We increase grid_size per octave manually in the function
        grid_sz = int(8 * (lacunarity**i))
        total += noise_4d_value(x, y, z, w, rng, grid_size=grid_sz) * amplitude
        max_value += amplitude
        amplitude *= persistence
    return total / max_value

def generate(texture_type: str, seed: int, scale: float) -> np.ndarray:
    """Generate a 256x256 toroidal noise map using 4D coordinate mapping."""
    rng = np.random.RandomState(seed)
    texture_type = texture_type.lower()

    W, H = 256, 256

    grid_x = np.linspace(0, 2 * np.pi, W, endpoint=False)
    grid_y = np.linspace(0, 2 * np.pi, H, endpoint=False)
    yy, xx = np.meshgrid(grid_y, grid_x, indexing='ij')

    scale_x = scale
    scale_y = scale

    if texture_type == "wood":
        stretch = 4
        scale_y = scale / stretch

    r_x = scale_x / (2 * np.pi)
    r_y = scale_y / (2 * np.pi)

    # Toroidal 4D mapping (perfect seamlessness)
    X = np.cos(xx) * r_x
    Y = np.sin(xx) * r_x
    Z = np.cos(yy) * r_y
    W_coord = np.sin(yy) * r_y

    if texture_type == "stone":
        noise = fractal_noise_4d(X, Y, Z, W_coord, rng, octaves=4)
    elif texture_type == "grass":
        noise = fractal_noise_4d(X, Y, Z, W_coord, rng, octaves=2)
    elif texture_type == "water":
        base = fractal_noise_4d(X, Y, Z, W_coord, rng, octaves=2)
        noise = np.sin(X*10 + base*10)
        noise = (noise + 1) / 2
    elif texture_type == "dirt":
        noise = noise_4d_value(X, Y, Z, W_coord, rng, grid_size=16)
    elif texture_type == "wood":
        base_noise = fractal_noise_4d(X, Y, Z, W_coord, rng, octaves=3)
        noise = np.sin(base_noise * 30)
        noise = (noise + 1) / 2
    else:
        noise = fractal_noise_4d(X, Y, Z, W_coord, rng, octaves=3)

    # Ensure range [0, 1]
    _min, _max = noise.min(), noise.max()
    if _max > _min:
        noise = (noise - _min) / (_max - _min)

    return noise.astype(np.float32)
