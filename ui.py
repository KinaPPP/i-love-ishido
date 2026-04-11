"""
ui.py — I LOVE ISHIDO UI描画モジュール

ゲームの描画補助メソッドを集約する。
ishido.py の Ishido クラスから `g`（ゲームインスタンス）を受け取り、
pyxel を直接呼び出す。副作用（状態の変更）は一切行わない。
"""

import pyxel
import math
import theme_default as theme

from constants import (
    BOARD_COLS, BOARD_ROWS, GAP_X, GAP_Y,
    MODE_ENDLESS, HINT_CYCLE, HINT_ACTIVE_FRAMES,
)

# ------------------------------------------------------------------ #
#  メッセージボックス共通ヘルパー（effect.py と同じ設計）
# ------------------------------------------------------------------ #
_BOX_TOP   = 100
_BOX_MG_Y  = 9
_LINE_H    = 11
_MIN_BW    = 144
_BOX_CX    = 128
_COL_N     = 5   # 通常（濃いグレー）
_COL_H     = 0   # ホバー（黒）

def _calc_box(lines):
    max_w = max((len(t)*4 for t,_ in lines), default=0) + 16
    bw    = max(max_w, _MIN_BW)
    bh    = _BOX_MG_Y + len(lines)*_LINE_H + _BOX_MG_Y
    bx    = _BOX_CX - bw//2
    return bx, _BOX_TOP, bw, bh

def _draw_frame(bx, by, bw, bh):
    pyxel.rect(bx,   by,   bw,   bh,   2)
    pyxel.rect(bx,   by,   bw-2, bh-2, 9)
    pyxel.rect(bx+2, by+2, bw-4, bh-4, 8)

def _ly(by, i):
    return by + _BOX_MG_Y + i * _LINE_H

def _tx(text):
    return _BOX_CX - len(text) * 2

def _hover(mx, my, tx, ty, text):
    return tx <= mx <= tx + len(text)*4 and ty <= my <= ty + 4


# ------------------------------------------------------------------ #
#  盤面・メイン描画
# ------------------------------------------------------------------ #

def draw_board(g):
    """盤面背景・外枠・セル・石を描画する。"""
    pyxel.cls(8)
    theme.draw_board_frame(
        g.offset_x - 4,
        g.offset_y - 4,
        BOARD_COLS * g.gap_x + 6,
        BOARD_ROWS * g.gap_y + 6,
    )
    for y in range(BOARD_ROWS):
        for x in range(BOARD_COLS):
            bx = g.offset_x + x * g.gap_x
            by = g.offset_y + y * g.gap_y
            pyxel.rect(bx, by, g.sw, g.sh, theme.get_cell_color(x, y))
            if g.board[y][x]:
                stone = g.board[y][x]
                if isinstance(stone, tuple) and stone[0] == "J":
                    theme.draw_joker_stone(bx, by, stone[1])
                else:
                    theme.draw_stone(bx, by, stone[0], stone[1])


def draw_cursor(g):
    """カーソルを描画する（置ける:白、置けない:赤）。"""
    is_ok = g.current_stone and g.is_placeable(g.cursor_x, g.cursor_y, g.current_stone)
    pyxel.rectb(
        g.offset_x + g.cursor_x * g.gap_x,
        g.offset_y + g.cursor_y * g.gap_y,
        g.sw, g.sh,
        1 if is_ok else 10
    )


def draw_info(g):
    """情報エリア（NEXT石・LEFT/SUB/LOOP/JOKER）を描画する。"""
    left = len(g.bag) + (1 if g.current_stone else 0)
    pyxel.text(g.offset_x, g.ui_row_y + 8, "NEXT:", 0)
    if g.current_stone:
        if isinstance(g.current_stone, tuple) and g.current_stone[0] == "J":
            theme.draw_joker_stone(g.offset_x + 25, g.ui_row_y, g.current_stone[1])
        else:
            theme.draw_stone(g.offset_x + 25, g.ui_row_y,
                             g.current_stone[0], g.current_stone[1])
    if g.game_mode == MODE_ENDLESS:
        pyxel.text(68,  g.ui_row_y + 2,  f"LEFT:{left:02}", 0)
        pyxel.text(72,  g.ui_row_y + 10, f"SUB:{len(g.sub_bag):02}", 0)
        pyxel.text(108, g.ui_row_y + 2,  f"LOOP:{g.loop_count}", 0)
        joker_col = 10 if g.joker_count > 0 else 0
        pyxel.text(108, g.ui_row_y + 10, f"JOKER:{g.joker_count}", joker_col)
    else:
        pyxel.text(68, g.ui_row_y + 8, f"LEFT: {left}", 0)
    return left


