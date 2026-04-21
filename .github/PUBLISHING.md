# 自动发布指南 / Publishing Guide

本仓库配置了 CI 自动发布流程，push tag `v*` 即可一键分发到 4 个主流平台。

> Push a `v*` tag → auto-publish to 4 major skill registries.

## 🎯 目标平台 / Target Registries

| 平台 | 类型 | 发布方式 | 所需凭证 |
|------|------|----------|----------|
| **ClawHub** | OpenClaw 官方注册表 | `clawhub publish` CLI | `CLAWHUB_TOKEN` |
| **agentskill.sh** | 社区目录 | GitHub webhook (push 事件) | 无需 secret（webhook URL 已内置） |
| **skills.sh** | 社区目录 | 遥测自动索引（无 API） | 无需配置 |
| **Smithery** | MCP 大市场 | Web UI 一次性绑定仓库 | 无需配置（一次性 Web 设置） |

## 🚀 发布流程 / Release Flow

### 1. 验证 (每次 push 都跑)

`.github/workflows/validate.yml` —— 校验 SKILL.md frontmatter、脚本烟雾测试、spec 合规性。

### 2. 发布 (仅 tag 触发)

```bash
# 打 tag 即可触发发布
git tag v4.1.0
git push origin v4.1.0
```

`.github/workflows/publish.yml` 会：

1. **打包** → 生成 `dist/tianji-4.1.0.zip`
2. **并行发布** → ClawHub / agentskill.sh（各自 continue-on-error，互不影响）
3. **记录通知** → skills.sh / Smithery（无发布 API，仅打印链接提示）
4. **GitHub Release** → 附带 zip 包，生成 changelog
5. **汇总** → 在 GitHub Actions Summary 显示每个平台的结果

### 3. 手动触发（测试或补发）

在 GitHub Actions 页面点击 **Run workflow**，可指定目标平台：

```
targets: clawhub,agentskill
```

留空则发布到全部平台。

## 🔐 首次设置 / First-Time Setup

### 必需：配置 Secrets

前往 **Settings → Secrets and variables → Actions → New repository secret**，添加：

| Secret Name | 获取方式 | 必需? |
|-------------|----------|-------|
| `CLAWHUB_TOKEN` | 访问 [clawhub.com](https://clawhub.com) 登录后在 Settings 生成 API Token | ClawHub 发布 |

未设置 token 的平台会被 CI 自动跳过，不会中断发布流程。

### 可选：一次性 Web 配置（提升体验）

以下平台无需 secret，但建议首次手动配置一次，之后完全自动：

#### ① agentskill.sh webhook

提升同步速度（默认每 24h 自动同步，配置 webhook 后 push 即时同步）：

1. 仓库 **Settings → Webhooks → Add webhook**
2. Payload URL: `https://agentskill.sh/api/webhooks/github`
3. Content type: `application/json`
4. Events: 仅选 **push**
5. 保存

CI 中已包含主动触发 webhook 的 fallback，即使未设置也能工作。

#### ② Smithery 仓库绑定

1. 访问 [smithery.ai](https://smithery.ai) 登录
2. 点击 **Add server** → 选择 GitHub → 授权 → 选择 `Ficere/tianji`
3. Smithery 会自动监听后续 push，无需 CI 动作

#### ③ agentskill.sh 验证所有权（可选）

1. 访问 [agentskill.sh](https://agentskill.sh) 登录
2. Account settings → **Connect GitHub**
3. `Ficere/tianji` 会自动认领并显示 ✓ 验证徽章

## 📦 版本号约定 / Versioning

- Tag 格式：`vMAJOR.MINOR.PATCH`（例：`v4.1.0`）
- CI 会自动从 tag 剥离 `v` 前缀写入 zip 文件名
- 建议同步更新 `SKILL.md` 中 `metadata.version` 字段（当前为 `4.0`）

## 🔍 发布后验证 / Verification

发布完成后可在各平台验证收录情况：

| 平台 | 验证 URL |
|------|----------|
| ClawHub | `https://clawhub.com/skills/tianji` |
| agentskill.sh | `https://agentskill.sh/skills/Ficere/tianji` |
| skills.sh | `https://skills.sh/Ficere/tianji` |
| Smithery | `https://smithery.ai/server/Ficere/tianji` |
| GitHub Release | `https://github.com/Ficere/tianji/releases` |

## ❓ 常见问题 / FAQ

**Q: 只想发布到指定平台怎么办？**

A: 使用手动触发：Actions → Publish to Registries → Run workflow，`targets` 填如 `clawhub` 或 `clawhub,agentskill`。

**Q: 某个平台发布失败了会阻塞其他平台吗？**

A: 不会。每个平台 job 都设了 `continue-on-error: true`，独立成败。

**Q: skills.sh 为什么没有主动发布步骤？**

A: skills.sh 是纯遥测索引型目录，首个用户执行 `npx skills add Ficere/tianji` 后会自动收录。

**Q: 发布前想预览会发生什么？**

A: 在 Actions 页手动触发 workflow，不打 tag，GitHub Release job 会被跳过（因 `if: startsWith(github.ref, 'refs/tags/v')`）。

## 🛠 本地调试 / Local Debug

```bash
# 模拟 CI 打包
mkdir -p dist
zip -r "dist/tianji-test.zip" . -x '.git/*' '.github/*' 'dist/*' 'tests/*'

# 本地发布测试（需先安装 clawhub CLI）
npm install -g clawhub@latest
clawhub publish dist/tianji-test.zip -n tianji -v 0.0.1-test -t YOUR_TOKEN
```
