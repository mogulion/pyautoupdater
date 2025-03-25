# PyAutoUpdater 与 PyDistMaker 集成示例

本示例展示了如何在使用 PyDistMaker 打包的 Python 应用程序中集成 PyAutoUpdater 自动更新功能。

## 项目结构

```
./
├── app.py                # 主应用程序
├── config.json           # PyAutoUpdater 配置文件
├── pydistmaker.json      # PyDistMaker 配置文件
├── keys/                 # 密钥目录
│   └── public_key.pem    # 用于验证更新包签名的公钥
└── README.md             # 本文档
```

## 使用方法

### 1. 安装依赖

```bash
pip install pyautoupdater pydistmaker
```

### 2. 配置 PyAutoUpdater

编辑 `config.json` 文件，配置更新源和其他参数：

- `package_name`: 应用程序包名
- `current_version`: 当前版本号
- `repositories`: 更新源仓库列表
- `security`: 安全配置，包括签名验证
- `delta`: 增量更新配置

### 3. 配置 PyDistMaker

编辑 `pydistmaker.json` 文件，配置打包参数：

- `app_name`: 应用程序名称
- `version`: 应用程序版本
- `entry_point`: 入口点文件
- `include_files`: 需要包含的文件列表，确保包含 `config.json