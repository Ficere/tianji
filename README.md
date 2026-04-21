# 🔮 天机 / Tianji

一站式命理测算 Agent Skill —— 输入出生日期和姓名，自动完成八字五行、袁天罡称骨、紫微斗数、西洋星座、三才五格姓名测算；多人时自动合盘评分。

适用于个人、夫妻、家庭、团队、合伙人等任意组合。

An all-in-one Agent Skill for traditional Chinese fortune analysis. Input birth data and name, get BaZi (Four Pillars), bone weight fortune, Zi Wei Dou Shu chart, Western zodiac, Sancai Wuge (name numerology based on Kangxi dictionary strokes), and multi-person synastry scoring.

遵循 [Agent Skills 开放标准](https://agentskills.io)，兼容 Claude Code、Cursor、GitHub Copilot、Codex、Windsurf、Gemini CLI、Perplexity Computer 等 30+ AI Agent 平台。

[🛠️ Coze 技能商店](https://www.coze.cn/skills?skill_share_pid=7629277828386947078) · [📦 npx 安装](#安装--install) · [📜 Agent Skills 标准](https://agentskills.io)

[![Validate](https://github.com/Ficere/tianji/actions/workflows/validate.yml/badge.svg)](https://github.com/Ficere/tianji/actions/workflows/validate.yml)
[![Publish](https://github.com/Ficere/tianji/actions/workflows/publish.yml/badge.svg)](https://github.com/Ficere/tianji/actions/workflows/publish.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

<!-- 各平台一键安装命令 / Per-platform one-liners -->

| 平台 / Platform | 一键安装 / One-liner |
|---|---|
| [ClawHub](https://clawhub.com) | `clawhub install tianji` |
| [skills.sh](https://skills.sh) | `npx skills add Ficere/tianji` |
| [agentskill.sh](https://agentskill.sh) | `/learn @Ficere/tianji` |
| [Smithery](https://smithery.ai) | Web UI 一键绑定 / one-click bind |
| [Coze 技能商店](https://www.coze.cn/skills?skill_share_pid=7629277828386947078) | Web UI 「获取」 / click "Get" |

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

**Coze 技能商店 / Coze Skill Store：**

直接访问 [技能商店页面](https://www.coze.cn/skills?skill_share_pid=7629277828386947078)，点击「获取」即可添加到你的 Coze Agent 中。

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
| **八字五行** | 四柱全自动计算（天文算法精确节气）、五行分布、十神、纳音、藏干、日主旺衰 |
| **袁天罡称骨** | 年月日时骨重查表、52 首歌诀、等级评定 |
| **紫微斗数** | 命宫/身宫、十二宫、五行局、命主/身主、大运方向 |
| **西洋星座** | 太阳星座、元素守护星、两人相位匹配 |
| **三才五格** | 康熙字典笔画（48700+ 字）、天格/人格/地格/外格/总格、81 数理吉凶、三才生克配置、综合评分与评级 |
| **合盘评分** | 五行互补 + 生肖关系 + 星座 + 日主生克 + 称骨 + 姓名合盘，100 分制综合评定 |

> **v4.0 新特性**：四柱八字现在完全由脚本自动计算，无需手动排盘。年柱基于立春精确时刻（Meeus VSOP87 太阳黄经算法），月柱基于 12 个月建节气的精确时刻，日柱基于儒略日编号，时柱基于五鼠遁。已经过多组边界用例交叉校验。
>
> **v4.0 New**: Four pillars are now fully auto-calculated. Year pillar uses precise Lichun timing (Meeus VSOP87), month pillar uses exact Jieqi moments, day pillar uses JDN, hour pillar uses Wushu Dun. Cross-verified against reference sites.

> **v4.1 修复**：三才五格新增「综合评级」，与「三才评级」明确区分。详见下方说明。
>
> **v4.1 Fix**: Added "Overall Rating" for name numerology, clearly separated from "Sancai Rating". See details below.

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

---

**⚠️ 三才评级 vs 综合评级（v4.1）**

姓名测算输出包含两个独立的评级，请注意区分：

| 评级 | 含义 | 示例 |
|------|------|------|
| **三才评级** | 仅评价三才配置（天格·人格·地格的五行生克关系） | "金金金" → 三才评级「大吉」 |
| **综合评级** | 基于五格数理吉凶 + 三才配置的加权综合评分 | 综合 66 分 → 综合评级「平·中等」 |

一个姓名可能三才配置极佳（如三才同属，评级「大吉」），但五格数理偏弱（如多为「半吉」），导致综合评分不高。反之，五格数理全为「大吉」的姓名即使三才仅为「吉」，综合评分仍可达 95+。

**综合评级标准 / Overall Rating Scale：**

| 综合评分 | 综合评级 | Score | Overall Rating |
|----------|----------|-------|----------------|
| ≥ 90 | 大吉 · 上上等 | ≥ 90 | Excellent |
| ≥ 80 | 吉 · 上等 | ≥ 80 | Good |
| ≥ 70 | 半吉 · 中上 | ≥ 70 | Above Average |
| ≥ 60 | 平 · 中等 | ≥ 60 | Average |
| ≥ 50 | 偏弱 · 中下 | ≥ 50 | Below Average |
| < 50 | 凶 · 下等 | < 50 | Poor |

**综合评分权重 / Score Weights：** 人格 35% + 地格 20% + 总格 20% + 三才 15% + 天格 5% + 外格 5%

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
      "lunar": {"month": 4, "day": 26},
      "surname_len": 1
    },
    {
      "name": "李四",
      "gender": "女",
      "solar_date": "1992-08-15",
      "birth_time": "14:00",
      "lunar": {"month": 7, "day": 17},
      "surname_len": 1
    }
  ]
}
```

> `bazi` 字段可省略，脚本基于天文算法自动计算完整四柱。若提供了 bazi，脚本会自动校验并修正。`surname_len` 用于三才五格计算（1=单姓，2=复姓）。

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

## 发布与分发 / Publishing

本仓库配置了 CI 自动发布流程，push tag `v*` 即可一键分发到以下主流平台：

| 平台 | 类型 | 安装命令 |
|------|------|----------|
| [ClawHub](https://clawhub.com) | OpenClaw 官方注册表 | `clawhub install tianji` |
| [agentskill.sh](https://agentskill.sh) | 社区目录 | `/learn @Ficere/tianji` |
| [skills.sh](https://skills.sh) | 多平台索引 | `npx skills add Ficere/tianji` |
| [Smithery](https://smithery.ai) | MCP 大市场 | Web UI 一键安装 |
| [Coze 技能商店](https://www.coze.cn/skills?skill_share_pid=7629277828386947078) | 字节 Coze | Web UI「获取」 |

发布流程与凭证配置见 [.github/PUBLISHING.md](.github/PUBLISHING.md)。

## 免责声明 / Disclaimer

本项目仅供学习和娱乐。命理学并非精确科学，人生命运取决于个人努力和选择。三才五格姓名学源自日本熊崎健翁的"五格剖象法"，属于民俗文化范畴，不应作为决策依据。

For educational and entertainment purposes only. Name numerology (Sancai Wuge) originates from Kumazaki Keno's "Five-Grid Method" and belongs to folk culture — it should not be used for life decisions.

## License

MIT
