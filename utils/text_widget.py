# utils/text_widget.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文字截短與展開組件
統一處理文字過長的顯示問題，提供點擊展開功能
"""

import tkinter as tk
from typing import Optional, Callable
from config.settings import AppConfig


class TruncatedTextWidget:
    """文字截短展開組件"""

    def __init__(self, parent, text: str, max_length: int = 50,
                 font=None, bg_color=None, fg_color=None,
                 width: int = None, anchor: str = 'w'):
        """
        初始化文字截短組件

        Args:
            parent: 父容器
            text: 要顯示的文字
            max_length: 最大顯示長度
            font: 字體設定
            bg_color: 背景色
            fg_color: 文字色
            width: 組件寬度
            anchor: 文字對齊方式
        """
        self.parent = parent
        self.original_text = text or ""
        self.max_length = max_length
        self.is_expanded = False
        self.popup_window = None

        # 樣式設定
        self.font = font or AppConfig.FONTS.get('text', ('SimHei', 10))
        self.bg_color = bg_color or AppConfig.COLORS.get('window_bg', '#F5F5F5')
        self.fg_color = fg_color or AppConfig.COLORS.get('text_color', '#333333')
        self.width = width
        self.anchor = anchor

        # 建立主要顯示組件
        self._create_widget()

    def _create_widget(self):
        """建立文字顯示組件"""
        # 建立框架容器
        self.container = tk.Frame(self.parent, bg=self.bg_color)

        # 建立文字標籤
        label_config = {
            'bg': self.bg_color,
            'fg': self.fg_color,
            'font': self.font,
            'anchor': self.anchor,
            'cursor': 'hand2' if self._needs_truncation() else 'arrow'
        }

        if self.width:
            label_config['width'] = self.width

        self.label = tk.Label(self.container, **label_config)
        self.label.pack(fill='x', expand=True)

        # 更新顯示文字
        self._update_display()

        # 綁定點擊事件
        if self._needs_truncation():
            self.label.bind('<Button-1>', self._on_click)
            self.label.bind('<Enter>', self._on_enter)
            self.label.bind('<Leave>', self._on_leave)

    def _needs_truncation(self) -> bool:
        """檢查是否需要截短"""
        return len(self.original_text) > self.max_length

    def _get_display_text(self) -> str:
        """取得要顯示的文字"""
        if not self._needs_truncation():
            return self.original_text

        if self.is_expanded:
            return self.original_text
        else:
            return self.original_text[:self.max_length] + "..."

    def _update_display(self):
        """更新顯示內容"""
        display_text = self._get_display_text()
        self.label.config(text=display_text)

        # 更新游標樣式
        if self._needs_truncation():
            cursor = 'hand2'
            # 添加視覺提示
            if not self.is_expanded:
                self.label.config(fg='#2196F3')  # 藍色表示可點擊
            else:
                self.label.config(fg=self.fg_color)
        else:
            cursor = 'arrow'
            self.label.config(fg=self.fg_color)

        self.label.config(cursor=cursor)

    def _on_click(self, event):
        """處理點擊事件"""
        if not self._needs_truncation():
            return

        if self.is_expanded:
            self._collapse()
        else:
            self._expand_popup()

    def _on_enter(self, event):
        """滑鼠進入事件"""
        if self._needs_truncation() and not self.is_expanded:
            self.label.config(fg='#1976D2')  # 深藍色hover效果

    def _on_leave(self, event):
        """滑鼠離開事件"""
        if self._needs_truncation() and not self.is_expanded:
            self.label.config(fg='#2196F3')  # 恢復藍色

    def _expand_popup(self):
        """彈出視窗顯示完整文字"""
        if self.popup_window:
            return

        # 建立彈出視窗
        self.popup_window = tk.Toplevel(self.parent)
        self.popup_window.title("完整內容")
        self.popup_window.configure(bg=self.bg_color)
        self.popup_window.resizable(False, False)
        self.popup_window.attributes('-topmost', True)

        # 設定視窗樣式
        self.popup_window.overrideredirect(True)

        # 建立內容框架
        content_frame = tk.Frame(
            self.popup_window,
            bg=self.bg_color,
            relief='solid',
            borderwidth=1
        )
        content_frame.pack(fill='both', expand=True, padx=2, pady=2)

        # 建立文字標籤
        text_label = tk.Label(
            content_frame,
            text=self.original_text,
            bg=self.bg_color,
            fg=self.fg_color,
            font=self.font,
            wraplength=300,  # 自動換行
            justify='left',
            anchor='nw'
        )
        text_label.pack(padx=10, pady=10, fill='both', expand=True)

        # 建立關閉按鈕
        close_btn = tk.Button(
            content_frame,
            text="關閉",
            command=self._close_popup,
            bg=AppConfig.COLORS.get('button_bg', '#2196F3'),
            fg=AppConfig.COLORS.get('button_fg', 'white'),
            font=AppConfig.FONTS.get('button', ('SimHei', 9)),
            width=8,
            height=1
        )
        close_btn.pack(pady=(0, 10))

        # 定位彈出視窗
        self._position_popup()

        # 綁定關閉事件
        self.popup_window.bind('<Escape>', lambda e: self._close_popup())
        self.popup_window.bind('<FocusOut>', lambda e: self._close_popup())

        # 設定焦點
        self.popup_window.focus_set()

        self.is_expanded = True
        self._update_display()

    def _position_popup(self):
        """定位彈出視窗"""
        try:
            # 更新幾何資訊
            self.popup_window.update_idletasks()
            self.label.update_idletasks()

            # 取得標籤位置
            x = self.label.winfo_rootx()
            y = self.label.winfo_rooty() + self.label.winfo_height() + 5

            # 取得螢幕尺寸
            screen_width = self.popup_window.winfo_screenwidth()
            screen_height = self.popup_window.winfo_screenheight()

            # 取得彈出視窗尺寸
            popup_width = self.popup_window.winfo_reqwidth()
            popup_height = self.popup_window.winfo_reqheight()

            # 調整位置避免超出螢幕
            if x + popup_width > screen_width:
                x = screen_width - popup_width - 10

            if y + popup_height > screen_height:
                y = self.label.winfo_rooty() - popup_height - 5

            self.popup_window.geometry(f"+{x}+{y}")

        except Exception as e:
            print(f"定位彈出視窗失敗: {e}")
            # 使用預設位置
            self.popup_window.geometry("320x150+100+100")

    def _close_popup(self):
        """關閉彈出視窗"""
        if self.popup_window:
            self.popup_window.destroy()
            self.popup_window = None

        self.is_expanded = False
        self._update_display()

    def _collapse(self):
        """收起文字"""
        self.is_expanded = False
        self._update_display()

    def pack(self, **kwargs):
        """Pack方法代理"""
        return self.container.pack(**kwargs)

    def grid(self, **kwargs):
        """Grid方法代理"""
        return self.container.grid(**kwargs)

    def place(self, **kwargs):
        """Place方法代理"""
        return self.container.place(**kwargs)

    def update_text(self, new_text: str):
        """更新文字內容"""
        self.original_text = new_text or ""

        # 如果有彈出視窗，先關閉
        if self.popup_window:
            self._close_popup()

        # 重新檢查是否需要截短
        needs_truncation = self._needs_truncation()
        cursor = 'hand2' if needs_truncation else 'arrow'
        self.label.config(cursor=cursor)

        # 重新綁定事件
        self.label.unbind('<Button-1>')
        self.label.unbind('<Enter>')
        self.label.unbind('<Leave>')

        if needs_truncation:
            self.label.bind('<Button-1>', self._on_click)
            self.label.bind('<Enter>', self._on_enter)
            self.label.bind('<Leave>', self._on_leave)

        # 更新顯示
        self._update_display()

    def configure(self, **kwargs):
        """配置組件屬性"""
        # 更新內部屬性
        if 'font' in kwargs:
            self.font = kwargs.pop('font')
            self.label.config(font=self.font)

        if 'bg' in kwargs:
            self.bg_color = kwargs.pop('bg')
            self.container.config(bg=self.bg_color)
            self.label.config(bg=self.bg_color)

        if 'fg' in kwargs:
            self.fg_color = kwargs.pop('fg')

        # 應用其他配置到標籤
        if kwargs:
            self.label.config(**kwargs)

        # 更新顯示
        self._update_display()

    def destroy(self):
        """銷毀組件"""
        if self.popup_window:
            self._close_popup()
        if self.container:
            self.container.destroy()


# 便利函數
def create_truncated_label(parent, text: str, max_length: int = 50, **kwargs) -> TruncatedTextWidget:
    """
    建立截短文字標籤的便利函數

    Args:
        parent: 父容器
        text: 文字內容
        max_length: 最大長度
        **kwargs: 其他標籤屬性

    Returns:
        TruncatedTextWidget: 截短文字組件實例
    """
    return TruncatedTextWidget(parent, text, max_length, **kwargs)