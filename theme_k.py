"""
theme_k.py — I LOVE ISHIDO 宝石型＋漢数字テーマ
"""
import pyxel
import random

PALETTE = [
    0x000000, 0xffffff, 0x1c0e04, 0x3d2309,  # 0〜3  墨〜濃茶
    0x634020, 0x8b5e35, 0xa87c52, 0xc9a478,  # 4〜7  中茶〜淡茶
    0xdfc09a, 0xf2e2cc, 0xcc4444, 0x4444cc,  # 8〜9 生成(ベージュ) / 10〜11 赤・青
    0xcccc44, 0x44cc44, 0xcc44cc, 0x44cccc,  # 12〜15 黄・緑・紫・水色
]

_KANJI_BITS = {
    1: ["XXXXXXXX.", ".XXXXXXXX"],
    2: [".XXXXX...", "..XXXXX..", ".........", "XXXXXXXX.", ".XXXXXXXX"],
    3: ["XXXXX..", ".XXXXX.", ".......", "XXXX...", ".XXXX..", ".......", "XXXXXX.", ".XXXXXX"],
    4: ["XXXXXXXX", "X.X.X.XX", "X.X.X.XX", "X.X.X.XX", "XXX.XXXX", "XX....XX", "XXXXXXXX"],
    5: ["..XXXXX..", "...XXXXX.", "....XX...", ".XXXXXXXX", "..XXXXXX.", "...XX.XX.", "XXXXXXXXX", ".XXXXXXXX"],
    6: ["....XX....", ".XXXXXXX..", "..XXXXXXX.", "..........", "..XX.XX...", ".XX...XXX.", "XXX....XXX"]
}

_MODERN_STONE_BITS = [
    "......RRRR......",
    "....RRRRRRRR....",
    "...RRRRHHHRRR...",
    "..RRRHRHHHHRRR..",
    "..RRHRHHHHHHRR..",
    ".RRRHRHHHHHHRRR.",
    ".RRHRHHHHHHHHRR.",
    ".RRHRHHHHHHHHRR.",
    "RRHRHHHHHHHHHHRR",
    "RRHRHHHHHHHHHHRR",
    "RRRHHHHHHHHHHHRR",
    "RRHHHHHHHHHHHHRR",
    "RRHHHHHHHHHHHRRR",
    "RRHHHHHHHHHHHRRR",
    "RRHHHHHHHHHHRHRR",
    "RRHHHHHHHHHHRHRR",
    ".RRHHHHHHHHRHRR.",
    ".RRHHHHHHHHRHRR.",
    ".RRRHHHHHHHRHRR.",
    "..RRHHHHHHRHRR..",
    "..RRRHHHHHRRRR..",
    "...RRRHHHRRRR...",
    "....RRRRRRRR....",
    "......RRRR......"
]

_CENTER_DARK = frozenset({(5, 4), (6, 3)})

def setup_palette():
    for i, c in enumerate(PALETTE):
        pyxel.colors[i] = c

def draw_board_frame(fx, fy, fw, fh):
    pyxel.rect(fx,     fy,     fw,     fh,     3)
    pyxel.rect(fx,     fy,     fw - 2, fh - 2, 7)
    pyxel.rect(fx + 2, fy + 2, fw - 4, fh - 4, 5)

def get_cell_color(x, y):
    return 8 if _is_light_cell(x, y) else 7

def draw_cell_bg(bx, by, x, y):
    is_light = _is_light_cell(x, y)
    wood_col  = 6
    cloth_col = 9 if is_light else 8
    pyxel.rect(bx,     by,     16, 24, wood_col)
    pyxel.rect(bx + 1, by + 1, 14, 22, cloth_col)
    deco_col = 12
    pyxel.pset(bx + 2, by + 2, deco_col); pyxel.pset(bx + 3, by + 2, deco_col); pyxel.pset(bx + 2, by + 3, deco_col)
    pyxel.pset(bx + 13, by + 2, deco_col); pyxel.pset(bx + 12, by + 2, deco_col); pyxel.pset(bx + 13, by + 3, deco_col)
    pyxel.pset(bx + 2, by + 21, deco_col); pyxel.pset(bx + 3, by + 21, deco_col); pyxel.pset(bx + 2, by + 20, deco_col)
    pyxel.pset(bx + 13, by + 21, deco_col); pyxel.pset(bx + 12, by + 21, deco_col); pyxel.pset(bx + 13, by + 20, deco_col)

def _is_light_cell(x, y):
    is_inner = 1 <= x <= 10 and 1 <= y <= 6
    if (x, y) in _CENTER_DARK:
        return False
    return is_inner

def draw_stone(x, y, color_id, number):
    stone_col = 9 + color_id
    _draw_modern_base(x, y, stone_col)
    _draw_kanji(x, y, number, 0)

def draw_joker_stone(x, y, mode):
    if mode == "C":
        stone_col = 10 + (pyxel.frame_count // 4) % 6
    elif mode == "N":
        stone_col = 0 if (pyxel.frame_count // 4) % 2 == 0 else 5
    else:
        stone_col = 7
    _draw_modern_base(x, y, stone_col, is_joker_c=(mode=="C"))
    if mode == "N":
        pyxel.text(x + 6, y + 9, "?", 0)

def _draw_modern_base(x, y, stone_col, is_joker_c=False):
    high_col = 1
    h, w = len(_MODERN_STONE_BITS), len(_MODERN_STONE_BITS[0])
    start_x, start_y = x + (16 - w) // 2, y + (24 - h) // 2
    for r, line in enumerate(_MODERN_STONE_BITS):
        for c, ch in enumerate(line):
            if ch == ".": continue
            cur_col = stone_col
            if is_joker_c and ch == "R":
                cur_col = 10 + ((pyxel.frame_count // 4 + r) % 6)
            if ch == "R":
                pyxel.pset(start_x + c, start_y + r, cur_col)
            elif ch == "H":
                pyxel.pset(start_x + c, start_y + r, high_col)

def _draw_kanji(bx, by, number, col):
    rows = _KANJI_BITS.get(number, [])
    if not rows: return
    h, w = len(rows), len(rows[0])
    start_x, start_y = bx + (16 - w) // 2, by + (24 - h) // 2
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == "X": pyxel.pset(start_x + c, start_y + r, col)

def get_initial_bag():
    bag = []
    for c in range(1, 7):
        for n in range(1, 7):
            bag.extend([(c, n), (c, n)])
    random.shuffle(bag)
    return bag
