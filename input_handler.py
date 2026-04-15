"""
input_handler.py — I LOVE ISHIDO 入力処理モジュール

スタート画面・プレイ中・リザルト画面の入力処理を集約する。
ishido.py の Ishido クラスから `g`（ゲームインスタンス）を受け取り、
g の状態を読み書きする。
"""

import pyxel
import effect
import theme  # ← 【重要】これをファイルの先頭に書きます

from constants import (
    BOARD_COLS, BOARD_ROWS,
    MODE_ALL_WAYS, MODE_ISHIDO, MODE_ENDLESS,
    STATE_START, STATE_PLAYING, STATE_RESULT, STATE_STALEMATE,
    HINT_IDLE_THRESHOLD, HINT_CYCLE, HINT_ACTIVE_FRAMES,
)
import game_logic as logic

# ボックス座標ヘルパー（effect.py / ui.py と共通設計）
_BOX_TOP  = 100
_BOX_MG_Y = 9
_LINE_H   = 11
_MIN_BW   = 144
_BOX_CX   = 128

def _calc_box(lines):
    max_w = max((len(t)*4 for t,_ in lines), default=0) + 16
    bw    = max(max_w, _MIN_BW)
    bh    = _BOX_MG_Y + len(lines)*_LINE_H + _BOX_MG_Y
    bx    = _BOX_CX - bw//2
    return bx, _BOX_TOP, bw, bh

def _ly(by, i):
    return by + _BOX_MG_Y + i * _LINE_H

def _tx(text):
    return _BOX_CX - len(text)*2

def _box_action_y(lines):
    """lines の最終行のy座標を返す。"""
    _, by, _, _ = _calc_box(lines)
    return _ly(by, len(lines)-1)

def _is_hit(mx, my, tx, ty, text):
    return tx <= mx <= tx+len(text)*4 and ty <= my <= ty+6


# ------------------------------------------------------------------ #
#  スタート画面
# ------------------------------------------------------------------ #

