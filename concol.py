from functools import lru_cache
from PIL import Image
import sys
import itertools
import math
import random
from collections import defaultdict
from tables import GAMMA

if sys.platform == "win32":
    import msvcrt
    from ctypes import windll

    stdout_handle = windll.kernel32.GetStdHandle(-11)

CONSOLE_COLORS = GAMMA

CONSOLE_CHAR_BLENDS = {
    0.00: " ",  # Space, but you already know that
    0.25: "\u2591",  # LIGHT SHADE
    0.50: "\u2592",  # MEDIUM SHADE
    0.75: "\u2593",  # DARK SHADE
    1.00: "\u2588",  # FULL BLOCK
}


def unpack_color(color):
    return (color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF)


def lerp(a, b, alpha):
    return int(a * (1.0 - alpha) + b * alpha)


def rgb_dist(a, b):
    # nb: this is euclidean distance ^ 2 -- for our use case (sorting)
    #     there's no reason to spend cycles doing the square root
    r0, g0, b0 = a
    r1, g1, b1 = b
    return ((r0 - r1) ** 2 + (g0 - g1) ** 2 + (b0 - b1) ** 2)


def get_blend_colors():
    colors = defaultdict(list)
    for fg, bg in itertools.combinations(CONSOLE_COLORS, 2):
        fg_rgb = unpack_color(CONSOLE_COLORS[fg])
        bg_rgb = unpack_color(CONSOLE_COLORS[bg])
        for blend_amt, blend_char in CONSOLE_CHAR_BLENDS.items():
            blended_color = tuple(lerp(bgc, fgc, blend_amt) for (fgc, bgc) in zip(fg_rgb, bg_rgb))
            colors[blended_color].append((fg, bg, blend_char))
    return colors


def set_color(fg, bg):
    if sys.platform == "win32":
        color = (bg << 4 | fg)
        windll.kernel32.SetConsoleTextAttribute(stdout_handle, color)
    else:
        raise NotImplementedError("Ni!")


def write(ch, fg=None, bg=None):
    if fg is not None and bg is not None:
        set_color(fg, bg)
    if sys.platform == "win32":
        msvcrt.putwch(ch)
    else:
        sys.stdout.write(ch)


class Palette(object):
    def __init__(self, blend_map, dither):
        self.blend_map = blend_map
        self.dither = dither
        if self.dither:
            self.get_color = lru_cache()(self._get_color_slow)
        else:
            self.get_color = lru_cache()(self._get_color_fast)

    def get_color(self, px):
        raise NotImplementedError("will be replaced during init")

    def _get_color_fast(self, px):
        best_dst = 16777216
        best_e = None
        for (pal_rgb, pal_e) in self.blend_map.items():
            dst = rgb_dist(px, pal_rgb)
            if dst < best_dst:
                best_dst = dst
                best_e = pal_e
                if best_dst < 10:
                    break
        return best_e[0]

    def _get_color_slow(self, px):
        distances = [(rgb_dist(px, pal_c), pal_e) for (pal_c, pal_e) in self.blend_map.items()]
        distances.sort()
        if self.dither:
            d0, d1 = distances[0][0], distances[1][0]
            idx = 0 if random.uniform(d0, d1) <= (d0 + d1) / 2 else 1
        else:
            idx = 0
        return distances[idx][1][0]


def main(dither=False):
    img = Image.open("lenna.png")
    aspect = 1.5
    width = 75
    img = img.resize((int(width), int(width / aspect)), Image.ANTIALIAS)
    width, height = img.size

    blend_map = get_blend_colors()
    palette = Palette(blend_map, dither=dither)

    data = img.load()
    for y in range(height):
        for x in range(width):
            fg_c, bg_c, char = palette.get_color(data[x, y])
            # px = data[(x, y)]
            # distances = [(tup_dist(px, pal_c), pal_e) for (pal_c, pal_e) in blend_map.items()]
            # distances.sort()
            # if dither:
            #     d0, d1 = distances[0][0], distances[1][0]
            #     idx = 0 if random.uniform(d0, d1) <= (d0 + d1) / 2 else 1
            # else:
            #     idx = 0
            # fg_c, bg_c, char = distances[idx][1][0]
            write(char, fg=fg_c, bg=bg_c)
        write("\n")


if __name__ == "__main__":
    main()
