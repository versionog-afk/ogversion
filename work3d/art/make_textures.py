"""Builds the two print textures and meta.json from the owner's original artwork.

    python3 work3d/art/make_textures.py            (run from the repository root)

Inputs (local only, not in git): work3d/ref/originals/na2.(png|webp) with a transparent background, and the back artwork
as map-black.(png|webp): the print-ready "V2" file rendered from its PDF at 300 ppi
(pdftocairo -png -r 300 -singlefile pdf/map-black.pdf map-black). It may be black ink on an opaque white page: then the
ink is taken from its darkness. PRINT_WIDTH_CM is the real width of the back artwork on the shirt (the PDF page width).
Outputs: work3d/art/front.png (3:2), back.png (3:4), meta.json.

Conventions the 3D page and the model rely on:
- front.png: the lettering centred on a 3:2 canvas, 1.5 % margin on its tightest sides.
- back.png: one warm-white ink colour on transparent, 3:4 canvas, the artwork (map, then caption) at its true
  proportions, full width minus a 1.5 % margin and TOP-aligned; the band under the caption stays empty.
- meta.json boxes are fractions of the canvas, v measured from the top.
"""
import glob, json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'ref', 'originals')
INK = (244, 242, 238)
FRONT_SIZE = (1500, 1000)
BACK_SIZE = (1536, 2048)
MARGIN = 0.015
PRINT_WIDTH_CM = 29.7   # width of the back artwork as printed (page width of the print-ready PDF)


def find(*names):
    for n in names:
        for ext in ('png', 'webp', 'tif', 'tiff'):
            p = glob.glob(os.path.join(SRC, n + '.' + ext))
            if p:
                return p[0]
    sys.exit('missing original: one of ' + ', '.join(names) + ' in ' + os.path.normpath(SRC))


def bbox(alpha, thr=24):
    ys, xs = np.where(alpha > thr)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def front():
    im = Image.open(find('na2')).convert('RGBA')
    a = np.asarray(im)[..., 3]
    x0, y0, x1, y1 = bbox(a)
    art = im.crop((x0, y0, x1, y1))
    W, H = FRONT_SIZE
    s = min(W * (1 - 2 * MARGIN) / art.width, H * (1 - 2 * MARGIN) / art.height)
    w, h = round(art.width * s), round(art.height * s)
    art = art.resize((w, h), Image.LANCZOS)
    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ox, oy = (W - w) // 2, (H - h) // 2
    canvas.alpha_composite(art, (ox, oy))
    # colour under fully transparent pixels: bleed nearby ink so texture filtering never shows a dark fringe
    arr = np.asarray(canvas).copy()
    arr = bleed(arr)
    Image.fromarray(arr, 'RGBA').save(os.path.join(HERE, 'front.png'), optimize=True)
    return {'w': W, 'h': H, 'artBox': box(ox, oy, w, h, W, H), 'sourcePx': [int(x1 - x0), int(y1 - y0)]}


def bleed(arr, rounds=24):
    """Spreads edge colours into transparent texels (alpha untouched)."""
    rgb = arr[..., :3].astype(np.float32); al = arr[..., 3]
    known = al > 8
    for _ in range(rounds):
        if known.all():
            break
        acc = np.zeros_like(rgb); cnt = np.zeros(al.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            k = np.roll(known, (dy, dx), (0, 1)); c = np.roll(rgb, (dy, dx), (0, 1))
            acc += c * k[..., None]; cnt += k
        new = (~known) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        known = known | new
    out = arr.copy(); out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    return out


def box(ox, oy, w, h, W, H):
    return {'u0': round(ox / W, 4), 'u1': round((ox + w) / W, 4), 'v0': round(oy / H, 4), 'v1': round((oy + h) / H, 4)}


def ink_alpha(im):
    """Ink coverage of single-colour line art: the alpha channel if the file has one, otherwise its darkness."""
    arr = np.asarray(im.convert('RGBA'))
    if arr[..., 3].min() < 250:
        return arr[..., 3]
    lum = np.asarray(im.convert('L')).astype(np.float32)
    return np.clip(255 - lum, 0, 255).astype(np.uint8)


def back():
    Image.MAX_IMAGE_PIXELS = None
    src = Image.open(find('map-black', 'map-white', 'map'))
    a = ink_alpha(src)
    x0, y0, x1, y1 = bbox(a)
    alpha = Image.fromarray(a[y0:y1, x0:x1])
    W, H = BACK_SIZE
    w = round(W * (1 - 2 * MARGIN)); s = w / alpha.width; h = round(alpha.height * s)
    if h > H * (1 - 2 * MARGIN):
        sys.exit('the back artwork is taller than a 3:4 canvas: change BACK_SIZE and the model contract together')
    alpha = alpha.resize((w, h), Image.LANCZOS)   # Pillow uses an area-weighted filter when shrinking: thin lines survive
    ox, oy = (W - w) // 2, round(H * MARGIN)
    A = np.zeros((H, W), np.uint8); A[oy:oy + h, ox:ox + w] = np.asarray(alpha)
    out = np.zeros((H, W, 4), np.uint8); out[..., :3] = INK; out[..., 3] = A
    Image.fromarray(out, 'RGBA').save(os.path.join(HERE, 'back.png'), optimize=True)
    # the caption is the last block of ink rows, separated from the map by the widest empty band
    rows = np.where((A > 24).sum(axis=1) > 0)[0]
    gaps = np.diff(rows); g = int(np.argmax(gaps))
    cap_top, map_bottom = rows[g + 1], rows[g] + 1
    cy0, cy1 = cap_top, rows[-1] + 1
    cols = np.where((A[cy0:cy1] > 24).sum(axis=0) > 0)[0]
    mcols = np.where((A[oy:map_bottom] > 24).sum(axis=0) > 0)[0]
    return {'w': W, 'h': H, 'artBox': box(ox, oy, w, h, W, H),
            'mapBox': box(int(mcols[0]), oy, int(mcols[-1] + 1 - mcols[0]), int(map_bottom - oy), W, H),
            'captionBox': box(int(cols[0]), int(cy0), int(cols[-1] + 1 - cols[0]), int(cy1 - cy0), W, H),
            'sourcePx': [int(x1 - x0), int(y1 - y0)],
            'printCm': [PRINT_WIDTH_CM, round(PRINT_WIDTH_CM * (y1 - y0) / (x1 - x0), 2)]}


if __name__ == '__main__':
    meta = {'placeholder': False, 'source': "owner's original artwork", 'front': front(), 'back': back()}
    json.dump(meta, open(os.path.join(HERE, 'meta.json'), 'w'), indent=1)
    print(json.dumps(meta, indent=1))
