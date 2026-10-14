# 出生输入收集

完整排盘对每位成员收集：

- `name`：可用“甲方/乙方”等代号；使用代号传 `name_is_alias: true`，跳过三才五格。
- `gender`：男/女，用于传统排盘中的大运方向。
- `solar_date`：公历 `YYYY-MM-DD`；先确认用户给的是公历还是农历。
- `birth_time`：出生地当地钟表时间 `HH:MM`，不要自行换成真太阳时再输入。
- `birth_city`：尽量精确到区县，保留用户原话展示。
- `birth_lat` / `birth_lon`：代表坐标，成对输入，优先于城市名称。
- `mbti`：可选，只作为用户自报的补充。
- `birth_time_source`：`recorded`、`recalled` 或用户明确指定的 `assumed`；假设时刻必须提供 `birth_time_note`，参照 `editorial-report.md`。

## 坐标与真太阳时

1. 内置 `references/city_coords.json` 没有用户给的区县或只有地级市时，自行检索区县政府驻地经纬度，不让用户查。
2. 以 `birth_lat` / `birth_lon` 传入；在 `time_note` 或 `editorial.coordinate_sources` 写明公开来源及代表点精度。
3. 默认 `time_basis: "true_solar"`。只有用户明确要求钟表直排才传 `"clock"`；西洋星座按真实出生瞬间，不重复做经度修正。
4. 时柱、日柱、农历日、称骨和紫微时辰共享真太阳校正；年柱/月柱与节气按出生瞬间比较。
5. 出现 `TRUE_SOLAR_UNAVAILABLE`，先补坐标重算，不交付伪完整报告。距时辰边界不足 15 分钟或时间来源不确定时，降级输入置信度并说明另一时辰；若范围可能跨午夜，另核对日期边界。

未知时间不自行默认中午。用户主动指定情景后才做条件完整盘，并保留醒目假设标记；否则补时间或做有限分析。晚子时采用不换日柱约定，核对其他工具先统一门派、时钟、时区与夏令时。
