#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单计算器应用 - 更新管理器部分

这个模块负责处理应用程序的自动更新功能，与业务逻辑完全分离。
它展示了如何将PyAutoUpdater集成到PyDistMaker打包的项目中。
"""

import os
import sys
import json
import logging
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, Optional, Callable

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.expanduser('~'), 'simple-calculator.log'))
    ]
)

logger = logging.getLogger(__name__)

# 导入PyAutoUpdater
try:
    from pyautoupdater import UpdateManager, HookManager, SecurityManager, DeltaManager
except ImportError:
    logger.error("请先安装PyAutoUpdater: pip install pyautoupdater")
    sys.exit(1)


def get_app_dir() -> str:
    """
    获取应用程序目录
    
    在打包环境中，需要特殊处理应用程序目录的获取
    """
    if getattr(sys, 'frozen', False):
        # 打包环境
        if hasattr(sys, '_MEIPASS'):  # PyInstaller
            app_dir = sys._MEIPASS
        else:  # 其他打包工具，如PyDistMaker
            app_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    logger.info(f"应用程序目录: {app_dir}")
    return app_dir


def load_config(config_path: str) -> Dict[str, Any]:
    """
    加载配置文件并处理环境变量
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 处理环境变量
        for key, value in config.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                if env_var == 'APP_DIR':
                    config[key] = get_app_dir()
                elif env_var == 'TEMP':
                    config[key] = os.environ.get('TEMP', os.path.join(os.path.expanduser('~'), 'temp'))
                else:
                    config[key] = os.environ.get(env_var, value)
        
        # 处理嵌套字典中的环境变量
        for section in ['security', 'delta']:
            if section in config and isinstance(config[section], dict):
                for key, value in config[section].items():
                    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                        env_var = value[2:-1]
                        if env_var == 'APP_DIR':
                            config[section][key] = get_app_dir()
                        elif env_var == 'TEMP':
                            config[section][key] = os.environ.get('TEMP', os.path.join(os.path.expanduser('~'), 'temp'))
                        else:
                            config[section][key] = os.environ.get(env_var, value)
        
        # 处理仓库配置中的环境变量
        for repo in config.get('repositories', []):
            for key, value in repo.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    env_var = value[2:-1]
                    repo[key] = os.environ.get(env_var, value)
        
        return config
    except Exception as e:
        logger.exception(f"加载配置文件失败: {str(e)}")
        raise


def config_migration_hook(version_info: Dict[str, Any]) -> bool:
    """
    配置迁移钩子函数
    
    在更新前执行，用于迁移配置文件
    """
    logger.info(f"正在迁移配置文件到版本 {version_info.get('version')}")
    # 在这里实现配置文件迁移逻辑
    return True


def restart_application() -> None:
    """
    重启应用程序
    
    在更新完成后重启应用程序
    """
    logger.info("正在重启应用程序...")
    if getattr(sys, 'frozen', False):
        # 打包环境
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        # 开发环境
        os.execl(sys.executable, sys.executable, *sys.argv)


