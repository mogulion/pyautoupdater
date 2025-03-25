#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单计算器应用 - 业务逻辑部分

这是一个简单的计算器应用，用于演示如何将PyAutoUpdater集成到PyDistMaker打包的项目中。
此文件只包含业务逻辑，不包含更新相关代码。
"""

import tkinter as tk
from tkinter import ttk, messagebox


class Calculator:
    """简单计算器类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("简单计算器 v1.0.0")
        self.root.geometry("300x400")
        self.root.resizable(False, False)
        
        self.result_var = tk.StringVar(value="0")
        self.expression = ""
        
        self._create_widgets()
    
    def _create_widgets(self):
        """创建UI组件"""
        # 结果显示区域
        result_frame = ttk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, padx=10, pady=10)
        
        result_entry = ttk.Entry(
            result_frame, 
            textvariable=self.result_var, 
            font=("Arial", 20), 
            justify="right",
            state="readonly"
        )
        result_entry.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 按钮布局
        buttons = [
            ("7", 0, 0), ("8", 0, 1), ("9", 0, 2), ("/", 0, 3),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2), ("*", 1, 3),
            ("1", 2, 0), ("2", 2, 1), ("3", 2, 2), ("-", 2, 3),
            ("0", 3, 0), (".", 3, 1), ("=", 3, 2), ("+", 3, 3),
            ("C", 4, 0, 2), ("退出", 4, 2, 2)
        ]
        
        # 创建按钮
        for button_info in buttons:
            text = button_info[0]
            row = button_info[1]
            col = button_info[2]
            colspan = button_info[3] if len(button_info) > 3 else 1
            
            btn = ttk.Button(
                button_frame, 
                text=text,
                command=lambda t=text: self._on_button_click(t)
            )
            btn.grid(row=row, column=col, columnspan=colspan, padx=5, pady=5, sticky="nsew")
        
        # 设置按钮区域的行列权重
        for i in range(5):
            button_frame.rowconfigure(i, weight=1)
        for i in range(4):
            button_frame.columnconfigure(i, weight=1)
    
    def _on_button_click(self, text):
        """按钮点击事件处理"""
        if text == "C":
            # 清除
            self.expression = ""
            self.result_var.set("0")
        elif text == "=":
            # 计算结果
            try:
                result = eval(self.expression)
                self.result_var.set(str(result))
                self.expression = str(result)
            except Exception as e:
                messagebox.showerror("错误", f"计算错误: {str(e)}")
                self.expression = ""
                self.result_var.set("0")
        elif text == "退出":
            # 退出应用
            self.root.quit()
        else:
            # 添加到表达式
            self.expression += text
            self.result_var.set(self.expression)


def run_calculator():
    """运行计算器应用"""
    root = tk.Tk()
    app = Calculator(root)
    root.mainloop()


if __name__ == "__main__":
    run_calculator()