# Relay 共创

多人 + AI 的 Web3 协作应用。本版本已实现前后端协作与真实钱包签名认证；预算和验收结算是持久化模拟账本，**没有真实资金转移、托管合约或自动到期退款**。

## 下载 Windows 部署包

[下载完整 Windows 部署包（约 8 MB）](https://github.com/chengchengjiang2003-gif/python--/raw/refs/heads/main/releases/relay-windows-py312.zip)

如果直接下载被浏览器拦截，请打开仓库的 `releases/relay-windows-py312.zip` 文件页面，使用 **Download raw file** 下载。完整包含应用源码和适用于 64 位 Python 3.12 的离线依赖，解压后进入 `relay` 文件夹。

## Windows 启动

1. 从 https://www.python.org/downloads/windows/ 安装 **64 位 Python 3.12**，勾选 **Add python.exe to PATH**。
2. 解压源码包到普通目录（例如 `C:\relay`）。
3. 双击 `start-windows.bat`。首次启动自动创建 `.venv` 并安装依赖。完整 Windows 部署包附带 Python 3.12 的 64 位依赖包，校验后离线安装；其他 Python 版本或仅源码版本首次启动需要联网访问 PyPI。
4. 服务就绪后自动打开浏览器。地址为 `http://127.0.0.1:8000`。
5. 点“创建账号”，填写账号、显示名称和至少 8 位密码。无需预置管理员密码。

终端保持打开。按 Ctrl+C 停止；重新启动会保留账号、项目、文档、文件和模拟结算记录。

命令行替代方式：

```powershell
cd C:\relay
py -3.12 run.py
# 8000 被占用时：
py -3.12 run.py --port 8001
```

PowerShell 用户也可运行 `start-windows.ps1`。如果执行策略限制脚本，直接使用 `.bat` 或上面的命令，不需要更改系统执行策略。

## 验证多人协作

1. 浏览器普通窗口创建账号 A，打开默认项目。
2. 点“邀请成员”，选择协作者并生成邀请，复制邀请编码。
3. 用另一浏览器或独立无痕会话创建账号 B。
4. 在“我的项目 → 使用邀请加入”输入编码。
5. 两个会话发送消息、更新任务或保存文档；另一会话无需手动刷新即可收到变化。
6. A 将任务转交给 B；B 提交固定交付内容；A 验收，生成不可重复的模拟结算记录。

同一浏览器的普通标签共享登录 Cookie，因此测试不同用户时需要独立浏览器上下文。

跨电脑协作需要所有人访问同一个后端及数据库。默认只监听本机。若需可信局域网演示，运行 `py -3 run.py --host 0.0.0.0`，由其他设备访问本机局域网 IP 的 8000 端口，并按 Windows 防火墙提示允许私有网络。跨设备邀请应从大家实际访问的同一地址生成。远程正式部署需要 HTTPS。

## 已实现

- 账号注册、密码哈希、HttpOnly 会话、退出登录。
- 浏览器 EVM 钱包签名登录、绑定现有账号、一次性带过期时间的挑战；服务端恢复签名地址。
- 私有项目、协作者/观察者邀请、邀请撤销、成员移除和服务端访问控制。
- 任务分配、领取执行、固定版本交付、要求修改、发起人验收。
- SQLite 模拟账本：预算上限、版本检查、事务结算、防止重复验收。
- WebSocket 项目通知、断线重连、数据库重新读取，以及后台定期补齐。
- 共享文档版本号、冲突合并提示。不是字符级 CRDT 编辑，当前只在保存时同步。
- 文件上传、摘要、项目权限校验后下载，最大 10 MB。
- 可选 OpenAI 兼容 AI 接口：读取项目文档、输出草稿、明确失败信息。
- 手机和桌面界面、中文表单、输入校验和加载/失败提示。

## AI（可选）

复制 `.env.example` 为 `.env`，在本机编辑：

```dotenv
RELAY_AI_API_KEY=在本机填写你的服务密钥
RELAY_AI_BASE_URL=https://api.openai.com/v1
RELAY_AI_MODEL=gpt-4.1-mini
```

不要把实际密钥发到聊天、提交到 Git 或分享在源码包里。模型名称须由你的服务支持。重启后点击“使用 AI 助手”。未配置时不会伪造 AI 输出，其余协作功能照常运行。模型服务费用由该 API 账户承担，不从模拟托管预算扣除。

## 钱包

支持可用 `window.ethereum` 的浏览器 EVM 钱包，使用 Base Sepolia 登录挑战。点击钱包按钮会申请连接、切换测试网络及签名；登录签名不会授权转账。服务端验证地址、nonce、域名与过期时间，并禁止重放。

当前支持普通外部账户（EOA）；尚未实现 ERC-1271 合约钱包验证。真实 MetaMask 扩展操作需要在本机浏览器验证，自动测试使用真实密码学签名验证服务端流程。

## 数据和备份

默认保存在 `data/relay.sqlite3` 与 `data/uploads/`。停止服务后备份整个 `data` 目录。运行过程中不要只复制 SQLite 主文件，因为 WAL 文件可能仍有未合并数据。修改 `.env` 的 `RELAY_DATA_DIR` 可以指定数据路径。

本地版使用一个 Uvicorn 进程和 SQLite。不要启动多个 worker：实时通知保存在该进程中。更多并发与多实例部署须迁移消息分发与数据库。

## 其他系统

```bash
python3 run.py
```

建议 Python 3.12，最低 3.11。使用 FastAPI + SQLite + 原生 HTML/CSS/JavaScript，不需要安装 Node.js 或编译前端。

可选 Docker 部署：`docker compose up --build`。Docker 路径的文件已提供，是否验证见 `VALIDATION.md`。

## 测试

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux/macOS 使用 `.venv/bin/python -m unittest discover -s tests -v`。机器可读 API 定义位于 `/openapi.json`，就绪接口为 `/api/health`。

可选完整浏览器检查位于 `tools/browser_check.py`，需要另外安装 Playwright 和 Chromium，并指向单独测试实例；它会创建测试账号。实际执行结果见 `VALIDATION.md`。

## 后续 Web3 范围

真实里程碑托管、合约事件确认与链重组、超时退款、收款分配、争议规则、x402 和 ERC-8004 尚未接入。不能把本地模拟账本当作链上交易。下一阶段先在本地 EVM 实现并测试托管，再部署 Base Sepolia；真实资金版本需要独立验证。
