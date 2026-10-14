# 编辑式固定输出

个人与多人最终报告默认用 `editorial`。沿用这次认可的“基础 → 个人 → 合盘 → 场景协作 → 时间线 → 和解 → 附录”结构，不复制真实案例，不把婚前模板用于亲子场景。

## 输入与假设

- 未知时辰不自动填值。用户主动指定假设时刻后，在成员输入中填 `birth_time_source: "assumed"` 和 `birth_time_note`，后者写明用户指定依据与实际未知；输入 schema 会拒绝缺说明的假设。
- 条件结果包括时柱、紫微、称骨、月亮、上升、起运、大限及受其影响的合盘分项。日柱也要核对真太阳午夜边界；不能因为假设是中午，就认定实际日柱已经确认。
- 假设标签由 `chart.json` 输入来源驱动，自动进入开头、成员标题、表格、合盘与 PDF 页眉；不是由 Agent 自由选择隐藏。
- `warnings` 是输入/计算告警，不等同预测有效性。假设计算可以可复现，但不是实际出生盘。

## 固定章节

| 顺序 | 章节 | 必须保留 |
|---|---|---|
| 开头 | 标题、短引句、场景与假设 | 民俗参考、条件分析声明；不把百分比当预测准确率 |
| 基础 | 基础信息与置信度 | 日期、钟表/真太阳时、出生地、四柱、生肖、输入完整度、坐标来源与晚子时约定 |
| 个人 | 每人独立命盘 | 八字/纳音/十神/藏干、表层五行、旺衰喜用、优势/风险/行动、称骨四项、紫微宫位与四化、太阳/月亮/上升、人格速写 |
| 合盘 | 场景合盘 | 五行地图、能量流向、关系矩阵、脚本分项/总分/分母；无合盘不造本节 |
| 协作 | 婚前/亲子/团队等对应指南 | 场景内容来自 narrative；婚前六项讨论与双向沟通；不把建议称为命盘事实 |
| 时间 | 当前阶段与时间线 | 当前八字大运、当前紫微大限、未来三年；虚岁与起运口径分开 |
| 结尾 | 和解命题与校准 | 三个观察方向、支持/反证、需要补充的输入；不作总体置信度百分比 |
| 附录 | 紫微十二宫 | 宫干支、十四主星/辅星分列、空宫借对宫 |

表层计数为零不等于藏干不存在；称骨历史歌诀不按字面许诺富贵或要求出家。星座分项须标为“太阳星座整宫分类”，不是精确黄经相位。不得将土克水写成克夫/克妻，不把分数变成劝婚、劝退或成功概率。

编辑式不要求六维信号打分，也不强制姓名、MBTI；已有姓名学事实仍可展示。完整是已定义模块完整呈现，不是全行星专业占星盘，也不保证现实预测。人物与话题数量可变，不能固定为两人或十二页。

## 叙事写法

沿用 `narrative_v1`；`six_dimensions` 在编辑式可省略，`footer.confidence_pct` 填 `null`。新字段 `editorial` 见 `templates/editorial-narrative.json`，包括短引句、用户明确的阶段、协作小节、坐标来源；其余事实全部由渲染器读 chart。

准备结婚时，协作章节必须覆盖：钱与债务、居住工作、家务照护、双方父母边界、生育亲密、冲突安全；再给双向沟通、一次低成本现实验证。已有 `relation.reading/nourish/drain/advice` 不得遗漏，`relation.window` 归入时间线。所有和解命题继续遵守原契约；不把多个民俗体系“相符”当成科学交叉验证。

## 渲染与 PDF

```bash
pip install -r requirements.txt
python scripts/tianji.py --input input.json --narrative narrative.json --output-dir out
# 用户要求 PDF 时
pip install -r requirements-report.txt
python scripts/tianji.py --input input.json --narrative narrative.json --output-dir out --pdf
# 仅渲染已有计算结果
python scripts/render_report.py --chart out/chart.json --narrative narrative.json --output-dir out --pdf
```

输出 `tianji_report.md/.html`；`--pdf` 追加 `.pdf`。PDF 由相同 HTML 生成，使用 `assets/editorial-report.css`：金墨封面、中文宋体标题/黑体正文、A4、清楚页眉页码、表格重复表头、禁止单行标题与孤立列表；不把十二页硬编码。先检查所有页，长表允许自然跨页但不截断条目；不得以缩小到不可读字号来强塞一页。明确假设文字用实色，避免透明文字导致 PDF 对比度误报。

旧格式可显式用 `--report-style legacy`，其原有 `six_dimensions` 和置信度数值保持兼容。Python 的 `run_pipeline` 为旧调用默认 legacy；CLI 与技能执行默认 editorial，程序调用需显式传 `report_style="editorial"`。
