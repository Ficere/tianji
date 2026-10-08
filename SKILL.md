---
name: tianji
description: "天机：传统命理与姓名民俗分析技能。仅当用户明确要求算命、八字、五行、称骨、紫微斗数、太阳/月亮/上升星座、三才五格、姓名测算、命盘或多人命理合盘时使用；支持 1–8 人的真太阳时确定性排盘与固定格式 Markdown/HTML 报告。普通沟通建议、工作安排、亲子或关系咨询若未明确要求命理视角，不应触发此技能。"
metadata:
  author: computer
  version: '8.4.0'
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

完整排盘对每位成员收集：

- `name`：可用“甲方/乙方”等代号；使用代号时传 `name_is_alias: true`，跳过三才五格。
- `gender`：男/女，用于传统排盘中的大运方向。
- `solar_date`：公历 `YYYY-MM-DD`。
- `birth_time`：出生地当地钟表时间 `HH:MM`（出生证明上的时间），不要自行换算成真太阳时。
- `birth_city`：出生地名称，尽量精确到区县。
- `birth_lat` / `birth_lon`：出生地坐标，优先于 `birth_city`。
- `mbti`：可选，只能作为用户自报的补充信息。

### 出生地坐标与真太阳时

时柱、日柱、农历日、称骨与紫微时辰默认按真太阳时排（`time_basis: "true_solar"`），年柱、月柱按出生瞬间与节气比较，西洋星座按出生瞬间。坐标决定时辰，必须由你解决，不要让用户自己查：

1. 用户给到区县（如“西双版纳州勐海县”）而 `references/city_coords.json` 只有地级市或没有该地时，自行检索该区县政府驻地的经纬度。
2. 以 `birth_lat`/`birth_lon` 传入，`birth_city` 保留用户原话用于展示；在报告 `time_note` 中写明坐标来源。
3. 只有用户明确要求按钟表时间排盘时才传 `time_basis: "clock"`。
4. 出现 `TRUE_SOLAR_UNAVAILABLE` 时不得交付完整报告，先补坐标重算。
5. 真太阳时距时辰边界不足 15 分钟，或用户提供的时间来源不确定时，在置信度表中降级并说明另一时辰的差异（渲染器会自动附钟表对照表）。
出生时间未知时，不要猜测中午、子时或其他默认值。说明完整四柱、紫微和上升星座无法可靠生成；请用户补充时间，或改做仅姓名/不依赖时辰的有限分析并清楚标注缺失。

多人场景还需确认 `scenario`：`情侣/伴侣`、`亲子`、`职场搭档`、`团队协作`、`管理者与下属`、`朋友`。没有上下文时，2 人默认“朋友”、3 人以上默认“团队协作”，并在结果中说明该假设。

输入结构以 [schemas/input_v1.schema.json](schemas/input_v1.schema.json) 为唯一契约；不要自行发明字段。

## 标准执行流程

1. 写 `input.json`（含坐标），运行排盘：

   ```bash
   python scripts/tianji.py --input input.json --output-dir tianji-output --scenario 团队协作
   ```

   依次完成输入校验、确定性计算（`chart.json`）、v8.3 `reading.json` 与快速预览 `report.html`。单人场景省略 `--scenario`。
2. 读 `chart.json` 的 `pillar_time`、`warnings`、`deep`、`ziwei`，按 [references/report-format.md](references/report-format.md) 写 `narrative.json`。只写解读，不复述或改写事实字段。
3. 渲染固定格式报告，交付 `tianji_report.md` 与 `tianji_report.html` 两份文件：

   ```bash
   python scripts/tianji.py --input input.json --narrative narrative.json --output-dir tianji-output
   ```

   渲染器校验姓名顺序、宫名与和解命题格式，失败时修正 narrative 后重跑。

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

- 输入没有被猜测或偷偷补齐。
- 每人 `pillar_time.basis` 为 `true_solar`，坐标来源已在报告中说明。
- `tianji_report.md` 与 `tianji_report.html` 均由渲染器生成，且解读中提到的干支、星曜、宫位、分数都能在 `chart.json` 中找到。
- 1–8 人的编号、场景和姓名/代号一致。
- 页面中姓名、标题、城市等外部文本已转义。
- 报告包含民俗参考声明和现实验证建议。
- 不声称第三方交叉验证证明命理具有科学预测效度；它只验证计算实现的一致性。
