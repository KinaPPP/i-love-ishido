"""
game_logic.py — I LOVE ISHIDO ゲームロジックモジュール

石の配置判定・盤面チェック・UNDO・ENDLESS専用処理を集約する。
ishido.py の Ishido クラスから `g`（ゲームインスタンス）を受け取り、
g の状態を読み書きする。
"""

import random
import effect

from constants import (
    BOARD_COLS, BOARD_ROWS,
    MODE_ISHIDO, MODE_ALL_WAYS, MODE_ENDLESS,
    STATE_PLAYING,
    JOKER_COLOR, JOKER_NUMBER,
)


# ------------------------------------------------------------------ #
#  配置判定
# ------------------------------------------------------------------ #

def is_placeable(g, x, y, stone):
    """指定セルに stone を置けるかどうかを返す。"""
    if g.board[y][x] is not None:
        return False

    adjacents = []
    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < BOARD_COLS and 0 <= ny < BOARD_ROWS:
            if g.board[ny][nx]:
                adjacents.append(g.board[ny][nx])

    if not adjacents:
        return False

    # ジョーカー石は隣接石さえあればどこでも置ける
    if isinstance(stone, tuple) and stone[0] == "J":
        return True

    if g.game_mode in (MODE_ISHIDO, MODE_ENDLESS):
        # XORルール: 全隣接石と色か数字のどちらか一方だけ一致
        for adj in adjacents:
            if isinstance(adj, tuple) and adj[0] == "J":
                continue
            color_match  = (stone[0] == adj[0])
            number_match = (stone[1] == adj[1])
            if not (color_match ^ number_match):
                return False
        return True
    else:
        # ALL WAYS: 全隣接石と色または数字のどちらかが一致（ブラックリスト方式）
        for adj in adjacents:
            if isinstance(adj, tuple) and adj[0] == "J":
                continue
            if stone[0] != adj[0] and stone[1] != adj[1]:
                return False
        return True


def check_stalemate(g):
    """現在の手番石が盤面のどこにも置けない場合 True を返す。"""
    if not g.current_stone:
        return False
    for y in range(BOARD_ROWS):
        for x in range(BOARD_COLS):
            if is_placeable(g, x, y, g.current_stone):
                return False
    return True


def check_board_full(g):
    """盤面が全マス埋まっているか判定する（ENDLESS CONGRATULATIONS!条件）。"""
    for y in range(BOARD_ROWS):
        for x in range(BOARD_COLS):
            if g.board[y][x] is None:
                return False
    return True


def check_board_empty(g):
    """持ち石が全て消えたかどうかを判定する（ENDLESS 全消しボーナス用）。
    JOKER石は持ち石ではないため判定から除外する。
    """
    for y in range(BOARD_ROWS):
        for x in range(BOARD_COLS):
            stone = g.board[y][x]
            if stone is None:
                continue
            if isinstance(stone, tuple) and stone[0] == "J":
                continue
            return False
    return True


def count_board_stones(g):
    """盤面上の持ち石の数を返す（JOKER石は除外）。"""
    count = 0
    for y in range(BOARD_ROWS):
        for x in range(BOARD_COLS):
            stone = g.board[y][x]
            if stone and not (isinstance(stone, tuple) and stone[0] == "J"):
                count += 1
    return count


def get_adj_directions(g, x, y):
    """指定セルの隣接石がある方向を時計回り順で返す。"""
    dirs = []
    for d in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
        nx, ny = x + d[0], y + d[1]
        if 0 <= nx < BOARD_COLS and 0 <= ny < BOARD_ROWS and g.board[ny][nx]:
            dirs.append(d)
    return dirs


# ------------------------------------------------------------------ #
#  UNDO / JOKER 操作
# ------------------------------------------------------------------ #

def undo(g):
    """一手戻す。履歴がある場合のみ実行し、成否を返す。"""
    if g.history:
        g.board, g.bag, g.current_stone, g.stats, g.sub_bag = g.history.pop()
        g.game_state    = STATE_PLAYING
        g.effects       = effect.EffectManager()
        g.undo_interval = 10
        return True
    return False


def activate_joker(g, mode):
    """ジョーカー石を選択し、COLOR/NUMBER モードで手番に加える。"""
    g.joker_panel_open  = False
    g.joker_mode        = mode
    g.joker_saved_stone = g.current_stone
    g.current_stone     = JOKER_COLOR if mode == "C" else JOKER_NUMBER
    g.history           = []
    g.joker_count      -= 1
    g.se.play_joker_only(1)


def cancel_joker(g):
    """ジョーカーパネルを閉じる（[B] BACK）。"""
    g.joker_panel_open = False


def trigger_hint(g):
    """ヒント表示のオン・オフを切り替える。"""
    g.hint_config_on = not g.hint_config_on
    if g.hint_config_on:
        g.force_hint_timer = 120


# ------------------------------------------------------------------ #
#  ENDLESS 専用処理
# ------------------------------------------------------------------ #

def endless_draw_next_stone(g):
    """ENDLESS MODE: メイン袋から次の石を引く。
    メイン袋が空の場合はサブ袋を昇格してループカウントを上げる。
    """
    if g.bag:
        return g.bag.pop()
    if g.sub_bag:
        random.shuffle(g.sub_bag)
        g.bag         = g.sub_bag
        g.sub_bag     = []
        g.loop_count  += 1
        g.joker_count += 2
        g.se.play_loop_and_joker(2)
        return g.bag.pop()
    return None