def draw_buttons(g):
    """ゲーム中のボタン行を描画する（J / U / H / R）。"""
    mx, my = pyxel.mouse_x, pyxel.mouse_y
    is_l   = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
    if g.game_mode == MODE_ENDLESS:
        joker_active = g.joker_count > 0 and not g.joker_mode
        draw_button_joker(
            g, g.btn_joker_x, g.ui_row_y,
            is_active=joker_active,
            is_pressed=(is_l and joker_active
                        and g.btn_joker_x <= mx < g.btn_joker_x + g.btn_w
                        and g.ui_row_y <= my < g.ui_row_y + g.btn_h)
        )
    draw_button(g, g.btn_hint_x,   g.ui_row_y, "H",
                is_active=g.hint_config_on,
                is_pressed=(is_l and g.btn_hint_x <= mx < g.btn_hint_x + g.btn_w
                            and g.ui_row_y <= my < g.ui_row_y + g.btn_h))
    draw_button(g, g.btn_undo_x,   g.ui_row_y, "U",
                is_active=False,
                is_pressed=(is_l and g.btn_undo_x <= mx < g.btn_undo_x + g.btn_w
                            and g.ui_row_y <= my < g.ui_row_y + g.btn_h))
    draw_button(g, g.btn_reload_x, g.ui_row_y, "R",
                is_active=False,
                is_pressed=(is_l and g.btn_reload_x <= mx < g.btn_reload_x + g.btn_w
                            and g.ui_row_y <= my < g.ui_row_y + g.btn_h))


# ------------------------------------------------------------------ #
#  個別ウィジェット
# ------------------------------------------------------------------ #

def draw_x_button(g):
    """右上の✕ボタンを描画する。"""
    x, y, w, h = g.btn_x_x, g.btn_x_y, g.btn_x_w, g.btn_x_h
    mx, my = pyxel.mouse_x, pyxel.mouse_y
    is_hover = x <= mx < x + w and y <= my < y + h
    base_col = 4 if is_hover else 6
    pyxel.rect(x, y, w, h, base_col)
    pyxel.line(x,         y,     x + w - 1, y,         7)
    pyxel.line(x,         y,     x,         y + h - 1, 7)
    pyxel.line(x + w - 1, y,     x + w - 1, y + h - 1, 2)
    pyxel.line(x,         y + h - 1, x + w - 1, y + h - 1, 2)
    pyxel.text(x + 4, y + 3, "X", 1 if is_hover else 0)


def draw_confirm_title():
    """タイトルへ戻る確認ダイアログをボックス型で描画する。"""
    lines = [("RETURN TO TITLE?", 1),
             ("[Y] YES   [N] NO", _COL_N)]
    bx, by, bw, bh = _calc_box(lines)
    _draw_frame(bx, by, bw, bh)
    pyxel.text(_tx("RETURN TO TITLE?"), _ly(by, 0), "RETURN TO TITLE?", 1)
    mx, my = pyxel.mouse_x, pyxel.mouse_y
    y_t  = "[Y] YES"
    n_t  = "[N] NO"
    tx_a = _tx("[Y] YES   [N] NO")
    tx_n = tx_a + len("[Y] YES   ") * 4
    ty_a = _ly(by, 1)
    yc   = _COL_H if _hover(mx,my,tx_a,ty_a,y_t) else _COL_N
    nc   = _COL_H if _hover(mx,my,tx_n,ty_a,n_t) else _COL_N
    pyxel.text(tx_a, ty_a, y_t, yc)
    pyxel.text(tx_n, ty_a, n_t, nc)


def draw_joker_panel():
    """ジョーカー石の COLOR / NUMBER 選択パネルをボックス型で描画する。
    ホバー色: 黒(0) → 白(1)（JOKERパネル専用・視認性優先）
    """
    lines = [("USE JOKER STONE:", 1),
             ("[C] COLOR  [N] NUMBER", _COL_N),
             ("[B] BACK", _COL_N),
             ("UNDO WILL CLEAR", 3)]
    bx, by, bw, bh = _calc_box(lines)
    _draw_frame(bx, by, bw, bh)
    pyxel.text(_tx("USE JOKER STONE:"), _ly(by, 0), "USE JOKER STONE:", 1)
    mx, my = pyxel.mouse_x, pyxel.mouse_y
    # 行1: [C] / [N]（ホバー: 黒→白）
    c_t = "[C] COLOR"
    n_t = "[N] NUMBER"
    tx_cn = _tx("[C] COLOR  [N] NUMBER")
    tx_n  = tx_cn + len("[C] COLOR  ") * 4
    ty1   = _ly(by, 1)
    cc = 1 if _hover(mx,my,tx_cn,ty1,c_t) else 0
    nc = 1 if _hover(mx,my,tx_n, ty1,n_t) else 0
    pyxel.text(tx_cn, ty1, c_t, cc)
    pyxel.text(tx_n,  ty1, n_t, nc)
    # 行2: [B] BACK
    ty2  = _ly(by, 2)
    tx_b = _tx("[B] BACK")
    bc   = 1 if _hover(mx,my,tx_b,ty2,"[B] BACK") else 0
    pyxel.text(tx_b, ty2, "[B] BACK", bc)
    # 行3: UNDO WILL CLEAR（操作不可・暗い表示）
    pyxel.text(_tx("UNDO WILL CLEAR"), _ly(by, 3), "UNDO WILL CLEAR", 3)


