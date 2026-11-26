"""Shared geometry: the sphere, the local map projection and the camera.

Earth is a sphere of radius R_EARTH (mean radius); geographic latitude and
longitude are used directly as spherical coordinates, as most web maps do.
All distances are kilometres, all angles in the public API are degrees.

Ground rasters are kept in an azimuthal equidistant projection centred on
Kaunas: x = km east, y = km north of the centre, true distances and bearings
from the centre. The camera is a plain pinhole.
"""
import math

import numpy as np

R_EARTH = 6371.0088

# GeoNames 598316 (Kaunas) and 594557 (Šilainiai, the district the film lands in)
KAUNAS_LAT, KAUNAS_LON = 54.90272, 23.90961
SILAINIAI_LAT, SILAINIAI_LON = 54.92911, 23.88599


def unit(lat, lon):
    """Unit vector(s) for latitude / longitude in degrees. x: lat 0 lon 0, y: lat 0 lon 90E, z: north pole."""
    la = np.radians(np.asarray(lat, dtype=np.float64))
    lo = np.radians(np.asarray(lon, dtype=np.float64))
    return np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1)


def enu(lat, lon):
    """East, north, up unit vectors at a point."""
    la, lo = math.radians(lat), math.radians(lon)
    e = np.array([-math.sin(lo), math.cos(lo), 0.0])
    n = np.array([-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)])
    u = np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])
    return e, n, u


class AE:
    """Azimuthal equidistant projection of the sphere, centred on (lat0, lon0)."""

    def __init__(self, lat0=KAUNAS_LAT, lon0=KAUNAS_LON):
        self.lat0, self.lon0 = lat0, lon0
        self.e, self.n, self.u = enu(lat0, lon0)

    def from_unit(self, p):
        """p: (..., 3) unit vectors -> x, y in km."""
        cu = np.clip(p @ self.u, -1.0, 1.0)
        pe = p @ self.e
        pn = p @ self.n
        s = np.sqrt(np.maximum(pe * pe + pn * pn, 1e-30))
        c = np.arctan2(s, cu)
        k = R_EARTH * c / s
        return pe * k, pn * k

    def forward(self, lat, lon):
        return self.from_unit(unit(lat, lon))

    def inverse(self, x, y):
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        r = np.hypot(x, y)
        c = r / R_EARTH
        sc = np.where(r > 0, np.sin(c) / np.maximum(r, 1e-12), 1.0 / R_EARTH)
        p = (np.cos(c)[..., None] * self.u + (x * sc)[..., None] * self.e + (y * sc)[..., None] * self.n)
        lat = np.degrees(np.arcsin(np.clip(p[..., 2], -1, 1)))
        lon = np.degrees(np.arctan2(p[..., 1], p[..., 0]))
        return lat, lon


