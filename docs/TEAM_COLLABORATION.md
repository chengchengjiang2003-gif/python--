# Relay 团队代码协作指南

本文件用于组织黑客松期间的代码协作。首次提交只增加文档，不更改程序功能。

## 现有项目
- 前端：`frontend/index.html`、`frontend/app.js`、`frontend/app.css`、`frontend/style.css`
- 后端：`app/main.py`
- 测试：`tests/`
- 启动与部署：`run.py`、`Dockerfile`、`compose.yaml`
- 技术说明：`README.md`、`VALIDATION.md`

现有 README 明确说明结算是模拟账本，不涉及真实资金转账和链上托管；钱包当前使用 EVM 签名验证。不要在介绍或演示中声称这些功能已是 Solana 链上部署。

## 推荐的分工
| 角色 | 建议负责区域 | 示例分支 |
| --- | --- | --- |
| 前端 | `frontend/` | `feat/wallet-ui` |
| 后端 | `app/` 和 API 测试 | `feat/api-improvement` |
| 测试与文档 | `tests/`、`docs/` | `test/smoke-check` |
| 项目集成负责人 | 审核 PR、验证演示、检查跨模块改动 | 按功能新建分支 |

分工不是权限隔离。涉及共享文件、接口格式、数据库改动，修改前先在 Issue 或群聊协调。

## 贡献代码的步骤
1. 克隆仓库，先切换 `main` 并获取最新代码。
2. 从最新 `main` 新建功能分支，命名如 `feat/feature-name` 或 `fix/bug-name`。
3. 在自己负责的区域开发，完成后运行适用的测试。
4. 提交 commit 并 Push 上传自己的分支。
5. 创建 Pull Request，Base 选择 `main`，Compare 选择自己的开发分支。
6. 在 PR 描述里说明功能、修改文件、测试方法、风险和截图。
7. 至少让另一位队友检查改动。确认没有冲突、测试通过以后再合并。
8. 合并后所有队友更新本地 `main`，从最新版本开始下个任务。

## 提交前检查
- 不要提交钱包助记词、私钥、真实 API Key 或个人账号密码。
- `.env` 和 `data/` 已列在 `.gitignore`，但提交前仍须检查改动清单。
- 不要将模拟结算描述为真实链上托管或真实转账。
- 不要把测试账号和真实钱包资金混用。
- 若修改 API，请同步前端调用和对应测试。
- 任何线上部署、链上交易及权限调整须单独确认。

## 第一次练习
本文件所在的 `docs/team-collaboration-guide` 分支用于演示 PR 流程。确认评审完成之前不要合并；可以在 GitHub 的 PR 页面查看 Files changed、Conversation 和 Checks。