def draw_confirm_reload():
    """リロード確認ダイアログをボックス型で描画する。"""
    lines = [("RELOAD?", 1),
             ("[Y] YES   [N] NO", _COL_N)]
    bx, by, bw, bh = _calc_box(lines)
    _draw_frame(bx, by, bw, bh)
    pyxel.text(_tx("RELOAD?"), _ly(by, 0), "RELOAD?", 1)
    mx, my = pyxel.mouse_x, pyxel.mouse_y
    y_t  = "[Y] YES"
    n_t  = "[N] NO"
    tx_a = _tx("[Y] YES   [N] NO")
    tx_n = tx_a + len("[Y] YES   ") * 4
    ty_a = _ly(by, 1)
    yc   = _COL_H if _hover(mx,my,tx_a,ty_a,y_t) else _COL_N
    nc   = _COL_H if _hover(mx,my,tx_n,ty_a,n_t) else _COL_N
    pyxel.text(tx_a, ty_a, y_t, yc)
    pyxel.text(tx_n, ty_a, n_t, nc)


def draw_start_screen():
    """スタート画面を描画する。"""
    pyxel.cls(7)
    pyxel.text(102, 110, "I LOVE ISHIDO", 2)
    mx, my = pyxel.mouse_x, pyxel.mouse_y
    a_col = 0 if (80 <= mx <= 210 and 155 <= my <= 170) else 5
    i_col = 0 if (80 <= mx <= 210 and 172 <= my <= 187) else 5
    e_col = 0 if (80 <= mx <= 210 and 189 <= my <= 204) else 5
    h_col = 0 if (80 <= mx <= 210 and 212 <= my <= 227) else 5
    pyxel.text(94, 160, "[A] ALL WAYS MODE",    a_col)
    pyxel.text(94, 175, "[I] ISHIDO+ MODE",     i_col)
    pyxel.text(94, 190, "[E] ENDLESS ISHIDO++", e_col)
    pyxel.text(94, 210, "[H] HOW TO PLAY",      h_col)


def draw_button(g, x, y, label, is_active, is_pressed):
    """御札風ボタンを描画する。"""
    base_col = 4 if is_active else 6
    if is_pressed:
        base_col = 3
    pyxel.rect(x, y, g.btn_w, g.btn_h, base_col)
    pyxel.line(x,              y,              x + g.btn_w - 1, y,              7)
    pyxel.line(x,              y,              x,              y + g.btn_h - 1, 7)
    pyxel.line(x + g.btn_w-1, y,              x + g.btn_w - 1, y + g.btn_h-1, 2)
    pyxel.line(x,              y + g.btn_h-1, x + g.btn_w - 1, y + g.btn_h-1, 2)
    pyxel.text(x + 5, y + 4, label, 0)


def draw_button_joker(g, x, y, is_active, is_pressed):
    """ジョーカー専用ボタン（赤ベース＋ゆっくり点滅）。"""
    if is_pressed:
        base_col = 3
    elif is_active:
        base_col = 10
    else:
        base_col = 6
    pyxel.rect(x, y, g.btn_w, g.btn_h, base_col)
    pyxel.line(x,              y,              x + g.btn_w - 1, y,              7)
    pyxel.line(x,              y,              x,              y + g.btn_h - 1, 7)
    pyxel.line(x + g.btn_w-1, y,              x + g.btn_w - 1, y + g.btn_h-1, 2)
    pyxel.line(x,              y + g.btn_h-1, x + g.btn_w - 1, y + g.btn_h-1, 2)
    j_col = (1 if (pyxel.frame_count // 30) % 2 == 0 else 10) if is_active else 0
    pyxel.text(x + 5, y + 4, "J", j_col)


def draw_hint_overlay(g):
    """置ける場所をドット点滅で示すヒントオーバーレイを描画する。"""
    if not g.current_stone:
        return
    if g.force_hint_timer > 0:
        alpha = math.sin(math.pi * (120 - g.force_hint_timer) / 120)
    else:
        alpha = math.sin(math.pi * (g.idle_timer % HINT_CYCLE) / HINT_ACTIVE_FRAMES)
    if alpha < 0:
        return
    center_col = 1 if alpha > 0.7 else 7
    edge_col   = 6 if alpha > 0.7 else 4
    for y in range(BOARD_ROWS):
        for x in range(BOARD_COLS):
            if g.is_placeable(x, y, g.current_stone):
                cx = g.offset_x + x * g.gap_x + g.sw // 2
                cy = g.offset_y + y * g.gap_y + g.sh // 2
                if pyxel.frame_count % 8 < 6:
                    pyxel.pset(cx, cy, center_col)
                    if alpha > 0.3:
                        pyxel.pset(cx-1, cy,   edge_col)
                        pyxel.pset(cx+1, cy,   edge_col)
                        pyxel.pset(cx,   cy-1, edge_col)
                        pyxel.pset(cx,   cy+1, edge_col)
