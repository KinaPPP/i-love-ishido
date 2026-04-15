"""
theme.py — I LOVE ISHIDO テーマ管理モジュール

テーマ切り替え順（[T] キー）:
  DEFAULT → KANJI → SEA → DEFAULT CUD → KANJI CUD → DEFAULT ...
"""

import theme_default
import theme_k
import theme_s
import theme_default_cud
import theme_k_cud

# テーマ切り替え順: 同デザインのCUD版を隣接させて比較しやすく
_THEMES = [theme_default, theme_default_cud, theme_k, theme_k_cud, theme_s]
_LABELS = ["DEFAULT", "DEFAULT CUD", "KANJI", "KANJI CUD", "SEA"]

# 初期テーマ
_current = theme_default


def switch():
    """テーマを順番に切り替え、パレットを即座に更新する。"""
    global _current
    idx = _THEMES.index(_current)
    _current = _THEMES[(idx + 1) % len(_THEMES)]
    _current.setup_palette()


def current_label():
    """現在のテーマ名を返す（タイトルバー表示用）。"""
    return _LABELS[_THEMES.index(_current)]


# --- 各モジュールから呼び出される共通インターフェース ---

def setup_palette():
    _current.setup_palette()

def draw_board_frame(fx, fy, fw, fh):
    _current.draw_board_frame(fx, fy, fw, fh)

def get_cell_color(x, y):
    return _current.get_cell_color(x, y)

def draw_cell_bg(bx, by, x, y):
    _current.draw_cell_bg(bx, by, x, y)

def draw_stone(x, y, color_id, number):
    _current.draw_stone(x, y, color_id, number)

def draw_joker_stone(x, y, mode):
    _current.draw_joker_stone(x, y, mode)

def get_initial_bag():
    return _current.get_initial_bag()
