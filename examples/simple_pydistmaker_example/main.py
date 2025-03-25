#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单计算器应用 - 主入口文件

这个文件是应用程序的主入口点，负责集成业务逻辑和自动更新功能。
它展示了如何在实际应用中将PyAutoUpdater与业务逻辑分离。
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, Menu

# 导入业务逻辑模块
from simple_app import Calculator, run_calculator

# 导入更新管理器模块
from updater import UpdaterManager


class MainApp(tk.Tk):
    """
    主应用程序类
    
    集成了计算器功能和自动更新功能
    """
    
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和大小
        self.title("简单计算器 v1.0.0")
        self.geometry("300x400")
        self.resizable(False, False)
        
        # 创建更新管理器
        self.updater = UpdaterManager(self)
        
        # 创建菜单栏
        self._create_menu()
        
        # 创建计算器界面
        self.calculator = Calculator(self)
        
        # 自动检查更新（可选）
        # self.after(1000, lambda: self.updater.check_for_updates(silent=True))
    
    def _create_menu(self):
        """
        创建菜单栏
        """
        menu_bar = Menu(self)
        
        # 文件菜单
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="退出", command=self.quit)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        
        # 帮助菜单
        help_menu = Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="检查更新", command=lambda: self.updater.check_for_updates())
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=self._show_about)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        
        self.config(menu=menu_bar)
    
    def _show_about(self):
        """
        显示关于对话框
        """
        messagebox.showinfo(
            "关于",
            "简单计算器 v1.0.0\n\n"
            "这是一个演示PyAutoUpdater与PyDistMaker集成的示例应用。\n"
            "© 2023 示例公司"
        )


def main():
    """
    应用程序入口点
    """
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()