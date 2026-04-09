import pyxel
import random

class EffectManager:
    """ゲーム内エフェクトと結果画面の描画を管理するクラス。

    担当エフェクト:
      - 4WAY 十字光＋リング
      - 2WAY / 3WAY 線エフェクト（時計回りに「シュパッ」と走る）
      - 勝利演出（CONGRATULATIONS! フェードイン）
      - STALEMATE 演出
      - ISHIDO MODE 専用「THE PATH」シーケンス
    """

    # 線エフェクトのパラメータ
    _LINE_GROW_FRAMES = 10   # 1本が伸びきるまでのフレーム数
    _LINE_OFFSET      = 7    # 次の線が始まるまでの時間差（フレーム）
    _H_LEN            = 22   # 横方向の最大伸長（px）
    _V_LEN            = 33   # 縦方向の最大伸長（px）

    # 時計回り方向定義（上→右→下→左）
    _CLOCKWISE = [(0, -1), (1, 0), (0, 1), (-1, 0)]

    # ディゾルブエフェクトのパラメータ
    _DISSOLVE_FRAMES = 45   # 4〜5回点滅と同程度の時間
    _STONE_W         = 16
    _STONE_H         = 24

    def __init__(self):
        self.effects        = []
        self.result_timer   = 0
        self.is_victory     = False
        self.is_stalemate   = False
        self.is_initial_stalemate = False
        self.firework_count = 0

        # THE PATH シーケンス
        self.path_sequence_active = False
        self.path_timer           = 0
        self.path_phase           = 0   # 1: 1行目表示中, 2: 2行目表示中
        self.path_done            = False

        # JOKER rescue フラグ（JOKER残りで STALEMATE した場合）
        self.is_joker_rescue      = False

        # 全消しボーナスシーケンス
        self.board_clear_active   = False
        self.board_clear_timer    = 0
        self.board_clear_done     = False

    # ------------------------------------------------------------------ #
    #  トリガー
    # ------------------------------------------------------------------ #

    def trigger_4way(self, cx, cy, col):
        """4WAY エフェクト（十字光＋リング）を登録する。
        timer=45 で 4WAY 達成音（40フレーム）に合わせた尺にする。
        """
        self.effects.append({
            "type": "4way", "cx": cx, "cy": cy, "col": col,
            "timer": 45, "max_time": 45
        })

    def trigger_way_lines(self, cx, cy, adj_directions):
        """2WAY / 3WAY / 4WAY エフェクト：置いた石から隣接石へ線が走る。

        adj_directions: _get_adj_directions() が返す時計回り済みのリスト
        """
        n = len(adj_directions)
        # 最後の線が伸びきるまでの時間 + 余韻
        total = self._LINE_GROW_FRAMES + (n - 1) * self._LINE_OFFSET + 8
        if n == 4:
            total = 40  # 4WAY は 4WAY 達成音に合わせた尺
        self.effects.append({
            "type": "way_lines",
            "cx": cx, "cy": cy,
            "directions": adj_directions,
            "timer": total, "max_time": total
        })

    def start_victory(self):
        """勝利演出を開始する。"""
        self.is_victory     = True
        self.is_stalemate   = False
        self.result_timer   = 0
        self.firework_count = 0

    def trigger_stalemate(self, is_initial=False, is_joker_rescue=False):
        """STALEMATE 演出を開始する。
        is_initial=True      : 初手詰まり扱いで自動リスタートへ遷移する。
        is_joker_rescue=True : JOKER残りで詰まった場合。[J] or [R] を促す。
        """
        self.is_stalemate         = True
        self.is_victory           = False
        self.is_initial_stalemate = is_initial
        self.is_joker_rescue      = is_joker_rescue
        self.result_timer         = 0

    def trigger_path_sequence(self):
        """ISHIDO MODE STALEMATE 時、[R] 押下で発動するリロード前演出を開始する。"""
        self.path_sequence_active = True
        self.path_timer           = 0
        self.path_phase           = 1
        self.path_done            = False

    def trigger_dissolve(self, stones_data):
        """ENDLESS MODE 専用：WAY達成石のディゾルブ（溶解消去）アニメーションを登録する。

        stones_data: [(bx, by, color_id, number), ...] 消去する石のリスト
        盤面からの論理削除・サブ袋追加は呼び出し元（ishido.py）で先に行うこと。
        描画だけをアニメーションで見せる。

        ディゾルブ方式:
          石の 16×24=384 ピクセル座標をシャッフルし、
          毎フレーム進行度に応じたピクセル数を背景色(color 6)で上書きする。
          ランダムな網目状に石が抜け落ちるように見える。
        """
        for bx, by, color_id, number in stones_data:
            # 全ピクセル座標をシャッフル
            pixels = [(px, py)
                      for py in range(self._STONE_H)
                      for px in range(self._STONE_W)]
            random.shuffle(pixels)
            self.effects.append({
                "type"    : "dissolve",
                "bx"      : bx, "by": by,
                "color_id": color_id, "number": number,
                "pixels"  : pixels,
                "timer"   : self._DISSOLVE_FRAMES,
                "max_time": self._DISSOLVE_FRAMES,
            })

    def trigger_board_clear_bonus(self):
        """ENDLESS MODE 全消しボーナスシーケンスを開始する。
        「THE BOARD IS YOURS!!」白↔黄点滅 → 白で静止
        → 「A JOKER JOINS YOUR JOURNEY.」出現
        → 豪華花火
        → board_clear_done=True で ishido.py 側が四隅再配置＋JOKER付与
        """
        self.board_clear_active = True
        self.board_clear_timer  = 0
        self.board_clear_done   = False
        # 豪華花火を一気に登録（通常の2倍以上）
        for _ in range(20):
            rx = random.randint(20, 235)
            ry = random.randint(15, 210)
            self.trigger_4way(rx, ry, random.choice([10, 11, 12, 14, 15, 1, 7]))

    # ------------------------------------------------------------------ #
    #  更新
    # ------------------------------------------------------------------ #

    def update(self):
        """エフェクトの更新。毎フレーム呼び出す。"""
        for e in self.effects[:]:
            e["timer"] -= 1
            if e["timer"] <= 0:
                self.effects.remove(e)

        if self.is_victory or self.is_stalemate:
            self.result_timer += 1
            if self.is_victory:
                if self.result_timer < 80 and self.result_timer % 4 == 0 and self.firework_count < 15:
                    rx = random.randint(40, 215)
                    ry = random.randint(30, 180)
                    # 4WAY 達成色（赤・青・黄・紫・水色）＋白で鮮やかに
                    self.trigger_4way(rx, ry, random.choice([10, 11, 12, 14, 15, 1]))
                    self.firework_count += 1

        if self.path_sequence_active:
            self.path_timer += 1
            if self.path_phase == 1 and self.path_timer >= 70:
                self.path_phase = 2
                self.path_timer = 0
            elif self.path_phase == 2 and self.path_timer >= 80:
                self.path_sequence_active = False
                self.path_done            = True

        # 全消しボーナス: 60フレーム点滅→2行目出現→150フレームで完了
        if self.board_clear_active:
            self.board_clear_timer += 1
            # 追加花火を断続的に打ち上げ
            if self.board_clear_timer < 120 and self.board_clear_timer % 6 == 0:
                rx = random.randint(20, 235)
                ry = random.randint(15, 180)
                self.trigger_4way(rx, ry, random.choice([10, 11, 12, 14, 15, 1, 7]))
            if self.board_clear_timer >= 150:
                self.board_clear_active = False
                self.board_clear_done   = True

    # ------------------------------------------------------------------ #
    #  描画
    # ------------------------------------------------------------------ #

    def draw(self, stats=None, left=0, loop=0, joker=0, is_endless=False):
        """エフェクト全体の描画。毎フレーム draw() 内で呼び出す。
        ENDLESS MODE では loop / joker / is_endless を渡してリザルトを2行表示する。
        """
        for e in self.effects:
            if e["type"] == "4way":
                self._draw_4way(e)
            elif e["type"] == "way_lines":
                self._draw_way_lines(e)
            elif e["type"] == "dissolve":
                self._draw_dissolve(e)
        if self.is_victory:
            self._draw_victory_sequence(stats, left, loop, joker, is_endless)
        if self.is_stalemate:
            self._draw_stalemate(stats, left, loop, joker, is_endless)
        if self.path_sequence_active:
            self._draw_path_sequence()
        if self.board_clear_active:
            self._draw_board_clear_bonus()

    def _draw_4way(self, e):
        """4WAY エフェクト（十字光＋リング）を描画する。"""
        t      = e["max_time"] - e["timer"]
        cx, cy = e["cx"], e["cy"]
        size   = min(t * 5, 45)
        col    = e["col"] if (e["timer"] // 2) % 2 == 0 else 1

        pyxel.line(cx - size, cy, cx + size, cy, col)
        pyxel.line(cx, cy - size, cx, cy + size, col)

        if t > 4:
            ring_size = (t - 4) * 4
            if ring_size < 55:
                pyxel.circb(cx, cy, ring_size, 7)

    def _draw_way_lines(self, e):
        """2WAY / 3WAY / 4WAY エフェクト：線が時計回りに「シュパッ」と走る。

        各線はピクセル色を変えながら伸長:
          伸び始め（progress < 0.4）: col 7（明るいハイライト）
          伸びきり（progress >= 0.4）: col 1（白、くっきり）
        """
        t      = e["max_time"] - e["timer"]  # 経過フレーム
        cx, cy = e["cx"], e["cy"]

        for i, (dx, dy) in enumerate(e["directions"]):
            line_t = t - i * self._LINE_OFFSET
            if line_t <= 0:
                continue

            progress = min(line_t / self._LINE_GROW_FRAMES, 1.0)
            max_len  = self._V_LEN if dx == 0 else self._H_LEN
            length   = int(max_len * progress)

            if length > 0:
                col = 7 if progress < 0.4 else 1
                pyxel.line(cx, cy,
                           cx + dx * length,
                           cy + dy * length,
                           col)

    def _draw_dissolve(self, e):
        """ディゾルブエフェクト：石が網目状に抜け落ちて背景に溶けるアニメーション。

        進行度（0.0〜1.0）に応じて消すピクセル数を計算し、
        シャッフル済みリストの先頭から順に背景色(color 6)で上書きする。
        """
        elapsed  = e["max_time"] - e["timer"]
        progress = elapsed / e["max_time"]
        n_clear  = int(len(e["pixels"]) * progress)
        bx, by   = e["bx"], e["by"]

        # まず石を普通に描画（block.Block.draw_stone と同じ内容をインライン展開）
        stone_col = 9 + e["color_id"]
        pyxel.rect(bx,     by,     16, 24, 2)
        pyxel.rect(bx,     by,     15, 23, 9)
        pyxel.rect(bx + 1, by + 1, 14, 22, 7)
        pyxel.rect(bx + 3, by + 3, 10, 18, stone_col)
        s      = str(e["number"])
        char_x = bx + 6 if len(s) == 1 else bx + 4
        pyxel.text(char_x, by + 5, s, 1)

        # 進行度分のピクセルを背景色で上書き（ランダム網目状に消える）
        for px, py in e["pixels"][:n_clear]:
            pyxel.pset(bx + px, by + py, 6)

    def _draw_victory_sequence(self, stats, left, loop=0, joker=0, is_endless=False):
        """勝利演出シーケンスを描画する。"""
        if self.result_timer > 30:
            pyxel.text(96, 110, "CONGRATULATIONS!", 1)

        alpha = min(max((self.result_timer - 100) / 40, 0), 1)
        if alpha > 0:
            step = 4 if alpha < 0.5 else 2 if alpha < 0.8 else 1
            for y in range(0, 256, step):
                pyxel.line(0, y, 255, y, 0)
            pyxel.text(96, 110, "CONGRATULATIONS!", 1)

        if alpha >= 1.0:
            self._draw_result_overlay(stats, left, loop, joker, is_endless)

    def _draw_stalemate(self, stats, left, loop=0, joker=0, is_endless=False):
        """STALEMATE 演出を描画する。THE PATH シーケンス中は非表示。
        ENDLESS MODE のみリザルトを2行表示する。
        レイアウト（帯 y=100〜159）:
          y=108 STALEMATE
          y=122 4WAY=00 3WAY=00 2WAY=00
          y=132 LEFT:00 LOOP:0 & JOKER:0  ← ENDLESS のみ
        """
        if self.path_sequence_active:
            return

        pyxel.rect(0, 100, 256, 60, 8)
        pyxel.line(0, 100, 255, 100, 9)
        pyxel.line(0, 159, 255, 159, 2)

        if self.result_timer < 60:
            blink    = (self.result_timer // 10) % 2
            text_col = 10 if blink == 0 else 7
        else:
            text_col = 1
        pyxel.text(110, 108, "STALEMATE", text_col)

        if not self.is_initial_stalemate and self.result_timer > 60:
            if is_endless:
                line1 = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02}"
                line2 = f"LEFT:{left:02} LOOP:{loop} & JOKER:{joker}"
                pyxel.text(82, 119, line1, 1)
                pyxel.text(80, 129, line2, 1)
                # JOKER rescue: マウスホバーで色変化
                if self.is_joker_rescue and joker > 0:
                    mx, my = pyxel.mouse_x, pyxel.mouse_y
                    # [J] USE JOKER: 9文字×4=36px → x=72〜108
                    # [R] GIVE UP:   9文字×4=36px → x=148〜184（スペース区切り）
                    j_col = 12 if (72 <= mx <= 120 and 139 <= my <= 149) else 1
                    r_col = 12 if (130 <= mx <= 178 and 139 <= my <= 149) else 1
                    pyxel.text( 72, 141, "[J] USE JOKER", j_col)
                    pyxel.text(130, 141, "[R] GIVE UP",   r_col)
            else:
                res = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02} LEFT:{left:02}"
                pyxel.text(70, 128, res, 1)

    def _draw_result_overlay(self, stats, left, loop=0, joker=0, is_endless=False):
        """ゲームクリア画面のリザルトとボタンを描画する。
        通常レイアウト:
          y=140  リザルト1行
          y=162  [G] GO AGAIN
          y=177  [T] TITLE
        ENDLESS レイアウト（2行リザルト）:
          y=135  4WAY=00 3WAY=00 2WAY=00
          y=145  LEFT:00 LOOP:0 & JOKER:0
          y=162  [G] GO AGAIN
          y=177  [T] TITLE
        ホバー: 通常 color 7（グレー）→ ホバー color 1（白）
        """
        if is_endless:
            line1 = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02}"
            line2 = f"LOOP:{loop} & JOKER:{joker}"
            
            # 文字数からx座標を自動計算して完全センタリング
            x1 = (256 - len(line1) * 4) // 2
            x2 = (256 - len(line2) * 4) // 2
            
            # 修正: 固定の数字ではなく、計算した変数 x1, x2 を渡す！
            pyxel.text(x1, 135, line1, 7)
            pyxel.text(x2, 145, line2, 7)
        else:
            # ALL WAYS / ISHIDO+ 用
            if left > 0:
                # STALEMATE時など、石が残っている場合はLEFTを表示
                res = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02} LEFT:{left:02}"
                pyxel.text(70, 140, res, 7)
            else:
                # クリア時（leftが0）はLEFTを非表示にし、少し右にずらしてセンタリング
                res = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02}"
                pyxel.text(86, 140, res, 7)
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        g_col = 1 if (104 <= mx <= 152 and 162 <= my <= 172) else 7
        t_col = 1 if (104 <= mx <= 140 and 177 <= my <= 187) else 7
        pyxel.text(104, 162, "[G] GO AGAIN", g_col)
        pyxel.text(104, 177, "[T] TITLE",    t_col)

    def _draw_board_clear_bonus(self):
        """全消しボーナスシーケンスを描画する。
        テキストセンタリング:
          "THE BOARD IS YOURS!!"       21文字 × 4px = 84px → x = 86
          "A JOKER JOINS YOUR JOURNEY." 28文字 × 4px = 112px → x = 72
        フェーズ:
          0〜59f  : 「THE BOARD IS YOURS!!」白(1)↔黄(12)で点滅
          60f〜   : 白(1)で静止
          90f〜   : 「A JOKER JOINS YOUR JOURNEY.」が黄(12)で出現
        """
        t = self.board_clear_timer

        # 帯（THE PATH / STALEMATE と同じスタイル）
        pyxel.rect(0, 100, 256, 60, 8)
        pyxel.line(0, 100, 255, 100, 9)
        pyxel.line(0, 159, 255, 159, 2)

        # 1行目: 点滅 → 白で静止
        if t < 60:
            col1 = 1 if (t // 10) % 2 == 0 else 12  # 白↔黄
        else:
            col1 = 1
        pyxel.text(86, 112, "THE BOARD IS YOURS!!", col1)

        # 2行目: 90f 以降に黄色で出現
        if t >= 90:
            pyxel.text(72, 128, "A JOKER JOINS YOUR JOURNEY.", 12)

    def _draw_path_sequence(self):
        """ISHIDO MODE 専用：リロード前の「THE PATH」メッセージを描画する。

        デザインコンセプト: 灰色の石に白文字が刻み込まれたイメージ。
        テキストのセンタリング:
          "THE PATH GOES ON..."          19文字 × 4px = 76px → x = 90
          "EVERY STONE, A STEP FORWARD." 29文字 × 4px = 116px → x = 70
        """
        # 灰色帯で STALEMATE 表示を覆う（ゲーム背景と同色系）
        pyxel.rect(0, 100, 256, 60, 8)
        pyxel.line(0, 100, 255, 100, 9)   # 上辺ハイライト
        pyxel.line(0, 159, 255, 159, 2)   # 下辺影（立体感）

        # 1行目: THE PATH GOES ON...（10フレーム後に白で出現）
        if self.path_phase >= 1:
            col1 = 1 if self.path_timer > 10 else 8
            pyxel.text(90, 112, "THE PATH GOES ON...", col1)

        # 2行目: EVERY STONE...（10フレーム後にやや暗い白で添える）
        if self.path_phase >= 2:
            col2 = 1 if self.path_timer > 10 else 8
            pyxel.text(70, 128, "EVERY STONE, A STEP FORWARD.", col2)
