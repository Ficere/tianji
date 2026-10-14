# 固定报告格式

默认最终输出为同内容的 Markdown 与金墨 HTML；用户要求 PDF 时追加同内容 A4 PDF。运行入口 `scripts/tianji.py` 或 `scripts/render_report.py`，CLI 默认 `--report-style editorial`。不得每次手写 HTML、复制真实报告或另做临时 PDF 脚本。

编写任何完整个人或多人报告前读取 [editorial-report.md](editorial-report.md)。准备结婚的伴侣报告额外读取 `templates/editorial-narrative.json` 字段片段；场景由用户确认，不按人数自动改成家庭。

## 事实与叙事

`chart.json` 提供四柱、十神、纳音、藏干、五行、称骨、紫微主辅星与四化、起运与流年、三星度数、姓名数理及合盘评分。`narrative.json` 只负责解读、现实验证、场景协作、置信度说明；不要重复或改写计算事实。

叙事继续符合 `schemas/narrative_v1.schema.json`，每人姓名同序、宫名标准、和解命题使用原契约：

「与XX和解——不是YY，而是ZZ。」

每人保留旺衰喜用、五行与十神三段式（优势/风险/行动）、称骨三段式、命宫与六宫以上解读、大限说明、三星三段式、建议和内核/阶段/外在/和解速写。姓名或 MBTI 未测时不补造；编辑式可省略 `six_dimensions`，`footer.confidence_pct` 可为 `null`，不输出总体预测准确率。

新增 `editorial` 字段包含短引句、阶段、协作小节、坐标来源。完整渲染字段与假设时刻标签见 `editorial-report.md`；绝不能只在页脚写时辰未知，却把个人章节和评分当作真实盘。

## 输出顺序

基础信息与置信度 → 个人命盘 → 场景合盘 → 对应协作指南 → 当前阶段与三年时间线 → 和解命题与校准 → 紫微十二宫附录。不得先堆互动仪表、强制六维评分，或把全部十二宫长表夹在每个人的叙事中。

用户明确要求旧版六维互动报告时才读 [legacy-report-format.md](legacy-report-format.md)，使用 `--report-style legacy`；旧版不支持假设时刻，以免隐藏输入边界。
