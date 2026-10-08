# 固定报告格式

最终交付物固定为同一内容的两份文件：`tianji_report.md`（可复制转发）与 `tianji_report.html`（金墨风格可视化）。两者由 `scripts/render_report.py` 渲染，不手写版面。

## 分工

| 来源 | 内容 | 规则 |
|---|---|---|
| `chart.json`（脚本） | 四柱、天干/藏干十神、纳音、五行统计、称骨四项与歌诀、紫微十二宫（宫干支、14 主星/辅星分列、空宫借对宫）、四化飞星、格局识别、大限与当前大限、太阳/月亮/上升度数、康熙笔画与五格数理、真太阳时说明与钟表对照、合盘分项与关系矩阵 | 渲染器直接读取，Agent 不复述、不改写 |
| `narrative.json`（Agent） | 旺衰与喜用的文字表述、三段式解读（优势/风险/行动建议）、六宫解读、大限说明、六维信号分、建议、人格速写、关系章节、置信度表、页脚 | 受 `schemas/narrative_v1.schema.json` 约束 |

解读必须与 chart 一致：写到的星曜、宫位、干支、分数都要能在 chart 中找到。

## 章节顺序

1. 标题、场景与假设（`title`/`scenario`/`assumption`）。
2. 基本信息：钟表时间、排盘时间（真太阳时·时辰）、农历、出生地、生肖、MBTI。
3. 时辰说明：经度修正、均时差、距时辰起止分钟数；时辰与钟表时间不同时自动附对照表（时柱、命宫、身宫、称骨）。`time_note` 可补充证件口径等说明。
4. 置信度表（`confidence`：`[维度, 星级, 主要影响因素]`）。
5. 合盘总览（仅 HTML 置于个人章节前；Markdown 置于个人章节后）。
6. 每人一章：四柱 → 五行解读 → 十神 → 称骨 → 紫微（命盘网格、四化、格局、大限、六宫深度解读）→ 西洋星座 → 三才五格（有姓名测算时）→ MBTI 说明 → 六维度倾向（HTML 可拖动权重）→ 建议 → 人格速写与和解命题。
7. 关系章节：`synastry`（多人合盘）或 `parent_child`（亲子）。
8. 页脚：置信度百分比、影响因素、校准问题、民俗参考声明。

## narrative.json 字段

- `persons[]`：与 `chart.members` 同名同序。
  - `strength`、`favor`：旺衰与喜用的一句话，须与 `deep.day_master`/`deep.yongshen` 一致。
  - `wx_reading[]`、`shishen_reading`、`bone_reading`、`western_combo`、`wuge_reading`（无姓名测算时省略）：三段式 `{adv, risk, act}`。
  - `ming_reading`、`dayun_note`：命宫概述与大限说明；`extra_patterns[]` 可补充 chart 未内置的格局。
  - `palace_readings[]`：6–12 项 `{palace, question, triad}`，`palace` 用标准宫名（如 `官禄宫`）；星曜标签由渲染器从 chart 生成。
  - `six_dimensions`：`career/wealth/marriage/health/children/spirit`，每项 `signals` 为 `{bazi|ziwei|bone|zodiac|name|mbti: [0–100 分, 依据]}` 与 `summary`。加权分由渲染器计算；`weights` 可覆盖默认 30/30/15/10/5/10，无 MBTI 或姓名测算时自动剔除对应权重。
  - `advice_title`、`advice[]`（3–8 条）、`sketch{core, fate, outer, reconciliation}`。
- `relation`（可选）：
  - 合盘：`{type:"synastry", score_note?, reading[], nourish, drain, window, advice:[[场景, 建议]], reconciliation}`。
  - 亲子：`{type:"parent_child", title, kid_core, match:[[维度, 关系]], nourish, suppress, advice:[[场景, 建议]], reconciliation}`。
- `confidence[]`、`footer{confidence_pct, factors, questions}`；`disclaimer` 省略时使用默认声明。

所有和解命题必须写成「与XX和解——不是YY，而是ZZ。」，否则渲染器拒绝输出。

## 运行

```bash
python scripts/tianji.py --input input.json --narrative narrative.json --output-dir tianji-output
# 或对已有 chart.json 单独渲染
python scripts/render_report.py --chart tianji-output/chart.json --narrative narrative.json --output-dir tianji-output
```

完整示例见 `examples/report/example_report_input.json` 与 `examples/report/example_narrative.json`（虚构人物）。
