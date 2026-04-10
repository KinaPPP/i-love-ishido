"""
input_handler.py — I LOVE ISHIDO 入力処理モジュール

スタート画面・プレイ中・リザルト画面の入力処理を集約する。
ishido.py の Ishido クラスから `g`（ゲームインスタンス）を受け取り、
g の状態を読み書きする。
"""

import pyxel
import effect

from constants import (
    BOARD_COLS, BOARD_ROWS,
    MODE_ALL_WAYS, MODE_ISHIDO, MODE_ENDLESS,
    STATE_START, STATE_PLAYING, STATE_RESULT, STATE_STALEMATE,
    HINT_IDLE_THRESHOLD, HINT_CYCLE, HINT_ACTIVE_FRAMES,
)
import game_logic as logic


# ------------------------------------------------------------------ #
#  スタート画面
# ------------------------------------------------------------------ #

def handle_start(g, mx, my):
    """スタート画面の入力処理。"""
    if pyxel.btnp(pyxel.KEY_A):
        g.game_mode = MODE_ALL_WAYS;  g.restart_game(); return
    if pyxel.btnp(pyxel.KEY_I):
        g.game_mode = MODE_ISHIDO;    g.restart_game(); return
    if pyxel.btnp(pyxel.KEY_E):
        g.game_mode = MODE_ENDLESS;   g.restart_game(); return
    if pyxel.btnp(pyxel.KEY_H):
        g.open_how_to_play(); return
    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and 80 <= mx <= 210:
        if   155 <= my <= 170: g.game_mode = MODE_ALL_WAYS; g.restart_game()
        elif 172 <= my <= 187: g.game_mode = MODE_ISHIDO;   g.restart_game()
        elif 189 <= my <= 204: g.game_mode = MODE_ENDLESS;  g.restart_game()
        elif 212 <= my <= 227: g.open_how_to_play()


# ------------------------------------------------------------------ #
#  リザルト / STALEMATE 画面
# ------------------------------------------------------------------ #

def handle_result(g, mx, my):
    """RESULT / STALEMATE 状態の入力処理。"""
    g.effects.update()

    # ✕ボタンによるタイトル確認ダイアログ
    if g.confirm_title:
        if pyxel.btnp(pyxel.KEY_Y) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and 88 <= mx <= 120 and 126 <= my <= 136
        ):
            g.confirm_title = False
            g.game_state    = STATE_START
            g.effects       = effect.EffectManager()
            return
        if pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and 132 <= mx <= 164 and 126 <= my <= 136
        ):
            g.confirm_title = False
        return

    # ✕ボタンのクリック
    if (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and g.btn_x_x <= mx < g.btn_x_x + g.btn_x_w
            and g.btn_x_y <= my < g.btn_x_y + g.btn_x_h):
        g.confirm_title = True
        return

    # THE PATH 完了 → リロード
    if g.effects.path_done:
        g.restart_game(); return

    # 全消しボーナス完了 → 継続
    if g.effects.board_clear_done:
        g.effects.board_clear_done = False
        g.game_state = STATE_PLAYING
        logic.endless_board_clear_restart(g)
        return

    # THE PATH シーケンス中はブロック
    if g.effects.path_sequence_active:
        return

    # 初手詰まり → 自動リスタート
    if g.game_state == STATE_STALEMATE and g.effects.is_initial_stalemate:
        if g.effects.result_timer > 100:
            g.restart_game()
        return

    # CONGRATULATIONS! 画面
    if g.effects.result_timer > 100 and g.game_state == STATE_RESULT:
        if pyxel.btnp(pyxel.KEY_G):
            g.restart_game()
        if pyxel.btnp(pyxel.KEY_T):
            g.game_state = STATE_START
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if 104 <= mx <= 152 and 162 <= my <= 172:
                g.restart_game()
            if 104 <= mx <= 140 and 177 <= my <= 187:
                g.game_state = STATE_START

    # STALEMATE 画面
    if g.game_state == STATE_STALEMATE and g.effects.result_timer > 60:
        if g.effects.is_joker_rescue:
            use_joker = pyxel.btnp(pyxel.KEY_J) or (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and (
                    (g.btn_joker_x <= mx < g.btn_joker_x + g.btn_w
                     and g.ui_row_y <= my < g.ui_row_y + g.btn_h)
                    or (72 <= mx <= 120 and 139 <= my <= 149)
                )
            )
            give_up = (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and 130 <= mx <= 178 and 139 <= my <= 149
            )
            if use_joker:
                g.game_state           = STATE_PLAYING
                g.effects.is_stalemate = False
                g.joker_panel_open     = True
                return
            if give_up:
                g.restart_game(); return

        is_reload = pyxel.btnp(pyxel.KEY_R) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and g.btn_reload_x <= mx < g.btn_reload_x + g.btn_w
            and g.ui_row_y <= my < g.ui_row_y + g.btn_h
        )
        if is_reload:
            if g.game_mode == MODE_ISHIDO and not g.effects.is_initial_stalemate:
                g.effects.trigger_path_sequence()
            else:
                g.restart_game()

        is_undo = (
            pyxel.btnp(pyxel.KEY_U)
            or pyxel.btnp(pyxel.KEY_BACKSPACE)
            or (g.undo_interval == 0 and (
                pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT)
                or (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                    and g.btn_undo_x <= mx < g.btn_undo_x + g.btn_w
                    and g.ui_row_y <= my < g.ui_row_y + g.btn_h)
            ))
        )
        if is_undo:
            logic.undo(g)


