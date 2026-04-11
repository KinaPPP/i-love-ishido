import pyxel
import random

class EffectManager:
    """ゲーム内エフェクトと結果画面の描画を管理するクラス。

    担当エフェクト:
      - 4WAY 十字光＋リング
      - 2WAY / 3WAY 線エフェクト（時計回りに「シュパッ」と走る）
      - 勝利演出（CONGRATULATIONS! フェードイン）
      - STALEMATE 演出
      - 全モード共通「THE PATH」シーケンス
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
        self.path_done            = False

        # JOKER rescue フラグ（JOKER残りで STALEMATE した場合）
        self.is_joker_rescue      = False

        # MARVELOUS フラグ（ENDLESS MODE 専用）
        # None / "HARMONY" / "MONSTER" / "FLOW"
        self.marvelous_rank       = None

        # 全消しボーナスシーケンス
        self.board_clear_active   = False
        self.board_clear_timer    = 0
        self.board_clear_done     = False

        # LOOP:99 / JOKER:99 演出
        self.milestone_active     = False  # 演出中フラグ
        self.milestone_timer      = 0
        self.milestone_type       = None   # "LOOP" / "JOKER" / "BOTH"
        self.milestone_phase      = 0      # 0=花火+メッセージ 1=YES/NO
        self.milestone_done       = False  # 演出完了（resume or retire）
        self.milestone_resume     = False  # True=続行 False=リタイア
        # BOTH時: 1本目完了後に2本目へ
        self.milestone_second     = False  # Trueなら2本目（JOKER）の演出中

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

    def trigger_stalemate(self, is_initial=False, is_joker_rescue=False,
                           marvelous_rank=None):
        """STALEMATE 演出を開始する。
        is_initial=True      : 初手詰まり扱いで自動リスタートへ遷移する。
        is_joker_rescue=True : JOKER残りで詰まった場合。[J] or [R] を促す。
        marvelous_rank       : "HARMONY" / "MONSTER" / "FLOW" / None
        """
        self.is_stalemate         = True
        self.is_victory           = False
        self.is_initial_stalemate = is_initial
        self.is_joker_rescue      = is_joker_rescue
        self.marvelous_rank       = marvelous_rank
        self.result_timer         = 0

    def trigger_path_sequence(self):
        """全モード共通: STALEMATE 時、[R] 押下で発動するリロード前演出を開始する。"""
        self.path_sequence_active = True
        self.path_timer           = 0
        self.path_done            = False

    def trigger_milestone(self, milestone_type):
        """LOOP:99 / JOKER:99 演出を開始する。
        milestone_type: "LOOP" / "JOKER" / "BOTH"
        BOTH の場合は LOOP → JOKER の順に2連続で演出する。
        """
        self.milestone_active  = True
        self.milestone_timer   = 0
        self.milestone_type    = milestone_type
        self.milestone_phase   = 0
        self.milestone_done    = False
        self.milestone_resume  = False
        self.milestone_second  = False  # BOTH の2本目フラグ

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
            # 約1.5秒（90フレーム）で即座に完了
            if self.path_timer >= 90:
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

        # LOOP:99 / JOKER:99 マイルストーン演出
        if self.milestone_active:
            self.milestone_timer += 1
            # フェーズ0: 花火を断続的に打ち上げ（120f）
            if self.milestone_phase == 0:
                if self.milestone_timer % 8 == 0 and self.milestone_timer < 120:
                    rx = random.randint(30, 225)
                    ry = random.randint(20, 160)
                    col = 15 if self.milestone_type in ("LOOP", "BOTH") else 10
                    self.trigger_4way(rx, ry, col)
                # 120f 経過でフェーズ1（YES/NO）へ
                if self.milestone_timer >= 120:
                    self.milestone_phase = 1
                    self.milestone_timer = 0

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
            if self.marvelous_rank:
                self._draw_marvelous(stats, left, loop=loop, joker=joker)
            else:
                self._draw_stalemate(stats, left, loop=loop, joker=joker, is_endless=is_endless)
        if self.path_sequence_active:
            self._draw_path_sequence()
        if self.board_clear_active:
            self._draw_board_clear_bonus()
        if self.milestone_active:
            self._draw_milestone()

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
        """STALEMATE をボックス型で描画する。"""
        if self.path_sequence_active:
            return

        mx, my = pyxel.mouse_x, pyxel.mouse_y

        # 行リスト構築
        if not self.is_initial_stalemate and self.result_timer > 60:
            if is_endless:
                l1 = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02}"
                l2 = f"LEFT:{left:02} LOOP:{loop} & JOKER:{joker}"
                stat_lines = [(l1,1),(l2,1)]
            else:
                res = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02} LEFT:{left:02}"
                stat_lines = [(res,1)]
            if is_endless and self.is_joker_rescue and joker > 0:
                act = [("[J] USE JOKER  [R] GIVE UP", self._COL_NORMAL)]
            else:
                act = [("[R] RELOAD", self._COL_NORMAL)]
            all_lines = [("STALEMATE",1)] + stat_lines + act
        else:
            all_lines = [("STALEMATE",1)]

        bx, by, bw, bh = self._calc_box(all_lines)
        self._draw_box_frame(bx, by, bw, bh)

        # 0行目: STALEMATE (点滅)
        if self.result_timer < 60:
            blink = (self.result_timer // 10) % 2
            tc    = 10 if blink == 0 else 7
        else:
            tc = 1
        pyxel.text(self._tx("STALEMATE"), self._ly(by, 0), "STALEMATE", tc)

        if self.is_initial_stalemate or self.result_timer <= 60:
            return

        # stats行（timer>60で表示済み）
        for i, (t, c) in enumerate(stat_lines, start=1):
            pyxel.text(self._tx(t), self._ly(by, i), t, c)

        # アクション行（1回だけ描画・ホバー対応）
        ai   = 1 + len(stat_lines)
        ty_a = self._ly(by, ai)
        if is_endless and self.is_joker_rescue and joker > 0:
            j_t = "[J] USE JOKER"
            r_t = "[R] GIVE UP"
            jx  = self._tx("[J] USE JOKER  [R] GIVE UP")
            rx  = jx + len("[J] USE JOKER  ") * 4
            jc  = self._COL_HOVER if self._is_hover(mx,my,jx,ty_a,j_t) else self._COL_NORMAL
            rc  = self._COL_HOVER if self._is_hover(mx,my,rx,ty_a,r_t) else self._COL_NORMAL
            pyxel.text(jx, ty_a, j_t, jc)
            pyxel.text(rx, ty_a, r_t, rc)
        else:
            r_t = "[R] RELOAD"
            rx  = self._tx(r_t)
            rc  = self._COL_HOVER if self._is_hover(mx,my,rx,ty_a,r_t) else self._COL_NORMAL
            pyxel.text(rx, ty_a, r_t, rc)

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
            pyxel.text(x1, 135, line1, 1)
            pyxel.text(x2, 145, line2, 1)
        else:
            if left > 0:
                res = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02} LEFT:{left:02}"
                pyxel.text(70, 140, res, 1)
            else:
                res = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02}"
                pyxel.text(86, 140, res, 1)
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        g_col = 1 if (104 <= mx <= 152 and 162 <= my <= 172) else 7
        t_col = 1 if (104 <= mx <= 140 and 177 <= my <= 187) else 7
        pyxel.text(104, 162, "[G] GO AGAIN", g_col)
        pyxel.text(104, 177, "[T] TITLE",    t_col)

    # サブメッセージ（称号ごとに異なる隠し演出）
    _MARVELOUS_MSGS = {
        "HARMONY": ("THE BOARD IS FULL OF HARMONY.",       13),  # 緑
        "MONSTER": ("MASTER OF CREATION AND DESTRUCTION.", 14),  # ピンク
        "FLOW":    ("THE FLOW NEVER ENDS.",                11),  # 青
    }

    # ボックス共通定数
    _BOX_TOP   = 100   # 上辺（固定）
    _BOX_MIN_W = 144   # 最小幅（col2〜col10）
    _BOX_MG_Y  = 9     # 上下マージン
    _BOX_LINE_H= 11    # 行高（テキスト4px + 間隔7px）
    _BOX_CX    = 128   # 中央x

    # ホバー色定数（全ダイアログ共通）
    _COL_NORMAL = 5    # 濃いグレー（非ホバー時）
    _COL_HOVER  = 0    # 黒（ホバー時）

    def _calc_box(self, lines):
        """行リストからボックス座標を計算して返す (bx, by, bw, bh)。"""
        max_w = max((len(t)*4 for t,_ in lines), default=0) + 16
        bw    = max(max_w, self._BOX_MIN_W)
        bh    = self._BOX_MG_Y + len(lines)*self._BOX_LINE_H + self._BOX_MG_Y
        bx    = self._BOX_CX - bw//2
        return bx, self._BOX_TOP, bw, bh

    def _draw_box_frame(self, bx, by, bw, bh):
        """ボックスの枠だけを描画する（テキストは描かない）。"""
        pyxel.rect(bx,   by,   bw,   bh,   2)
        pyxel.rect(bx,   by,   bw-2, bh-2, 9)
        pyxel.rect(bx+2, by+2, bw-4, bh-4, 8)

    def _ly(self, by, i):
        """i行目のy座標を返す。"""
        return by + self._BOX_MG_Y + i * self._BOX_LINE_H

    def _tx(self, text):
        """テキストを中央揃えにするx座標を返す。"""
        return self._BOX_CX - len(text)*2

    def _is_hover(self, mx, my, tx, ty, text):
        """テキスト上にマウスがあるか判定する。"""
        return tx <= mx <= tx + len(text)*4 and ty <= my <= ty + 4

    def _draw_marvelous(self, stats, left, loop=0, joker=0):
        """MARVELOUS! 演出をボックス型で描画する（ENDLESS MODE 専用）。
        timer <  60 : "MARVELOUS!" が赤↔黄で点滅
        timer >= 60 : サブメッセージ出現
        timer >= 90 : stats行出現
        timer >= 120: アクション行出現
        """
        if self.path_sequence_active:
            return

        mx, my  = pyxel.mouse_x, pyxel.mouse_y
        msg_txt, msg_col = self._MARVELOUS_MSGS.get(self.marvelous_rank, ("", 1))
        l1 = f"4WAY={stats['4WAY']:02} 3WAY={stats['3WAY']:02} 2WAY={stats['2WAY']:02}"
        l2 = f"LOOP:{loop} & JOKER:{joker}"

        # 最終行リストを構築（座標計算用）
        base_lines = [("MARVELOUS!", 1)]
        if msg_txt:           base_lines.append((msg_txt, msg_col))
        base_lines += [(l1,1),(l2,1)]
        if self.is_joker_rescue:
            act_txt = "[J] USE JOKER  [R] GIVE UP"
            act_lines = [(act_txt, self._COL_NORMAL)]
        else:
            act_lines = [("[U] UNDO   [R] RELOAD", self._COL_NORMAL)]
        all_lines = base_lines + act_lines

        bx, by, bw, bh = self._calc_box(all_lines)
        self._draw_box_frame(bx, by, bw, bh)

        # 0行目: MARVELOUS! (点滅)
        if self.result_timer < 60:
            blink = (self.result_timer // 8) % 2
            t_col = 10 if blink == 0 else 12
        else:
            t_col = 1
        pyxel.text(self._tx("MARVELOUS!"), self._ly(by, 0), "MARVELOUS!", t_col)

        if self.result_timer < 60:
            return  # 点滅中はここまで

        # 1行目: サブメッセージ
        if msg_txt:
            pyxel.text(self._tx(msg_txt), self._ly(by, 1), msg_txt, msg_col)
            si = 2  # stats開始行
        else:
            si = 1

        if self.result_timer < 90:
            return

        # stats行
        pyxel.text(self._tx(l1), self._ly(by, si),   l1, 1)
        pyxel.text(self._tx(l2), self._ly(by, si+1), l2, 1)

        if self.result_timer < 120:
            return

        # アクション行（ホバー対応・1回だけ描画）
        ai = si + 2
        ty_a = self._ly(by, ai)
        if self.is_joker_rescue and joker > 0:
            j_t = "[J] USE JOKER"
            r_t = "[R] GIVE UP"
            jx  = self._tx("[J] USE JOKER  [R] GIVE UP")
            rx  = jx + len("[J] USE JOKER  ") * 4
            jc  = self._COL_HOVER if self._is_hover(mx,my,jx,ty_a,j_t) else self._COL_NORMAL
            rc  = self._COL_HOVER if self._is_hover(mx,my,rx,ty_a,r_t) else self._COL_NORMAL
            pyxel.text(jx, ty_a, j_t, jc)
            pyxel.text(rx, ty_a, r_t, rc)
        else:
            u_t = "[U] UNDO"
            r_t = "[R] RELOAD"
            tx_u = self._tx("[U] UNDO   [R] RELOAD")
            tx_r = tx_u + len("[U] UNDO   ") * 4
            uc = self._COL_HOVER if self._is_hover(mx,my,tx_u,ty_a,u_t) else self._COL_NORMAL
            rc = self._COL_HOVER if self._is_hover(mx,my,tx_r,ty_a,r_t) else self._COL_NORMAL
            pyxel.text(tx_u, ty_a, u_t, uc)
            pyxel.text(tx_r, ty_a, r_t, rc)

    def _draw_path_sequence(self):
        """全モード共通：THE PATH メッセージをボックス型で描画する（1.5秒同時出し）。"""
        lines = [("THE PATH GOES ON...",          1),
                 ("EVERY STONE, A STEP FORWARD.", 1)]
        bx, by, bw, bh = self._calc_box(lines)
        self._draw_box_frame(bx, by, bw, bh)

        # 最初の数フレームだけ赤(8)でフワッと表示し、すぐ白(1)に
        col = 1 if self.path_timer > 5 else 8
        pyxel.text(self._tx("THE PATH GOES ON..."),
                   self._ly(by, 0), "THE PATH GOES ON...", col)
        pyxel.text(self._tx("EVERY STONE, A STEP FORWARD."),
                   self._ly(by, 1), "EVERY STONE, A STEP FORWARD.", col)

    def _draw_milestone(self):
        """LOOP:99 / JOKER:99 マイルストーン演出を描画する。"""
        # 現在表示する称号種別（BOTHの2本目はJOKER）
        cur = "JOKER" if (self.milestone_type == "BOTH" and self.milestone_second) \
              else ("LOOP" if self.milestone_type in ("LOOP","BOTH") else "JOKER")

        # 称号テキスト・色設定
        if cur == "LOOP":
            title     = "THE LONGEST ROAD IS THE ONE YOU CHOSE TO WALK."
            sub_col   = 15   # 水色
            blink_col = 15
        else:
            title     = "NINETY-NINE COMPANIONS GATHERED."
            sub2      = "WITH YOU -- ONE HUNDRED UPON THE ROAD."
            sub_col   = 10   # 赤
            blink_col = 10

        # 問いかけメッセージ（全共通）
        ask_msg = "THE COUNTER STOPS HERE. STILL PROCEED?"
        ask_col = 7  # 少し落ち着いたグレー

        # 行リスト構築（フェーズに応じて追加）
        if cur == "LOOP":
            lines_all = [("LOOP : 99",     1),
                         (title,           sub_col),
                         (ask_msg,         ask_col),
                         ("[Y] YES   [N] NO", self._COL_NORMAL)]
        else:
            lines_all = [("JOKER : 99",    1),
                         (title,           sub_col),
                         (sub2,            sub_col),
                         (ask_msg,         ask_col),
                         ("[Y] YES   [N] NO", self._COL_NORMAL)]

        # フェーズ0: 問いかけと YES/NO は隠す（後ろから2行を除外）
        if self.milestone_phase == 0:
            draw_lines = lines_all[:-2]
        else:
            draw_lines = lines_all

        bx, by, bw, bh = self._calc_box(lines_all)
        self._draw_box_frame(bx, by, bw, bh)

        # タイトル行: 点滅（フェーズ0）→ 白固定（フェーズ1）
        title_txt = "LOOP : 99" if cur == "LOOP" else "JOKER : 99"
        if self.milestone_phase == 0:
            blink = (self.milestone_timer // 8) % 2
            t_col = blink_col if blink == 0 else 1
        else:
            t_col = 1
        pyxel.text(self._tx(title_txt), self._ly(by, 0), title_txt, t_col)

        # サブメッセージ行（フェーズ0: timer>10 から表示）
        if self.milestone_phase == 0 and self.milestone_timer <= 10:
            pass  # まだ表示しない
        else:
            pyxel.text(self._tx(title), self._ly(by, 1), title, sub_col)
            if cur == "JOKER":
                pyxel.text(self._tx(sub2), self._ly(by, 2), sub2, sub_col)

        # 問いかけ と YES/NO行（フェーズ1のみ）
        if self.milestone_phase == 1:
            ask_i = len(lines_all) - 2
            pyxel.text(self._tx(ask_msg), self._ly(by, ask_i), ask_msg, ask_col)

            ai    = len(lines_all) - 1
            ty_a  = self._ly(by, ai)
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            y_t   = "[Y] YES"
            n_t   = "[N] NO"
            tx_yn = self._tx("[Y] YES   [N] NO")
            tx_n  = tx_yn + len("[Y] YES   ") * 4
            yc = self._COL_HOVER if self._is_hover(mx,my,tx_yn,ty_a,y_t) else self._COL_NORMAL
            nc = self._COL_HOVER if self._is_hover(mx,my,tx_n, ty_a,n_t) else self._COL_NORMAL
            pyxel.text(tx_yn, ty_a, y_t, yc)
            pyxel.text(tx_n,  ty_a, n_t, nc)

    def _draw_board_clear_bonus(self):
        """全消しボーナスシーケンスをボックス型で描画する。"""
        t = self.board_clear_timer
        lines = [("THE BOARD IS YOURS!!", 1)]
        if t >= 90:
            lines.append(("A JOKER JOINS YOUR JOURNEY.", 12))

        bx, by, bw, bh = self._calc_box(lines)
        self._draw_box_frame(bx, by, bw, bh)

        # 1行目: 点滅 → 白で静止
        if t < 60:
            col1 = 1 if (t // 10) % 2 == 0 else 12  # 白↔黄
        else:
            col1 = 1
        pyxel.text(self._tx("THE BOARD IS YOURS!!"), self._ly(by, 0), "THE BOARD IS YOURS!!", col1)

        # 2行目: 90f 以降に黄色で出現
        if t >= 90:
            pyxel.text(self._tx("A JOKER JOINS YOUR JOURNEY."), self._ly(by, 1), "A JOKER JOINS YOUR JOURNEY.", 12)
