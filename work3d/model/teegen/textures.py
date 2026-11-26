"""Atlas packing and procedural texture synthesis (tangent-space normal map + occlusion map).
Everything is rasterised in UV space from per-vertex attributes measured in the garment's rest metric, so
stitch lines run exactly parallel to the hems and seams whatever the folds do."""
import numpy as np
from . import finish as F
from .uvs import shelf_pack


# ------------------------------------------------------------------------------------------ packing
def pack(G, atlas=2048, margin=10, collar_boost=1.45, inner_scale=0.5, log=print):
    isl_ids = sorted(set(G.isl.tolist()))
    box = {}
    for i in isl_ids:
        m = G.isl == i
        box[i] = (G.uvm[m].min(0), G.uvm[m].max(0))

    def rel(i):
        if i == F.ISL_LABEL:
            return 2.0
        return collar_boost if i == F.ISL_COLLAR else (inner_scale if i >= F.ISL_INNER else 1.0)

    best = None
    for S in np.arange(1700, 600, -5.0):
        sizes = [((box[i][1] - box[i][0]) * S * rel(i) + 2).astype(int) + 1 for i in isl_ids]
        posn = shelf_pack([(int(s[0]), int(s[1])) for s in sizes], atlas, margin)
        if posn is not None:
            best = (S, posn)
            break
    S, posn = best
    px = np.zeros((len(G.pos), 2))
    scale = {}
    rect = {}
    for k, i in enumerate(isl_ids):
        m = G.isl == i
        s = S * rel(i)
        lo, hi = box[i]
        x0, y0 = posn[k]
        px[m, 0] = x0 + 1 + (G.uvm[m, 0] - lo[0]) * s
        px[m, 1] = y0 + 1 + (hi[1] - G.uvm[m, 1]) * s            # image y grows downwards
        scale[i] = s
        rect[i] = (x0, y0, int((hi[0] - lo[0]) * s) + 3, int((hi[1] - lo[1]) * s) + 3)
    log(f"[tex] atlas {atlas}px, fabric texel {1000.0 / S:.2f} mm (outer), islands: " +
        ", ".join(f"{i}:{rect[i][2]}x{rect[i][3]}" for i in isl_ids))
    G.px = px
    G.uv = px / atlas                                             # glTF convention: origin top-left
    G.isl_scale = scale
    G.atlas = atlas
    return G


# ------------------------------------------------------------------------------------------ rasteriser
def rasterize(px, tris, vals, tri_isl, size):
    """Barycentric rasterisation of per-vertex values. Returns (img (size,size,c), island image)."""
    c = vals.shape[1]
    img = np.zeros((size, size, c), np.float32)
    isl = np.full((size, size), -1, np.int8)
    P0, P1, P2 = px[tris[:, 0]], px[tris[:, 1]], px[tris[:, 2]]
    den = (P1[:, 1] - P2[:, 1]) * (P0[:, 0] - P2[:, 0]) + (P2[:, 0] - P1[:, 0]) * (P0[:, 1] - P2[:, 1])
    lo = np.floor(np.minimum(np.minimum(P0, P1), P2) - 1).astype(int)
    hi = np.ceil(np.maximum(np.maximum(P0, P1), P2) + 1).astype(int)
    lo = np.clip(lo, 0, size - 1)
    hi = np.clip(hi, 0, size - 1)
    eps = 0.02
    for t in range(len(tris)):
        d = den[t]
        if abs(d) < 1e-12:
            continue
        x0, y0 = lo[t]
        x1, y1 = hi[t]
        xs = np.arange(x0, x1 + 1) + 0.5
        ys = np.arange(y0, y1 + 1) + 0.5
        X, Y = np.meshgrid(xs, ys)
        a = ((P1[t, 1] - P2[t, 1]) * (X - P2[t, 0]) + (P2[t, 0] - P1[t, 0]) * (Y - P2[t, 1])) / d
        b = ((P2[t, 1] - P0[t, 1]) * (X - P2[t, 0]) + (P0[t, 0] - P2[t, 0]) * (Y - P2[t, 1])) / d
        g = 1 - a - b
        m = (a >= -eps) & (b >= -eps) & (g >= -eps)
        if not m.any():
            continue
        v0, v1, v2 = vals[tris[t, 0]], vals[tris[t, 1]], vals[tris[t, 2]]
        sub = img[y0:y1 + 1, x0:x1 + 1]
        sub[m] = a[m][:, None] * v0 + b[m][:, None] * v1 + g[m][:, None] * v2
        isl[y0:y1 + 1, x0:x1 + 1][m] = tri_isl[t]
    return img, isl