class UpdaterManager:
    """
    更新管理器类
    
    负责处理应用程序的自动更新功能
    """
    
    def __init__(self, parent: Optional[tk.Tk] = None):
        """
        初始化更新管理器
        
        Args:
            parent: 父窗口，用于显示更新对话框
        """
        self.parent = parent
        
        # 加载配置
        app_dir = get_app_dir()
        self.config_path = os.path.join(app_dir, 'config.json')
        try:
            self.config = load_config(self.config_path)
        except Exception as e:
            logger.error(f"无法加载配置文件: {str(e)}")
            if self.parent:
                messagebox.showerror("配置加载错误", f"无法加载配置文件: {str(e)}")
            return
        
        # 创建更新管理器
        try:
            # 创建钩子管理器并注册钩子
            self.hook_manager = HookManager()
            self.hook_manager.register_pre_update_hook(config_migration_hook)
            
            # 创建安全管理器
            self.security_manager = SecurityManager(self.config.get('security', {}))
            
            # 创建增量更新管理器
            self.delta_manager = DeltaManager(self.config.get('delta', {}))
            
            # 创建更新管理器
            self.update_manager = UpdateManager(
                config=self.config,
                hook_manager=self.hook_manager,
                security_manager=self.security_manager,
                delta_manager=self.delta_manager
            )
        except Exception as e:
            logger.exception(f"创建更新管理器失败: {str(e)}")
            if self.parent:
                messagebox.showerror("更新管理器错误", f"无法创建更新管理器: {str(e)}")
    
    def check_for_updates(self, silent: bool = False) -> bool:
        """
        检查更新
        
        Args:
            silent: 是否静默检查，不显示对话框
            
        Returns:
            是否有更新可用
        """
        try:
            update_available, latest_version, version_info = self.update_manager.check_for_updates()
            
            if update_available:
                current_version = self.config.get('current_version', '未知')
                logger.info(f"发现新版本: {latest_version}，当前版本: {current_version}")
                
                if not silent and self.parent:
                    user_response = messagebox.askyesno(
                        "更新可用",
                        f"发现新版本: {latest_version}\n当前版本: {current_version}\n\n是否现在更新?"
                    )
                    
                    if user_response:
                        self.perform_update()
                
                return True
            else:
                logger.info("当前已是最新版本")
                if not silent and self.parent:
                    messagebox.showinfo("检查更新", "当前已是最新版本")
                return False
        except Exception as e:
            logger.exception(f"检查更新失败: {str(e)}")
            if not silent and self.parent:
                messagebox.showerror("检查更新错误", f"检查更新失败: {str(e)}")
            return False
    
    def update_progress_callback(self, progress: float, message: str) -> None:
        """
        更新进度回调函数
        """
        logger.info(f"更新进度: {progress:.2f} - {message}")
    
    def update_status_callback(self, status: str, data: Dict[str, Any]) -> None:
        """
        更新状态回调函数
        """
        logger.info(f"更新状态: {status}")
        if 'error' in data:
            logger.error(f"更新错误: {data['error']}")
    
    def perform_update(self, on_success: Optional[Callable] = None) -> bool:
        """
        执行更新
        
        Args:
            on_success: 更新成功后的回调函数
            
        Returns:
            更新是否成功
        """
        try:
            if self.parent:
                # 创建进度对话框
                progress_window = tk.Toplevel(self.parent)
                progress_window.title("正在更新")
                progress_window.geometry("300x100")
                progress_window.resizable(False, False)
                progress_window.transient(self.parent)
                progress_window.grab_set()
                
                # 进度条
                progress_label = tk.Label(progress_window, text="正在下载更新...")
                progress_label.pack(pady=10)
                
                progress_bar = ttk.Progressbar(progress_window, length=250, mode="determinate")
                progress_bar.pack(pady=10)
                
                # 自定义进度回调
                def gui_progress_callback(progress: float, message: str) -> None:
                    self.update_progress_callback(progress, message)
                    progress_bar["value"] = progress * 100
                    progress_label["text"] = message
                    progress_window.update()
                
                # 执行更新
                success = self.update_manager.perform_update(
                    progress_callback=gui_progress_callback,
                    status_callback=self.update_status_callback
                )
                
                # 关闭进度窗口
                progress_window.destroy()
                
                if success:
                    messagebox.showinfo("更新完成", "应用程序已更新到最新版本，点击确定重启应用。")
                    if on_success:
                        on_success()
                    else:
                        restart_application()
                else:
                    messagebox.showerror("更新失败", "更新过程中发生错误，请查看日志获取详细信息。")
            else:
                # 无GUI模式
                success = self.update_manager.perform_update(
                    progress_callback=self.update_progress_callback,
                    status_callback=self.update_status_callback
                )
                
                if success:
                    logger.info("更新成功，准备重启应用程序")
                    if on_success:
                        on_success()
                    else:
                        restart_application()
                else:
                    logger.error("更新失败")
            
            return success
        except Exception as e:
            logger.exception(f"执行更新失败: {str(e)}")
            if self.parent:
                messagebox.showerror("更新错误", f"执行更新失败: {str(e)}")
            return False


# 测试代码
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    updater = UpdaterManager(root)
    updater.check_for_updates()
    
    root.mainloop()