# 🔮 天机 / Tianji

一站式命理测算 Agent Skill —— 输入出生日期和姓名，自动完成八字五行、袁天罡称骨、紫微斗数、西洋星座、三才五格姓名测算；多人时自动合盘评分。

适用于个人、夫妻、家庭、团队、合伙人等任意组合。

An all-in-one Agent Skill for traditional Chinese fortune analysis. Input birth data and name, get BaZi (Four Pillars), bone weight fortune, Zi Wei Dou Shu chart, Western zodiac, Sancai Wuge (name numerology based on Kangxi dictionary strokes), and multi-person synastry scoring.

遵循 [Agent Skills 开放标准](https://agentskills.io)，兼容 Claude Code、Cursor、GitHub Copilot、Codex、Windsurf、Gemini CLI、Perplexity Computer 等 30+ AI Agent 平台。

## 安装 / Install

```bash
npx skills add Ficere/tianji
```

> 需要 Node.js。安装后 Agent 会自动发现并按需加载该技能。
>
> Requires Node.js. Once installed, your agent will auto-discover and load this skill when relevant.

<details>
<summary>其他安装方式 / Alternative methods</summary>

**手动安装 / Manual install：**

```bash
git clone https://github.com/Ficere/tianji.git
# 将整个目录复制到你的 Agent 的 skills 目录下即可
# Copy the directory to your agent's skills folder:
#   Claude Code:  ~/.claude/skills/
#   Cursor:       .cursor/skills/
#   Copilot:      .github/skills/
#   Codex:        ~/.codex/skills/
#   Gemini CLI:   .gemini/skills/
```

**Perplexity Computer：**

下载本仓库 zip → 在 [Skills 管理页面](https://www.perplexity.ai/computer/skills) 上传。

</details>

## 使用 / Usage

安装后直接用自然语言触发，无需任何配置：

```
帮我算一下，张三 1990年5月20日 08:30 出生，男
```

```
张三 1990-05-20 08:30 男，李四 1992-08-15 14:00 女，做个合盘分析
```

```
帮我测一下"刘德华"这个名字的三才五格
```

```
帮我排个紫微命盘
```

```
天秤座和白羊座配不配
```

## 测算能力 / Features

| 模块 | 说明 |
|------|------|
| **八字五行** | 四柱排盘、五行分布、十神、纳音、藏干、日主旺衰 |
| **袁天罡称骨** | 年月日时骨重查表、52 首歌诀、等级评定 |
| **紫微斗数** | 命宫/身宫、十二宫、五行局、命主/身主、大运方向 |
| **西洋星座** | 太阳星座、元素守护星、两人相位匹配 |
| **三才五格** | 康熙字典笔画（48700+ 字）、天格/人格/地格/外格/总格、81 数理吉凶、三才生克配置、综合评分 |
| **合盘评分** | 五行互补 + 生肖关系 + 星座 + 日主生克 + 称骨 + 姓名合盘，100 分制综合评定 |

<details>
<summary>合盘评分细则 / Scoring breakdown</summary>

| 维度 | 分值 | 评估内容 |
|------|------|----------|
| 五行互补 | 25 | 合计五行平衡度、互补关系 |
| 五行俱全 | 5 | 是否五行齐全 |
| 生肖关系 | 20 | 六合 / 三合 / 六冲 / 相害 |
| 星座合盘 | 15 | 相位角度匹配度 |
| 日主生克 | 20 | 天干合 / 相生 / 相克 |
| 称骨对比 | 15 | 平均骨重 |
| 姓名合盘 | 5 | 人格五行互补 + 三才配置（仅提供姓名时） |
| **总分** | **100** | ★ ~ ★★★★★ |

</details>

<details>
<summary>三才五格计算说明 / Sancai Wuge details</summary>

**五格计算公式：**

| 类型 | 天格 | 人格 | 地格 | 外格 | 总格 |
|------|------|------|------|------|------|
| 单姓复名 | 姓+1 | 姓+名₁ | 名₁+名₂ | 总-人+1 | 全部之和 |
| 单姓单名 | 姓+1 | 姓+名 | 名+1 | 2 | 全部之和 |
| 复姓复名 | 姓₁+姓₂ | 姓₂+名₁ | 名₁+名₂ | 总-人 | 全部之和 |
| 复姓单名 | 姓₁+姓₂ | 姓₂+名 | 名+1 | 总-人+1 | 全部之和 |

**数理五行映射：** 尾数 1-2 木、3-4 火、5-6 土、7-8 金、9-0 水

**81 数理：** 超过 81 减去 80 后查吉凶表

**笔画标准：** 康熙字典（非现代简体），内置 48700+ 字查找表

</details>

## 独立脚本 / Standalone Scripts

两个脚本均可脱离 Agent 平台独立运行（Python 3，无第三方依赖）：

**命理测算引擎：**
```bash
python scripts/fortune_calc.py --input data.json --output result.json
```

**三才五格姓名测算：**
```bash
python scripts/name_wuge_calc.py --name "张三" --surname-len 1
python scripts/name_wuge_calc.py --input names.json --output result.json
```

<details>
<summary>命理测算输入 JSON 示例 / Sample input for fortune_calc</summary>

```json
{
  "members": [
    {
      "name": "张三",
      "gender": "男",
      "solar_date": "1990-05-20",
      "birth_time": "08:30",
      "bazi": ["庚午", "辛巳", "乙酉", "庚辰"],
      "lunar": {"month": 4, "day": 26},
      "surname_len": 1
    },
    {
      "name": "李四",
      "gender": "女",
      "solar_date": "1992-08-15",
      "birth_time": "14:00",
      "bazi": ["壬申", "戊申", "癸亥", "乙未"],
      "lunar": {"month": 7, "day": 17},
      "surname_len": 1
    }
  ]
}
```

> ⚠️ `bazi` 中的日柱必须通过万年历验证，不可手算。`surname_len` 用于三才五格计算（1=单姓，2=复姓）。

</details>

<details>
<summary>姓名测算输入 JSON 示例 / Sample input for name_wuge_calc</summary>

```json
{
  "names": [
    {"name": "张三", "surname_len": 1},
    {"name": "欧阳明华", "surname_len": 2}
  ]
}
```

</details>

## 目录结构 / Structure

```
tianji/
├── SKILL.md                           # 技能入口（Agent 自动读取）
├── scripts/
│   ├── fortune_calc.py                # 命理测算引擎（八字/称骨/紫微/星座/合盘）
│   └── name_wuge_calc.py              # 三才五格姓名测算引擎
├── references/
│   ├── kangxi_strokes.json            # 康熙字典笔画查找表（48700+ 字）
│   ├── weight-tables.md               # 称骨对照表（52 首歌诀）
│   └── output-template.md             # 报告输出模板
├── LICENSE
└── README.md
```

## 免责声明 / Disclaimer

本项目仅供学习和娱乐。命理学并非精确科学，人生命运取决于个人努力和选择。三才五格姓名学源自日本熊崎健翁的"五格剖象法"，属于民俗文化范畴，不应作为决策依据。

For educational and entertainment purposes only. Name numerology (Sancai Wuge) originates from Kumazaki Keno's "Five-Grid Method" and belongs to folk culture — it should not be used for life decisions.

## License

MIT
