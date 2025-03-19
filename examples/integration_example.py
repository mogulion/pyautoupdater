"""
示例：如何在应用程序中集成PyAutoUpdater

此示例展示了如何在Python应用程序中集成自动更新功能，
包括配置加载、更新检查、进度回调和钩子注册。
"""

import os
import sys
import json
import logging
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 导入PyAutoUpdater
try:
    from pyautoupdater import UpdateManager, HookManager, SecurityManager, DeltaManager
except ImportError:
    print("请先安装PyAutoUpdater: pip install pyautoupdater")
    sys.exit(1)


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件并处理环境变量"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 处理环境变量
    for key, value in config.items():
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            config[key] = os.environ.get(env_var, value)
    
    # 处理嵌套字典中的环境变量
    for section in ['security', 'delta']:
        if section in config and isinstance(config[section], dict):
            for key, value in config[section].items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    config[section][key] = os.environ.get(env_var, value)
    
    # 处理仓库配置中的环境变量
    for repo in config.get('repositories', []):
        for key, value in repo.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                repo[key] = os.environ.get(env_var, value)
    
    return config


def update_progress_callback(progress: float, message: str) -> None:
    """更新进度回调函数"""
    print(f"更新进度: {progress:.2f} - {message}")


def update_status_callback(status: str, data: Dict[str, Any]) -> None:
    """更新状态回调函数"""
    print(f"更新状态: {status}")
    if 'error' in data:
        print(f"错误: {data['error']}")


def config_migration_hook(version_info: Dict[str, Any]) -> bool:
    """配置迁移钩子函数"""
    print(f"正在迁移配置文件到版本 {version_info.get('version')}")
    # 在这里实现配置文件迁移逻辑
    return True


def service_restart_hook(version_info: Dict[str, Any]) -> bool:
    """服务重启钩子函数"""
    print(f"正在重启服务，新版本: {version_info.get('version')}")
    # 在这里实现服务重启逻辑
    return True


def main():
    """主函数"""
    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    config = load_config(config_path)
    
    # 创建钩子管理器并注册钩子
    hook_manager = HookManager()
    hook_manager.register_pre_update_hook(config_migration_hook)
    hook_manager.register_post_update_hook(service_restart_hook)
    
    # 创建安全管理器
    security_manager = SecurityManager(config.get('security', {}))
    
    # 创建增量更新管理器
    delta_manager = DeltaManager(config.get('delta', {}))
    
    # 创建更新管理器
    update_manager = UpdateManager(
        config=config,
        hook_manager=hook_manager,
        security_manager=security_manager,
        delta_manager=delta_manager
    )
    
    # 检查更新
    update_available, latest_version, version_info = update_manager.check_for_updates()
    
    if update_available:
        print(f"发现新版本: {latest_version}，当前版本: {config['current_version']}")
        print(f"版本信息: {version_info}")
        
        # 询问用户是否更新
        user_input = input("是否更新到新版本? (y/n): ")
        if user_input.lower() in ['y', 'yes']:
            # 执行更新
            success = update_manager.perform_update(
                progress_callback=update_progress_callback,
                status_callback=update_status_callback
            )
            
            if success:
                print(f"更新成功，新版本: {latest_version}")
            else:
                print("更新失败，请查看日志获取详细信息")
    else:
        print("当前已是最新版本")


if __name__ == "__main__":
    main()