#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyAutoUpdater 与 PyDistMaker 集成示例

此示例展示了如何在使用 PyDistMaker 打包的应用程序中集成 PyAutoUpdater 自动更新功能。
"""

import os
import sys
import json
import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.expanduser('~'), 'my-application.log'))
    ]
)

logger = logging.getLogger(__name__)

# 导入 PyAutoUpdater
try:
    from pyautoupdater import UpdateManager, HookManager, SecurityManager, DeltaManager
except ImportError:
    logger.error("请先安装 PyAutoUpdater: pip install pyautoupdater")
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
        else:  # 其他打包工具，如 Nuitka 或 PyDistMaker
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


class UpdaterApp(tk.Tk):
    """
    更新器应用程序
    
    一个简单的 GUI 应用程序，用于演示 PyAutoUpdater 的使用
    """
    
    def __init__(self):
        super().__init__()
        
        self.title("PyAutoUpdater 示例应用")
        self.geometry("500x400")
        self.resizable(True, True)
        
        # 加载配置
        app_dir = get_app_dir()
        self.config_path = os.path.join(app_dir, 'config.json')
        try:
            self.config = load_config(self.config_path)
        except Exception as e:
            messagebox.showerror("配置加载错误", f"无法加载配置文件: {str(e)}")
            self.destroy()
            sys.exit(1)
        
        # 创建更新管理器
        self.create_update_manager()
        
        # 创建 UI
        self.create_widgets()
        
        # 自动检查更新
        self.after(1000, self.check_for_updates)
    
    def create_update_manager(self) -> None:
        """
        创建更新管理器
        """
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
            messagebox.showerror("更新管理器错误", f"无法创建更新管理器: {str(e)}")
            self.destroy()
            sys.exit(1)
    
    def create_widgets(self) -> None:
        """
        创建 UI 组件
        """
        # 版本信息
        version_frame = ttk.Frame(self)
        version_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(version_frame, text="当前版本:").pack(side=tk.LEFT)
        self.version_label = ttk.Label(version_frame, text=self.config.get('current_version', '未知'))
        self.version_label.pack(side=tk.LEFT, padx=5)
        
        # 更新按钮
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.check_button = ttk.Button(button_frame, text="检查更新", command=self.check_for_updates)
        self.check_button.pack(side=tk.LEFT, padx=5)
        
        self.update_button = ttk.Button(button_frame, text="执行更新", command=self.perform_update, state=tk.DISABLED)
        self.update_button.pack(side=tk.LEFT, padx=5)
        
        # 状态信息
        status_frame = ttk.LabelFrame(self, text="状态信息")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.status_text = tk.Text(status_frame, wrap=tk.WORD, height=10)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 进度条
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(progress_frame, text="更新进度:").pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(progress_frame, length=300, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 更新信息
        self.latest_version = None
        self.version_info = None
    
    def log_status(self, message: str) -> None:
        """
        记录状态信息
        """
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        logger.info(message)
    
    def update_progress_callback(self, progress: float, message: str) -> None:
        """
        更新进度回调函数
        """
        self.progress_bar['value'] = progress * 100
        self.log_status(f"更新进度: {progress:.2f} - {message}")
        self.update()
    
    def update_status_callback(self, status: str, data: Dict[str, Any]) -> None:
        """
        更新状态回调函数
        """
        self.log_status(f"更新状态: {status}")
        if 'error' in data:
            self.log_status(f"错误: {data['error']}")
        self.update()
    
    def check_for_updates(self) -> None:
        """
        检查更新
        """
        self.log_status("正在检查更新...")
        self.check_button.config(state=tk.DISABLED)
        
        try:
            update_available, latest_version, version_info = self.update_manager.check_for_updates()
            
            if update_available:
                self.latest_version = latest_version
                self.version_info = version_info
                self.log_status(f"发现新版本: {latest_version}，当前版本: {self.config['current_version']}")
                self.log_status(f"版本信息: {version_info}")
                self.update_button.config(state=tk.NORMAL)
            else:
                self.log_status("当前已是最新版本")
                self.update_button.config(state=tk.DISABLED)
        except Exception as e:
            logger.exception(f"检查更新失败: {str(e)}")
            self.log_status(f"检查更新失败: {str(e)}")
            messagebox.showerror("更新检查错误", f"检查更新失败: {str(e)}")
        finally:
            self.check_button.config(state=tk.NORMAL)
    
    def perform_update(self) -> None:
        """
        执行更新
        """
        if not self.latest_version:
            return
        
        self.log_status(f"开始更新到版本 {self.latest_version}...")
        self.check_button.config(state=tk.DISABLED)
        self.update_button.config(state=tk.DISABLED)
        
        try:
            # 执行更新
            success = self.update_manager.perform_update(
                progress_callback=self.update_progress_callback,
                status_callback=self.update_status_callback
            )
            
            if success:
                self.log_status(f"更新成功，新版本: {self.latest_version}")
                messagebox.showinfo("更新成功", f"已成功更新到版本 {self.latest_version}，点击确定重启应用程序。")
                restart_application()
            else:
                self.log_status("更新失败，请查看日志获取详细信息")
                messagebox.showerror("更新失败", "更新失败，请查看日志获取详细信息。")
        except Exception as e:
            logger.exception(f"执行更新失败: {str(e)}")
            self.log_status(f"执行更新失败: {str(e)}")
            messagebox.showerror("更新错误", f"执行更新失败: {str(e)}")
        finally:
            self.check_button.config(state=tk.NORMAL)
            self.update_button.config(state=tk.NORMAL)


def main():
    """
    主函数
    """
    try:
        app = UpdaterApp()
        app.mainloop()
    except Exception as e:
        logger.exception(f"应用程序运行失败: {str(e)}")
        if not getattr(sys, 'frozen', False):
            raise