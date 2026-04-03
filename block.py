import pyxel
import random

class Block:
    """石（御札）の生成と描画を担当するクラス。"""

    @staticmethod
    def get_initial_bag():
        """色1〜6 × 数字1〜6 の組み合わせ × 2個 = 72個の袋を作成してシャッフル。"""
        bag = []
        for c in range(1, 7):
            for n in range(1, 7):
                bag.append((c, n))
                bag.append((c, n))
        random.shuffle(bag)
        return bag

    @staticmethod
    def draw_stone(x, y, color_id, number):
        """御札を描画する。
        カラーパネルの色は setup_palette で設定したパレット 10〜15 番を使用。
        数字の色はパレット 1 番（白）で描画する。
        """
        stone_col = 9 + color_id

        # 御札のベース（右・下に影、左・上にハイライト、表面グレー）
        pyxel.rect(x,     y,     16, 24, 2)  # 影
        pyxel.rect(x,     y,     15, 23, 9)  # ハイライト
        pyxel.rect(x + 1, y + 1, 14, 22, 7)  # 表面

        # 中央のカラーパネル
        pyxel.rect(x + 3, y + 3, 10, 18, stone_col)

        # 数字（パレット 1 番：白）
        s = str(number)
        char_x = x + 6 if len(s) == 1 else x + 4
        pyxel.text(char_x, y + 5, s, 1)

    @staticmethod
    def draw_joker_stone(x, y, mode):
        """ジョーカー石を描画する。
        mode: "C" → 虹色サイクルパネル
              "N" → グレーパネル＋「？」（影付き）
              None → のっぺらぼう（未選択状態）
        """
        # ベース（通常石と同じ構造）
        pyxel.rect(x,     y,     16, 24, 2)   # 影
        pyxel.rect(x,     y,     15, 23, 9)   # ハイライト
        pyxel.rect(x + 1, y + 1, 14, 22, 7)  # 表面

        if mode == "C":
            # 虹色ライン: 上から下へ光が流れるエフェクト
            # 各横ラインに (frame_count + row) % 6 の色を割り当て
            # speed=3 で流れる速さを調整（小さいほど速い）
            _speed = 3
            for row in range(18):
                col_idx = ((pyxel.frame_count // _speed) + row) % 6
                pyxel.line(x + 3, y + 3 + row, x + 12, y + 3 + row, 10 + col_idx)
        elif mode == "N":
            # グレーパネル＋「？」（影付きで存在感を出す）
            pyxel.rect(x + 3, y + 3, 10, 18, 5)   # 暗めグレーパネル
            pyxel.text(x + 7, y + 10, "?", 2)     # 影（暗色）
            pyxel.text(x + 6, y + 9,  "?", 1)     # 白「？」
        else:
            # のっぺらぼう: パネル部分を表面と同じグレーにして無地に見せる
            pyxel.rect(x + 3, y + 3, 10, 18, 7)