# ------------------------------------------------------------------ #
#  プレイ中
# ------------------------------------------------------------------ #

def handle_playing(g, mx, my):
    """ゲームプレイ中の入力処理。"""
    input_active = False

    # タイトル確認ダイアログ
    if g.confirm_title:
        if pyxel.btnp(pyxel.KEY_Y) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and 88 <= mx <= 120 and 126 <= my <= 136
        ):
            g.confirm_title = False
            g.game_state    = STATE_START
            return
        if pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and 132 <= mx <= 164 and 126 <= my <= 136
        ):
            g.confirm_title = False
        return

    # ✕ボタン
    if (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and g.btn_x_x <= mx < g.btn_x_x + g.btn_x_w
            and g.btn_x_y <= my < g.btn_x_y + g.btn_x_h
            and not g.confirm_title):
        g.confirm_title = True
        return

    # ジョーカーパネル操作
    if g.joker_panel_open:
        if pyxel.btnp(pyxel.KEY_C):
            logic.activate_joker(g, "C")
        elif pyxel.btnp(pyxel.KEY_N):
            logic.activate_joker(g, "N")
        elif pyxel.btnp(pyxel.KEY_B) or pyxel.btnp(pyxel.KEY_ESCAPE):
            logic.cancel_joker(g)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if   72 <= mx <= 108  and 118 <= my <= 128: logic.activate_joker(g, "C")
            elif 144 <= mx <= 184 and 118 <= my <= 128: logic.activate_joker(g, "N")
            elif 112 <= mx <= 144 and 130 <= my <= 140: logic.cancel_joker(g)
        return

    # Jボタン（ENDLESS）
    if g.game_mode == MODE_ENDLESS and not g.joker_mode:
        if pyxel.btnp(pyxel.KEY_J) and g.joker_count > 0:
            g.joker_panel_open = True
        if (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and g.btn_joker_x <= mx < g.btn_joker_x + g.btn_w
                and g.ui_row_y <= my < g.ui_row_y + g.btn_h
                and g.joker_count > 0):
            g.joker_panel_open = True

    # リロード確認ダイアログ
    if g.confirm_reload:
        if pyxel.btnp(pyxel.KEY_Y):
            g.confirm_reload = False; g.restart_game(); return
        if pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE):
            g.confirm_reload = False; input_active = True; return
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if  96 <= mx <= 124 and 126 <= my <= 136:
                g.confirm_reload = False; g.restart_game(); return
            if 128 <= mx <= 152 and 126 <= my <= 136:
                g.confirm_reload = False; input_active = True
        return

    # R / H ボタン
    if pyxel.btnp(pyxel.KEY_R):
        g.confirm_reload = True; input_active = True
    if pyxel.btnp(pyxel.KEY_H):
        logic.trigger_hint(g); input_active = True

    # UNDO（ジョーカー使用中は無効）
    is_undo = False if g.joker_mode else (
        pyxel.btnp(pyxel.KEY_U) or pyxel.btnp(pyxel.KEY_BACKSPACE))
    if g.undo_interval == 0:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            is_undo = True
        if (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and g.btn_undo_x <= mx < g.btn_undo_x + g.btn_w
                and g.ui_row_y <= my < g.ui_row_y + g.btn_h):
            is_undo = True
    if is_undo and logic.undo(g):
        input_active = True

    # ボタンエリアのクリック
    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and g.ui_row_y <= my < g.ui_row_y + g.btn_h:
        if g.btn_hint_x   <= mx < g.btn_hint_x   + g.btn_w:
            logic.trigger_hint(g); input_active = True
        if g.btn_reload_x <= mx < g.btn_reload_x + g.btn_w:
            g.confirm_reload = True; input_active = True

    # カーソル更新
    if (g.offset_x <= mx < g.offset_x + BOARD_COLS * g.gap_x
            and g.offset_y <= my < g.offset_y + BOARD_ROWS * g.gap_y):
        g.cursor_x = (mx - g.offset_x) // g.gap_x
        g.cursor_y = (my - g.offset_y) // g.gap_y

    # 石の配置
    is_place = pyxel.btnp(pyxel.KEY_SPACE) or (
        pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and my < g.ui_row_y
    )
    if is_place:
        if g.place_stone():
            input_active = True
        elif g.current_stone:
            g.se.play_place_ng()

    # アイドルタイマー・ヒント制御
    mouse_moved = (mx != g.prev_mouse_x or my != g.prev_mouse_y)
    if input_active or mouse_moved:
        g.idle_timer = 0
    else:
        g.idle_timer += 1
    g.prev_mouse_x, g.prev_mouse_y = mx, my

    hint_cycle_active = (
        (g.idle_timer - HINT_IDLE_THRESHOLD) % HINT_CYCLE < HINT_ACTIVE_FRAMES
    )
    g.show_hint_spiritual = (
        g.force_hint_timer > 0
        or (g.hint_config_on and g.idle_timer > HINT_IDLE_THRESHOLD and hint_cycle_active)
    )
    if g.force_hint_timer > 0:
        g.force_hint_timer -= 1

    # 勝利演出遅延
    if g.victory_delay > 0:
        g.victory_delay -= 1
        if g.victory_delay == 0:
            g.game_state = STATE_RESULT
            g.effects.start_victory()

    g.effects.update()
