# title: I LOVE ISHIDO
# author: KINA
# desc: A reimagining of the classic stone-placement game ISHIDO. Three modes: ALL WAYS, ISHIDO+, and ENDLESS ISHIDO++.
# site: https://github.com/KINAppp
# license: MIT
# version: 1.0.0

import pyxel
import math
import block
import se
import bgm
import effect

try:
    import js
    IS_WEB = True
except ImportError:
    import webbrowser
    IS_WEB = False

# ------------------------------------------------------------------ #
#  定数
# ------------------------------------------------------------------ #

# 盤面パラメータ
BOARD_COLS  = 12
BOARD_ROWS  = 8
STONE_W     = 16
STONE_H     = 24
GAP_X       = 18
GAP_Y       = 26
OFFSET_X    = 20
OFFSET_Y    = 8

# UI エリア
UI_ROW_Y    = 228
BTN_W       = 14
BTN_H       = 22

# ゲーム状態
STATE_START     = "START"
STATE_PLAYING   = "PLAYING"
STATE_RESULT    = "RESULT"
STATE_STALEMATE = "STALEMATE"

# ゲームモード
MODE_ISHIDO   = "ISHIDO+"          # XOR ルール（独自強化版）
MODE_ALL_WAYS = "ALL WAYS"         # OR ルール（本家準拠）
MODE_ENDLESS  = "ENDLESS ISHIDO++"  # XOR ルール＋JOKER

# ENDLESS MODE: 盤面全埋めを判定するマス数
BOARD_TOTAL_CELLS = BOARD_COLS * BOARD_ROWS  # 96

# ジョーカー石の内部表現
JOKER_COLOR  = ("J", "C")   # COLOR モードで選択されたジョーカー
JOKER_NUMBER = ("J", "N")   # NUMBER モードで選択されたジョーカー

# ヒントのアイドル発火しきい値（フレーム）
HINT_IDLE_THRESHOLD = 1200
HINT_CYCLE          = 240
HINT_ACTIVE_FRAMES  = 120

