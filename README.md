# I LOVE ISHIDO

PC-98版「石道」へのリスペクト作品。3つのゲームモードと5つのビジュアルテーマを収録したパズルゲームです。

**▶ [Play in browser](https://kinappp.github.io/i-love-ishido/ishido.html)**

---

## ゲームモード

**ALL WAYS MODE**
隣接する全ての石と、色か数字のどちらかが一致すれば置ける。ORルール。

**ISHIDO+ MODE**
隣接する石とちょうど一方だけ一致（XORルール）。完全一致は不可。

**ENDLESS ISHIDO++**
XORルール＋ジョーカー石＋盤面全消し＋LOOP。72個の石が石道を永遠に巡る。

---

## 特徴

- **5テーマ** — DEFAULT / DEFAULT CUD / KANJI / KANJI CUD / SEA。`[T]`キーでいつでも切り替え
- **CUD対応** — 色覚サポート配色（オレンジ・深緑・プラチナ）でP型・D型でも識別しやすく
- **左手完結操作** — `WASD`カーソル + `SPACE`配置 + `Z`アンドゥ でマウス不要
- **ヒント機能** — `[Q]`で置ける場所をドット表示
- **スクリーンショット** — `[P]`でいつでもPNG保存

---

## 操作

| キー | 機能 |
|---|---|
| `WASD` / `↑↓←→` | カーソル移動 |
| `SPACE` / クリック | 石を置く |
| `Z` / `U` | アンドゥ |
| `Q` / `H` | ヒント表示 |
| `F` / `J` | ジョーカー使用（ENDLESS） |
| `R` | リロード |
| `T` | テーマ切替 |
| `P` | スクリーンショット |

詳しい遊び方 → **[HOW TO PLAY](howtoplay.html)**

---

## 開発

Built with [Pyxel](https://github.com/kitao/pyxel) — a retro game engine for Python.

```
pyxel package . ishido.py
pyxel app2html ishido.pyxapp
```

Developed by **KINA** with Claude and Gemini.

---

MIT License
