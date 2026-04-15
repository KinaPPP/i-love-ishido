"""
theme_s.py — I LOVE ISHIDO 海テーマ（Sea）

深海から浅瀬への青系グラデーションUI ＋ CUD対応石カラー。
巻貝＋金貨袋型コマ、ローマ数字（I〜VI）刻印。

石カラー（パレット10〜15）:
  10: 赤  #cc4444  ← デフォルト据え置き
  11: オレンジ #cc7733  ← 青の代替（CUD対応）
  12: 黄  #cccc44  ← デフォルト据え置き
  13: 深緑 #339944  ← 明緑の代替（海藻）
  14: 紫  #cc44cc  ← デフォルト据え置き
  15: シルバー #aab4b8 ← 砂金→真珠シルバーに変更（白との差を確保）
"""

import pyxel
import random

# ------------------------------------------------------------------ #
#  パレット定義
#  0〜1  : 黒・白（変更なし）
#  2〜9  : 深海→浅瀬グラデーション（UI・盤面用）
#  10〜15: 石カラー（CUD対応）
# ------------------------------------------------------------------ #
PALETTE = [
    0x000000, 0xffffff, 0x020810, 0x041428,  # 0〜3  黒〜深海
    0x082040, 0x103060, 0x1a4878, 0x286090,  # 4〜7  深青〜中青
    0x3c7aaa, 0x5898c0, 0xcc4444, 0xcc7733,  # 8〜9  浅青 / 10〜11 赤・オレンジ
    0xcccc44, 0x339944, 0xcc44cc, 0xaab4b8,  # 12〜15 黄・深緑・紫・シルバー（真珠）
]

_CORNERS     = frozenset({(0, 0), (11, 0), (0, 7), (11, 7)})
_CENTER_DARK = frozenset({(5, 4), (6, 3)})

# ------------------------------------------------------------------ #
#  石ピクセルデータ（EDGE1.bmp から抽出、16×24）
#  W = 白ハイライト（color 1）
#  C = 石カラー（stone_col）
#  . = スキップ（背景を透過）
# ------------------------------------------------------------------ #
_STONE_PIXELS = [
    ".....WWWWWW.....",   # y= 0: 巻貝トップ
    "....WWCCCCCW....",   # y= 1
    "....WCWWCCCCW...",   # y= 2
    "...WCCCCWCCCCW..",   # y= 3
    "...WCCCCCWWWCW..",   # y= 4
    "..WCCCCCCCCCW...",   # y= 5
    "..WWCCWWWWWW....",   # y= 6
    "..WCWWWCCW......",   # y= 7
    "..WCCCCWWWW.....",   # y= 8
    ".WCCCWWCCCCWW...",   # y= 9
    ".WCCWCCCCCWCCW..",   # y=10
    ".WCCCCCCCCCCCCW.",   # y=11
    "WCCCCCCCCCCCCCW.",   # y=12: 巻貝ボトム
    "WCCCCCCCCCCCCCCW",   # y=13: 袋エリア開始（クリーン）
    "WCCCCCCCCCCCCCCW",   # y=14
    "WCCCCCCCCCCCCCCW",   # y=15
    "WCCCCCCCCCCCCCCW",   # y=16
    "WCCCCCCCCCCCCCCW",   # y=17
    "WCCCCCCCCCCCCCCW",   # y=18
    "WCCCCCCCCCCCCCCW",   # y=19
    "WCCCCCCCCCCCCCCW",   # y=20: 袋エリア終了
    ".WCCCCCCCCCCCCW.",   # y=21
    "..WWCCCCCCCCWW..",   # y=22
    "....WWWWWWWW....",   # y=23
]

# ------------------------------------------------------------------ #
#  ローマ数字グリフ（roman.bmp から抽出）
#  W = 白ピクセル, . = 透明
#  I=3×6, II=6×6, III=7×6, IV=8×6, V=8×6, VI=8×6
# ------------------------------------------------------------------ #
_ROMAN_GLYPHS = {
    1: ["WWWW",        # I: 4×8, 2pxストローク＋上下セリフ
        ".WW.",
        ".WW.",
        ".WW.",
        ".WW.",
        ".WW.",
        ".WW.",
        "WWWW"],
    2: ["WWWWWWW",     # II: 7×8, 2本2pxストローク＋共通セリフ
        ".WW.WW.",
        ".WW.WW.",
        ".WW.WW.",
        ".WW.WW.",
        ".WW.WW.",
        ".WW.WW.",
        "WWWWWWW"],
    3: ["WWWWWWWWWW",  # III: 10×8, 3本2pxストローク＋共通セリフ
        ".WW.WW.WW.",
        ".WW.WW.WW.",
        ".WW.WW.WW.",
        ".WW.WW.WW.",
        ".WW.WW.WW.",
        ".WW.WW.WW.",
        "WWWWWWWWWW"],
    4: ["WWWWWWWWWWW",  # IV: VIを水平反転（I左・V右）= 11×8
        "WW.WW....WW",
        "WW.WW....WW",
        "WW..WW..WW.",
        "WW..WW..WW.",
        "WW...WWWW..",
        "WW...WWWW..",
        "WW....WW..."],
    5: ["WW....WW",    # V: 8×8, 2pxストローク収束V字
        "WW....WW",
        ".WW..WW.",
        ".WW..WW.",
        "..WWWW..",
        "..WWWW..",
        "...WW...",
        "...WW..."],
    6: ["WWWWWWWWWWW",  # VI: 11×8, V(8px)+I(2px)
        "WW....WW.WW",
        "WW....WW.WW",
        ".WW..WW..WW",
        ".WW..WW..WW",
        "..WWWW...WW",
        "..WWWW...WW",
        "...WW....WW"],
}