def endless_board_clear_restart(g):
    """全消しボーナス後: 四隅に石を再配置＋JOKER1個付与してゲーム継続。"""
    for x, y in [(0, 0), (11, 0), (0, 7), (11, 7)]:
        if g.bag:
            g.board[y][x] = g.bag.pop()
        elif g.sub_bag:
            random.shuffle(g.sub_bag)
            g.bag         = g.sub_bag
            g.sub_bag     = []
            g.loop_count += 1
            g.board[y][x] = g.bag.pop()
    g.joker_count += 1
    g.se.play_joker_only(1)
    # 手持ちがない場合のみ次の石を引く（JOKERで全消し時は saved_stone が残っている）
    if not g.current_stone:
        g.current_stone = endless_draw_next_stone(g)


# ------------------------------------------------------------------ #
#  石の配置（_place_stone）
# ------------------------------------------------------------------ #

def place_stone(g):
    """カーソル位置に手番石を置く。戻り値は配置成功の bool。"""
    from effect import EffectManager as _EM
    from constants import STATE_RESULT, STATE_STALEMATE

    if not (g.current_stone and is_placeable(g, g.cursor_x, g.cursor_y, g.current_stone)):
        return False

    g.se.play_place_ok()
    adj_dirs = get_adj_directions(g, g.cursor_x, g.cursor_y)
    adj      = len(adj_dirs)
    is_joker = (isinstance(g.current_stone, tuple) and g.current_stone[0] == "J")

    # 履歴保存
    g.history.append((
        [row[:] for row in g.board],
        g.bag[:],
        g.joker_saved_stone if is_joker else g.current_stone,
        g.stats.copy(),
        g.sub_bag[:],
    ))

    # 2WAY以上 → 統計＋エフェクト
    if adj >= 2:
        g.stats[f"{adj}WAY"] += 1
        cx = g.offset_x + g.cursor_x * g.gap_x + g.sw // 2
        cy = g.offset_y + g.cursor_y * g.gap_y + g.sh // 2
        g.effects.trigger_way_lines(cx, cy, adj_dirs)
        if adj == 4:
            g.effects.trigger_4way(cx, cy, 15)
            g.se.play_4way_match()
        else:
            g.se.play_way_match()

    # 石を配置
    g.board[g.cursor_y][g.cursor_x] = g.current_stone

    if is_joker:
        if g.game_mode == MODE_ENDLESS and adj >= 2:
            dissolve_data = []
            g.board[g.cursor_y][g.cursor_x] = None
            for dx, dy in adj_dirs:
                tx, ty = g.cursor_x + dx, g.cursor_y + dy
                stone  = g.board[ty][tx]
                if stone and stone[0] != "J":
                    bx = g.offset_x + tx * g.gap_x
                    by = g.offset_y + ty * g.gap_y
                    dissolve_data.append((bx, by, stone[0], stone[1]))
                    g.sub_bag.append(stone)
                    g.board[ty][tx] = None
            if dissolve_data:
                g.effects.trigger_dissolve(dissolve_data)
            if check_board_empty(g):
                g.effects.trigger_board_clear_bonus()
                g.game_state        = STATE_STALEMATE  # 演出中の入力をブロック
                g.current_stone     = g.joker_saved_stone
                g.joker_mode        = None
                g.joker_saved_stone = None
                return True
        g.current_stone     = g.joker_saved_stone
        g.joker_mode        = None
        g.joker_saved_stone = None

    elif g.game_mode == MODE_ENDLESS:
        g.current_stone = endless_draw_next_stone(g)
        if adj >= 2:
            dissolve_data = []
            placed_stone = g.board[g.cursor_y][g.cursor_x]
            if placed_stone and placed_stone[0] != "J":
                bx = g.offset_x + g.cursor_x * g.gap_x
                by = g.offset_y + g.cursor_y * g.gap_y
                dissolve_data.append((bx, by, placed_stone[0], placed_stone[1]))
                g.sub_bag.append(placed_stone)
                g.board[g.cursor_y][g.cursor_x] = None
            for dx, dy in adj_dirs:
                tx, ty = g.cursor_x + dx, g.cursor_y + dy
                stone  = g.board[ty][tx]
                if stone:
                    bx = g.offset_x + tx * g.gap_x
                    by = g.offset_y + ty * g.gap_y
                    is_adj_joker = isinstance(stone, tuple) and stone[0] == "J"
                    if is_adj_joker:
                        dissolve_data.append((bx, by, 7, 0))
                    else:
                        dissolve_data.append((bx, by, stone[0], stone[1]))
                        g.sub_bag.append(stone)
                    g.board[ty][tx] = None
            if dissolve_data:
                g.effects.trigger_dissolve(dissolve_data)
            if check_board_empty(g):
                g.effects.trigger_board_clear_bonus()
                g.game_state = STATE_STALEMATE  # 演出中の入力をブロック
                return True
    else:
        g.current_stone = g.bag.pop() if g.bag else None

    # 終了判定
    if g.game_mode == MODE_ENDLESS:
        if check_board_full(g):
            g.game_state = STATE_RESULT
            g.effects.start_victory()
        elif not g.current_stone:
            g.game_state = STATE_STALEMATE
            g.effects.trigger_stalemate()
        elif check_stalemate(g):
            g.game_state = STATE_STALEMATE
            g.effects.trigger_stalemate(is_joker_rescue=(g.joker_count > 0))
    else:
        if not g.current_stone and not g.bag:
            if adj >= 2:
                way_duration = _EM._LINE_GROW_FRAMES + (adj - 1) * _EM._LINE_OFFSET + 8
                g.victory_delay = way_duration + 5
            else:
                g.game_state = STATE_RESULT
                g.effects.start_victory()
        elif check_stalemate(g):
            g.game_state = STATE_STALEMATE
            g.effects.trigger_stalemate()

    return True
