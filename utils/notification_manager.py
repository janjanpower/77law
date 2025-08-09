#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
統一通知管理器 - 🔥 100%無控制台閃爍最終版
專為 PyInstaller --noconsole 打包優化
"""
import os
import threading
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox
from typing import List, Dict, Any, Callable

from config.notification_settings import NotificationConfig


# 🔥 關鍵：只導入不會引起控制台閃爍的模組
try:
    import winsound  # Windows音效播放 - 安全，不會閃爍控制台
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

try:
    import pygame  # 音效播放引擎 - 安全，不會閃爍控制台
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from pydub import AudioSegment  # 音效處理 - 安全，不會閃爍控制台
    from pydub.playback import play
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# 🔥 移除 plyer - 這是控制台閃爍的主要原因之一
# 改用 Windows API 或者完全不使用桌面通知
try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class NotificationManager:
    """統一通知管理器 - 🔥 100%無控制台閃爍最終版"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """單例模式確保全域唯一"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.config = NotificationConfig()
            self.sound_enabled = True
            self.desktop_notification_enabled = False  # 🔥 預設關閉桌面通知避免控制台閃爍
            self.today_reminder_enabled = True
            self.notification_history = []
            self._notification_queue = []
            self._is_processing = False
            self._bell_callback = None
            self._pygame_initialized = False

            # 音量控制相關屬性
            self.current_volume = self.config.NOTIFICATION_SETTINGS.get('volume', 0.8)
            self.volume_method = 'auto'

            self._initialized = True

            self.main_window_ref = None  # 🔥 新增主視窗參考
            self._notification_dialog = None  # 🔥 新增通知對話框參考

            # 🆕 通知狀態變更回調列表
            self._notification_state_callbacks = []


            # 選擇最安全的音效播放方法
            self._select_safe_audio_method()

    def _select_safe_audio_method(self):
        """🔥 選擇100%安全的音效播放方法（不會閃爍控制台）"""
        if PYGAME_AVAILABLE:
            self.volume_method = 'pygame'
            print("🎛️ 選擇音效方法: pygame (安全)")
        elif PYDUB_AVAILABLE:
            self.volume_method = 'pydub'
            print("🎛️ 選擇音效方法: pydub (安全)")
        elif WINSOUND_AVAILABLE and os.name == 'nt':
            self.volume_method = 'winsound'
            print("🎛️ 選擇音效方法: winsound (安全)")
        else:
            self.volume_method = 'silent'
            print("🎛️ 音效方法: 靜音模式")

    def check_tomorrow_reminders(self, upcoming_stages: List[Dict[str, Any]]) -> bool:
        """🔥 修正版：檢查是否有明日事項 - 檢查鈴聲通知開關"""
        # 🔥 如果鈴聲通知關閉，直接返回False
        if not self.sound_enabled:
            return False

        if not self.today_reminder_enabled:
            return False

        tomorrow = datetime.now().date() + timedelta(days=1)
        tomorrow_stages = [
            stage for stage in upcoming_stages
            if stage['stage_date'] == tomorrow
        ]

        if tomorrow_stages:
            self._trigger_tomorrow_notification(tomorrow_stages)
            return True
        return False

    def check_today_urgent_reminders(self, upcoming_stages: List[Dict[str, Any]]) -> bool:
        """🔥 修正版：檢查是否有一日內緊急事項 - 檢查鈴聲通知開關"""
        # 🔥 如果鈴聲通知關閉，直接返回False
        if not self.sound_enabled:
            return False

        if not self.today_reminder_enabled:
            return False

        today = datetime.now().date()
        today_stages = [
            stage for stage in upcoming_stages
            if stage['stage_date'] == today
        ]

        if today_stages:
            self._trigger_today_urgent_notification(today_stages)
            return True
        return False

    def _trigger_tomorrow_notification(self, tomorrow_stages: List[Dict[str, Any]]):
        """觸發明日提醒 - 🔥 100%安全版本"""
        print(f"🔔 觸發明日提醒 - {len(tomorrow_stages)} 個案件")

        # 只播放音效，不使用桌面通知
        if self.sound_enabled:
            success = self._play_safe_sound('tomorrow_reminder')
            if not success:
                print("⚠️ 音效播放失敗")

        # 🔥 使用安全的彈出視窗替代桌面通知
        if self.desktop_notification_enabled:
            self._show_safe_notification_dialog(tomorrow_stages, "明日案件提醒")

        # 記錄通知歷史
        self._record_notification('tomorrow_reminder', tomorrow_stages)

    def _trigger_today_urgent_notification(self, today_stages: List[Dict[str, Any]]):
        """觸發一日內緊急提醒 - 🔥 100%安全版本"""
        print(f"🚨 觸發緊急提醒 - {len(today_stages)} 個案件")

        # 只播放音效，不使用桌面通知
        if self.sound_enabled:
            success = self._play_safe_sound('bell_notification')
            if not success:
                self._play_safe_system_beep()

        # 觸發鈴鐺圖示動畫
        if self._bell_callback:
            self._bell_callback(True, len(today_stages))

        # 🔥 使用安全的彈出視窗替代桌面通知
        if self.desktop_notification_enabled:
            self._show_safe_notification_dialog(today_stages, "今日緊急案件提醒")

        # 記錄通知歷史
        self._record_notification('today_urgent', today_stages)

    def _play_safe_sound(self, sound_type: str) -> bool:
        """
        🔥 100%安全的音效播放（絕對不會閃爍控制台）

        Args:
            sound_type: 音效類型

        Returns:
            bool: 播放是否成功
        """
        try:
            sound_file = self.config.get_sound_file(sound_type)

            if not sound_file:
                print(f"❌ 無法取得音效檔: {sound_type}")
                return False

            # 處理系統預設音效
            if sound_file == "SYSTEM_DEFAULT":
                return self._play_safe_system_beep()

            # 檢查檔案是否存在
            if not os.path.exists(sound_file):
                print(f"❌ 音效檔不存在: {sound_file}")
                return False

            print(f"🔊 播放音效: {sound_file} (音量: {int(self.current_volume * 100)}%)")

            # 在背景執行緒播放音效，避免阻塞UI
            threading.Thread(
                target=self._play_safe_sound_async,
                args=(sound_file,),
                daemon=True,
                name=f"SafeAudioPlayer-{sound_type}"
            ).start()

            return True

        except Exception as e:
            print(f"❌ 音效播放異常: {e}")
            return False

    def _play_safe_sound_async(self, sound_file: str):
        """🔥 100%安全的異步音效播放"""
        try:
            file_path = Path(sound_file)
            success = False

            # 按安全優先級嘗試播放
            if self.volume_method == 'pygame' and PYGAME_AVAILABLE:
                success = self._play_with_pygame_safe(sound_file)
            elif self.volume_method == 'pydub' and PYDUB_AVAILABLE:
                success = self._play_with_pydub_safe(sound_file)
            elif self.volume_method == 'winsound' and WINSOUND_AVAILABLE:
                success = self._play_with_winsound_safe(sound_file)

            # 如果主要方法失敗，嘗試其他安全方法
            if not success:
                if PYGAME_AVAILABLE and self.volume_method != 'pygame':
                    success = self._play_with_pygame_safe(sound_file)
                elif PYDUB_AVAILABLE and self.volume_method != 'pydub':
                    success = self._play_with_pydub_safe(sound_file)
                elif WINSOUND_AVAILABLE and self.volume_method != 'winsound':
                    success = self._play_with_winsound_safe(sound_file)

            if success:
                print(f"✅ 音效播放成功: {file_path.name}")
            else:
                print(f"❌ 所有安全播放方式都失敗: {file_path.name}")

        except Exception as e:
            print(f"❌ 異步音效播放異常: {e}")

    def _play_with_pygame_safe(self, sound_file: str) -> bool:
        """使用 pygame 安全播放音效"""
        try:
            if not PYGAME_AVAILABLE:
                return False

            # 初始化 pygame.mixer（只需初始化一次）
            if not self._pygame_initialized:
                pygame.mixer.init()
                self._pygame_initialized = True

            # 載入並播放音效
            sound = pygame.mixer.Sound(sound_file)
            sound.set_volume(self.current_volume)
            sound.play()

            # 等待播放完成
            while pygame.mixer.get_busy():
                pygame.time.wait(100)

            return True

        except Exception as e:
            print(f"❌ pygame 播放失敗: {e}")
            return False

    def _play_with_pydub_safe(self, sound_file: str) -> bool:
        """使用 pydub 安全播放音效"""
        try:
            if not PYDUB_AVAILABLE:
                return False

            # 載入音效檔案
            audio = AudioSegment.from_file(sound_file)

            # 調整音量
            if self.current_volume <= 0.0:
                return True  # 靜音，直接返回成功
            elif self.current_volume < 1.0:
                db_change = 20 * (self.current_volume - 1.0)
                audio = audio + db_change

            # 播放音效
            play(audio)
            return True

        except Exception as e:
            print(f"❌ pydub 播放失敗: {e}")
            return False

    def _play_with_winsound_safe(self, sound_file: str) -> bool:
        """使用 winsound 安全播放音效（僅WAV格式）"""
        try:
            if not WINSOUND_AVAILABLE or os.name != 'nt':
                return False

            file_path = Path(sound_file)

            # 如果音量設定很低，跳過播放
            if self.current_volume < 0.1:
                print(f"🔇 音量過低，跳過播放")
                return True

            # 只支援 WAV 格式的直接播放
            if file_path.suffix.lower() == '.wav':
                winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return True
            else:
                return False

        except Exception as e:
            print(f"❌ winsound 播放失敗: {e}")
            return False

    def _play_safe_system_beep(self) -> bool:
        """🔥 100%安全的系統音效播放"""
        try:
            if WINSOUND_AVAILABLE and os.name == 'nt':
                # 使用 winsound 播放系統音效，絕對不會顯示控制台
                winsound.PlaySound("SystemDefault", winsound.SND_ALIAS | winsound.SND_ASYNC)
                print("🔊 播放系統預設音效")
                return True
            else:
                # 非Windows系統，使用系統嗶聲
                print("\a")  # ASCII 響鈴字符
                return True
        except Exception as e:
            print(f"❌ 系統音效播放失敗: {e}")
            return False

    def _show_safe_notification_dialog(self, stages: List[Dict[str, Any]], title: str):
        """
        🔥 修正版：顯示安全的通知對話框 - 先檢查鈴聲通知開關

        Args:
            stages: 案件階段列表
            title: 通知標題
        """
        # 🔥 核心修正：如果鈴聲通知關閉，則不顯示任何彈出視窗
        if not self.sound_enabled:
            print("🔕 鈴聲通知已關閉，跳過彈出視窗顯示")
            return

        try:
            # 檢查是否已有通知視窗存在
            if hasattr(self, '_notification_dialog') and self._notification_dialog:
                try:
                    if self._notification_dialog.winfo_exists():
                        self._notification_dialog.destroy()
                except:
                    pass
                self._notification_dialog = None

            # 建立通知視窗
            self._notification_dialog = tk.Toplevel()
            self._notification_dialog.title(title)
            self._notification_dialog.geometry("400x300")
            self._notification_dialog.configure(bg=AppConfig.COLORS['window_bg'])
            self._notification_dialog.resizable(False, False)

            # ========================================
            # 🔥 核心修改：限制置頂範圍
            # ========================================
            # 取得主視窗參考
            main_window = self._get_main_window()

            if main_window:
                # 只相對於主視窗置頂，而不是全域置頂
                self._notification_dialog.transient(main_window)
                self._notification_dialog.lift(main_window)

                # 設定視窗位置（在主視窗中央偏上）
                self._center_on_main_window(self._notification_dialog, main_window)
            else:
                # 如果找不到主視窗，使用一般置中
                self._center_window(self._notification_dialog)

            # ❌ 移除全域置頂設定
            # self._notification_dialog.attributes('-topmost', True)  # 移除此行

            # 建立內容
            self._create_notification_content(self._notification_dialog, stages, title)

            # 設定關閉行為
            self._notification_dialog.protocol("WM_DELETE_WINDOW", self._close_notification_dialog)

            # 顯示視窗
            self._notification_dialog.deiconify()
            self._notification_dialog.focus_force()

            # 自動關閉計時器（10秒後自動關閉）
            self._notification_dialog.after(10000, self._close_notification_dialog)

            print(f"✅ 通知對話框已顯示: {title}")

        except Exception as e:
            print(f"❌ 顯示通知對話框失敗: {e}")

    def set_main_window_reference(self, main_window):
        """
        🔥 新增：設定主視窗參考（供外部呼叫）

        Args:
            main_window: 主視窗物件
        """
        self.main_window_ref = main_window
        print(f"✅ 已設定主視窗參考: {main_window.title() if main_window else 'None'}")


    def _close_notification_dialog(self):
        """
        🔥 修改：關閉通知對話框
        """
        try:
            if hasattr(self, '_notification_dialog') and self._notification_dialog:
                if self._notification_dialog.winfo_exists():
                    self._notification_dialog.destroy()
                self._notification_dialog = None
                print("✅ 通知對話框已關閉")
        except Exception as e:
            print(f"⚠️ 關閉通知對話框失敗: {e}")


    def _get_main_window(self):
        """
        🔥 新增：取得主視窗參考

        Returns:
            主視窗物件或None
        """
        try:
            # 方法1：通過tkinter取得根視窗
            import tkinter as tk
            root = tk._default_root
            if root and root.winfo_exists():
                return root

            # 方法2：通過全域變數取得（需要在主程式中設定）
            if hasattr(self, 'main_window_ref') and self.main_window_ref:
                if self.main_window_ref.winfo_exists():
                    return self.main_window_ref

            # 方法3：搜尋所有頂層視窗，找出主視窗
            for widget in tk.Tk.winfo_children(tk._default_root):
                if isinstance(widget, tk.Toplevel):
                    # 可以根據標題或其他屬性判斷是否為主視窗
                    if "案件管理系統" in widget.title():
                        return widget

            return None

        except Exception as e:
            print(f"⚠️ 取得主視窗失敗: {e}")
            return None

    def _center_on_main_window(self, dialog, main_window):
        """
        🔥 新增：將對話框置中於主視窗上方

        Args:
            dialog: 對話框視窗
            main_window: 主視窗
        """
        try:
            # 更新視窗以取得實際尺寸
            dialog.update_idletasks()
            main_window.update_idletasks()

            # 取得主視窗位置和尺寸
            main_x = main_window.winfo_x()
            main_y = main_window.winfo_y()
            main_width = main_window.winfo_width()
            main_height = main_window.winfo_height()

            # 取得對話框尺寸
            dialog_width = dialog.winfo_reqwidth()
            dialog_height = dialog.winfo_reqheight()

            # 計算置中位置（主視窗中央偏上）
            x = main_x + (main_width - dialog_width) // 2
            y = main_y + (main_height - dialog_height) // 3  # 偏上1/3位置

            # 確保不會超出螢幕邊界
            screen_width = dialog.winfo_screenwidth()
            screen_height = dialog.winfo_screenheight()

            x = max(0, min(x, screen_width - dialog_width))
            y = max(0, min(y, screen_height - dialog_height))

            # 設定位置
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        except Exception as e:
            print(f"⚠️ 對話框定位失敗: {e}")
            # 失敗時使用螢幕置中
            self._center_window(dialog)

    def _center_window(self, window):
        """
        🔥 修改：將視窗置中於螢幕

        Args:
            window: 要置中的視窗
        """
        try:
            window.update_idletasks()
            width = window.winfo_reqwidth()
            height = window.winfo_reqheight()

            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()

            x = (screen_width - width) // 2
            y = (screen_height - height) // 2

            window.geometry(f"{width}x{height}+{x}+{y}")

        except Exception as e:
            print(f"⚠️ 視窗置中失敗: {e}")


    def _show_notification_dialog_async(self, stages: List[Dict[str, Any]], title: str):
        """異步顯示通知對話框"""
        try:
            stage_count = len(stages)

            if stage_count == 1:
                stage = stages[0]
                message = f"有案件階段到期：\n{stage['client']} - {stage['stage_name']}"
            else:
                message = f"有 {stage_count} 個案件階段到期"

            # 創建臨時的 Tkinter 根視窗
            root = tk.Tk()
            root.withdraw()  # 隱藏主視窗

            # 顯示訊息對話框
            messagebox.showinfo(title, message)

            # 關閉臨時視窗
            root.destroy()

        except Exception as e:
            print(f"❌ 異步通知對話框失敗: {e}")

    def _record_notification(self, notification_type: str, stages: List[Dict[str, Any]]):
        """記錄通知歷史"""
        try:
            record = {
                'timestamp': datetime.now().isoformat(),
                'type': notification_type,
                'stage_count': len(stages),
                'volume': self.current_volume,
                'stages': [
                    {
                        'client': stage.get('client', ''),
                        'stage_name': stage.get('stage_name', ''),
                        'stage_date': stage.get('stage_date', '').isoformat() if hasattr(stage.get('stage_date', ''), 'isoformat') else str(stage.get('stage_date', ''))
                    }
                    for stage in stages
                ]
            }

            self.notification_history.append(record)

            # 限制歷史記錄數量
            if len(self.notification_history) > 100:
                self.notification_history = self.notification_history[-50:]

            print(f"📝 通知記錄已儲存: {notification_type}")

        except Exception as e:
            print(f"❌ 記錄通知失敗: {e}")

    def set_bell_callback(self, callback: Callable):
        """設定鈴鐺圖示回調函數"""
        self._bell_callback = callback

    def get_notification_history(self) -> List[Dict]:
        """取得通知歷史"""
        return self.notification_history.copy()

    def set_sound_enabled(self, enabled: bool):
        """🔥 修改：設定音效開關 - 新增回調通知"""
        old_enabled = self.sound_enabled
        self.sound_enabled = enabled

        # 🆕 觸發通知狀態變更回調
        self._notify_notification_state_change(old_enabled, enabled)

    def _notify_notification_state_change(self, old_enabled: bool, new_enabled: bool):
        """🆕 通知鈴聲通知狀態變更"""
        try:
            for callback in self._notification_state_callbacks:
                try:
                    callback(old_enabled, new_enabled)
                except Exception as e:
                    print(f"通知狀態變更回調執行失敗: {e}")
        except Exception as e:
            print(f"通知鈴聲通知狀態變更失敗: {e}")


    def register_notification_state_callback(self, callback):
        """🆕 註冊通知狀態變更回調函數"""
        if callback not in self._notification_state_callbacks:
            self._notification_state_callbacks.append(callback)

    def unregister_notification_state_callback(self, callback):
        """🆕 取消註冊通知狀態變更回調函數"""
        if callback in self._notification_state_callbacks:
            self._notification_state_callbacks.remove(callback)

    def get_sound_enabled(self) -> bool:
        """🆕 取得當前鈴聲通知開關狀態"""
        return self.sound_enabled

    def toggle_sound_enabled(self) -> bool:
        """🆕 切換鈴聲通知開關狀態"""
        new_enabled = not self.sound_enabled
        self.set_sound_enabled(new_enabled)
        return new_enabled

    def set_desktop_notification_enabled(self, enabled: bool):
        """設定桌面通知開關"""
        self.desktop_notification_enabled = enabled

    def set_today_reminder_enabled(self, enabled: bool):
        """設定一日內提醒開關"""
        self.today_reminder_enabled = enabled

    # 🔥 向後相容方法
    def _play_sound_with_volume(self, sound_type: str) -> bool:
        """向後相容方法"""
        return self._play_safe_sound(sound_type)

    def _play_sound(self, sound_type: str) -> bool:
        """向後相容方法"""
        return self._play_safe_sound(sound_type)