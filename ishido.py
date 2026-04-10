# title: I LOVE ISHIDO
# author: KINA
# desc: A reimagining of the classic stone-placement game ISHIDO. Three modes: ALL WAYS, ISHIDO+, and ENDLESS ISHIDO++.
# site: https://github.com/KINAppp
# license: MIT
# version: 1.0.0

import pyxel
import random

import theme_default as theme
import se
import bgm
import effect
import ui
import game_logic as logic
import input_handler as inp

from constants import (
    BOARD_COLS, BOARD_ROWS, STONE_W, STONE_H,
    GAP_X, GAP_Y, OFFSET_X, OFFSET_Y,
    UI_ROW_Y, BTN_W, BTN_H,
    STATE_START, STATE_PLAYING, STATE_RESULT, STATE_STALEMATE,
    MODE_ISHIDO, MODE_ALL_WAYS, MODE_ENDLESS,
    JOKER_COLOR, JOKER_NUMBER,
    HINT_IDLE_THRESHOLD,
)

try:
    import js
    IS_WEB = True
except ImportError:
    import webbrowser
    IS_WEB = False

if not IS_WEB:
    try:
        import debug as _debug
        _DEBUG_ENABLED = True
    except ImportError:
        _DEBUG_ENABLED = False
else:
    _DEBUG_ENABLED = False


class Ishido:
    """石道ゲームのメインクラス。"""

    def __init__(self):
        pyxel.init(256, 256, title="I LOVE ISHIDO", fps=30)
        pyxel.mouse(True)   # マウスポインターを表示
        theme.setup_palette()
        self.se      = se.SEPlayer()
        self.bgm     = bgm.BGMPlayer()
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
        self.btn_reload_x  = self.board_right - self.btn_w
        self.btn_hint_x    = self.btn_reload_x - 20
        self.btn_undo_x    = self.btn_hint_x   - 20
        self.btn_joker_x   = self.btn_undo_x   - 24

        # ✕ボタン
        self.btn_x_x  = 241
        self.btn_x_y  = 3
        self.btn_x_w  = 12
        self.btn_x_h  = 12

        # ゲーム状態
        self.game_state          = STATE_START
        self.game_mode           = MODE_ALL_WAYS
        self.show_hint_spiritual = False
        self.undo_interval       = 0

        # カーソル・マウス
        self.cursor_x     = 0
        self.cursor_y     = 0
        self.prev_mouse_x = 0
        self.prev_mouse_y = 0
        self.victory_delay = 0

        # ダイアログフラグ
        self.confirm_reload = False
        self.confirm_title  = False

        # ジョーカー石の状態
        self.joker_panel_open  = False
        self.joker_mode        = None
        self.joker_saved_stone = None

        # ヒント
        self.hint_config_on   = False
        self.idle_timer       = 0
        self.force_hint_timer = 0

        # ENDLESS MODE 用フィールド
        self.sub_bag    = []
        self.loop_count = 0
        self.joker_count = 0

        # ゲームデータ（restart_game で初期化）
        self.bag           = []
        self.board         = []
        self.history       = []
        self.stats         = {}
        self.current_stone = None

        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------ #
    #  初期化
    # ------------------------------------------------------------------ #

    def restart_game(self):
        """ゲームを初期状態にリセットして開始する。"""
        self.bag     = theme.get_initial_bag()
        self.board   = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
        self.history = []
        self.stats   = {"4WAY": 0, "3WAY": 0, "2WAY": 0}

        # 初期配置: 四隅＋中央 (5,3)(6,4) の 6 マス
        for x, y in [(0, 0), (11, 0), (0, 7), (11, 7), (5, 3), (6, 4)]:
            self.board[y][x] = self.bag.pop()

        self.current_stone    = self.bag.pop()
        self.effects          = effect.EffectManager()
        self.confirm_reload   = False
        self.confirm_title    = False
        self.joker_panel_open = False
        self.joker_mode       = None
        self.joker_saved_stone = None
        self.undo_interval    = 0
        self.idle_timer       = 0
        self.force_hint_timer = 0
        self.victory_delay    = 0
        self.hint_config_on   = False

        self.sub_bag     = []
        self.loop_count  = 0
        self.joker_count = 1 if self.game_mode == MODE_ENDLESS else 0

        self.game_state = STATE_PLAYING

        # 初手詰まりチェック
        if logic.check_stalemate(self):
            self.game_state = STATE_STALEMATE
            self.effects.trigger_stalemate(is_initial=True)

    # ------------------------------------------------------------------ #
    #  公開インターフェース（input_handler / game_logic から呼ぶ）
    # ------------------------------------------------------------------ #

    def is_placeable(self, x, y, stone):
        return logic.is_placeable(self, x, y, stone)

    def place_stone(self):
        return logic.place_stone(self)

    def open_how_to_play(self):
        """ローカルとWebで適切にHow To Playページを開く。"""
        filename = "howtoplay.html"
        if IS_WEB:
            js.window.open(filename, "_blank")
        else:
            import os
            base_dir   = os.path.dirname(__file__)
            target_path = os.path.abspath(os.path.join(base_dir, filename))
            webbrowser.open(target_path)

    # ------------------------------------------------------------------ #
    #  更新（状態別）
    # ------------------------------------------------------------------ #

    def update(self):
        """メインループの更新処理。"""
        if self.undo_interval > 0:
            self.undo_interval -= 1

        mx, my = pyxel.mouse_x, pyxel.mouse_y

        if self.game_state == STATE_START:
            inp.handle_start(self, mx, my)
            return

        if self.game_state in [STATE_RESULT, STATE_STALEMATE]:
            inp.handle_result(self, mx, my)
            return

        # プレイ中
        if _DEBUG_ENABLED:
            _debug.handle_debug_keys(self)
            if self.game_state != STATE_PLAYING:
                return

        inp.handle_playing(self, mx, my)

    # ------------------------------------------------------------------ #
    #  描画
    # ------------------------------------------------------------------ #

    def draw(self):
        """メインループの描画処理。"""
        if self.game_state == STATE_START:
            ui.draw_start_screen()
            return

        ui.draw_board(self)
        if self.show_hint_spiritual:
            ui.draw_hint_overlay(self)
        ui.draw_cursor(self)

        left = ui.draw_info(self)
        ui.draw_buttons(self)

        self.effects.draw(
            self.stats, left,
            loop=self.loop_count,
            joker=self.joker_count,
            is_endless=(self.game_mode == MODE_ENDLESS)
        )

        ui.draw_x_button(self)

        if self.joker_panel_open:
            ui.draw_joker_panel()
        if self.confirm_title:
            ui.draw_confirm_title()
        if self.confirm_reload:
            ui.draw_confirm_reload()


if __name__ == "__main__":
    Ishido()
