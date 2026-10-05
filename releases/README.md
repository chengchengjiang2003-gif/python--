# Windows 部署包

`relay-windows-py312.zip` 是可直接解压使用的完整部署包，包含源码和 64 位 Python 3.12 的离线依赖。

安装 64 位 Python 3.12，解压后进入 `relay` 文件夹，双击 `start-windows.bat`。

`relay-windows-py312.zip.sha256` 用于检查 ZIP 完整性。包内不含数据库、本地会话或实际 API 密钥。

当前预算与验收结算为模拟账本；AI 需要在本机 `.env` 配置可用的服务密钥。