# --- handle_start 関数内 ---
def handle_start(g, mx, my):
    is_title_clicked = (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and 100 <= mx <= 160 and 110 <= my <= 125)

    if pyxel.btnp(pyxel.KEY_T) or is_title_clicked:
        theme.switch()  # ← インポートはせず、ただ呼び出すだけでOKです！

    # (以降の [A][I][E][H] 等の処理へ)
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

    # [T] キーの処理
    if pyxel.btnp(pyxel.KEY_T):
        # 演出中、または選択・リロード待ちの状態を定義
        is_busy = (
            g.effects.milestone_active or           # [5] マイルストーン
            g.effects.path_sequence_active or       # [9] THE PATH
            g.effects.board_clear_active or         # [8] 全消し
            g.effects.is_joker_rescue or             # [3] JOKER救済
            g.effects.marvelous_rank is not None or    # [M] MARVELOUS
            g.effects.is_initial_stalemate or        # [1] 初手詰まり
            (g.effects.is_victory and g.effects.result_timer < 140) or # [0] 勝利演出中
            g.effects.is_stalemate                  # [2] 詰み状態（リロード待ちの間はずっとガード）
        )

        if not is_busy:
            # 完全に演出が終わり、勝利リザルト画面のボタンが出た後のみタイトルへ
            g.game_state = STATE_START
            return
        else:
            # 演出中やリロード待ち、JOKER選択中は「テーマ切り替え」として機能
            theme.switch()

    g.effects.update()

    # LOOP:99 / JOKER:99 マイルストーン演出中の入力処理
    if g.effects.milestone_active:
        if g.effects.milestone_phase == 1:  # YES/NO 表示中のみ入力受付
            # ボックス座標計算 (THE COUNTER STOPS HERE. のためのダミー行を追加)
            cur = "JOKER" if (g.effects.milestone_type == "BOTH"
                              and g.effects.milestone_second) \
                  else ("LOOP" if g.effects.milestone_type in ("LOOP","BOTH") else "JOKER")
            if cur == "LOOP":
                ml = [("LOOP : 99",1),("x"*48,15),("x"*38,7),("[Y] YES   [N] NO",5)]
            else:
                ml = [("JOKER : 99",1),("x"*32,10),("x"*38,10),("x"*38,7),("[Y] YES   [N] NO",5)]
            _, ml_by,_,_ = _calc_box(ml)
            ty_ml = _ly(ml_by, len(ml)-1)
            tx_y  = _tx("[Y] YES   [N] NO")
            tx_n  = tx_y + len("[Y] YES   ")*4

            yes_hit = pyxel.btnp(pyxel.KEY_Y) or (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and _is_hit(mx,my,tx_y,ty_ml,"[Y] YES")
            )
            no_hit = pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE) or (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and _is_hit(mx,my,tx_n,ty_ml,"[N] NO")
            )

            if yes_hit or no_hit:
                # BOTHの1本目（LOOP）なら、YES/NOどちらを押しても「強制的に」2本目（JOKER）へ移行！
                if g.effects.milestone_type == "BOTH" and not g.effects.milestone_second:
                    g.effects.milestone_second = True
                    g.effects.milestone_timer  = 0
                    g.effects.milestone_phase  = 0
                    return

                # 2本目（JOKER）、または単独演出の場合の「最終決定」
                if yes_hit:
                    # 続行: 盤面へ戻る
                    g.effects.milestone_active = False
                    g.effects.milestone_done   = True
                    g.effects.milestone_resume = True
                    g.game_state = STATE_PLAYING
                else:
                    # リタイア: 潔く THE PATH シーケンスへ直行
                    g.effects.milestone_active  = False
                    g.effects.milestone_done    = True
                    g.effects.milestone_resume  = False
                    g.game_state = STATE_STALEMATE
                    g.effects.trigger_path_sequence()
                return
        return  # 演出中（フェーズ0）は他の入力をブロック

    # ✕ボタンによるタイトル確認ダイアログ
    if g.confirm_title:
        ct_l = [("RETURN TO TITLE?",1),("[Y] YES   [N] NO",5)]
        _, ct_by,_,_ = _calc_box(ct_l)
        ty_ct= _ly(ct_by,1); tx_y=_tx("[Y] YES   [N] NO")
        tx_n = tx_y+len("[Y] YES   ")*4
        if pyxel.btnp(pyxel.KEY_Y) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and _is_hit(mx,my,tx_y,ty_ct,"[Y] YES")
        ):
            g.confirm_title = False
            g.game_state    = STATE_START
            g.effects       = effect.EffectManager()
            return
        if pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and _is_hit(mx,my,tx_n,ty_ct,"[N] NO")
        ):
            g.confirm_title = False
        return

    # [P] スクリーンショット（STALEMATE / RESULT 画面でも撮影可）
    #if pyxel.btnp(pyxel.KEY_P):
        #import datetime
        #pyxel.screenshot(f"ishido_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")

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
            use_joker = pyxel.btnp(pyxel.KEY_J) or pyxel.btnp(pyxel.KEY_F) or (
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
                g.effects.trigger_path_sequence(); return

        # MARVELOUS / 通常STALEMATE のアクション入力処理
        # ボックス座標をリアルタイム計算して使用
        is_marvelous = bool(g.effects.marvelous_rank)

        if is_marvelous and g.effects.result_timer < 120:
            return  # 演出中はブロック

        # アクション行のy座標を計算
        if is_marvelous:
            msg_txt, _ = g.effects._MARVELOUS_MSGS.get(
                g.effects.marvelous_rank, ("", 1))
            base = [("MARVELOUS!", 1)]
            if msg_txt: base.append((msg_txt, 5))
            base += [("x"*23, 1), ("x"*18, 1)]  # stats2行
            act_lines = base + [("x"*21, 5)]
        else:
            if g.game_mode == MODE_ENDLESS:
                l1 = "x"*23
                l2 = "LEFT:00 LOOP:0 & JOKER:0"
                stat_lines = [(l1, 1), (l2, 1)]
            else:
                res = "4WAY=00 3WAY=00 2WAY=00 LEFT:00"
                stat_lines = [(res, 1)]

            act  = "x"*26 if (g.game_mode==MODE_ENDLESS and g.effects.is_joker_rescue) else "x"*10
            act_lines = [("STALEMATE", 1)] + stat_lines + [(act, 5)]

        ty_a = _box_action_y(act_lines)

        # JOKER rescue 入力
        if (g.game_mode == MODE_ENDLESS
                and g.effects.is_joker_rescue
                and g.joker_count > 0):
            j_t = "[J] USE JOKER"
            r_t = "[R] GIVE UP"
            jx  = _tx("[J] USE JOKER  [R] GIVE UP")
            rx  = jx + len("[J] USE JOKER  ")*4
            use_joker = pyxel.btnp(pyxel.KEY_J) or pyxel.btnp(pyxel.KEY_F) or (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and (_is_hit(mx,my,jx,ty_a,j_t)
                     or (g.btn_joker_x <= mx < g.btn_joker_x+g.btn_w
                         and g.ui_row_y <= my < g.ui_row_y+g.btn_h))
            )
            give_up = (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                       and _is_hit(mx,my,rx,ty_a,r_t))
            if use_joker:
                g.game_state           = STATE_PLAYING
                g.effects.is_stalemate = False
                g.joker_panel_open     = True
                return
            if give_up:
                g.effects.trigger_path_sequence(); return

        # [R] RELOAD（MARVELOUSまたは通常STALEMATE共通）
        r_t  = "[R] RELOAD"
        if is_marvelous:
            rx_r = _tx("[U] UNDO   [R] RELOAD") + len("[U] UNDO   ")*4  # 右側に移動
        else:
            rx_r = _tx(r_t)

        is_reload = pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_C) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and (_is_hit(mx, my, rx_r, ty_a, r_t)
                 or (g.btn_reload_x <= mx < g.btn_reload_x+g.btn_w
                     and g.ui_row_y <= my < g.ui_row_y+g.btn_h))
        )
        if is_reload:
            if not g.effects.is_initial_stalemate:
                g.effects.trigger_path_sequence()
            else:
                g.restart_game()
            return

        # [U] UNDO
        u_t  = "[U] UNDO"
        tx_u = _tx("[U] UNDO   [R] RELOAD")  # 左側に移動
        is_undo = (
            pyxel.btnp(pyxel.KEY_U)
            or pyxel.btnp(pyxel.KEY_BACKSPACE)
            or pyxel.btnp(pyxel.KEY_Z)
            or (g.undo_interval == 0 and (
                pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT)
                or (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                    and (_is_hit(mx,my,tx_u,ty_a,u_t)
                         or (g.btn_undo_x <= mx < g.btn_undo_x+g.btn_w
                             and g.ui_row_y <= my < g.ui_row_y+g.btn_h)))
            ))
        )
        if is_undo:
            logic.undo(g)


