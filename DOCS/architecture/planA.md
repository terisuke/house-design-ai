### 最終結論 – 「生成 × 制約ソルバ」二段構えで確実に動く間取りパイプラインを作る

#### 1. アーキテクチャ決定版

* 敷地・要件
   │
   ▼
(0) データ整備               … YOLOアノテ→JSON(Polygon＋Graph)
   │
   ▼
(1) 生成レイヤ               … HouseDiffusion ◎（Graph2Planを補完）
   │   ‣ 敷地・部屋リスト条件付きで 100–500 案を“自由形状”で吐く
   ▼
(2) 制約ソルバレイヤ         … OR-Tools CP-SAT 100 % 法規充足
   │   ‣ 910 mm グリッド化・採光・階段・1F↔2F 整合を整数制約で宣言
   ▼
(3) 評価 & 絞り込み          … 動線・採光・無駄率スコア
   │   ‣ 上位 N（=施主提示候補）を残す
   ▼
(4) ポストプロセス／出力     … FreeCAD / IFC / SVG / CSV

生成で“らしさ”を学習し、制約ソルバで「必ず建てられる図面」へ仕上げる——この二段構えが 実用と研究の両立をもっとも低リスクで実現します。

⸻

#### 2. 既存リポジトリへの改修ポイント

| 既存コンポーネント | 改修内容 | 工数感 (人日) |
| --- | --- | --- |
| Streamlit UI | 生成⇄評価⇄ソルバのパイプラインを1クリック実行生成候補はサイドバーのst.selectboxで切替表示 | 1 |
| GCP / Docker | ① Diffusion 学習→ Vertex AI GPU② CP-SAT は CPU Auto-Scaling | 0.5 |
| YOLOv8 土地検出 | 土地ポリゴンを np.ndarray→shapely.Polygon に変換し生成層の condition に渡す | 0.5 |
| FreeCAD API ラッパ | 下記サンプルを utils/freecad_export.py として追加 | 0.5 |

⸻

#### 3. まず 10 日でやるべき To-Do

| # | タスク | 成果物 |
| --- | --- | --- |
| 1 | アノテ→JSON スクリプト完成(YOLO txt → Polygon & Graph) | dataset/json/*.json |
| 2 | CP-SAT PoC：3LDK / 8 m × 10 m 敷地で910 mm スナップ＋採光＋隣接制約を解けるか検証 | notebooks/cp_sat_poc.ipynb |
| 3 | Diffusion repo fork→ I/O を自社 JSON に合わせて改造 | models/house_diffusion/ |
| 4 | 評価器 v0.1：動線長・無駄率 (%)・採光率 | src/evaluator.py |
| 5 | Streamlit ミニ UI：敷地アップロード → 上位 3 案を SVG プレビュー | app/main.py |

⸻

#### 4. CP-SAT ＆ FreeCAD の最小サンプル

```python
# requirements: ortools, shapely, FreeCAD (or freecad-library in Docker)

from ortools.sat.python import cp_model
from shapely.geometry import box, Polygon
import FreeCAD, Part

GRID = 910                   # mm
WALL = 100                   # mm 厚み
H, W = 10, 8                 # グリッド数 → 敷地 8m x 9.1m

# ===== CP-SAT ===========
model = cp_model.CpModel()
room = {
    'LDK': dict(
        x = model.NewIntVar(0, W-4, 'ldk_x'),   # 最小幅 4マス
        y = model.NewIntVar(0, H-5, 'ldk_y'),   # 最小高 5マス
        w = model.NewIntVar(4, W,   'ldk_w'),
        h = model.NewIntVar(5, H,   'ldk_h')
    ),
    'BR1': dict(
        x = model.NewIntVar(0, W-3, 'br1_x'),
        y = model.NewIntVar(0, H-3, 'br1_y'),
        w = model.NewIntVar(3, 4,   'br1_w'),
        h = model.NewIntVar(3, 4,   'br1_h')
    )
}

# 敷地内に収まる
for r in room.values():
    model.Add(r['x'] + r['w'] <= W)
    model.Add(r['y'] + r['h'] <= H)

# 部屋重なり禁止 (LDK vs BR1)
M = max(H, W)
model.Add(room['LDK']['x'] + room['LDK']['w'] <= room['BR1']['x'] 
          ).OnlyEnforceIf(model.NewBoolVar('left'))
model.Add(room['BR1']['x'] + room['BR1']['w'] <= room['LDK']['x'] 
          ).OnlyEnforceIf(model.NewBoolVar('right'))
# 上下方向も同様…（略）

solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 5
status = solver.Solve(model)
assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

# ===== 910 mm→mm 変換 & ポリゴン化 ===========
def to_poly(r):
    x = solver.Value(r['x']) * GRID
    y = solver.Value(r['y']) * GRID
    w = solver.Value(r['w']) * GRID
    h = solver.Value(r['h']) * GRID
    return Polygon([(x,y), (x+w,y), (x+w,y+h), (x,y+h)])

ldk_poly  = to_poly(room['LDK'])
br1_poly  = to_poly(room['BR1'])

# ===== FreeCAD 出力 ===========
doc = FreeCAD.newDocument()
for label, poly in [('LDK', ldk_poly), ('BR1', br1_poly)]:
    pts  = [(p[0], p[1], 0) for p in poly.exterior.coords]
    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    extrusion = face.extrude(FreeCAD.Vector(0, 0, 2400))
    obj = doc.addObject("Part::Feature", label)
    obj.Shape = extrusion
doc.recompute()
doc.saveAs("rect_sample.FCStd")
print("✅ FreeCAD file saved: rect_sample.FCStd")

所要: 100 行弱。
この PoC をベースに 部屋数を増やす→制約を足す→2F 変数を追加 と段階的に拡張してください。

⸻

#### 5. 今後の意思決定ガイドライン

| 判断タイミング | 「分岐の基準」 |
| --- | --- |
| Diffusion か Graph2Plan か | 生成候補 100 案中、CP-SAT合格率が 5 % 未満 → Graph2Plan を追加 |
| CP-SAT 解の探索時間 >30 s | ‣ ペナルティを緩める‣ 部屋をプリスナップして決定変数を削減 |
| 1F/2F 壁ズレ > 300 mm | ペナルティ係数か 壁集合の変数範囲 を調整し再実行 |
| 拡散モデルが発散 | 学習率 ↓、βスケジュール logging、データ拡張で対処 |

⸻

#### 結語
	1.	生成（創造性） と 制約（確実性） を明確に層分け。
	2.	既存 YOLO・Streamlit・GCP 資産をそのまま活かす。
	3.	まず CP-SAT PoC と データ整形 を“10 日で出す”——以降は拡張あるのみ。

これが最短で動くうえ、後から研究要素（生成モデル高度化・評価指標洗練）を好きなだけ増やせるロードマップです。
ご不明点や追加コードが必要なタイミングで、またお声掛けください！