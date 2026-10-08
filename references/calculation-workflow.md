# 计算工作流

仅在调试、只运行某个阶段或一站式入口失败时加载本文件。

## 环境

运行时依赖：

```bash
pip install -r requirements.txt
```

开发与第三方复核：

```bash
pip install -r requirements-dev.txt
npm ci
```

`lunar-python`、`pysweph` 和 `iztro` 都是测试依赖，不参与生产计算。

## 分阶段执行

1. 验证输入：

   ```bash
   python scripts/reading_contract.py input.json --kind input
   ```

2. 确定性排盘：

   ```bash
   python scripts/fortune_calc.py --input input.json --output chart.json
   ```

3. 构建受约束的解读骨架：

   ```bash
   python scripts/build_reading.py \
     --chart chart.json \
     --output reading.json \
     --scenario 团队协作
   ```

4. 在需要时由 Agent 补充解释性字段。不得更改确定性数值；修改后再次验证：

   ```bash
   python scripts/reading_contract.py reading.json
   ```

5. 渲染：

   ```bash
   python scripts/generate_html.py --reading reading.json --output report.html
   ```

## 降级规则

- `zhdate` 缺失：农历转换和称骨不可用，输出高严重度 warning。
- `timezonefinder`/`pytz` 缺失或失效：境外时区按经度估算；夏令时和历史时区可能不准。
- 出生地坐标缺失：太阳/月亮沿用 UTC+8 的兼容默认值，上升星座不生成，时柱按钟表时间。Agent 应先查得区县级经纬度并以 `birth_lat`/`birth_lon` 重算。
- 任何计算模块异常：保留模块 warning，不用叙事层补造结果。

## 时间约定

- `birth_time` 是出生地当地钟表时间（出生证明记录的时间）。
- 中国大陆（含新疆、西藏）按北京时间 UTC+8 处理，1986–1991 年夏令时期间按 UTC+9；港澳台按各自历史时区；邻国按其实际时区。
- 夏令时期间出生记录若是未拨快的北京标准时间，需把 `birth_time` 加 1 小时后传入。
- 默认 `time_basis = "true_solar"`：真太阳时 = 钟表时间 +（经度 − 时区中央经线）× 4 分钟 + 均时差。
- 日柱、时柱、农历日、称骨时辰、紫微时辰均按真太阳时；跨日时日柱与农历日随之调整。
- 年柱、月柱与起运天数按出生瞬间（换算为北京时间）与节气时刻比较，不受真太阳时影响。
- 太阳、月亮和上升星座按出生瞬间换算为 UT，不使用真太阳时。
- 仅当用户明确要求钟表时间排盘时传 `time_basis = "clock"`。
- 缺少可解析坐标时降级为钟表时间，并输出高严重度 `TRUE_SOLAR_UNAVAILABLE`。
- 晚子时使用“不换日柱”约定（以真太阳时判断是否处于 23:00 之后）。

