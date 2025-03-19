# PyAutoUpdater

[English](./README_EN.md) | [中文](./README.md)

## 概述

PyAutoUpdater是一个全面的Python应用程序自动更新解决方案，专为编译型Python工具设计。它提供标准化的自动更新功能，支持版本检测、增量更新和更新前后处理，确保私有化部署环境下工具更新的安全性和稳定性。

## 核心功能

- **多打包工具支持**：兼容PyInstaller、Nuitka等主流Python打包工具生成的二进制文件
- **私有PyPI仓库集成**：支持从私有PyPI仓库获取更新，包括认证和SSL验证
- **增量更新**：通过仅下载和应用版本间的变更来提高更新效率
- **安全机制**：支持多种签名验证方法（GPG、RSA、简单哈希）确保更新包的完整性和真实性
- **生命周期钩子**：提供更新前、更新后和错误处理钩子，支持自定义业务逻辑
- **进度回调**：实时反馈更新进度和状态
- **备份和回滚**：自动备份更新前的文件，支持更新失败时回滚

## 安装

### 使用pip

```bash
pip install pyautoupdater
```

### 可选依赖

安装安全功能：

```bash
pip install pyautoupdater[security]
```

安装增量更新功能：

```bash
pip install pyautoupdater[delta]
```

安装所有功能：

```bash
pip install pyautoupdater[security,delta]
```

## 快速开始

### 基本配置

创建配置文件 `config.json`：

```json
{
    "package_name": "my-application",
    "current_version": "1.0.0",
    "repositories": [
        {
            "url": "https://private-pypi.example.com",
            "username": "${PYPI_USERNAME}",
            "password": "${PYPI_PASSWORD}",
            "verify_ssl": true
        }
    ],
    "temp_dir": "${TEMP}/my-app-updates",
    "backup_dir": "${TEMP}/my-app-backups",
    "enable_delta": true
}
```

### 基本用法

```python
from pyautoupdater import UpdateManager
import json

# 加载配置
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 创建更新管理器
update_manager = UpdateManager(config)

# 检查更新
update_available, latest_version, version_info = update_manager.check_for_updates()
if update_available:
    print(f"发现新版本: {latest_version}")
    
    # 执行更新
    success = update_manager.perform_update(
        progress_callback=lambda progress, message: print(f"更新进度: {progress:.2f} - {message}")
    )
    
    if success:
        print("更新成功，请重启应用程序")
    else:
        print("更新失败")
else:
    print("已是最新版本")
```

## 高级用法

### 注册生命周期钩子

```python
from pyautoupdater import UpdateManager, HookManager

# 创建钩子管理器
hook_manager = HookManager()

# 注册更新前钩子
def pre_update_hook(version_info):
    print(f"准备更新到版本 {version_info.get('version')}")
    # 执行更新前准备工作，如关闭数据库连接
    return True  # 返回True继续更新，False中止更新

hook_manager.register_pre_update_hook(pre_update_hook)

# 注册更新后钩子
def post_update_hook(version_info):
    print(f"已更新到版本 {version_info.get('version')}")
    # 执行更新后任务，如迁移配置文件
    return True

hook_manager.register_post_update_hook(post_update_hook)

# 创建带钩子管理器的更新管理器
update_manager = UpdateManager(config, hook_manager=hook_manager)
```

### 启用安全验证

```python
from pyautoupdater import UpdateManager, SecurityManager

# 安全配置
security_config = {
    "signature_verification": True,
    "signature_type": "rsa",
    "public_key_path": "path/to/public_key.pem"
}

# 创建安全管理器
security_manager = SecurityManager(security_config)

# 创建带安全管理器的更新管理器
update_manager = UpdateManager(config, security_manager=security_manager)
```

### 启用增量更新

```python
from pyautoupdater import UpdateManager, DeltaManager

# 增量更新配置
delta_config = {
    "enable_delta": True,
    "manifest_filename": "manifest.json",
    "chunk_size": 4096
}

# 创建增量更新管理器
delta_manager = DeltaManager(delta_config)

# 创建带增量更新管理器的更新管理器
update_manager = UpdateManager(config, delta_manager=delta_manager)
```

## API参考

### UpdateManager

负责处理更新过程的更新管理器。

```python
UpdateManager(config, hook_manager=None, security_manager=None, delta_manager=None)
```

主要方法：
- `check_for_updates()`: 检查是否有可用更新
- `perform_update()`: 执行更新过程
- `rollback_update()`: 回滚到更新前的版本

### HookManager

管理更新生命周期钩子的管理器。

```python
HookManager()
```

主要方法：
- `register_pre_update_hook(hook)`: 注册更新前钩子
- `register_post_update_hook(hook)`: 注册更新后钩子
- `register_error_hook(hook)`: 注册错误处理钩子

### SecurityManager

管理更新安全性的管理器。

```python
SecurityManager(config=None)
```

主要方法：
- `verify_signature(file_path, version_info)`: 验证文件签名
- `verify_hash(file_path, expected_hash)`: 验证文件哈希值

### DeltaManager

管理增量更新的管理器。

```python
DeltaManager(config=None)
```

主要方法：
- `generate_manifest(directory)`: 生成文件清单
- `compare_manifests(old_manifest, new_manifest)`: 比较清单找出差异
- `apply_delta_update(app_dir, delta_dir, changes)`: 应用增量更新

### PackageAdapter

为不同打包工具提供适配的基类。

```python
PackageAdapter.detect_package_type(app_dir)
PackageAdapter.create_adapter(package_type)
```

派生类：
- `PyInstallerAdapter`: PyInstaller打包适配器
- `NuitkaAdapter`: Nuitka打包适配器
- `HybridAdapter`: 混合打包适配器
- `StandardAdapter`: 标准Python包适配器

## 贡献

欢迎提交问题报告、功能请求和代码贡献。请确保遵循项目的代码风格和贡献指南。

## 许可证

本项目采用MIT许可证。详情请参阅LICENSE文件。
