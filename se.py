import pyxel

class SEPlayer:
    """効果音（SE）を管理するクラス。

    チャンネル割り当て:
      Ch0: 石の操作音（置けた「コトッ」/ 置けない「ブブ」）
      Ch1: WAY マッチ音（2WAY・3WAY / 4WAY）
      Ch2: 演出・画面遷移用（スタート・クリア画面等）
      Ch3: 予約済み（将来用）

    サウンドスロット:
      0: 置ける「コトッ」  → Ch0
      1: 置けない「ブブ」  → Ch0
      2: 2WAY/3WAY 達成   → Ch1
      3: 4WAY 達成        → Ch1
    """

    def __init__(self):
        # --- Ch0: 石の操作音 ---
        # Sound 0:「コトッ」硬い盤面に石を置く2音の打音
        #   1音目: ノイズ → 打撃の瞬間的な硬い衝撃
        #   2音目: トライアングル → 石の余韻・共鳴
        pyxel.sounds[0].set("a3e3", "NT", "74", "NN", 5)

        # Sound 1:「ブブ」置けない場所へのエラー音
        #   低い矩形波2音で短く鈍い拒否感
        pyxel.sounds[1].set("c2c2", "SS", "54", "NN", 6)

        # --- Ch1: WAY マッチ音 ---
        # Sound 2: 2WAY / 3WAY 達成音
        #   上昇パルス波2音＋ビブラート → 清涼感のある短い煌めき
        pyxel.sounds[2].set("g3c4", "PP", "63", "VV", 12)

        # Sound 3: 4WAY 達成音
        #   4音上昇パルス波＋ビブラート → より広がりのある格調高い煌めき
        #   speed=10 × 4音 = 40フレーム（4WAY エフェクトの尺に合わせる）
        pyxel.sounds[3].set("c3e3g3c4", "P", "7531", "V", 10)

        # --- Ch2: LOOP UP / JOKER 登場 ---
        # Sound 4: LOOP UP ファンファーレ
        #   上昇アルペジオ → 達成感のある凱旋サウンド
        pyxel.sounds[4].set("c3e3g3c4e4g4", "PPPPPP", "776655", "VVVVVV", 10)

        # Sound 5: JOKER シュルル（1つ目）
        #   素早い上昇グリッサンド → 相棒が滑り込んでくる感覚
        pyxel.sounds[5].set("c4d4e4f4g4", "PPPPP", "54321", "NNNNN", 4)

        # Sound 6: JOKER シュルルル（2つ目、少し長め）
        #   5→6音でやや長く → 2人目が続いて登場する感覚
        pyxel.sounds[6].set("g3a3b3c4d4e4", "PPPPPP", "654321", "NNNNNN", 4)

    def play_place_ok(self):
        """石を正常に置いたときの SE を再生する（Ch0）。"""
        pyxel.play(0, 0)

    def play_place_ng(self):
        """置けない場所にアクションしたときのエラー SE を再生する（Ch0）。"""
        pyxel.play(0, 1)

    def play_way_match(self):
        """2WAY / 3WAY 達成時の SE を再生する（Ch1）。"""
        pyxel.play(1, 2)

    def play_4way_match(self):
        """4WAY 達成時の SE を再生する（Ch1）。"""
        pyxel.play(1, 3)

    def play_loop_and_joker(self, joker_count):
        """LOOP UP + JOKER 登場 SE を ch2 で連続再生する。
        Sound 4: LOOP UP ファンファーレ（上昇アルペジオ）
        Sound 5: JOKER シュルル（1つ目）
        Sound 6: JOKER シュルルル（2つ目、joker_count >= 2 の時）
        """
        if joker_count >= 2:
            pyxel.play(2, [4, 5, 6])   # LOOP + JOKER×2
        else:
            pyxel.play(2, [4, 5])       # LOOP + JOKER×1

    def play_joker_only(self, count=1):
        """JOKER 追加時のみの SE（全消しボーナス等）を ch2 で再生する。"""
        if count >= 2:
            pyxel.play(2, [5, 6])
        else:
            pyxel.play(2, 5)
