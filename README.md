# 🔮 天机 / Tianji

一站式命理测算 Agent Skill —— 输入出生日期，自动完成八字五行、袁天罡称骨、紫微斗数、西洋星座分析；多人时自动合盘评分。

适用于个人、夫妻、家庭、团队、合伙人等任意组合。

An all-in-one Agent Skill for traditional Chinese fortune analysis. Input birth data, get BaZi (Four Pillars), bone weight fortune, Zi Wei Dou Shu chart, Western zodiac analysis, and multi-person synastry scoring — for individuals, couples, families, teams, or any group.

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
| **合盘评分** | 五行互补 + 生肖关系 + 星座 + 日主生克 + 称骨，100 分制综合评定 |

<details>
<summary>合盘评分细则 / Scoring breakdown</summary>

| 维度 | 分值 | 评估内容 |
|------|------|----------|
| 五行互补 | 25 | 合计五行平衡度、互补关系 |
| 五行俱全 | 5 | 是否五行齐全 |
| 生肖关系 | 20 | 六合 / 三合 / 六冲 / 相害 |
| 星座合盘 | 15 | 相位角度匹配度 |
| 日主生克 | 20 | 天干合 / 相生 / 相克 |
| 称骨对比 | 20 | 平均骨重 |
| **总分** | **100** | ★ ~ ★★★★★ |

</details>

## 独立脚本 / Standalone Script

`scripts/fortune_calc.py` 也可以脱离 Agent 平台独立运行（Python 3，无第三方依赖）：

```bash
python scripts/fortune_calc.py --input data.json --output result.json
```

<details>
<summary>输入 JSON 示例 / Sample input</summary>

```json
{
  "members": [
    {
      "name": "张三",
      "gender": "男",
      "solar_date": "1990-05-20",
      "birth_time": "08:30",
      "bazi": ["庚午", "辛巳", "甲子", "戊辰"],
      "lunar": {"month": 4, "day": 26}
    },
    {
      "name": "李四",
      "gender": "女",
      "solar_date": "1992-08-15",
      "birth_time": "14:00",
      "bazi": ["壬申", "戊申", "丙寅", "乙未"],
      "lunar": {"month": 7, "day": 17}
    }
  ]
}
```

> ⚠️ `bazi` 中的日柱必须通过万年历验证，不可手算。

</details>

## 目录结构 / Structure

```
tianji/
├── SKILL.md               # 技能入口（Agent 自动读取）
├── scripts/
│   └── fortune_calc.py    # 计算引擎
├── references/
│   ├── weight-tables.md   # 称骨对照表（52 首歌诀）
│   └── output-template.md # 报告输出模板
├── LICENSE
└── README.md
```

## 免责声明 / Disclaimer

本项目仅供学习和娱乐。命理学并非精确科学，人生命运取决于个人努力和选择。

For educational and entertainment purposes only.

## License

MIT
