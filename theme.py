"""
theme.py — I LOVE ISHIDO テーマ管理モジュール
"""
import theme_default
import theme_k

# 初期テーマはデフォルトを設定
_current = theme_default

def switch():
    """テーマを切り替え、パレットを即座に更新する"""
    global _current
    _current = theme_k if _current == theme_default else theme_default
    _current.setup_palette()

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
