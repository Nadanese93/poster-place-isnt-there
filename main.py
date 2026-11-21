#!/usr/bin/env python3
"""VELMORA — Isles of the Amber Sea.

A travel poster for a place that does not exist, drawn by a deterministic
pure-stdlib renderer (no third-party packages, no network, no randomness).

The poster: golden-hour sky, a low sun, floating islands with waterfalls
pouring into mist, a calm sea with a sunlit reflection column, and the
invented place name VELMORA set in large geometric capitals.

Run:  MAKEFUN_OUTPUT_DIR=/output python3 main.py
Writes: $MAKEFUN_OUTPUT_DIR/entry.png (1024x1024, PNG, <= 1 MiB).
Python 3.13 standard library only.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
SKY_STOPS = [  # (y, r, g, b) — golden-hour gradient, top to horizon
    (0, 36, 22, 64),
    (180, 91, 35, 80),
    (340, 168, 62, 78),
    (480, 217, 106, 62),
    (600, 239, 169, 79),
    (660, 246, 212, 124),
    (720, 232, 155, 78),
    (780, 201, 123, 63),
]
SUN_CORE = (255, 246, 207)
SUN_GLOW = (246, 196, 83)
ISLE_DARK = (58, 31, 61)
ISLE_FACE = (84, 44, 66)
RIM = (232, 163, 76)
FALL = (251, 239, 208)
MIST = (242, 200, 121)
SEA_TOP = (22, 78, 90)
SEA_BOT = (12, 44, 56)
HORIZON = (201, 123, 63)
CREAM = (255, 246, 220)
SHADOW = (91, 35, 80)
FRAME = (255, 246, 220)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def blend(self, x, y, color, alpha):
        """Alpha-over blend of a flat color onto the pixel."""
        if 0 <= x < self.w and 0 <= y < self.h and 0.0 < alpha:
            if alpha >= 1.0:
                self.set(x, y, color)
                return
            i = (y * self.w + x) * 3
            inv = 1.0 - alpha
            self.px[i] = int(color[0] * alpha + self.px[i] * inv + 0.5)
            self.px[i + 1] = int(color[1] * alpha + self.px[i + 1] * inv + 0.5)
            self.px[i + 2] = int(color[2] * alpha + self.px[i + 2] * inv + 0.5)

    def hline(self, x0, x1, y, color):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        i = (y * self.w + x0) * 3
        r, g, b = color
        for x in range(x0, x1 + 1):
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b
            i += 3

    def hline_alpha(self, x0, x1, y, color, alpha):
        if y < 0 or y >= self.h or alpha <= 0.0:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        for x in range(x0, x1 + 1):
            self.blend(x, y, color, alpha)

    def vgrad(self, y0, y1, stops):
        """Fill rows y0..y1 with a multi-stop vertical gradient."""
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            c = sample_stops(stops, y)
            self.hline(0, self.w - 1, y, c)

    def fill_rect(self, x0, y0, x1, y1, color):
        for y in range(max(0, int(y0)), min(self.h, int(y1) + 1)):
            self.hline(x0, x1, y, color)

    def fill_circle(self, cx, cy, r, color):
        r = int(r)
        for dy in range(-r, r + 1):
            y = cy + dy
            if y < 0 or y >= self.h:
                continue
            half = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline(cx - half, cx + half, y, color)

    def fill_ellipse(self, cx, cy, rx, ry, color):
        for dy in range(-int(ry), int(ry) + 1):
            y = cy + dy
            if y < 0 or y >= self.h:
                continue
            t = 1.0 - (dy * dy) / float(ry * ry)
            half = int(rx * math.sqrt(max(0.0, t)))
            self.hline(cx - half, cx + half, y, color)

    def fill_ellipse_alpha(self, cx, cy, rx, ry, color, alpha):
        for dy in range(-int(ry), int(ry) + 1):
            y = cy + dy
            if y < 0 or y >= self.h:
                continue
            t = 1.0 - (dy * dy) / float(ry * ry)
            half = int(rx * math.sqrt(max(0.0, t)))
            self.hline_alpha(cx - half, cx + half, y, color, alpha)

    def fill_poly(self, pts, color):
        """Scanline fill of a simple polygon (list of (x, y))."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(math.ceil(min(ys))))
        y1 = min(self.h - 1, int(math.floor(max(ys))))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y - y1p) / float(y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(xs[k], xs[k + 1], y, color)

    def thick_line(self, x0, y0, x1, y1, width, color):
        """A stroked segment with round caps, drawn as a polygon + circles."""
        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        r = width / 2.0
        if length < 0.5:
            self.fill_circle(int(round(x0)), int(round(y0)), int(math.ceil(r)), color)
            return
        nx = -dy / length * r
        ny = dx / length * r
        poly = [
            (x0 + nx, y0 + ny),
            (x1 + nx, y1 + ny),
            (x1 - nx, y1 - ny),
            (x0 - nx, y0 - ny),
        ]
        self.fill_poly(poly, color)
        self.fill_circle(int(round(x0)), int(round(y0)), int(math.ceil(r)), color)
        self.fill_circle(int(round(x1)), int(round(y1)), int(math.ceil(r)), color)

    def glow(self, cx, cy, radius, color, peak):
        """Additive radial glow, bounded to a square around (cx, cy)."""
        r2 = radius * radius
        for dy in range(-radius, radius + 1):
            y = cy + dy
            if y < 0 or y >= self.h:
                continue
            half = int(math.sqrt(max(0, r2 - dy * dy)))
            for x in range(max(0, cx - half), min(self.w - 1, cx + half) + 1):
                dx = x - cx
                d2 = dx * dx + dy * dy
                if d2 >= r2:
                    continue
                t = 1.0 - math.sqrt(d2) / radius
                self.blend(x, y, color, peak * t * t)


def sample_stops(stops, y):
    if y <= stops[0][0]:
        return stops[0][1:]
    for i in range(1, len(stops)):
        y0 = stops[i - 1][0]
        y1 = stops[i][0]
        if y <= y1:
            t = (y - y0) / float(y1 - y0)
            a = stops[i - 1][1:]
            b = stops[i][1:]
            return tuple(int(a[c] + (b[c] - a[c]) * t + 0.5) for c in range(3))
    return stops[-1][1:]


# ------------------------------------------------------- geometric type
# Each glyph: segments on a 10 x 14 grid (x 0..10, y 0..14, y down).
# Single-stroke deco capitals, drawn with thick lines.
GLYPHS = {
    "A": [((1, 14), (5, 0)), ((5, 0), (9, 14)), ((3.2, 9), (6.8, 9))],
    "B": [((1, 0), (1, 14)),
          ((1, 0), (6, 0)), ((6, 0), (8.5, 2)), ((8.5, 2), (8.5, 5)),
          ((8.5, 5), (6, 7)), ((6, 7), (1, 7)),
          ((1, 7), (6, 7)), ((6, 7), (8.5, 9.5)), ((8.5, 9.5), (8.5, 12)),
          ((8.5, 12), (6, 14)), ((6, 14), (1, 14))],
    "E": [((1, 0), (1, 14)), ((1, 0), (9, 0)), ((1, 7), (7, 7)),
          ((1, 14), (9, 14))],
    "F": [((1, 0), (1, 14)), ((1, 0), (9, 0)), ((1, 7), (7, 7))],
    "H": [((1, 0), (1, 14)), ((9, 0), (9, 14)), ((1, 7), (9, 7))],
    "I": [((2, 0), (8, 0)), ((5, 0), (5, 14)), ((2, 14), (8, 14))],
    "L": [((1, 0), (1, 14)), ((1, 14), (9, 14))],
    "M": [((1, 14), (1, 0)), ((1, 0), (5, 8)), ((5, 8), (9, 0)),
          ((9, 0), (9, 14))],
    "N": [((1, 14), (1, 0)), ((1, 0), (9, 14)), ((9, 14), (9, 0))],
    "O": [((5, 0), (8, 1)), ((8, 1), (9, 4)), ((9, 4), (9, 10)),
          ((9, 10), (8, 13)), ((8, 13), (5, 14)), ((5, 14), (2, 13)),
          ((2, 13), (1, 10)), ((1, 10), (1, 4)), ((1, 4), (2, 1)),
          ((2, 1), (5, 0))],
    "R": [((1, 0), (1, 14)),
          ((1, 0), (6, 0)), ((6, 0), (8.5, 2)), ((8.5, 2), (8.5, 5)),
          ((8.5, 5), (6, 7)), ((6, 7), (1, 7)),
          ((5.5, 7), (9, 14))],
    "S": [((8, 1), (3, 1)), ((3, 1), (1, 3)), ((1, 3), (1, 5)),
          ((1, 5), (3, 7)), ((3, 7), (7, 7)), ((7, 7), (9, 9)),
          ((9, 9), (9, 11)), ((9, 11), (7, 13)), ((7, 13), (2, 13))],
    "T": [((1, 0), (9, 0)), ((5, 0), (5, 14))],
    "V": [((1, 0), (5, 14)), ((5, 14), (9, 0))],
}
ADVANCE = 12.0   # grid units per letter
SPACE_ADVANCE = 7.0


def text_width(text, unit):
    w = 0.0
    for ch in text:
        w += SPACE_ADVANCE if ch == " " else ADVANCE
    return w * unit


def draw_text(cv, text, cx, top, cap_height, color, stroke_units=1.8):
    unit = cap_height / 14.0
    width = text_width(text, unit)
    x = cx - width / 2.0
    wpx = stroke_units * unit
    for ch in text:
        if ch == " ":
            x += SPACE_ADVANCE * unit
            continue
        for (ax, ay), (bx, by) in GLYPHS[ch]:
            cv.thick_line(x + ax * unit, top + ay * unit,
                          x + bx * unit, top + by * unit, wpx, color)
        x += ADVANCE * unit


# ---------------------------------------------------------------- scene
def draw_sky(cv):
    cv.vgrad(0, 780, SKY_STOPS)


def draw_clouds(cv):
    # Soft horizontal bands, warm cream / rose, low alpha.
    cv.fill_ellipse_alpha(300, 168, 210, 26, (255, 214, 170), 0.16)
    cv.fill_ellipse_alpha(360, 176, 150, 18, (255, 214, 170), 0.12)
    cv.fill_ellipse_alpha(780, 310, 220, 20, (244, 178, 150), 0.14)
    cv.fill_ellipse_alpha(700, 318, 140, 14, (244, 178, 150), 0.10)
    cv.fill_ellipse_alpha(180, 330, 170, 18, (255, 196, 150), 0.10)


def draw_sun(cv):
    cv.glow(350, 612, 230, SUN_GLOW, 0.5)
    cv.fill_circle(350, 612, 58, SUN_CORE)
    cv.fill_circle(350, 612, 46, (255, 250, 220))


def draw_birds(cv):
    for (bx, by, s) in [(140, 300, 10), (205, 342, 8), (860, 292, 9),
                        (912, 342, 8), (742, 330, 7)]:
        cv.thick_line(bx - s, by, bx, by + s * 0.45, 3, (46, 26, 52))
        cv.thick_line(bx, by + s * 0.45, bx + s, by, 3, (46, 26, 52))


def island_body(cv, top_pts, bottom_pts, face_pts):
    """A floating island: dark body, lighter face, warm rim on top."""
    body = top_pts + bottom_pts
    cv.fill_poly(body, ISLE_DARK)
    if face_pts:
        cv.fill_poly(face_pts, ISLE_FACE)
    # Warm rim light along the top edge.
    for i in range(len(top_pts) - 1):
        (x0, y0), (x1, y1) = top_pts[i], top_pts[i + 1]
        cv.thick_line(x0, y0, x1, y1, 5, RIM)


def dissolve(cv, x0, x1, y_top, y_bot):
    """Fade a waterfall's lower end into mist with pale strips."""
    span = 48
    for y in range(max(y_top, y_bot - span), y_bot + 1):
        t = (y - (y_bot - span)) / float(span)
        cv.hline_alpha(x0, x1, y, MIST, 0.85 * t)


def waterfall(cv, wx, wy, ww, y_bot):
    """A gently curving fall ribbon that dissolves into mist."""
    left = []
    right = []
    steps = 8
    for k in range(steps + 1):
        y = wy + (y_bot - wy) * k / steps
        bend = 4.0 * math.sin((y - wy) / 90.0)
        left.append((wx + bend, y))
        right.append((wx + ww + bend, y))
    cv.fill_poly(left + right[::-1], FALL)
    dissolve(cv, wx - 2, wx + ww + 2, y_bot - 48, y_bot)


def draw_main_isle(cv):
    top = [(430, 432), (470, 406), (560, 398), (660, 400), (740, 416),
           (768, 444)]
    face = [(470, 406), (560, 398), (640, 400), (620, 440), (500, 440)]
    island_body(cv, top, [(652, 592), (600, 648), (545, 595)], face)
    # Lighthouse on the plateau.
    cv.fill_rect(682, 352, 698, 404, CREAM)
    cv.fill_rect(678, 344, 702, 354, ISLE_DARK)
    cv.fill_circle(690, 340, 6, SUN_CORE)
    # Two small trees.
    for (tx, ty, s) in [(500, 400, 16), (540, 396, 13), (620, 398, 15)]:
        cv.fill_poly([(tx - s, ty), (tx, ty - s * 1.6), (tx + s, ty)],
                     (30, 66, 44))
        cv.fill_rect(tx - 2, ty, tx + 2, ty + 6, (46, 26, 52))
    # Waterfalls off both edges, dissolving into mist.
    for (wx, wy, ww) in [(454, 452, 10), (744, 448, 9)]:
        waterfall(cv, wx, wy, ww, 700)


def draw_left_isle(cv):
    top = [(180, 376), (220, 356), (300, 350), (360, 362), (384, 384)]
    island_body(cv, top, [(315, 518), (282, 562), (250, 520)], None)
    # Tiny pavilion, clear of the subtitle.
    cv.fill_rect(258, 328, 306, 352, CREAM)
    cv.fill_poly([(252, 330), (282, 312), (312, 330)], (120, 40, 60))
    cv.fill_rect(278, 336, 286, 352, ISLE_DARK)
    # One waterfall, dissolving into mist.
    waterfall(cv, 198, 388, 10, 700)


def draw_right_islet(cv):
    top = [(820, 470), (860, 452), (920, 452), (950, 470)]
    island_body(cv, top, [(912, 542), (885, 578), (858, 540)], None)
    cv.fill_poly([(872, 452), (885, 430), (898, 452)], (30, 66, 44))


def draw_mist(cv):
    for y in range(688, 762):
        t = (y - 688) / 74.0
        alpha = 0.26 * math.sin(math.pi * min(1.0, max(0.0, t)))
        cv.hline_alpha(0, W - 1, y, MIST, alpha)


def draw_sea(cv):
    for y in range(740, H):
        t = (y - 740) / float(H - 740)
        c = tuple(int(SEA_TOP[i] + (SEA_BOT[i] - SEA_TOP[i]) * t + 0.5)
                  for i in range(3))
        cv.hline(0, W - 1, y, c)
    # Warm horizon band.
    for y in range(740, 772):
        t = (y - 740) / 32.0
        alpha = 0.55 * (1.0 - t)
        cv.hline_alpha(0, W - 1, y, HORIZON, alpha)
    # Sun reflection column: shimmering dashes under the sun.
    for i, y in enumerate(range(782, 1000, 16)):
        w = 70 + (i % 4) * 30
        x0 = 350 - w // 2 + ((i * 37) % 41) - 20
        cv.hline_alpha(x0, x0 + w, y, (246, 212, 124),
                       max(0.08, 0.46 - (y - 782) * 0.0016))
    # Gentle wave lines.
    for y in (830, 880, 930, 980):
        cv.hline_alpha(60, 964, y, (120, 190, 180), 0.10)


def draw_frame(cv):
    cv.fill_rect(26, 26, W - 26, 28, FRAME)
    cv.fill_rect(26, H - 28, W - 26, H - 26, FRAME)
    cv.fill_rect(26, 26, 28, H - 26, FRAME)
    cv.fill_rect(W - 28, 26, W - 26, H - 26, FRAME)
    cv.fill_rect(40, 40, W - 40, 41, FRAME)
    cv.fill_rect(40, H - 41, W - 40, H - 40, FRAME)
    cv.fill_rect(40, 40, 41, H - 40, FRAME)
    cv.fill_rect(W - 41, 40, W - 40, H - 40, FRAME)


def render():
    cv = Canvas(W, H)
    draw_sky(cv)
    draw_clouds(cv)
    draw_sun(cv)
    draw_birds(cv)
    draw_left_isle(cv)
    draw_main_isle(cv)
    draw_right_islet(cv)
    draw_mist(cv)
    draw_sea(cv)
    # Title: plum shadow 6 px below, then cream on top.
    draw_text(cv, "VELMORA", 512, 118, 116, SHADOW, 1.8)
    draw_text(cv, "VELMORA", 512, 112, 116, CREAM, 1.8)
    draw_text(cv, "ISLES OF THE AMBER SEA", 512, 252, 34, CREAM, 1.8)
    draw_frame(cv)
    return cv


# ---------------------------------------------------------------- png
def encode_png(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(1)  # Sub filter
        row = cv.px[y * stride:(y + 1) * stride]
        prev = 0
        for i, b in enumerate(row):
            left = row[i - 3] if i >= 3 else 0
            raw.append((b - left) & 0xFF)
    data = zlib.compress(bytes(raw), 6)

    def chunk(kind, payload):
        out = struct.pack(">I", len(payload)) + kind + payload
        out += struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", data) + chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = render()
    png = encode_png(cv)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s (%d bytes, %dx%d)" % (path, len(png), W, H))


if __name__ == "__main__":
    main()
