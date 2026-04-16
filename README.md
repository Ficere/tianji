# 🏮 Chinese Fortune Analysis Skills / 中华命理测算技能合集

一套用于 [Perplexity Computer](https://www.perplexity.ai/computer/skills) 的命理测算 Agent Skills，涵盖八字五行、袁天罡称骨、紫微斗数、西洋星座、多人合盘评分等完整测算能力。

A collection of Agent Skills for [Perplexity Computer](https://www.perplexity.ai/computer/skills) that perform traditional Chinese fortune analysis — BaZi (Four Pillars), bone weight fortune telling, Zi Wei Dou Shu charting, Western zodiac, and multi-person synastry scoring.

---

## 📦 技能列表 / Skills

| 技能 / Skill | 说明 / Description |
|---|---|
| **fortune-full-analysis** | 🔮 一站式综合测算。输入出生信息，自动完成八字、称骨、紫微、星座全流程分析，多人时自动合盘评分。<br/>Full pipeline: input birth data → BaZi + bone weight + Zi Wei + zodiac + synastry scoring. |
| **bazi-analysis** | 八字五行排盘。排四柱、算五行分布、十神、纳音、藏干、日主旺衰。<br/>Four Pillars of Destiny — heavenly stems, earthly branches, five elements, ten gods. |
| **bone-weight-fortune** | 袁天罡称骨算命。按年月日时查骨重，对应歌诀解命。<br/>Yuan Tiangang bone weight fortune — sum year/month/day/hour weights, look up destiny poem. |
| **ziwei-chart** | 紫微斗数概要排盘。安命宫身宫、十二宫、五行局、命主身主。<br/>Zi Wei Dou Shu overview — life palace, body palace, twelve palaces, five-element bureau. |
| **zodiac-analysis** | 西洋星座分析与配对。判断星座、元素、守护星、两人相位匹配度。<br/>Western zodiac — sign traits, elements, ruling planets, aspect compatibility. |
| **family-synastry** | 家庭 / 团队合盘评估。五行互补、生肖关系、星座合盘、日主生克、称骨对比，综合评分 100 分制。<br/>Multi-person synastry — five elements balance, Chinese zodiac relations, zodiac aspects, day master interactions, bone weight comparison. |

---

## 🚀 安装方法 / Installation

### 方式一：安装综合技能（推荐）

如果只需要一站式测算能力，安装 `fortune-full-analysis` 即可，它整合了所有子技能的逻辑：

1. 下载 `skills/fortune-full-analysis/` 目录
2. 压缩为 `.zip` 文件
3. 在 [Perplexity Computer Skills 管理页面](https://www.perplexity.ai/computer/skills) 上传安装

```bash
cd skills
zip -r fortune-full-analysis.zip fortune-full-analysis/
```

### 方式二：安装全部 6 个技能

分别安装每个子技能，可以按需单独调用：

```bash
cd skills
for skill in bazi-analysis bone-weight-fortune ziwei-chart zodiac-analysis family-synastry fortune-full-analysis; do
  zip -r "${skill}.zip" "${skill}/"
done
```

然后在 Skills 管理页面逐一上传 6 个 `.zip` 文件。

### 方式三：手动安装单个技能

如果某个技能目录只有 `SKILL.md`（无 references / scripts），可以直接上传 `SKILL.md` 文件。

---

## 📖 使用方式 / Usage

安装后，在 Perplexity Computer 中直接用自然语言触发即可：

**综合测算：**
> "帮我算一下，张三 1990年5月20日 08:30 出生，男"

**多人合盘：**
> "张三 1990-05-20 08:30 男，李四 1992-08-15 14:00 女，帮我们做个合盘分析"

**单项查询：**
> "我想查查庚午年三月的称骨有多重"
> "帮我排一下紫微命盘"
> "天秤座和白羊座配对怎么样"

---

## 🗂 目录结构 / Repository Structure

```
fortune-skills/
├── README.md
├── LICENSE
└── skills/
    ├── fortune-full-analysis/     # 综合测算（一站式）
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── fortune_calc.py    # 完整计算脚本
    │   └── references/
    │       ├── weight-tables.md   # 称骨对照表
    │       └── output-template.md # 报告模板
    ├── bazi-analysis/             # 八字五行
    │   ├── SKILL.md
    │   └── references/
    │       └── output-template.md
    ├── bone-weight-fortune/       # 袁天罡称骨
    │   ├── SKILL.md
    │   └── references/
    │       └── weight-tables.md
    ├── ziwei-chart/               # 紫微斗数
    │   ├── SKILL.md
    │   └── references/
    │       └── ziwei-tables.md
    ├── zodiac-analysis/           # 西洋星座
    │   ├── SKILL.md
    │   └── references/
    │       └── zodiac-details.md
    └── family-synastry/           # 合盘评估
        ├── SKILL.md
        └── references/
            └── output-format.md
```

---

## 🔧 计算脚本 / Calculation Script

`fortune-full-analysis` 内置了一个独立的 Python 计算脚本 `fortune_calc.py`，也可以脱离 Perplexity Computer 单独使用：

```bash
python skills/fortune-full-analysis/scripts/fortune_calc.py \
  --input data.json \
  --output result.json
```

输入 JSON 示例：

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

> ⚠️ `bazi` 字段中的日柱必须通过万年历或在线排盘工具验证，不可手算。

---

## 📐 测算维度 / Analysis Dimensions

### 八字五行 (BaZi / Four Pillars)
- 四柱排盘（年柱、月柱、日柱、时柱）
- 天干地支五行统计（金木水火土分布）
- 六十甲子纳音五行
- 十神分析（比肩、劫财、食神、伤官、偏印、正印、偏财、正财、七杀、正官）
- 地支藏干
- 日主旺衰与喜用神

### 袁天罡称骨 (Bone Weight Fortune)
- 年、月、日、时四项骨重查表
- 总骨重与等级（2两1钱 ~ 7两2钱）
- 对应歌诀解读（52 首）

### 紫微斗数 (Zi Wei Dou Shu)
- 命宫、身宫定位
- 十二宫位排列
- 五行局（水二局 ~ 火六局）
- 命主、身主星
- 大运方向

### 西洋星座 (Western Zodiac)
- 太阳星座判定
- 元素属性（火/土/风/水）
- 守护星与模式
- 两人相位分析（0°~180°）

### 合盘评分 (Synastry Scoring)

| 维度 | 权重 | 评估内容 |
|------|------|----------|
| 五行互补 | 25分 | 合计五行平衡度、互补关系 |
| 五行俱全 | 5分 | 家庭是否五行齐全 |
| 生肖关系 | 20分 | 六合 / 三合 / 六冲 / 相害 |
| 星座合盘 | 15分 | 相位角度匹配度 |
| 日主生克 | 20分 | 天干合 / 相生 / 相克 |
| 称骨对比 | 20分 | 家庭平均骨重 |
| **总分** | **100分** | ★~★★★★★ 五级评定 |

---

## ⚠️ 免责声明 / Disclaimer

本项目仅供学习研究和娱乐参考。命理学并非精确科学，人生命运主要取决于个人努力和选择。

This project is for educational and entertainment purposes only. Fortune telling is not an exact science — your life is shaped by your own efforts and choices.

---

## 📄 License

MIT License — 详见 [LICENSE](./LICENSE)