class Camera:
    """Pinhole camera above the sphere.

    Built from a look-at: the camera sits `dist` km from the ground point
    `target` (lat, lon), seen from there at elevation `elev` above the local
    horizontal and at azimuth `az_from` (clockwise from north; 180 = the camera
    is south of the target and looks north). The horizon is level (no roll).
    `shift_y` moves the target that many pixels below the frame centre.
    """

    def __init__(self, target, dist, elev, az_from=180.0, vfov=60.0, width=1920, height=1080, shift_y=0.0):
        self.width, self.height, self.vfov = width, height, vfov
        self.focal = (height / 2.0) / math.tan(math.radians(vfov) / 2.0)
        e, n, u = enu(*target)
        el, az = math.radians(elev), math.radians(az_from)
        tgt = R_EARTH * u
        self.pos = tgt + dist * (math.cos(el) * (math.sin(az) * e + math.cos(az) * n) + math.sin(el) * u)
        fwd = tgt - self.pos
        fwd /= np.linalg.norm(fwd)
        zen = self.pos / np.linalg.norm(self.pos)
        right = np.cross(fwd, zen)
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        if shift_y:
            a = math.atan(shift_y / self.focal)  # pitch up so the target drops below the centre
            fwd, up = math.cos(a) * fwd + math.sin(a) * up, math.cos(a) * up - math.sin(a) * fwd
        self.fwd, self.right, self.up = fwd, right, up
        self.cx, self.cy = width / 2.0, height / 2.0
        self.target = target
        self.dist = dist

    # ---- description, for the json and the independent check -------------
    def describe(self):
        r = float(np.linalg.norm(self.pos))
        zen = self.pos / r
        lat = math.degrees(math.asin(zen[2]))
        lon = math.degrees(math.atan2(zen[1], zen[0]))
        e, n, u = enu(lat, lon)
        heading = math.degrees(math.atan2(self.fwd @ e, self.fwd @ n)) % 360.0
        pitch = math.degrees(math.asin(max(-1.0, min(1.0, -(self.fwd @ u)))))  # below the local horizontal
        # roll: angle of the image right axis out of the local horizontal plane
        roll = math.degrees(math.asin(max(-1.0, min(1.0, self.right @ u))))
        return {
            "model": "pinhole camera above a sphere",
            "earth_radius_km": R_EARTH,
            "subpoint_lat": lat, "subpoint_lon": lon, "altitude_km": r - R_EARTH,
            "heading_deg": heading, "pitch_down_deg": pitch, "roll_deg": roll,
            "vfov_deg": self.vfov, "focal_px": self.focal,
            "width": self.width, "height": self.height,
            "principal_point_px": [self.cx, self.cy],
            "pixel_convention": "x to the right, y down, pixel centres at integer + 0.5",
            "horizon_dip_deg": math.degrees(math.acos(R_EARTH / r)),
        }

    # ---- projection -------------------------------------------------------
    def project(self, lat, lon, alt=0.0):
        """Ground points -> pixel x, y and a visibility flag (in front of the horizon and of the lens)."""
        p = unit(lat, lon)
        w = p * (R_EARTH + alt) - self.pos
        zc = w @ self.fwd
        with np.errstate(divide="ignore", invalid="ignore"):
            px = self.cx + self.focal * (w @ self.right) / zc
            py = self.cy - self.focal * (w @ self.up) / zc
        # visible when the point faces the camera: the line of sight leaves the sphere outward
        facing = np.einsum("...i,...i->...", p, -w) > 0
        return px, py, (zc > 0) & facing

    def rays(self, jx=0.0, jy=0.0, dtype=np.float32):
        """Unit ray directions for every pixel centre, shifted by a sub-pixel jitter."""
        xs = (np.arange(self.width, dtype=np.float64) + 0.5 + jx - self.cx) / self.focal
        ys = (np.arange(self.height, dtype=np.float64) + 0.5 + jy - self.cy) / self.focal
        d = (self.fwd[None, None, :] + xs[None, :, None] * self.right[None, None, :]
             - ys[:, None, None] * self.up[None, None, :])
        d /= np.linalg.norm(d, axis=-1, keepdims=True)
        return d.astype(dtype)

    def hit_sphere(self, d, alt=0.0):
        """Nearest intersection of rays with the sphere of radius R + alt.

        Returns the ray parameter s (km, nan where there is no hit in front of the camera)."""
        pos = self.pos
        b = (d @ pos.astype(d.dtype))
        c = float(pos @ pos) - (R_EARTH + alt) ** 2
        disc = b.astype(np.float64) ** 2 - c
        ok = disc > 0
        sq = np.sqrt(np.where(ok, disc, 0.0))
        s = -b - sq
        # camera inside the shell (alt above the camera): no downward hit on the near side
        s = np.where(ok & (s > 0), s, np.nan)
        return s


def great_circle_km(lat1, lon1, lat2, lon2):
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin((l2 - l1) / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(h))


def bearing_deg(lat1, lon1, lat2, lon2):
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    y = math.sin(l2 - l1) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(l2 - l1)
    return math.degrees(math.atan2(y, x)) % 360.0
