"""
theme_default_cud.py — I LOVE ISHIDO デフォルトテーマ CUD版

theme_default の描画コードをそのまま使い、
石カラー（10〜15）のみ色覚多様性（CUD）対応色に差し替える。

変更点（石カラーのみ）:
  11: 青   #4444cc → オレンジ #cc7733（赤緑混同を避ける暖色代替）
  13: 緑   #44cc44 → 深緑   #339944（P型・D型での赤緑混同を軽減）
  15: 水色 #44cccc → プラチナ #aab4b8（青系とは別の無彩色系）

UI カラー（0〜9）はデフォルトと同一。
"""

import pyxel
from theme_default import (
    draw_board_frame,
    get_cell_color,
    draw_cell_bg,
    draw_stone,
    draw_joker_stone,
    get_initial_bag,
)

PALETTE = [
    0x000000, 0xffffff, 0x222222, 0x444444,  # 0〜3
    0x666666, 0x888888, 0x999999, 0xaaaaaa,  # 4〜7
    0xbbbbbb, 0xcccccc, 0xcc4444, 0xcc7733,  # 8〜11 赤・オレンジ
    0xcccc44, 0x339944, 0xcc44cc, 0xaab4b8,  # 12〜15 黄・深緑・紫・プラチナ
]


def setup_palette():
    """CUD 対応パレットを pyxel に設定する。"""
    for i, c in enumerate(PALETTE):
        pyxel.colors[i] = c
