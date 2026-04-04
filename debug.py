"""
debug.py — I LOVE ISHIDO ローカルデバッグ機能

IS_WEB=False（ローカル実行）時のみ ishido.py から呼び出す。
Web版にはこのファイルをアップロードしないこと。

キー一覧:
  [0] 即クリア（CONGRATULATIONS! / LEFT:0）
  [1] 初手 STALEMATE 強制
  [2] 通常 STALEMATE 強制
  [3] JOKER rescue STALEMATE 強制（ENDLESS MODE のみ）
  [4] 4WAY エフェクト＋SE 強制
  [5] 2WAY エフェクト＋SE 強制
  [6] 3WAY エフェクト＋SE 強制
  [7] LOOP UP SE 強制（ジョーカー2個補給も）
  [8] 全消しボーナスシーケンス強制
  [9] THE PATH シーケンス強制（STALEMATE → THE PATH を一連で）
"""

import pyxel


def handle_debug_keys(game):
    """デバッグキーの入力処理。update() 内でゲームプレイ中にのみ呼び出す。"""

    # [0] 即クリア（CONGRATULATIONS!）
    if pyxel.btnp(pyxel.KEY_0):
        game.bag           = []
        game.current_stone = None
        game.game_state    = "RESULT"
        game.effects.start_victory()
        return

    # [1] 初手 STALEMATE 強制
    if pyxel.btnp(pyxel.KEY_1):
        game.game_state = "STALEMATE"
        game.effects.trigger_stalemate(is_initial=True)

    # [2] 通常 STALEMATE 強制
    if pyxel.btnp(pyxel.KEY_2):
        game.game_state = "STALEMATE"
        game.effects.trigger_stalemate(is_initial=False)

    # [3] JOKER rescue STALEMATE 強制（ENDLESS MODE のみ）
    if pyxel.btnp(pyxel.KEY_3):
        game.game_state = "STALEMATE"
        game.effects.trigger_stalemate(
            is_initial=False,
            is_joker_rescue=(game.joker_count > 0)
        )

    # [4] 4WAY エフェクト＋SE 強制（カーソル位置で発火）
    if pyxel.btnp(pyxel.KEY_4):
        cx = game.offset_x + game.cursor_x * game.gap_x + game.sw // 2
        cy = game.offset_y + game.cursor_y * game.gap_y + game.sh // 2
        game.effects.trigger_4way(cx, cy, 15)
        game.se.play_4way_match()

    # [5] 2WAY エフェクト＋SE 強制（カーソル位置から上・右方向へ）
    if pyxel.btnp(pyxel.KEY_5):
        cx = game.offset_x + game.cursor_x * game.gap_x + game.sw // 2
        cy = game.offset_y + game.cursor_y * game.gap_y + game.sh // 2
        game.effects.trigger_way_lines(cx, cy, [(0, -1), (1, 0)])
        game.se.play_way_match()

    # [6] 3WAY エフェクト＋SE 強制（カーソル位置から上・右・下方向へ）
    if pyxel.btnp(pyxel.KEY_6):
        cx = game.offset_x + game.cursor_x * game.gap_x + game.sw // 2
        cy = game.offset_y + game.cursor_y * game.gap_y + game.sh // 2
        game.effects.trigger_way_lines(cx, cy, [(0, -1), (1, 0), (0, 1)])
        game.se.play_way_match()

    # [7] LOOP UP SE 強制（ジョーカー2個補給も）
    if pyxel.btnp(pyxel.KEY_7):
        game.joker_count += 2
        game.loop_count  += 1
        game.se.play_loop_and_joker(2)

    # [8] 全消しボーナスシーケンス強制
    if pyxel.btnp(pyxel.KEY_8):
        game.effects.trigger_board_clear_bonus()
        game.game_state = "STALEMATE"   # 入力ブロックのため一時的に STALEMATE へ

    # [9] THE PATH シーケンス強制（STALEMATE → THE PATH を一連で）
    if pyxel.btnp(pyxel.KEY_9):
        game.game_state = "STALEMATE"
        game.effects.trigger_stalemate(is_initial=False)
        game.effects.result_timer = 999     # 待機時間をスキップ
        game.effects.trigger_path_sequence()
