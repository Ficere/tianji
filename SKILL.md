---
name: tianji
description: "天机：八字、紫微、称骨、星座与姓名民俗分析，支持 1–8 人真太阳时排盘、个人与场景合盘及固定金墨风 Markdown/HTML/PDF 报告。仅用于明确命理请求；普通关系、工作、亲子咨询不触发。"
metadata:
  author: computer
  version: '8.5.0'
  language: zh-CN
---

# 天机

把确定性排盘与解释性叙事分开：脚本负责可复现计算，Agent 负责结合用户问题形成克制、可验证的民俗解读。

## 使用边界

- 仅在用户明确要求命理、星盘或姓名民俗测算时使用。不要把普通的人际、管理、亲子或职业问题自动转换成命理分析。
- 明示：命理学属于民俗文化参考，不是科学预测，不替代医疗、法律、财务、招聘、婚育等现实决策。
- 允许用户用代号。除非用户主动要求姓名测算，否则无需真实姓名。
- 不索取身份证号、住址、联系方式等无关敏感信息。
- 不把推演写成确定事实；用“可能、可观察、建议核对”等措辞，并给出现实世界的验证问题。

## 任务路由

先判断任务类型，只加载对应资料：

1. **仅姓名测算**：只需要姓名，可用代号以外的待测名字。运行 `scripts/name_wuge_calc.py`。无需出生信息。
2. **单人完整分析**：需要公历出生日期、出生时间、性别；推荐出生城市。
3. **多人合盘**：收集每个人的完整信息，并确认场景。支持 2–8 人。
4. **渲染已有 reading.json**：先验证契约，再运行 `scripts/generate_html.py`；无需重新排盘。
5. **只问某一模块**：仅回答该模块，不强行扩成完整报告。

场景选择和多人叙事规则见 [references/scenario-guides.md](references/scenario-guides.md)。

## 收集输入

完整排盘需每人的性别、公历日期、当地钟表出生时间及出生城市；MBTI 可选。收集或补齐输入时读取 [references/input-collection.md](references/input-collection.md)，由你查区县代表坐标并记录来源；默认真太阳时，不让用户查坐标，不自行换算输入出生时间。
出生时间未知时，不要自行补中午、子时或其他默认值。先补充时间或做有限分析；只有用户明确指定假设时刻，才可做完整条件合盘。此时传 `birth_time_source: "assumed"` 与 `birth_time_note`（记录用户指定及真实时辰未知），不得称为真实出生盘。边界、标签和评分规则见 [references/editorial-report.md](references/editorial-report.md)，出现假设时刻时必读。

多人场景还需确认 `scenario`：`情侣/伴侣`、`亲子`、`职场搭档`、`团队协作`、`管理者与下属`、`朋友`。没有上下文时，2 人默认“朋友”、3 人以上默认“团队协作”，并在结果中说明该假设。

输入结构以 [schemas/input_v1.schema.json](schemas/input_v1.schema.json) 为唯一契约；不要自行发明字段。

## 标准执行流程

1. 写 `input.json`（含坐标），运行排盘：

   ```bash
   python scripts/tianji.py --input input.json --output-dir tianji-output --scenario 团队协作
   ```

   依次完成输入校验、确定性计算（`chart.json`）、v8.3 `reading.json` 与快速预览 `report.html`。单人场景省略 `--scenario`。
