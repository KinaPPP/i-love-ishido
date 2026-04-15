"""
theme_k_cud.py — I LOVE ISHIDO 漢字テーマ CUD版

theme_k の描画コードをそのまま使い、
石カラー（10〜15）のみ色覚多様性（CUD）対応色に差し替える。

変更点（石カラーのみ）:
  11: 青   #4444cc → オレンジ #cc7733
  13: 緑   #44cc44 → 深緑   #339944
  15: 水色 #44cccc → プラチナ #aab4b8

UI カラー（0〜9）は漢字テーマの茶系グラデーションと同一。
"""

import pyxel
from theme_k import (
    draw_board_frame,
    get_cell_color,
    draw_cell_bg,
    draw_stone,
    draw_joker_stone,
    get_initial_bag,
)

PALETTE = [
    0x000000, 0xffffff, 0x1c0e04, 0x3d2309,  # 0〜3  墨〜濃茶
    0x634020, 0x8b5e35, 0xa87c52, 0xc9a478,  # 4〜7  中茶〜淡茶
    0xdfc09a, 0xf2e2cc, 0xcc4444, 0xcc7733,  # 8〜11 赤・オレンジ
    0xcccc44, 0x339944, 0xcc44cc, 0xaab4b8,  # 12〜15 黄・深緑・紫・プラチナ
]


def setup_palette():
    """CUD 対応パレットを pyxel に設定する。"""
    for i, c in enumerate(PALETTE):
        pyxel.colors[i] = c