def dilate(img, mask, iters):
    """Grow valid pixels outwards (nearest neighbour copy)."""
    img = img.copy()
    mask = mask.copy()
    for _ in range(iters):
        if mask.all():
            break
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sm = np.roll(mask, (dy, dx), (0, 1))
            si = np.roll(img, (dy, dx), (0, 1))
            take = sm & ~mask
            img[take] = si[take]
            mask = mask | take
    return img, mask


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def stitch(dd, a, period=0.0034, thread=0.00055, height=0.00032, groove=0.00020):
    """Height of one row of stitches: dd distance from the stitch line, a coordinate along it (metres)."""
    x = (a / period) % 1.0
    env = sstep(0.04, 0.22, x) * (1 - sstep(0.78, 0.96, x))
    across = np.exp(-(dd / thread) ** 2)
    h = height * across * (0.55 + 0.45 * np.sin(np.pi * np.clip((x - 0.04) / 0.92, 0, 1))) * env
    h -= groove * np.exp(-(dd / (thread * 2.2)) ** 2)
    h -= 0.00022 * np.exp(-(dd / (thread * 0.9)) ** 2) * (1 - env)          # needle holes between stitches
    return h


def grain_noise(size, seed=3):
    """Band-limited anisotropic noise that suggests the wales of a jersey knit (unit variance)."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((size, size)).astype(np.float32)
    f = np.fft.rfft2(w)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.rfftfreq(size)[None, :]
    # horizontal band around 0.30 cycles/px (wales), vertical low-pass (loops elongated along the wale)
    filt = np.exp(-((fx - 0.30) / 0.10) ** 2) * np.exp(-(fy / 0.16) ** 2) + 0.35 * np.exp(-((np.hypot(fx, fy) - 0.22) / 0.10) ** 2)
    g = np.fft.irfft2(f * filt, s=(size, size))
    g /= g.std()
    return g.astype(np.float32)


def wrinkle_noise(size, seed=11):
    """Very low frequency soft noise (subtle surface unevenness of washed cotton)."""
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((size, size)).astype(np.float32)
    f = np.fft.rfft2(w)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.rfftfreq(size)[None, :]
    r = np.hypot(fx, fy)
    filt = np.exp(-(r / 0.012) ** 2) * (r > 0)
    g = np.fft.irfft2(f * filt, s=(size, size))
    g /= g.std()
    return g.astype(np.float32)


def build_maps(G, P, ao_vert, grain=0.000055, wrinkle=0.00010, log=print):
    size = G.atlas
    RM = G.rest_metrics
    vals = np.concatenate([G.att, ao_vert[:, None]], 1).astype(np.float32)
    tri_isl = G.isl[G.tris[:, 0]]
    img, isl = rasterize(G.px, G.tris, vals, tri_isl, size)
    mask = isl >= 0
    scale = np.zeros((size, size), np.float32)
    for i, s in G.isl_scale.items():
        scale[isl == i] = s
    A = img
    d_hem, d_neck, d_sh, d_slv, d_arm = (A[:, :, k] for k in range(5))
    a_hem, a_neck, a_slv = A[:, :, 5], A[:, :, 6], A[:, :, 7]
    ao = A[:, :, 8]
    H = np.zeros((size, size), np.float32)
    body_o = (isl == F.ISL_FRONT) | (isl == F.ISL_BACK)
    slv_o = (isl == F.ISL_SL) | (isl == F.ISL_SR)
    col = isl == F.ISL_COLLAR
    body_i = (isl == F.ISL_INNER + F.ISL_FRONT) | (isl == F.ISL_INNER + F.ISL_BACK)
    slv_i = (isl == F.ISL_INNER + F.ISL_SL) | (isl == F.ISL_INNER + F.ISL_SR)

    # ---- bottom hem: double layer band + twin needle stitching
    hb = 0.00045 * (1 - sstep(0.0238, 0.0258, d_hem)) + stitch(d_hem - 0.0218, a_hem) + stitch(d_hem - 0.0158, a_hem + 0.0011)
    H += np.where(body_o, hb, 0)
    # ---- collar seam on the body: seam allowance + cover stitch
    nb = 0.00030 * (1 - sstep(0.0058, 0.0078, d_neck)) + stitch(d_neck - 0.0042, a_neck) - 0.00035 * np.exp(-(d_neck / 0.0009) ** 2)
    H += np.where(body_o, nb, 0)
    # ---- shoulder seams (taped): soft ridge with a row of stitches on each side
    sh = 0.00030 * (1 - sstep(0.0050, 0.0072, d_sh)) + stitch(d_sh - 0.0040, d_neck) - 0.00030 * np.exp(-(d_sh / 0.0008) ** 2)
    H += np.where(body_o, sh, 0)
    # ---- sleeve hems
    hs = 0.00045 * (1 - sstep(0.0208, 0.0228, d_slv)) + stitch(d_slv - 0.0188, a_slv) + stitch(d_slv - 0.0128, a_slv + 0.0011)
    # ---- armhole seam (allowance pressed into the sleeve, top stitched)
    ar = 0.00034 * (1 - sstep(0.0062, 0.0082, d_arm)) + stitch(d_arm - 0.0046, a_slv) - 0.00040 * np.exp(-(d_arm / 0.0009) ** 2)
    H += np.where(slv_o, hs + ar, 0)
    # ---- collar: 1x1 rib knit
    n_ribs = int(round(RM["neck_len"] / 0.0030))
    ph = a_hem / RM["neck_len"] * n_ribs
    rib = 0.00042 * (np.abs(np.cos(np.pi * ph)) ** 0.7 - 0.6)
    # d_hem channel = profile arc on the collar, d_neck = height above the seam
    fade = sstep(0.0004, 0.0022, d_neck)
    H += np.where(col, rib * fade, 0)
    # ---- inside: hem allowances (raised towards the inside) with the back of the stitching
    hi_b = 0.00045 * (1 - sstep(0.0240, 0.0256, d_hem)) + 0.6 * stitch(d_hem - 0.0218, a_hem, period=0.0017) + 0.6 * stitch(d_hem - 0.0158, a_hem, period=0.0017)
    H += np.where(body_i, hi_b, 0)
    hi_s = 0.00045 * (1 - sstep(0.0210, 0.0226, d_slv)) + 0.6 * stitch(d_slv - 0.0188, a_slv, period=0.0017) + 0.6 * stitch(d_slv - 0.0128, a_slv, period=0.0017)
    H += np.where(slv_i, hi_s, 0)

    # ---- woven label: twill weave, a row of stitches along the top, an embossed size letter
    lab = isl == F.ISL_LABEL
    lu, lv = d_hem, d_neck                       # label coordinates (metres): across, down from the seam
    weave = 0.00005 * np.sin(2 * np.pi * (lu + 0.5 * lv) / 0.0016) * np.sin(2 * np.pi * lv / 0.0011)

    def box(x, a, b, w=0.00035):
        return sstep(a - w, a + w, x) * (1 - sstep(b - w, b + w, x))
    letter = np.maximum(box(lu, -0.0042, -0.0014) * box(lv, 0.0200, 0.0340), box(lu, -0.0042, 0.0042) * box(lv, 0.0312, 0.0340))
    lh = weave + 0.00028 * letter + stitch(lv - 0.0075, lu, period=0.0026)
    H += np.where(lab, lh, 0)

    fabric = mask & ~col & ~lab
    if grain > 0:
        H += np.where(fabric, grain * grain_noise(size), 0)
    if wrinkle > 0:
        H += np.where(fabric, wrinkle * wrinkle_noise(size), 0)

    Hd, _ = dilate(H[:, :, None], mask, 12)
    Hd = Hd[:, :, 0]
    sd, near = dilate(scale[:, :, None], mask, 5)
    sd = sd[:, :, 0]
    gx = (np.roll(Hd, -1, 1) - np.roll(Hd, 1, 1)) * 0.5 * sd          # dH/dx (metres per metre)
    gy = (np.roll(Hd, -1, 0) - np.roll(Hd, 1, 0)) * 0.5 * sd          # dH/dy, y pointing down in the image
    # tangent space: x = +u (image right), y = image up
    n = np.stack([-gx, gy, np.ones_like(gx)], 2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    valid = near
    nmap = np.where(valid[:, :, None], n * 0.5 + 0.5, np.array([0.5, 0.5, 1.0], np.float32))
    nmap, _ = dilate(nmap.astype(np.float32), valid, 14)

    # Inside of the garment: keep the occlusion gentle. With MSAA, edge-on sliver triangles of the near wall can be
    # dropped for single samples, and whatever lies behind (the far inner wall) shows through; a very dark inner
    # wall would then read as pin-point specks on a light material.
    inside = (isl >= F.ISL_INNER)
    ao = np.where(inside, 0.58 + 0.42 * ao, ao)
    aod, m2 = dilate(ao[:, :, None], mask, 12)
    aod = aod[:, :, 0]
    # small blur of the occlusion (per-vertex AO is slightly faceted)
    for _ in range(2):
        aod = (aod + np.roll(aod, 1, 0) + np.roll(aod, -1, 0) + np.roll(aod, 1, 1) + np.roll(aod, -1, 1)) / 5
    aom = np.where(m2, aod, 1.0)
    log(f"[tex] coverage {mask.mean() * 100:.1f}% of the atlas, {n_ribs} ribs on the collar")
    return nmap.astype(np.float32), np.clip(aom, 0, 1).astype(np.float32), dict(H=H, isl=isl)


def print_normal(P, grain, w=1024, aspect=3600.0 / 2959.0, width_m=0.30, fabric_texel_m=None):
    """Normal map for the print decal: the same knit grain as the fabric, at the decal's own texel density."""
    h = int(round(w / aspect))
    px_per_m = w / width_m
    size = 1024
    rng = np.random.default_rng(5)
    wn = rng.standard_normal((size, size)).astype(np.float32)
    f = np.fft.rfft2(wn)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.rfftfreq(size)[None, :]
    # the fabric grain has its wale band at 0.30 cycles per fabric texel (~0.72 mm): same physical frequency here
    k = (1.0 / px_per_m) / 0.00072
    filt = np.exp(-((fx - 0.30 * k) / (0.10 * k)) ** 2) * np.exp(-(fy / (0.16 * k)) ** 2) + \
        0.35 * np.exp(-((np.hypot(fx, fy) - 0.22 * k) / (0.10 * k)) ** 2)
    g = np.fft.irfft2(f * filt, s=(size, size))
    g = (g / g.std())[:h, :w] * grain
    gx = (np.roll(g, -1, 1) - np.roll(g, 1, 1)) * 0.5 * px_per_m
    gy = (np.roll(g, -1, 0) - np.roll(g, 1, 0)) * 0.5 * px_per_m
    n = np.stack([-gx, gy, np.ones_like(gx)], 2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return (n * 0.5 + 0.5).astype(np.float32)
