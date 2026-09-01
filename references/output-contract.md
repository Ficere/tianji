# 输出契约

## 文件职责

- `chart.json`：确定性计算的完整原始输出，可包含计算层扩展字段。
- `reading.json`：受 `schemas/reading_v8.schema.json` 约束的报告数据。
- `report.html`：由 reading 渲染的静态展示文件，不是新的事实源。

## 版本

- 契约版本：`meta.version = "8.3"`。
- v8.3 新生成文件的引擎版本：`meta.engine_version = "8.3.0"`；旧示例迁移时可省略，避免伪造原始引擎来源。
- `meta.scene` 只取 `personal` 或 `synastry`。
- `persons` 支持 1–8 人；`person_index` 从 1 连续编号。
- 单人时 `synastry` 为 `null`；多人时必须提供合盘结构。

## 旧版迁移

`scripts/reading_contract.py --normalize` 支持以下 v8.0–v8.2 别名：

| 旧字段 | v8.3 字段 |
|---|---|
| `meta.mode` | `meta.scene` |
| `western` | `western_astro` |
| `name_wuge` | `name_analysis` |
| `sketch` | `personality_sketch` |
| `confidence` | `confidence_table` |

迁移器不会推测缺失的业务内容。契约错误应中止渲染并返回具体字段路径。

## 安全

渲染器会递归 HTML 转义所有外部字符串。不要把用户提供的 HTML 当作可信富文本，也不要在解释字段中嵌入脚本、事件属性或远程资源。
