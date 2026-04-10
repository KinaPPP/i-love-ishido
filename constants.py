"""
constants.py — I LOVE ISHIDO 定数定義

ゲーム全体で共有する定数を一元管理する。
"""

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
MODE_ISHIDO   = "ISHIDO+"
MODE_ALL_WAYS = "ALL WAYS"
MODE_ENDLESS  = "ENDLESS ISHIDO++"

# ENDLESS MODE: 盤面全埋めを判定するマス数
BOARD_TOTAL_CELLS = BOARD_COLS * BOARD_ROWS  # 96

# ジョーカー石の内部表現
JOKER_COLOR  = ("J", "C")
JOKER_NUMBER = ("J", "N")

# ヒントのアイドル発火しきい値（フレーム）
HINT_IDLE_THRESHOLD = 1200
HINT_CYCLE          = 240
HINT_ACTIVE_FRAMES  = 120
