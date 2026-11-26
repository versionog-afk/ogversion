"""Small image helpers on top of Blender's image IO (no PIL in this environment)."""
import numpy as np


def load(path):
    import bpy
    im = bpy.data.images.load(path, check_existing=False)
    im.colorspace_settings.name = "Non-Color"
    w, h = im.size
    px = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(h, w, 4)[::-1].copy()


def save(path, img, fmt="PNG", quality=90):
    """Writes the buffer as is (no colour management): PNG or JPEG."""
    import bpy
    img = np.asarray(img, np.float32)
    if img.ndim == 2:
        img = np.repeat(img[:, :, None], 3, 2)
    h, w = img.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :img.shape[2]] = img
    im = bpy.data.images.new("tmp", w, h, alpha=False, float_buffer=False)
    im.colorspace_settings.name = "Non-Color"
    im.pixels.foreach_set(np.clip(rgba[::-1], 0, 1).ravel())
    im.filepath_raw = path
    im.file_format = fmt
    if fmt == "JPEG":
        im.save(quality=quality)
    else:
        im.save()
    bpy.data.images.remove(im)


def enhance(src, dst, lo=0.55, hi=1.0, gamma=2.2, crop=None):
    """Contrast stretch of the bright clay renders so that shading becomes readable."""
    a = load(src)[:, :, :3]
    if crop:
        x0, y0, x1, y1 = crop
        a = a[y0:y1, x0:x1]
    a = np.clip((a - lo) / (hi - lo), 0, 1) ** gamma
    save(dst, a)
