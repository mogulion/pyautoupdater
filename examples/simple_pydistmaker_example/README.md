# PyAutoUpdater 与 PyDistMaker 集成示例

这是一个简单的计算器应用示例，展示了如何在使用 PyDistMaker 打包的 Python 应用程序中集成 PyAutoUpdater 自动更新功能。

## 项目结构

```
./
├── main.py               # 主入口文件（集成业务逻辑和更新功能）
├── simple_app.py         # 业务逻辑文件（计算器功能）
├── updater.py            # 更新管理器（PyAutoUpdater 集成代码）
├── config.json           # PyAutoUpdater 配置文件
├── pydistmaker.json      # PyDistMaker 配置文件
├── keys/                 # 密钥目录
│   └── public_key.pem    # 用于验证更新包签名的公钥
└── README.md             # 本文档
```

## 集成说明

本示例将业务逻辑和更新功能完全分离，便于理解集成过程：

1. **业务逻辑（simple_app.py）**：
   - 纯粹的业务代码，不包含任何更新相关的代码
   - 可以独立运行，提供基本的计算器功能

2. **更新管理器（updater.py）**：
   - 封装了所有与 PyAutoUpdater 相关的功能
   - 提供了检查更新、执行更新等方法
   - 处理配置加载、环境变量替换等通用功能

3. **主入口（main.py）**：
   - 将业务逻辑和更新功能集成在一起
   - 提供用户界面，包括菜单栏中的更新选项

## 集成步骤

### 1. 安装依赖

```bash
pip install pyautoupdater pydistmaker
```

### 2. 配置 PyAutoUpdater

编辑 `config.json` 文件，配置更新源和其他参数。关键配置项：

- `package_name`: 应用程序包名
- `current_version`: 当前版本号（发布新版本时需要更新）
- `repositories`: 更新源仓库列表
- `security`: 安全配置，包括签名验证

### 3. 配置 PyDistMaker

编辑 `pydistmaker.json` 文件，配置打包参数：

- `app_name`: 应用程序名称
- `version`: 应用程序版本
- `entry_point`: 入口点文件（main.py）
- `include_files`: 需要包含的文件列表，确保包含 `config.json` 和公钥文件
- `hidden_imports`: 需要包含的隐藏导入，确保包含 `pyautoupdater`

### 4. 集成到业务代码

在主入口文件中，导入业务逻辑和更新管理器：

```python
# 导入业务逻辑模块
from simple_app import Calculator

# 导入更新管理器模块
from updater import UpdaterManager
```

创建更新管理器实例并添加更新功能：

```python
# 创建更新管理器
self.updater = UpdaterManager(self)

# 添加检查更新菜单项
help_menu.add_command(label="检查更新", command=lambda: self.updater.check_for_updates())
```

### 5. 使用 PyDistMaker 打包

```bash
pydistmaker build
```

## 关键技术点

1. **路径处理**：在打包环境中，需要特殊处理应用程序目录的获取

```python
def get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        # 打包环境
        if hasattr(sys, '_MEIPASS'):  # PyInstaller
            app_dir = sys._MEIPASS
        else:  # 其他打包工具，如PyDistMaker
            app_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境
        app_dir = os.path.dirname(os.path.abspath(__file__))
    return app_dir
```

2. **环境变量替换**：配置文件中的环境变量需要在运行时替换

3. **应用重启**：更新完成后需要重启应用程序

```python
def restart_application() -> None:
    if getattr(sys, 'frozen', False):
        # 打包环境
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        # 开发环境
        os.execl(sys.executable, sys.executable, *sys.argv)
```

4. **钩子函数**：使用钩子函数处理更新前后的操作

```python
# 创建钩子管理器并注册钩子
self.hook_manager = HookManager()
self.hook_manager.register_pre_update_hook(config_migration_hook)
```

## 注意事项

1. 确保配置文件中的版本号与实际应用版本一致
2. 打包时必须包含配置文件和公钥文件
3. 私钥文件不应包含在发布版本中，仅用于签名更新包
4. 更新源需要配置正确的URL和认证信息