# ------------------------------------------------------------------ #
#  テーマ初期化
# ------------------------------------------------------------------ #

def setup_palette():
    """海系パレットを pyxel に設定する。起動時に 1 回呼ぶ。"""
    for i, c in enumerate(PALETTE):
        pyxel.colors[i] = c


# ------------------------------------------------------------------ #
#  盤面描画
# ------------------------------------------------------------------ #

def draw_board_frame(fx, fy, fw, fh):
    """盤面外枠を深海木箱風ベベルで描画する。"""
    pyxel.rect(fx,     fy,     fw,     fh,     3)   # 深海（影）
    pyxel.rect(fx,     fy,     fw - 2, fh - 2, 7)   # 中青（ハイライト）
    pyxel.rect(fx + 2, fy + 2, fw - 4, fh - 4, 5)   # 深青（パネル面）


def get_cell_color(x, y):
    """セル背景色を返す（後方互換用）。"""
    return 8 if _is_light_cell(x, y) else 7


def draw_cell_bg(bx, by, x, y):
    """空きセルを深海砂地風で描画する。
    明るいセル: 浅青（col 8）+ 砂粒ハイライト
    暗いセル  : 中青（col 7）
    """
    is_light = _is_light_cell(x, y)
    base_col  = 8 if is_light else 7

    pyxel.rect(bx, by, 16, 24, base_col)

    if is_light:
        # 砂粒をドット3点でアクセント（位置は固定・座標から決定論的に）
        seed = (x * 7 + y * 13) & 0xFF
        for i in range(3):
            dx = (seed * (i + 1) * 5) % 12 + 2
            dy = (seed * (i + 1) * 3) % 20 + 2
            pyxel.pset(bx + dx, by + dy, 9)  # 浅青より明るい点


def _is_light_cell(x, y):
    is_inner  = 1 <= x <= 10 and 1 <= y <= 6
    is_corner = (x, y) in _CORNERS
    is_c_dark = (x, y) in _CENTER_DARK
    return (is_inner or is_corner) and not is_c_dark


# ------------------------------------------------------------------ #
#  石・ジョーカー石の描画
# ------------------------------------------------------------------ #

def draw_stone(x, y, color_id, number):
    """巻貝＋金貨袋型の石を描画する。
    color_id: 1〜6（パレット 10〜15 に対応）
    number  : 1〜6（ローマ数字 I〜VI）
    """
    stone_col = 9 + color_id
    _draw_stone_base(x, y, stone_col)
    _draw_roman(x, y, number, stone_col)


def draw_joker_stone(x, y, mode):
    """ジョーカー石を描画する。
    mode: "C" → 石色が虹アニメーション（frame_count で色サイクル）
          "N" → 石色グレー（col 5）＋「?」白文字
          None → 石色を col 6（暗め）で無地
    """
    if mode == "C":
        stone_col = 10 + (pyxel.frame_count // 4) % 6
        _draw_stone_base(x, y, stone_col)
        # ハイライトを虹アニメで上書き（ライン走査）
        for row in range(24):
            for col in range(16):
                ch = _STONE_PIXELS[row][col]
                if ch == 'C':
                    cidx = (pyxel.frame_count // 4 + row) % 6
                    pyxel.pset(x + col, y + row, 10 + cidx)
    elif mode == "N":
        _draw_stone_base(x, y, 5)  # 暗青で無地袋
        # 「?」を袋エリア中央に描画（影付き）
        pyxel.text(x + 7, y + 17, "?", 4)  # 影
        pyxel.text(x + 6, y + 16, "?", 1)  # 白
    else:
        _draw_stone_base(x, y, 6)  # 中青で未選択


# ------------------------------------------------------------------ #
#  内部ヘルパー
# ------------------------------------------------------------------ #

def _draw_stone_base(x, y, stone_col):
    """_STONE_PIXELS を使って石の形を描画する。
    W → color 1（白ハイライト）
    C → stone_col
    . → スキップ（背景透過）
    """
    for row, line in enumerate(_STONE_PIXELS):
        for col, ch in enumerate(line):
            if ch == 'W':
                pyxel.pset(x + col, y + row, 1)
            elif ch == 'C':
                pyxel.pset(x + col, y + row, stone_col)


def _draw_roman(x, y, number, stone_col):
    """ローマ数字グリフを金貨袋エリア（y=13〜20）中央に描画する。
    EDGE0ベースなので袋エリアはクリーン。白抜き描画のみ。
    """
    glyph = _ROMAN_GLYPHS.get(number)
    if not glyph:
        return
    gw     = len(glyph[0])
    gh     = len(glyph)
    gx_off = (16 - gw) // 2    # 水平センタリング（14px袋内）
    gy_off = 13                  # 袋エリア先頭（8px分 y=13〜20 をフル活用）

    for r, row_str in enumerate(glyph):
        for c, ch in enumerate(row_str):
            if ch == 'W':
                pyxel.pset(x + gx_off + c, y + gy_off + r, 1)


# ------------------------------------------------------------------ #
#  石袋生成（テーマ共通）
# ------------------------------------------------------------------ #

def get_initial_bag():
    """色1〜6 × 数字1〜6 の組み合わせ × 2個 = 72個の袋を作成してシャッフル。"""
    bag = []
    for c in range(1, 7):
        for n in range(1, 7):
            bag.extend([(c, n), (c, n)])
    random.shuffle(bag)
    return bag
