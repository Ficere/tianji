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
- 出生城市缺失：太阳/月亮沿用 UTC+8 的兼容默认值，上升星座不生成。境外用户应补城市或经纬度。
- 任何计算模块异常：保留模块 warning，不用叙事层补造结果。

## 时间约定

- `birth_time` 是出生地当地钟表时间。
- 中国大陆、港澳台按法定 UTC+8 处理，再以实际经度计算真太阳时展示。
- 太阳、月亮和上升星座先按当地时区换算为 UT。
- 晚子时使用“不换日柱”约定。

