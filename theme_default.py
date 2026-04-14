"""
theme_default.py — I LOVE ISHIDO デフォルトテーマ

パレット・盤面・石の描画を一括管理する。
別テーマを作る場合はこのファイルをコピーして改変し、
ishido.py の import 行を切り替えるだけで適用できる。

  import theme_default as theme   # デフォルト
  # import theme_k as theme       # 漢字テーマ（将来）
  # import theme_r as theme       # ローマ数字テーマ（将来）
"""

import pyxel

# ------------------------------------------------------------------ #
#  パレット定義
#  0〜9  : UI 系グレースケール
#  10〜15: 石のカラーパネル（赤・青・黄・緑・紫・水色）
# ------------------------------------------------------------------ #
PALETTE = [
    0x000000, 0xffffff, 0x222222, 0x444444,  # 0〜3
    0x666666, 0x888888, 0x999999, 0xaaaaaa,  # 4〜7
    0xbbbbbb, 0xcccccc, 0xcc4444, 0x4444cc,  # 8〜11
    0xcccc44, 0x44cc44, 0xcc44cc, 0x44cccc,  # 12〜15
]

# セルカラー定義（盤面描画で参照）
_CORNERS     = frozenset({(0, 0), (11, 0), (0, 7), (11, 7)})
_CENTER_DARK = frozenset({(5, 4), (6, 3)})   # 中央チェッカーの暗い対角

# ------------------------------------------------------------------ #
#  テーマ初期化
# ------------------------------------------------------------------ #

def setup_palette():
    """ゲーム用カラーパレットを pyxel に設定する。ゲーム起動時に1回呼ぶ。"""
    for i, c in enumerate(PALETTE):
        pyxel.colors[i] = c


# ------------------------------------------------------------------ #
#  盤面描画
# ------------------------------------------------------------------ #

def draw_board_frame(fx, fy, fw, fh):
    """盤面外枠をベベルスタイルで描画する。
    引数は外枠の左上座標と幅・高さ（ピクセル）。
    """
    pyxel.rect(fx,     fy,     fw,     fh,     2)  # 右・下の影
    pyxel.rect(fx,     fy,     fw - 2, fh - 2, 9)  # 左・上のハイライト
    pyxel.rect(fx + 2, fy + 2, fw - 4, fh - 4, 4)  # 中央パネル


def get_cell_color(x, y):
    """盤面セル（x, y）の背景色を返す。
    明るい（color 7）: 四隅・内側（x=1〜10, y=1〜6）・中央初期配置（5,3）(6,4)
    暗い  （color 6）: 外周リング・中央対角（5,4）(6,3)
    """
    is_inner  = 1 <= x <= 10 and 1 <= y <= 6
    is_corner = (x, y) in _CORNERS
    is_c_dark = (x, y) in _CENTER_DARK
    return 7 if (is_inner or is_corner) and not is_c_dark else 6


def draw_cell_bg(bx, by, x, y):
    """空きセルの背景を描画する（デフォルト: get_cell_color による単色矩形）。
    theme_k 等の別テーマではこの関数をオーバーライドして装飾を追加できる。
    """
    pyxel.rect(bx, by, 16, 24, get_cell_color(x, y))


# ------------------------------------------------------------------ #
#  石・ジョーカー石の描画
# ------------------------------------------------------------------ #

def draw_stone(x, y, color_id, number):
    """御札（通常石）を描画する。
    color_id: 1〜6（パレット 10〜15 に対応）
    number  : 1〜6
    """
    stone_col = 9 + color_id

    # 御札のベース（右・下に影、左・上にハイライト、表面グレー）
    pyxel.rect(x,     y,     16, 24, 2)   # 影
    pyxel.rect(x,     y,     15, 23, 9)   # ハイライト
    pyxel.rect(x + 1, y + 1, 14, 22, 7)  # 表面

    # 中央のカラーパネル
    pyxel.rect(x + 3, y + 3, 10, 18, stone_col)

    # 数字（パレット 1 番：白）
    s      = str(number)
    char_x = x + 6 if len(s) == 1 else x + 4
    pyxel.text(char_x, y + 5, s, 1)


def draw_joker_stone(x, y, mode):
    """ジョーカー石を描画する。
    mode: "C" → 虹色ラインが流れるカラーパネル
          "N" → グレーパネル＋「？」（影付き）
          None → のっぺらぼう（未選択状態）
    """
    # 御札のベース（通常石と同じ構造）
    pyxel.rect(x,     y,     16, 24, 2)   # 影
    pyxel.rect(x,     y,     15, 23, 9)   # ハイライト
    pyxel.rect(x + 1, y + 1, 14, 22, 7)  # 表面

    if mode == "C":
        # 虹色ライン: 上から下へ光が流れる（speed=3）
        _speed = 3
        for row in range(18):
            col_idx = ((pyxel.frame_count // _speed) + row) % 6
            pyxel.line(x + 3, y + 3 + row, x + 12, y + 3 + row, 10 + col_idx)
    elif mode == "N":
        # グレーパネル＋「？」（影付きで存在感を出す）
        pyxel.rect(x + 3, y + 3, 10, 18, 5)   # 暗めグレーパネル
        pyxel.text(x + 7, y + 10, "?", 2)     # 影（暗色）
        pyxel.text(x + 6, y + 9,  "?", 1)     # 白「？」
    else:
        # のっぺらぼう: 表面と同じグレーで無地
        pyxel.rect(x + 3, y + 3, 10, 18, 7)


# ------------------------------------------------------------------ #
#  石の袋生成（テーマ共通）
# ------------------------------------------------------------------ #

import random

def get_initial_bag():
    """色1〜6 × 数字1〜6 の組み合わせ × 2個 = 72個の袋を作成してシャッフル。"""
    bag = []
    for c in range(1, 7):
        for n in range(1, 7):
            bag.append((c, n))
            bag.append((c, n))
    random.shuffle(bag)
    return bag