2. 读 `chart.json` 的 `pillar_time`、`warnings`、`deep`、`ziwei`，按 [references/report-format.md](references/report-format.md) 写 `narrative.json`。只写解读，不复述或改写事实字段。
3. 按固定编辑式结构渲染：基础与置信度 → 个人命盘 → 场景合盘 → 协作指南 → 时间线 → 和解命题 → 十二宫附录。准备结婚时，读取 [references/editorial-report.md](references/editorial-report.md) 与 [templates/editorial-narrative.json](templates/editorial-narrative.json)，填写婚前六项讨论与双向沟通，不改成亲子报告。

   ```bash
   python scripts/tianji.py --input input.json --narrative narrative.json --output-dir tianji-output
   ```

   默认交付 `tianji_report.md/.html`；用户要求 PDF 时安装 `requirements-report.txt` 并在命令中加 `--pdf`，生成同内容金墨 A4 的 `tianji_report.pdf`。检查中文、表格、假设页眉和分页后交付；具体样式与旧版 `--report-style legacy` 见 [references/editorial-report.md](references/editorial-report.md)。渲染校验失败时修正 narrative 后重跑。

计算模块或排错时再按 [references/calculation-workflow.md](references/calculation-workflow.md) 分步运行。

## 解释层要求

- `chart.json` 是计算事实源；不要为了叙事顺畅改写四柱、黄经、星曜落宫或分数。
- `reading.json` 必须符合 [schemas/reading_v8.schema.json](schemas/reading_v8.schema.json)。字段语义和旧版迁移见 [references/output-contract.md](references/output-contract.md)。
- 区分两类置信度：计算可复现性/输入完整度，与命理观点的预测有效性不是一回事。
- 同时呈现支持与反证：指出哪项信息支持某个假设，也指出用户可用什么现实行为验证或否定它。
- 合盘评分用于组织观察维度，不用于给关系下结论。优先解释分项、现实摩擦点和沟通实验。
- 避免恐吓、宿命化、人格定型、吉凶承诺和精确事件预测。

完整写作纪律见 [references/interpretation-guidelines.md](references/interpretation-guidelines.md)。需要结构化叙事时使用 [prompts/reading_json_prompt.md](prompts/reading_json_prompt.md)；合盘额外加载 [prompts/synastry_addendum.md](prompts/synastry_addendum.md)。

## 姓名专用流程

```bash
python scripts/name_wuge_calc.py --name "欧阳娜娜"
```

- 脚本会自动识别常见复姓；只有自动识别不符预期时才传 `--surname-len 1|2`。
- 清楚区分“三才评级”和基于五格加权的“综合评级”。
- 姓名学属于民俗数理，不据此判断人格、能力或现实资格。

## 渲染已有结果

```bash
python scripts/reading_contract.py reading.json --normalize
python scripts/generate_html.py --reading reading.json --output report.html
```

`--normalize` 只迁移 v8.0–v8.2 的已知字段别名；未知或缺失的必填结构仍应报错，不静默补造内容。

## 验证与故障处理

- 运行完整测试：`python -m unittest discover -s tests -p 'test_*.py'`。
- 安装第三方验证依赖：`pip install -r requirements-dev.txt && npm ci`。
- 依赖缺失、城市无法解析或时区只能估算时，保留 `warnings`，不要把降级结果包装成完整精度。
- 算法的第三方对照、固定版本与容差见 [references/validation-sources.md](references/validation-sources.md)。
- 晚子时采用“不换日柱”约定；若用户拿其他工具对比，先核对门派约定、时区、历法与夏令时，再判断是否为错误。

## 交付检查

交付前确认：

- 输入没有被猜测或偷偷补齐；用户指定的假设时刻必须保留来源、醒目标签与限制。
- 每人 `pillar_time.basis` 为 `true_solar`，坐标来源已在报告中说明。
- `tianji_report.md` 与 `tianji_report.html` 均由渲染器生成，且解读中提到的干支、星曜、宫位、分数都能在 `chart.json` 中找到。
- 1–8 人的编号、场景和姓名/代号一致。
- 页面中姓名、标题、城市等外部文本已转义。
- 报告包含民俗参考声明和现实验证建议。
- 编辑式报告不强制六维信号打分或总体置信度百分比；合盘得分不是婚姻成功率，不用于劝婚或劝退。
- 不声称第三方交叉验证证明命理具有科学预测效度；它只验证计算实现的一致性。