class Ishido:
    """石道ゲームのメインクラス。"""

    def __init__(self):
        pyxel.init(256, 256, title="I LOVE ISHIDO")
        self._setup_palette()
        self.se  = se.SEPlayer()
        self.bgm = bgm.BGMPlayer()
        self.effects = effect.EffectManager()

        # 盤面・UI 座標
        self.sw, self.sh   = STONE_W, STONE_H
        self.gap_x         = GAP_X
        self.gap_y         = GAP_Y
        self.offset_x      = OFFSET_X
        self.offset_y      = OFFSET_Y
        self.board_right   = self.offset_x + BOARD_COLS * self.gap_x - 2
        self.ui_row_y      = UI_ROW_Y
        self.btn_w         = BTN_W
        self.btn_h         = BTN_H
        self.btn_reload_x  = self.board_right - self.btn_w        # R: 右端
        self.btn_hint_x   = self.btn_reload_x - 20               # H: 右から2番目
        self.btn_undo_x   = self.btn_hint_x   - 20               # U: 右から3番目
        self.btn_joker_x  = self.btn_undo_x   - 24               # J: 左端（ENDLESS のみ）

        # ゲーム状態
        self.game_state           = STATE_START
        self.game_mode            = MODE_ALL_WAYS  # デフォルトは本家準拠モード
        self.show_hint_spiritual  = False
        self.undo_interval        = 0

        # カーソル・マウス
        self.cursor_x      = 0
        self.cursor_y      = 0
        self.prev_mouse_x  = 0
        self.prev_mouse_y  = 0
        self.victory_delay = 0

        # リロード確認ダイアログ
        self.confirm_reload  = False

        # タイトルへ戻る確認ダイアログ
        self.confirm_title   = False

        # ✕ボタン（右上・スタート画面以外で常時表示）
        # 正方形 12×12、盤面右端(234)より少し離して配置
        self.btn_x_x  = 241
        self.btn_x_y  = 3
        self.btn_x_w  = 12
        self.btn_x_h  = 12

        # ジョーカー石の状態（ENDLESS MODE 専用）
        self.joker_panel_open  = False        # パネル表示中
        self.joker_mode        = None         # "C" / "N" / None
        self.joker_saved_stone = None         # ジョーカー使用中の本来の NEXT 石

        # ENDLESS MODE 用フィールド（他モードでは未使用）
        self.sub_bag     = []  # WAY で消えた石が入るサブ袋
        self.loop_count  = 0   # メイン袋消化完了回数
        self.joker_count = 0   # ジョーカー石の所持数（第3段階で本格実装）

        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------ #
    #  初期化
    # ------------------------------------------------------------------ #

    def _setup_palette(self):
        """ゲーム用カラーパレットを設定する。
        0〜9: UI 用グレースケール系
        10〜15: 石のカラーパネル用（赤・青・黄・緑・紫・水色）
        """
        colors = [
            0x000000, 0xffffff, 0x222222, 0x444444,
            0x666666, 0x888888, 0x999999, 0xaaaaaa,
            0xbbbbbb, 0xcccccc, 0xcc4444, 0x4444cc,
            0xcccc44, 0x44cc44, 0xcc44cc, 0x44cccc,
        ]
        for i, c in enumerate(colors):
            pyxel.colors[i] = c

    def restart_game(self):
        """ゲームを初期状態にリセットして開始する。"""
        self.bag     = block.Block.get_initial_bag()
        self.board   = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
        self.history = []
        self.stats   = {"4WAY": 0, "3WAY": 0, "2WAY": 0}

        self.idle_timer       = 0
        self.hint_config_on   = False
        self.force_hint_timer = 0
        self.victory_delay    = 0
        self.confirm_reload    = False
        self.confirm_title     = False
        self.joker_panel_open  = False
        self.joker_mode        = None
        self.joker_saved_stone = None
        self.game_state        = STATE_PLAYING
        self.effects          = effect.EffectManager()

        # ENDLESS MODE 専用フィールドをリセット
        self.sub_bag    = []
        self.loop_count = 0
        # ENDLESS は最初から JOKER:1 を持ってスタート（序盤の色偏り救済）
        self.joker_count = 1 if self.game_mode == MODE_ENDLESS else 0

        pyxel.title(f"I LOVE ISHIDO [MODE: {self.game_mode}]")

        # 初期配置（四隅＋中央2マス）
        for x, y in [(0, 0), (11, 0), (0, 7), (11, 7), (5, 3), (6, 4)]:
            if self.bag:
                self.board[y][x] = self.bag.pop()

        self.current_stone = self.bag.pop() if self.bag else None

        # 初手詰まりチェック
        if self._check_stalemate():
            self.game_state = STATE_STALEMATE
            self.effects.trigger_stalemate(is_initial=True)

    # ------------------------------------------------------------------ #
    #  ゲームロジック
    # ------------------------------------------------------------------ #

    def is_placeable(self, x, y, stone):
        """指定セルに stone を置けるかどうかを返す。"""
        if self.board[y][x] is not None:
            return False

        adjacents = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < BOARD_COLS and 0 <= ny < BOARD_ROWS:
                if self.board[ny][nx]:
                    adjacents.append(self.board[ny][nx])

        if not adjacents:
            return False

        # ジョーカー石は隣接石さえあればどこでも置ける
        if isinstance(stone, tuple) and stone[0] == "J":
            return True

        if self.game_mode in (MODE_ISHIDO, MODE_ENDLESS):
            # ISHIDO / ENDLESS: XORルール
            # 全隣接石と「色か数字のどちらか一方だけ」一致する必要がある
            # 完全一致（同色同数字）も、完全不一致も不可
            # ただし盤面上のJOKER石は隣接チェックをスキップ（万能扱い）
            for adj in adjacents:
                if isinstance(adj, tuple) and adj[0] == "J":
                    continue  # JOKER隣接石はどんな石でも受け入れる
                color_match  = (stone[0] == adj[0])
                number_match = (stone[1] == adj[1])
                if not (color_match ^ number_match):
                    return False
            return True
        else:
            # ALL WAYS: いずれか一つと色または数字が一致すれば置ける
            # 盤面上のJOKER石は常に一致扱い
            for adj in adjacents:
                if isinstance(adj, tuple) and adj[0] == "J":
                    return True
                if stone[0] == adj[0] or stone[1] == adj[1]:
                    return True
            return False

    def _check_stalemate(self):
        """現在の手番石が盤面のどこにも置けない場合 True を返す。"""
        if not self.current_stone:
            return False
        for y in range(BOARD_ROWS):
            for x in range(BOARD_COLS):
                if self.is_placeable(x, y, self.current_stone):
                    return False
        return True

    def _check_board_full(self):
        """盤面が全マス埋まっているか判定する（ENDLESS MODE 終了条件）。"""
        for y in range(BOARD_ROWS):
            for x in range(BOARD_COLS):
                if self.board[y][x] is None:
                    return False
        return True

    def _check_board_empty(self):
        """盤面が完全に空かどうかを判定する（ENDLESS MODE 全消しボーナス用）。"""
        for y in range(BOARD_ROWS):
            for x in range(BOARD_COLS):
                if self.board[y][x] is not None:
                    return False
        return True

    def _endless_board_clear_restart(self):
        """全消しボーナス後の処理: 四隅に石を配置＋JOKER石を1個付与してゲーム継続。"""
        # 四隅のみ再配置（中央2枚なし）
        for x, y in [(0, 0), (11, 0), (0, 7), (11, 7)]:
            if self.bag:
                self.board[y][x] = self.bag.pop()
            elif self.sub_bag:
                import random
                random.shuffle(self.sub_bag)
                self.bag    = self.sub_bag
                self.sub_bag = []
                self.loop_count += 1
                self.board[y][x] = self.bag.pop()
        # JOKER 1個プレゼント＋SE
        self.joker_count += 1
        self.se.play_joker_only(1)
        # 次の手番石を引く
        self.current_stone = self._endless_draw_next_stone()

    def _endless_draw_next_stone(self):
        """ENDLESS MODE 専用：メイン袋から次の石を引く。
        メイン袋が空の場合はサブ袋をメイン袋に昇格してループカウントを上げる。
        両方空の場合は None を返す。
        """
        if self.bag:
            return self.bag.pop()
        if self.sub_bag:
            import random
            random.shuffle(self.sub_bag)
            self.bag      = self.sub_bag
            self.sub_bag  = []
            self.loop_count  += 1
            self.joker_count += 2  # ループ達成ボーナス（LOOP:1以降は常に2個）
            self.se.play_loop_and_joker(2)  # LOOP UP + JOKER×2 SE
            return self.bag.pop()
        return None

    def _get_adj_directions(self, x, y):
        """指定セルの隣接石がある方向を時計回り（上→右→下→左）順で返す。
        effect.trigger_way_lines() に渡すリストとして使用する。
        """
        dirs = []
        for d in [(0, -1), (1, 0), (0, 1), (-1, 0)]:  # 時計回り順
            nx, ny = x + d[0], y + d[1]
            if 0 <= nx < BOARD_COLS and 0 <= ny < BOARD_ROWS and self.board[ny][nx]:
                dirs.append(d)
        return dirs

    def _undo(self):
        """一手戻す。履歴がある場合のみ実行し、成否を返す。"""
        if self.history:
            self.board, self.bag, self.current_stone, self.stats = self.history.pop()
            self.game_state = STATE_PLAYING
            self.effects    = effect.EffectManager()
            self.undo_interval = 10
            return True
        return False

    def _trigger_hint(self):
        """ヒント表示のオン・オフを切り替える。"""
        self.hint_config_on = not self.hint_config_on
        if self.hint_config_on:
            self.force_hint_timer = 120

    def _activate_joker(self, mode):
        """ジョーカー石を選択し、COLOR/NUMBER モードで手番に加える。
        UNDO 履歴をクリアして joker_count を消費する。
        """
        self.joker_panel_open  = False
        self.joker_mode        = mode
        self.joker_saved_stone = self.current_stone
        self.current_stone     = JOKER_COLOR if mode == "C" else JOKER_NUMBER
        self.history           = []          # ストロングスタイル：UNDO 履歴クリア
        self.joker_count      -= 1
        self.se.play_joker_only(1)           # ジョーカー登場 SE

    def _cancel_joker(self):
        """ジョーカーパネルを閉じる（[B] BACK）。選択前のみ有効。"""
        self.joker_panel_open = False

    def _place_stone(self):
        """カーソル位置に手番石を置く。戻り値は配置成功の bool。"""
        if not (self.current_stone and self.is_placeable(self.cursor_x, self.cursor_y, self.current_stone)):
            return False

        self.se.play_place_ok()
        adj_dirs = self._get_adj_directions(self.cursor_x, self.cursor_y)
        adj      = len(adj_dirs)
        is_joker = (isinstance(self.current_stone, tuple) and self.current_stone[0] == "J")

        # 履歴を保存（ジョーカー使用時は既にクリア済み）
        self.history.append((
            [row[:] for row in self.board],
            self.bag[:],
            self.joker_saved_stone if is_joker else self.current_stone,
            self.stats.copy(),
        ))

        # 2WAY 以上なら統計更新＋エフェクト発火
        if adj >= 2:
            self.stats[f"{adj}WAY"] += 1
            cx = self.offset_x + self.cursor_x * self.gap_x + self.sw // 2
            cy = self.offset_y + self.cursor_y * self.gap_y + self.sh // 2
            self.effects.trigger_way_lines(cx, cy, adj_dirs)
            if adj == 4:
                self.effects.trigger_4way(cx, cy, 15)
                self.se.play_4way_match()
            else:
                self.se.play_way_match()

        # 石を配置
        self.board[self.cursor_y][self.cursor_x] = self.current_stone

        if is_joker:
            # ジョーカー使用後: saved_stone を NEXT に戻し、ジョーカー状態をリセット
            if self.game_mode == MODE_ENDLESS:
                # ENDLESS: WAY達成 → ジョーカー自身は消滅、隣接石のみサブ袋へ
                if adj >= 2:
                    dissolve_data = []
                    # ジョーカー石は即消去（サブ袋に入らない）
                    self.board[self.cursor_y][self.cursor_x] = None
                    # 隣接石はサブ袋へ返却＋ディゾルブ
                    for dx, dy in adj_dirs:
                        tx, ty = self.cursor_x + dx, self.cursor_y + dy
                        stone  = self.board[ty][tx]
                        if stone and stone[0] != "J":  # ジョーカー以外
                            bx = self.offset_x + tx * self.gap_x
                            by = self.offset_y + ty * self.gap_y
                            dissolve_data.append((bx, by, stone[0], stone[1]))
                            self.sub_bag.append(stone)
                            self.board[ty][tx] = None
                    if dissolve_data:
                        self.effects.trigger_dissolve(dissolve_data)
                    if self._check_board_empty():
                        self.effects.trigger_board_clear_bonus()
                        self.current_stone  = self.joker_saved_stone
                        self.joker_mode        = None
                        self.joker_saved_stone = None
                        return True
            self.current_stone     = self.joker_saved_stone
            self.joker_mode        = None
            self.joker_saved_stone = None
        elif self.game_mode == MODE_ENDLESS:
            self.current_stone = self._endless_draw_next_stone()
            # ENDLESS 通常石: WAY達成 → 置いた石＋隣接石をサブ袋へ
            if adj >= 2:
                dissolve_data = []
                placed_stone = self.board[self.cursor_y][self.cursor_x]
                if placed_stone and placed_stone[0] != "J":
                    bx = self.offset_x + self.cursor_x * self.gap_x
                    by = self.offset_y + self.cursor_y * self.gap_y
                    dissolve_data.append((bx, by, placed_stone[0], placed_stone[1]))
                    self.sub_bag.append(placed_stone)
                    self.board[self.cursor_y][self.cursor_x] = None
                for dx, dy in adj_dirs:
                    tx, ty = self.cursor_x + dx, self.cursor_y + dy
                    stone  = self.board[ty][tx]
                    if stone:
                        bx = self.offset_x + tx * self.gap_x
                        by = self.offset_y + ty * self.gap_y
                        is_adj_joker = isinstance(stone, tuple) and stone[0] == "J"
                        if is_adj_joker:
                            # JOKER は消えるがサブ袋には戻らない
                            dissolve_data.append((bx, by, 7, 0))  # グレーでディゾルブ
                        else:
                            dissolve_data.append((bx, by, stone[0], stone[1]))
                            self.sub_bag.append(stone)
                        self.board[ty][tx] = None
                if dissolve_data:
                    self.effects.trigger_dissolve(dissolve_data)
                if self._check_board_empty():
                    self.effects.trigger_board_clear_bonus()
                    return True
        else:
            self.current_stone = self.bag.pop() if self.bag else None

        # 終了判定
        if self.game_mode == MODE_ENDLESS:
            if self._check_board_full():
                self.game_state = STATE_RESULT
                self.effects.start_victory()
            elif not self.current_stone:
                self.game_state = STATE_STALEMATE
                self.effects.trigger_stalemate()
            elif self._check_stalemate():
                self.game_state = STATE_STALEMATE
                # ジョーカーが残っている場合は特別な STALEMATE（投了 or JOKER 使用を選べる）
                self.effects.trigger_stalemate(is_joker_rescue=(self.joker_count > 0))
        else:
            if not self.current_stone and not self.bag:
                if adj >= 2:
                    from effect import EffectManager as _EM
                    way_duration = _EM._LINE_GROW_FRAMES + (adj - 1) * _EM._LINE_OFFSET + 8
                    self.victory_delay = way_duration + 5
                else:
                    self.game_state = STATE_RESULT
                    self.effects.start_victory()
            elif self._check_stalemate():
                self.game_state = STATE_STALEMATE
                self.effects.trigger_stalemate()

        return True

    # ------------------------------------------------------------------ #
    #  更新（状態別）
    # ------------------------------------------------------------------ #

    def update(self):
        """メインループの更新処理。"""
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        if self.undo_interval > 0:
            self.undo_interval -= 1

        if self.game_state == STATE_START:
            self._handle_input_start(mx, my)
            return

        if self.game_state in [STATE_RESULT, STATE_STALEMATE]:
            self._handle_input_result(mx, my)
            return

        self._handle_input_playing(mx, my)
    def _open_how_to_play(self):
        """ローカルとWebで適切にHow To Playページを開く"""
        url = "https://kinappp.github.io/i-love-ishido/howtoplay.html"
        if IS_WEB:
            js.window.open(url, "_blank")  # Web版はJavaScriptの機能で別タブを開く
        else:
            webbrowser.open(url)           # ローカル版は標準ブラウザを開く

    def _handle_input_start(self, mx, my):
        """スタート画面の入力処理。
        表示順: [A] ALL WAYS → [I] ISHIDO+ → [E] ENDLESS ISHIDO++ → [H] HOW TO PLAY
        """
        if pyxel.btnp(pyxel.KEY_A):
            self.game_mode = MODE_ALL_WAYS
            self.restart_game()
        if pyxel.btnp(pyxel.KEY_I):
            self.game_mode = MODE_ISHIDO
            self.restart_game()
        if pyxel.btnp(pyxel.KEY_E):
            self.game_mode = MODE_ENDLESS
            self.restart_game()
        if pyxel.btnp(pyxel.KEY_H):
            self._open_how_to_play()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and 80 <= mx <= 210:
            if 155 <= my <= 170:
                self.game_mode = MODE_ALL_WAYS
                self.restart_game()
            elif 172 <= my <= 187:
                self.game_mode = MODE_ISHIDO
                self.restart_game()
            elif 189 <= my <= 204:
                self.game_mode = MODE_ENDLESS
                self.restart_game()
            elif 212 <= my <= 227:
                self._open_how_to_play()

    def _handle_input_result(self, mx, my):
        """RESULT / STALEMATE 状態の入力処理。"""
        self.effects.update()

        # THE PATH シーケンス完了 → リロード
        if self.effects.path_done:
            self.restart_game()
            return

        # 全消しボーナス完了 → 四隅再配置＋JOKER付与でゲーム継続
        if self.effects.board_clear_done:
            self.effects.board_clear_done = False
            self.game_state = STATE_PLAYING
            self._endless_board_clear_restart()
            return

        # THE PATH シーケンス中は他の入力を受け付けない
        if self.effects.path_sequence_active:
            return

        # 初手詰まりは一定時間後に自動リスタート
        if self.game_state == STATE_STALEMATE and self.effects.is_initial_stalemate:
            if self.effects.result_timer > 100:
                self.restart_game()
            return

        if self.effects.result_timer > 100:
            if self.game_state == STATE_RESULT:
                if pyxel.btnp(pyxel.KEY_G):
                    self.restart_game()
                if pyxel.btnp(pyxel.KEY_T):
                    self.game_state = STATE_START
                if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    # [G] GO AGAIN: x=104, y=162
                    if 104 <= mx <= 152 and 162 <= my <= 172:
                        self.restart_game()
                    # [T] TITLE: x=104, y=177
                    if 104 <= mx <= 140 and 177 <= my <= 187:
                        self.game_state = STATE_START

        if self.game_state == STATE_STALEMATE and self.effects.result_timer > 60:
            # JOKER rescue: JOKER残りで詰まった場合 → [J] で JOKER 使用、[R] で投了
            if self.effects.is_joker_rescue:
                use_joker = pyxel.btnp(pyxel.KEY_J) or (
                    pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and (
                        # [J] ボタン
                        (self.btn_joker_x <= mx < self.btn_joker_x + self.btn_w
                         and self.ui_row_y <= my < self.ui_row_y + self.btn_h)
                        # 帯内 [J] USE JOKER テキスト
                        or (72 <= mx <= 120 and 139 <= my <= 149)
                    )
                )
                give_up = (
                    pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                    and 130 <= mx <= 178 and 139 <= my <= 149
                )
                if use_joker:
                    self.game_state           = STATE_PLAYING
                    self.effects.is_stalemate = False
                    self.joker_panel_open     = True
                    return
                if give_up:
                    # [R] GIVE UP → ENDLESS は即リスタート
                    self.restart_game()
                    return

            is_reload = pyxel.btnp(pyxel.KEY_R) or (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and self.btn_reload_x <= mx < self.btn_reload_x + self.btn_w
                and self.ui_row_y <= my < self.ui_row_y + self.btn_h
            )
            if is_reload:
                if self.game_mode == MODE_ISHIDO and not self.effects.is_initial_stalemate:
                    self.effects.trigger_path_sequence()
                else:
                    self.restart_game()

            is_undo = (
                pyxel.btnp(pyxel.KEY_U)
                or pyxel.btnp(pyxel.KEY_BACKSPACE)
                or (self.undo_interval == 0 and (
                    pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT)
                    or (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                        and self.btn_undo_x <= mx < self.btn_undo_x + self.btn_w
                        and self.ui_row_y <= my < self.ui_row_y + self.btn_h)
                ))
            )
            if is_undo:
                self._undo()

    def _handle_input_playing(self, mx, my):
        """ゲームプレイ中の入力処理。"""
        input_active = False

        # タイトルへ戻る確認ダイアログ
        if self.confirm_title:
            if pyxel.btnp(pyxel.KEY_Y) or (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and 88 <= mx <= 120 and 126 <= my <= 136
            ):
                self.confirm_title = False
                self.game_state    = STATE_START
                return
            if pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE) or (
                pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and 132 <= mx <= 164 and 126 <= my <= 136
            ):
                self.confirm_title = False
            return

        # ✕ボタン（右上）のクリック
        if (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                and self.btn_x_x <= mx < self.btn_x_x + self.btn_x_w
                and self.btn_x_y <= my < self.btn_x_y + self.btn_x_h
                and not self.confirm_title):
            self.confirm_title = True
            return

        # ジョーカーパネル操作（パネルが開いている間は他の入力をブロック）
        if self.joker_panel_open:
            if pyxel.btnp(pyxel.KEY_C):
                self._activate_joker("C")
            elif pyxel.btnp(pyxel.KEY_N):
                self._activate_joker("N")
            elif pyxel.btnp(pyxel.KEY_B) or pyxel.btnp(pyxel.KEY_ESCAPE):
                self._cancel_joker()
            elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if 72 <= mx <= 108 and 118 <= my <= 128:   # [C] COLOR
                    self._activate_joker("C")
                elif 144 <= mx <= 184 and 118 <= my <= 128: # [N] NUMBER
                    self._activate_joker("N")
                elif 112 <= mx <= 144 and 130 <= my <= 140: # [B] BACK
                    self._cancel_joker()
            return  # パネル中は他の入力を受け付けない

        # ジョーカーボタン [J]（ENDLESS MODE のみ）
        if self.game_mode == MODE_ENDLESS and not self.joker_mode:
            if pyxel.btnp(pyxel.KEY_J) and self.joker_count > 0:
                self.joker_panel_open = True
            if (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                    and self.btn_joker_x <= mx < self.btn_joker_x + self.btn_w
                    and self.ui_row_y <= my < self.ui_row_y + self.btn_h
                    and self.joker_count > 0):
                self.joker_panel_open = True

        # リスタート（確認ダイアログ）
        if self.confirm_reload:
            # キーボード操作
            if pyxel.btnp(pyxel.KEY_Y):
                self.confirm_reload = False
                self.restart_game()
                return
            if pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE):
                self.confirm_reload = False
                input_active = True
                return
            # マウスクリック操作
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if 96 <= mx <= 124 and 126 <= my <= 136:   # [Y] YES
                    self.confirm_reload = False
                    self.restart_game()
                    return
                if 128 <= mx <= 152 and 126 <= my <= 136:  # [N] NO
                    self.confirm_reload = False
                    input_active = True
            return  # 確認中は他の入力を受け付けない

        if pyxel.btnp(pyxel.KEY_R):
            self.confirm_reload = True
            input_active = True
        if pyxel.btnp(pyxel.KEY_H):
            self._trigger_hint()
            input_active = True

        # アンドゥ判定（ジョーカー使用中は無効）
        is_undo = False if self.joker_mode else (
            pyxel.btnp(pyxel.KEY_U) or pyxel.btnp(pyxel.KEY_BACKSPACE))
        if self.undo_interval == 0:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
                is_undo = True
            if (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
                    and self.btn_undo_x <= mx < self.btn_undo_x + self.btn_w
                    and self.ui_row_y <= my < self.ui_row_y + self.btn_h):
                is_undo = True
        if is_undo and self._undo():
            input_active = True

        # ボタンエリアのクリック
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.ui_row_y <= my < self.ui_row_y + self.btn_h:
            if self.btn_hint_x <= mx < self.btn_hint_x + self.btn_w:
                self._trigger_hint()
                input_active = True
            if self.btn_reload_x <= mx < self.btn_reload_x + self.btn_w:
                self.confirm_reload = True
                input_active = True

        # カーソル更新（盤面内のみ）
        if (self.offset_x <= mx < self.offset_x + BOARD_COLS * self.gap_x
                and self.offset_y <= my < self.offset_y + BOARD_ROWS * self.gap_y):
            self.cursor_x = (mx - self.offset_x) // self.gap_x
            self.cursor_y = (my - self.offset_y) // self.gap_y

        # 石の配置
        is_place = pyxel.btnp(pyxel.KEY_SPACE) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and my < self.ui_row_y
        )
        if is_place:
            if self._place_stone():
                input_active = True
            elif self.current_stone:
                # 置けない場所への操作 → エラー SE
                self.se.play_place_ng()

        # アイドルタイマーとヒント制御
        mouse_moved = (mx != self.prev_mouse_x or my != self.prev_mouse_y)
        if input_active or mouse_moved:
            self.idle_timer = 0
        else:
            self.idle_timer += 1

        self.prev_mouse_x, self.prev_mouse_y = mx, my

        hint_cycle_active = (
            (self.idle_timer - HINT_IDLE_THRESHOLD) % HINT_CYCLE < HINT_ACTIVE_FRAMES
        )
        self.show_hint_spiritual = (
            self.force_hint_timer > 0
            or (self.hint_config_on and self.idle_timer > HINT_IDLE_THRESHOLD and hint_cycle_active)
        )
        if self.force_hint_timer > 0:
            self.force_hint_timer -= 1

        # 最終手が WAY だった場合の勝利演出遅延処理
        if self.victory_delay > 0:
            self.victory_delay -= 1
            if self.victory_delay == 0:
                self.game_state = STATE_RESULT
                self.effects.start_victory()

        self.effects.update()

    # ------------------------------------------------------------------ #
    #  描画
    # ------------------------------------------------------------------ #

    def draw(self):
        """メインループの描画処理。"""
        if self.game_state == STATE_START:
            self._draw_start_screen()
            return

        # 盤面背景
        pyxel.cls(8)

        # 盤面外枠（立体表現：石やボタンと同じベベル方式）
        _fx = self.offset_x - 4
        _fy = self.offset_y - 4
        _fw = BOARD_COLS * self.gap_x + 6
        _fh = BOARD_ROWS * self.gap_y + 6
        pyxel.rect(_fx,     _fy,     _fw,     _fh,     2)  # 右・下の影
        pyxel.rect(_fx,     _fy,     _fw - 2, _fh - 2, 9)  # 左・上のハイライト
        pyxel.rect(_fx + 2, _fy + 2, _fw - 4, _fh - 4, 4)  # 中央パネル

        # 盤面セルと石
        # セルカラーのルール:
        #   明るい（color 7）: 四隅・内側（x=1〜10, y=1〜6）・中央初期配置（5,3）（6,4）
        #   暗い（color 6）: 外周リング・中央対角（5,4）（6,3）
        # 中央2×2エリアは (5,3)(6,4)=明、(5,4)(6,3)=暗 のチェッカー模様
        _corners        = {(0, 0), (11, 0), (0, 7), (11, 7)}
        _center_dark    = {(5, 4), (6, 3)}   # 中央チェッカーの暗い対角
        for y in range(BOARD_ROWS):
            for x in range(BOARD_COLS):
                bx = self.offset_x + x * self.gap_x
                by = self.offset_y + y * self.gap_y
                is_inner  = 1 <= x <= 10 and 1 <= y <= 6
                is_corner = (x, y) in _corners
                is_c_dark = (x, y) in _center_dark
                if (is_inner or is_corner) and not is_c_dark:
                    cell_col = 7  # 明るいグレー
                else:
                    cell_col = 6  # 通常グレー
                pyxel.rect(bx, by, self.sw, self.sh, cell_col)
                if self.board[y][x]:
                    stone = self.board[y][x]
                    if isinstance(stone, tuple) and stone[0] == "J":
                        block.Block.draw_joker_stone(bx, by, stone[1])
                    else:
                        block.Block.draw_stone(bx, by, stone[0], stone[1])

        # ヒントオーバーレイ
        if self.show_hint_spiritual:
            self._draw_hint_overlay()

        # カーソル（置ける: 白、置けない: 赤）
        is_ok = self.current_stone and self.is_placeable(self.cursor_x, self.cursor_y, self.current_stone)
        pyxel.rectb(
            self.offset_x + self.cursor_x * self.gap_x,
            self.offset_y + self.cursor_y * self.gap_y,
            self.sw, self.sh,
            1 if is_ok else 10
        )

        # 情報エリア
        left = len(self.bag) + (1 if self.current_stone else 0)
        pyxel.text(self.offset_x, self.ui_row_y + 8, "NEXT:", 0)
        if self.current_stone:
            if isinstance(self.current_stone, tuple) and self.current_stone[0] == "J":
                block.Block.draw_joker_stone(
                    self.offset_x + 25, self.ui_row_y, self.current_stone[1]
                )
            else:
                block.Block.draw_stone(
                    self.offset_x + 25, self.ui_row_y,
                    self.current_stone[0], self.current_stone[1]
                )
        if self.game_mode == MODE_ENDLESS:
            # ENDLESS: LEFT/SUB を左ブロック、LOOP/JOKER を中ブロックに分けて表示
            pyxel.text(68, self.ui_row_y + 2,  f"LEFT:{left:02}", 0)
            pyxel.text(72, self.ui_row_y + 10, f"SUB:{len(self.sub_bag):02}", 0)
            pyxel.text(108, self.ui_row_y + 2,  f"LOOP:{self.loop_count}", 0)
            # JOKER: 所持数が1以上の時は赤固定
            joker_col = 10 if self.joker_count > 0 else 0
            pyxel.text(108, self.ui_row_y + 10, f"JOKER:{self.joker_count}", joker_col)
        else:
            pyxel.text(68, self.ui_row_y + 8, f"LEFT: {left}", 0)

        # ボタン（H: ヒント / U: アンドゥ / R: リスタート）
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        is_l   = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
        if self.game_mode == MODE_ENDLESS:
            joker_active = self.joker_count > 0 and not self.joker_mode
            self._draw_button_joker(
                self.btn_joker_x, self.ui_row_y,
                is_active=joker_active,
                is_pressed=(is_l and joker_active
                            and self.btn_joker_x <= mx < self.btn_joker_x + self.btn_w
                            and self.ui_row_y <= my < self.ui_row_y + self.btn_h)
            )
        self._draw_button(
            self.btn_hint_x, self.ui_row_y, "H",
            is_active=self.hint_config_on,
            is_pressed=(is_l and self.btn_hint_x <= mx < self.btn_hint_x + self.btn_w
                        and self.ui_row_y <= my < self.ui_row_y + self.btn_h)
        )
        self._draw_button(
            self.btn_undo_x, self.ui_row_y, "U",
            is_active=False,
            is_pressed=(is_l and self.btn_undo_x <= mx < self.btn_undo_x + self.btn_w
                        and self.ui_row_y <= my < self.ui_row_y + self.btn_h)
        )
        self._draw_button(
            self.btn_reload_x, self.ui_row_y, "R",
            is_active=False,
            is_pressed=(is_l and self.btn_reload_x <= mx < self.btn_reload_x + self.btn_w
                        and self.ui_row_y <= my < self.ui_row_y + self.btn_h)
        )

        # エフェクト（最前面）
        self.effects.draw(
            self.stats, left,
            loop=self.loop_count,
            joker=self.joker_count,
            is_endless=(self.game_mode == MODE_ENDLESS)
        )

        # ✕ボタン（右上・常時表示）
        self._draw_x_button()

        # ジョーカーパネル（最前面）
        if self.joker_panel_open:
            self._draw_joker_panel()

        # タイトルへ戻る確認ダイアログ
        if self.confirm_title:
            self._draw_confirm_title()

        # リロード確認ダイアログ（最前面・エフェクトより手前）
        if self.confirm_reload:
            self._draw_confirm_reload()

    def _draw_x_button(self):
        """右上の✕ボタンを描画する（スタート画面以外で常時表示）。"""
        x, y, w, h = self.btn_x_x, self.btn_x_y, self.btn_x_w, self.btn_x_h
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        is_hover = x <= mx < x + w and y <= my < y + h

        # ボタンベース
        base_col = 4 if is_hover else 6
        pyxel.rect(x, y, w, h, base_col)
        pyxel.line(x,         y,     x + w - 1, y,         7)
        pyxel.line(x,         y,     x,         y + h - 1, 7)
        pyxel.line(x + w - 1, y,     x + w - 1, y + h - 1, 2)
        pyxel.line(x,         y + h - 1, x + w - 1, y + h - 1, 2)

        # ✕の文字
        col = 1 if is_hover else 0
        pyxel.text(x + 4, y + 3, "X", col)

    def _draw_confirm_title(self):
        """タイトルへ戻る確認ダイアログを描画する。
        テキスト:
          "RETURN TO TITLE?" 16文字×4px=64px → x=96
          "[Y] YES"  x=88  / "[N] NO" x=132
        """
        pyxel.rect(0, 100, 256, 60, 8)
        pyxel.line(0, 100, 255, 100, 9)
        pyxel.line(0, 159, 255, 159, 2)
        pyxel.text(96, 112, "RETURN TO TITLE?", 1)
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        y_col = 0 if (88 <= mx <= 120 and 126 <= my <= 136) else 5
        n_col = 0 if (132 <= mx <= 164 and 126 <= my <= 136) else 5
        pyxel.text( 88, 128, "[Y] YES", y_col)
        pyxel.text(132, 128, "[N] NO",  n_col)

    def _draw_joker_panel(self):
        """ジョーカー石の COLOR / NUMBER 選択パネルを描画する。
        帯スタイル（y=100〜159）はSTALEMATE帯と同じ。
        レイアウト:
          y=108 USE JOKER STONE:  （16文字=64px → x=96）
          y=120 [C] COLOR（x=72）  [N] NUMBER（x=144）
          y=132 [B] BACK           （x=112、センタリング）
          y=146 UNDO WILL CLEAR    （x=98）
        """
        pyxel.rect(0, 100, 256, 60, 8)
        pyxel.line(0, 100, 255, 100, 9)
        pyxel.line(0, 159, 255, 159, 2)

        pyxel.text(96, 108, "USE JOKER STONE:", 1)

        mx, my = pyxel.mouse_x, pyxel.mouse_y
        c_col = 0 if (72 <= mx <= 108 and 118 <= my <= 128) else 5
        n_col = 0 if (144 <= mx <= 184 and 118 <= my <= 128) else 5
        b_col = 0 if (112 <= mx <= 144 and 130 <= my <= 140) else 5

        pyxel.text( 72, 120, "[C] COLOR",  c_col)
        pyxel.text(144, 120, "[N] NUMBER", n_col)
        pyxel.text(112, 132, "[B] BACK",   b_col)
        pyxel.text( 98, 146, "UNDO WILL CLEAR", 3)

    def _draw_confirm_reload(self):
        """リロード確認ダイアログを描画する。
        STALEMATE 帯と同じスタイルで中央に表示する。
        テキスト:
          "RELOAD?" 7文字 × 4px = 28px → x = 114
          "[Y] YES" 7文字 × 4px = 28px → x = 96
          "[N] NO"  6文字 × 4px = 24px → x = 136 （[Y] の [ に揃えた右側）
        """
        pyxel.rect(0, 100, 256, 60, 8)
        pyxel.line(0, 100, 255, 100, 9)   # 上辺ハイライト
        pyxel.line(0, 159, 255, 159, 2)   # 下辺影
        pyxel.text(114, 112, "RELOAD?", 1)
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        y_col = 0 if (96 <= mx <= 124 and 126 <= my <= 136) else 5
        n_col = 0 if (128 <= mx <= 152 and 126 <= my <= 136) else 5
        pyxel.text( 96, 128, "[Y] YES", y_col)
        pyxel.text(128, 128, "[N] NO",  n_col)

    def _draw_start_screen(self):
        """スタート画面を描画する。
        レイアウト:
          y=110  I LOVE ISHIDO   （センタリング）
          y=160  [I] ISHIDO MODE （センタリング）
          y=175  [A] ALL WAYS MODE（[I] の [ に左揃え）
        """
        pyxel.cls(7)
        pyxel.text(102, 110, "I LOVE ISHIDO", 2)

        mx, my = pyxel.mouse_x, pyxel.mouse_y
        # 表示順: [A] ALL WAYS → [I] ISHIDO+ → [E] ENDLESS ISHIDO++
        # x=94 で [の位置を揃える
        a_col = 0 if (80 <= mx <= 210 and 155 <= my <= 170) else 5
        i_col = 0 if (80 <= mx <= 210 and 172 <= my <= 187) else 5
        e_col = 0 if (80 <= mx <= 210 and 189 <= my <= 204) else 5
        h_col = 0 if (80 <= mx <= 210 and 212 <= my <= 227) else 5
        pyxel.text(94, 160, "[A] ALL WAYS MODE",    a_col)
        pyxel.text(94, 175, "[I] ISHIDO+ MODE",     i_col)
        pyxel.text(94, 190, "[E] ENDLESS ISHIDO++", e_col)
        pyxel.text(94, 210, "[H] HOW TO PLAY",      h_col)

    def _draw_button(self, x, y, label, is_active, is_pressed):
        """御札風ボタンを描画する。"""
        base_col = 4 if is_active else 6
        if is_pressed:
            base_col = 3
        pyxel.rect(x, y, self.btn_w, self.btn_h, base_col)
        pyxel.line(x,                  y,                  x + self.btn_w - 1, y,                  7)
        pyxel.line(x,                  y,                  x,                  y + self.btn_h - 1, 7)
        pyxel.line(x + self.btn_w - 1, y,                  x + self.btn_w - 1, y + self.btn_h - 1, 2)
        pyxel.line(x,                  y + self.btn_h - 1, x + self.btn_w - 1, y + self.btn_h - 1, 2)
        pyxel.text(x + 5, y + 4, label, 0)

    def _draw_button_joker(self, x, y, is_active, is_pressed):
        """ジョーカー専用ボタン。
        JOKER所持中（is_active）: ベースを赤（color 10）にして「J」の文字をゆっくり点滅
        非所持時: 通常ボタンと同じグレー
        """
        if is_pressed:
            base_col = 3
        elif is_active:
            base_col = 10  # 赤
        else:
            base_col = 6
        pyxel.rect(x, y, self.btn_w, self.btn_h, base_col)
        pyxel.line(x,                  y,                  x + self.btn_w - 1, y,                  7)
        pyxel.line(x,                  y,                  x,                  y + self.btn_h - 1, 7)
        pyxel.line(x + self.btn_w - 1, y,                  x + self.btn_w - 1, y + self.btn_h - 1, 2)
        pyxel.line(x,                  y + self.btn_h - 1, x + self.btn_w - 1, y + self.btn_h - 1, 2)
        # 「J」の文字: 所持中はゆっくり点滅（30フレーム周期）
        if is_active:
            j_col = 1 if (pyxel.frame_count // 30) % 2 == 0 else 10
        else:
            j_col = 0
        pyxel.text(x + 5, y + 4, "J", j_col)

    def _draw_hint_overlay(self):
        """置ける場所をドット点滅で示すヒントオーバーレイを描画する。"""
        if not self.current_stone:
            return

        if self.force_hint_timer > 0:
            alpha = math.sin(math.pi * (120 - self.force_hint_timer) / 120)
        else:
            alpha = math.sin(math.pi * (self.idle_timer % HINT_CYCLE) / HINT_ACTIVE_FRAMES)

        if alpha < 0:
            return

        center_col = 1 if alpha > 0.7 else 7
        edge_col   = 6 if alpha > 0.7 else 4

        for y in range(BOARD_ROWS):
            for x in range(BOARD_COLS):
                if self.is_placeable(x, y, self.current_stone):
                    cx = self.offset_x + x * self.gap_x + self.sw // 2
                    cy = self.offset_y + y * self.gap_y + self.sh // 2
                    if pyxel.frame_count % 8 < 6:
                        pyxel.pset(cx, cy, center_col)
                        if alpha > 0.3:
                            pyxel.pset(cx - 1, cy,     edge_col)
                            pyxel.pset(cx + 1, cy,     edge_col)
                            pyxel.pset(cx,     cy - 1, edge_col)
                            pyxel.pset(cx,     cy + 1, edge_col)


if __name__ == "__main__":
    Ishido()