# ------------------------------------------------------------------ #
#  プレイ中
# ------------------------------------------------------------------ #

# --- handle_playing 関数内 ---
def handle_playing(g, mx, my):
    """プレイ中の入力処理。"""

    # [T] キー、または画面左下の「NEXT石」エリアのタップでテーマ切り替え
    # 石の判定エリアを右に寄せ、x:40 から 幅16ピクセル分（56まで）に設定
    is_next_stone_clicked = (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and
                             45 <= mx <= 61 and g.ui_row_y <= my <= g.ui_row_y + 24)

    if pyxel.btnp(pyxel.KEY_T) or is_next_stone_clicked:
        theme.switch()
    input_active = False

    # タイトル確認ダイアログ
    if g.confirm_title:
        ct_l = [("RETURN TO TITLE?",1),("[Y] YES   [N] NO",5)]
        _, ct_by,_,_ = _calc_box(ct_l)
        ty_ct= _ly(ct_by,1); tx_y=_tx("[Y] YES   [N] NO")
        tx_n = tx_y+len("[Y] YES   ")*4
        if pyxel.btnp(pyxel.KEY_Y) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and _is_hit(mx,my,tx_y,ty_ct,"[Y] YES")
        ):
            g.confirm_title = False
            g.game_state    = STATE_START
            return
        if pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_X) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            and _is_hit(mx,my,tx_n,ty_ct,"[N] NO")
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
        # JOKERパネルのボックス座標計算
        jp_l = [("USE JOKER STONE:",1),("[C] COLOR  [N] NUMBER",5),("[B] BACK",5),("UNDO WILL CLEAR",3)]
        _, jp_by,_,_ = _calc_box(jp_l)
        ty1 = _ly(jp_by,1); ty2 = _ly(jp_by,2)
        tx_c = _tx("[C] COLOR  [N] NUMBER")
        tx_n = tx_c + len("[C] COLOR  ")*4
        tx_b = _tx("[B] BACK")
        if pyxel.btnp(pyxel.KEY_C):
            logic.activate_joker(g, "C")
        elif pyxel.btnp(pyxel.KEY_N):
            logic.activate_joker(g, "N")
        elif pyxel.btnp(pyxel.KEY_B) or pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_X):
            logic.cancel_joker(g)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if   _is_hit(mx,my,tx_c,ty1,"[C] COLOR"):  logic.activate_joker(g,"C")
            elif _is_hit(mx,my,tx_n,ty1,"[N] NUMBER"): logic.activate_joker(g,"N")
            elif _is_hit(mx,my,tx_b,ty2,"[B] BACK"):   logic.cancel_joker(g)
        return

    # Jボタン（ENDLESS）
    if g.game_mode == MODE_ENDLESS and not g.joker_mode:
        if (pyxel.btnp(pyxel.KEY_J) or pyxel.btnp(pyxel.KEY_F)) and g.joker_count > 0:
            g.joker_panel_open = True
        if (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and g.btn_joker_x <= mx < g.btn_joker_x + g.btn_w
                and g.ui_row_y <= my < g.ui_row_y + g.btn_h
                and g.joker_count > 0):
            g.joker_panel_open = True

    # リロード確認ダイアログ
    if g.confirm_reload:
        cr_l = [("RELOAD?",1),("[Y] YES   [N] NO",5)]
        _, cr_by,_,_ = _calc_box(cr_l)
        ty_cr = _ly(cr_by,1); tx_y=_tx("[Y] YES   [N] NO")
        tx_n  = tx_y+len("[Y] YES   ")*4
        if pyxel.btnp(pyxel.KEY_Y) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            g.confirm_reload = False; g.restart_game(); return
        if pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_X):
            g.confirm_reload = False; input_active = True; return
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if _is_hit(mx,my,tx_y,ty_cr,"[Y] YES"):
                g.confirm_reload = False; g.restart_game(); return
            if _is_hit(mx,my,tx_n,ty_cr,"[N] NO"):
                g.confirm_reload = False; input_active = True
        return

    # R / H ボタン
    if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_C):
        g.confirm_reload = True; input_active = True
    if pyxel.btnp(pyxel.KEY_H) or pyxel.btnp(pyxel.KEY_Q):
        logic.trigger_hint(g); input_active = True

    # [P] スクリーンショット（ローカル=PNG保存 / Web=ブラウザダウンロード）
    #if pyxel.btnp(pyxel.KEY_P):
        #import datetime
        #pyxel.screenshot(f"ishido_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")

    # UNDO（ジョーカー使用中は無効）
    is_undo = False if g.joker_mode else (
        pyxel.btnp(pyxel.KEY_U) or pyxel.btnp(pyxel.KEY_BACKSPACE) or pyxel.btnp(pyxel.KEY_Z))
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

    # カーソル更新（マウス）
    if (g.offset_x <= mx < g.offset_x + BOARD_COLS * g.gap_x
            and g.offset_y <= my < g.offset_y + BOARD_ROWS * g.gap_y):
        g.cursor_x = (mx - g.offset_x) // g.gap_x
        g.cursor_y = (my - g.offset_y) // g.gap_y

    # カーソル移動（WASD / 矢印キー）
    if pyxel.btnp(pyxel.KEY_W) or pyxel.btnp(pyxel.KEY_UP):
        g.cursor_y = max(0, g.cursor_y - 1);              input_active = True
    if pyxel.btnp(pyxel.KEY_S) or pyxel.btnp(pyxel.KEY_DOWN):
        g.cursor_y = min(BOARD_ROWS - 1, g.cursor_y + 1); input_active = True
    if pyxel.btnp(pyxel.KEY_A) or pyxel.btnp(pyxel.KEY_LEFT):
        g.cursor_x = max(0, g.cursor_x - 1);              input_active = True
    if pyxel.btnp(pyxel.KEY_D) or pyxel.btnp(pyxel.KEY_RIGHT):
        g.cursor_x = min(BOARD_COLS - 1, g.cursor_x + 1); input_active = True

    # 石の配置
    is_place = pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or (
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
