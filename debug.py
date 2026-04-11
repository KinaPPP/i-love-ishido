"""
debug.py — I LOVE ISHIDO ローカルデバッグ機能

IS_WEB=False（ローカル実行）時のみ ishido.py から呼び出す。
Web版にはこのファイルをアップロードしないこと。

キー一覧:
  [0] 即クリア（CONGRATULATIONS! / LEFT:0）
  [1] 初手 STALEMATE 強制
  [2] 通常 STALEMATE 強制
  [3] JOKER rescue STALEMATE 強制（ENDLESS MODE のみ）
  [4] WAY演出サイクル（1回目=2WAY / 2回目=3WAY / 3回目=4WAY）
  [5] 99演出サイクル（1回目=LOOP:99 / 2回目=JOKER:99 / 3回目=両方同時）
  [6] 空き
  [7] LOOP UP SE 強制（JOKER+2 / LOOP+1）
  [8] 全消しボーナスシーケンス強制
  [9] THE PATH シーケンス強制
  [M] MARVELOUS 強制サイクル（HARMONY→MONSTER→FLOW→OFF）
"""

import pyxel

# サイクルカウンター（モジュールレベルで保持）
_key4_count = 0  # [4]: 0=未押 1=2WAY 2=3WAY 3=4WAY → 次は0に戻る
_key5_count = 0  # [5]: 0=未押 1=LOOP:99 2=JOKER:99 3=両方


def handle_debug_keys(game):
    """デバッグキーの入力処理。update() 内でゲームプレイ中にのみ呼び出す。"""
    global _key4_count, _key5_count

    cx = game.offset_x + game.cursor_x * game.gap_x + game.sw // 2
    cy = game.offset_y + game.cursor_y * game.gap_y + game.sh // 2

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

    # [4] WAY演出サイクル
    #   1回目: 2WAY（上・右）
    #   2回目: 3WAY（上・右・下）
    #   3回目: 4WAY（上・右・下・左）→ 次は1回目に戻る
    if pyxel.btnp(pyxel.KEY_4):
        _key4_count = (_key4_count % 3) + 1
        if _key4_count == 1:
            game.effects.trigger_way_lines(cx, cy, [(0,-1),(1,0)])
            game.se.play_way_match()
            print("[DEBUG] [4]-1: 2WAY")
        elif _key4_count == 2:
            game.effects.trigger_way_lines(cx, cy, [(0,-1),(1,0),(0,1)])
            game.se.play_way_match()
            print("[DEBUG] [4]-2: 3WAY")
        else:
            game.effects.trigger_way_lines(cx, cy, [(0,-1),(1,0),(0,1),(-1,0)])
            game.effects.trigger_4way(cx, cy, 15)
            game.se.play_4way_match()
            print("[DEBUG] [4]-3: 4WAY")

    # [5] 99演出サイクル（ENDLESS MODE で動作確認用）
    #   1回目: LOOP:99 演出強制
    #   2回目: JOKER:99 演出強制
    #   3回目: 両方同時演出強制 → 次は1回目に戻る
    if pyxel.btnp(pyxel.KEY_5):
        import game_logic as logic
        _key5_count = (_key5_count % 3) + 1
        game.game_state = "STALEMATE"  # 演出中は状態を切り替える

        if _key5_count == 1:
            game.loop_count = 99
            logic._milestone_triggered.add("LOOP")  # 公式フラグを立てる
            game.effects.trigger_milestone("LOOP")
            print("[DEBUG] [5]-1: LOOP:99 演出")
        elif _key5_count == 2:
            game.joker_count = 99
            logic._milestone_triggered.add("JOKER") # 公式フラグを立てる
            game.effects.trigger_milestone("JOKER")
            print("[DEBUG] [5]-2: JOKER:99 演出")
        else:
            game.loop_count  = 99
            game.joker_count = 99
            logic._milestone_triggered.add("LOOP")  # 公式フラグを立てる
            logic._milestone_triggered.add("JOKER") # 公式フラグを立てる
            game.effects.trigger_milestone("BOTH")
            print("[DEBUG] [5]-3: LOOP:99 + JOKER:99 両方演出")

    # [6] 空き（将来の拡張用）

    # [7] LOOP UP SE 強制（JOKER+2 / LOOP+1）
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
        game.effects.result_timer = 999
        game.effects.trigger_path_sequence()

    # [M] MARVELOUS 強制サイクル（HARMONY → MONSTER → FLOW → OFF）
    if pyxel.btnp(pyxel.KEY_M):
        ranks = [None, "HARMONY", "MONSTER", "FLOW"]
        current = game.effects.marvelous_rank
        next_rank = ranks[(ranks.index(current) + 1) % len(ranks)]
        game.game_state = "STALEMATE"
        game.effects.trigger_stalemate(
            is_initial=False,
            marvelous_rank=next_rank
        )
        label = next_rank if next_rank else "OFF (通常STALEMATE)"
        print(f"[DEBUG] MARVELOUS: {label}")
