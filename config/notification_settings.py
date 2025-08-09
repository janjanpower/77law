#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通知功能設定配置 - 🔥 控制台閃爍修正版本
解決音效檔案路徑和播放問題，新增專業的錯誤處理
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any


class NotificationConfig:
    """通知設定配置 - 統一路徑管理與防控制台閃爍"""

    def __init__(self):
        """初始化配置，自動檢測專案根目錄"""
        self._init_project_paths()

    def _init_project_paths(self):
        """初始化專案路徑"""
        # 獲取專案根目錄 - 支援多種部署情境
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller 打包後的情況
            self.project_root = Path(sys._MEIPASS)
        else:
            # 開發環境 - 從 config 目錄向上找到專案根目錄
            config_dir = Path(__file__).parent
            self.project_root = config_dir.parent

        # 確保 assets 目錄存在
        self.assets_dir = self.project_root / 'assets'
        self.sounds_dir = self.assets_dir / 'sounds'
        self.icons_dir = self.assets_dir / 'icons'

        # 自動建立必要目錄
        self._ensure_directories_exist()

    def _ensure_directories_exist(self):
        """確保必要的資源目錄存在"""
        try:
            self.assets_dir.mkdir(exist_ok=True)
            self.sounds_dir.mkdir(exist_ok=True)
            self.icons_dir.mkdir(exist_ok=True)
            print(f"✅ 資源目錄確認: {self.assets_dir}")
        except Exception as e:
            print(f"⚠️ 建立資源目錄失敗: {e}")

    # 🔥 修正版音效檔案配置 - 支援多種格式並包含靜音選項
    SOUNDS = {
        'tomorrow_reminder': {
            'files': ['tomorrow_reminder.mp3', 'tomorrow_reminder.wav', 'tomorrow_reminder.ogg'],
            'fallback': 'SYSTEM_DEFAULT',
            'description': '明日案件提醒音效'
        },
        'bell_notification': {
            'files': ['bell_notification.mp3', 'bell_notification.wav', 'bell_notification.ogg'],
            'fallback': 'SYSTEM_DEFAULT',
            'description': '緊急案件鈴聲'
        },
        'system_alert': {
            'files': ['system_alert.mp3', 'system_alert.wav'],
            'fallback': 'SYSTEM_DEFAULT',
            'description': '系統警示音效'
        }
    }

    # 圖示檔案配置
    ICONS = {
        'notification': 'notification.png',
        'urgent': 'urgent.ico',
        'bell': 'bell.png',
        'bell_active': 'bell_active.png'
    }

    # 🔥 修正版通知設定 - 新增防控制台閃爍選項
    NOTIFICATION_SETTINGS = {
        'sound_enabled': True,
        'desktop_notification_enabled': True,
        'console_output_enabled': False,  # 🆕 關閉控制台輸出
        'volume': 0.4,  # 預設音量 80%
        'notification_timeout': 10,
        'urgent_notification_timeout': 15,
        'max_history_records': 100,
        'audio_engine_priority': ['pydub', 'pygame', 'winsound'],  # 🆕 音效引擎優先級
        'prevent_console_flash': True,  # 🆕 防止控制台閃爍
        'fallback_to_system_sound': True  # 🆕 失敗時使用系統音效
    }

    def get_sound_file(self, sound_type: str) -> Optional[str]:
        """
        🔥 修正版：取得音效檔案路徑（優先級檢查，防控制台閃爍）

        Args:
            sound_type: 音效類型

        Returns:
            str: 音效檔案完整路徑，或 None 如果找不到
        """
        try:
            if sound_type not in self.SOUNDS:
                print(f"⚠️ 未知的音效類型: {sound_type}")
                return None

            sound_config = self.SOUNDS[sound_type]

            # 如果是字典格式（新版），按優先級檢查檔案
            if isinstance(sound_config, dict):
                sound_files = sound_config.get('files', [])

                # 按順序檢查每個音效檔案是否存在
                for sound_file in sound_files:
                    full_path = self.sounds_dir / sound_file
                    if full_path.exists():
                        return str(full_path)

                # 如果沒有找到任何檔案，返回備用選項
                fallback = sound_config.get('fallback', 'SYSTEM_DEFAULT')
                if fallback == 'SYSTEM_DEFAULT':
                    return 'SYSTEM_DEFAULT'
                else:
                    fallback_path = self.sounds_dir / fallback
                    return str(fallback_path) if fallback_path.exists() else 'SYSTEM_DEFAULT'

            # 向後相容：如果是字串格式（舊版）
            elif isinstance(sound_config, str):
                full_path = self.sounds_dir / sound_config
                return str(full_path) if full_path.exists() else 'SYSTEM_DEFAULT'

            return None

        except Exception as e:
            print(f"❌ 取得音效檔案失敗: {e}")
            return 'SYSTEM_DEFAULT'

    def get_icon_file(self, icon_type: str) -> Optional[str]:
        """
        取得圖示檔案路徑

        Args:
            icon_type: 圖示類型

        Returns:
            str: 圖示檔案完整路徑，或 None 如果找不到
        """
        try:
            if icon_type not in self.ICONS:
                print(f"⚠️ 未知的圖示類型: {icon_type}")
                return None

            icon_file = self.ICONS[icon_type]
            full_path = self.icons_dir / icon_file

            return str(full_path) if full_path.exists() else None

        except Exception as e:
            print(f"❌ 取得圖示檔案失敗: {e}")
            return None

    def get_project_info(self) -> Dict[str, Any]:
        """取得專案相關資訊"""
        return {
            'project_root': str(self.project_root),
            'assets_dir': str(self.assets_dir),
            'sounds_dir': str(self.sounds_dir),
            'icons_dir': str(self.icons_dir),
            'sounds_dir_exists': self.sounds_dir.exists(),
            'icons_dir_exists': self.icons_dir.exists()
        }

    def validate_sound_files(self) -> Dict[str, Any]:
        """
        🔥 修正版：驗證音效檔案存在性

        Returns:
            dict: 驗證結果
        """
        validation_result = {
            'total_files': 0,
            'existing_files': [],
            'missing_files': [],
            'supported_formats': []
        }

        try:
            for sound_type, sound_config in self.SOUNDS.items():
                if isinstance(sound_config, dict):
                    # 新版格式：支援多個檔案
                    sound_files = sound_config.get('files', [])
                    description = sound_config.get('description', sound_type)

                    found_any = False
                    for sound_file in sound_files:
                        validation_result['total_files'] += 1
                        full_path = self.sounds_dir / sound_file

                        if full_path.exists():
                            validation_result['existing_files'].append({
                                'type': sound_type,
                                'file': sound_file,
                                'path': str(full_path),
                                'description': description
                            })
                            found_any = True

                            # 記錄支援的格式
                            file_ext = full_path.suffix.lower()
                            if file_ext not in validation_result['supported_formats']:
                                validation_result['supported_formats'].append(file_ext)

                    # 如果該類型的所有檔案都不存在
                    if not found_any:
                        validation_result['missing_files'].append({
                            'type': sound_type,
                            'expected_files': sound_files,
                            'expected_path': str(self.sounds_dir),
                            'description': description
                        })

                elif isinstance(sound_config, str):
                    # 舊版格式：單一檔案
                    validation_result['total_files'] += 1
                    full_path = self.sounds_dir / sound_config

                    if full_path.exists():
                        validation_result['existing_files'].append({
                            'type': sound_type,
                            'file': sound_config,
                            'path': str(full_path),
                            'description': sound_type
                        })

                        file_ext = full_path.suffix.lower()
                        if file_ext not in validation_result['supported_formats']:
                            validation_result['supported_formats'].append(file_ext)
                    else:
                        validation_result['missing_files'].append({
                            'type': sound_type,
                            'expected_files': [sound_config],
                            'expected_path': str(full_path),
                            'description': sound_type
                        })

        except Exception as e:
            print(f"❌ 音效檔案驗證失敗: {e}")

        return validation_result

    def validate_icon_files(self) -> Dict[str, Any]:
        """驗證圖示檔案存在性"""
        validation_result = {
            'total_files': len(self.ICONS),
            'existing_files': [],
            'missing_files': []
        }

        try:
            for icon_type, icon_file in self.ICONS.items():
                full_path = self.icons_dir / icon_file

                if full_path.exists():
                    validation_result['existing_files'].append({
                        'type': icon_type,
                        'file': icon_file,
                        'path': str(full_path)
                    })
                else:
                    validation_result['missing_files'].append({
                        'type': icon_type,
                        'expected_file': icon_file,
                        'expected_path': str(full_path)
                    })

        except Exception as e:
            print(f"❌ 圖示檔案驗證失敗: {e}")

        return validation_result

    def create_default_sound_files_info(self) -> str:
        """
        🆕 生成預設音效檔案資訊（用於文件或錯誤提示）

        Returns:
            str: 音效檔案需求說明
        """
        info_lines = [
            "📁 音效檔案需求說明",
            "=" * 40,
            f"音效目錄：{self.sounds_dir}",
            "",
            "🎵 需要的音效檔案："
        ]

        for sound_type, sound_config in self.SOUNDS.items():
            if isinstance(sound_config, dict):
                files = sound_config.get('files', [])
                description = sound_config.get('description', sound_type)
                info_lines.append(f"• {description} ({sound_type}):")
                for file_name in files:
                    info_lines.append(f"  - {file_name}")
            elif isinstance(sound_config, str):
                info_lines.append(f"• {sound_type}: {sound_config}")

        info_lines.extend([
            "",
            "💡 說明：",
            "• 系統會按順序尋找音效檔案",
            "• 如果找不到檔案，將使用系統預設音效",
            "• 支援格式：MP3, WAV, OGG",
            "• 建議音效長度：1-3秒"
        ])

        return "\n".join(info_lines)

    def get_audio_engine_priority(self) -> List[str]:
        """🆕 取得音效引擎優先級列表"""
        return self.NOTIFICATION_SETTINGS.get('audio_engine_priority', ['pydub', 'pygame', 'winsound'])

    def is_console_flash_prevented(self) -> bool:
        """🆕 檢查是否啟用防控制台閃爍"""
        return self.NOTIFICATION_SETTINGS.get('prevent_console_flash', True)

    def should_fallback_to_system_sound(self) -> bool:
        """🆕 檢查是否應該備用系統音效"""
        return self.NOTIFICATION_SETTINGS.get('fallback_to_system_sound', True)

    def export_config_summary(self) -> Dict[str, Any]:
        """🆕 匯出配置摘要（用於除錯或日誌）"""
        try:
            sound_validation = self.validate_sound_files()
            icon_validation = self.validate_icon_files()

            return {
                'project_info': self.get_project_info(),
                'sound_files': {
                    'total': sound_validation['total_files'],
                    'existing': len(sound_validation['existing_files']),
                    'missing': len(sound_validation['missing_files']),
                    'supported_formats': sound_validation['supported_formats']
                },
                'icon_files': {
                    'total': icon_validation['total_files'],
                    'existing': len(icon_validation['existing_files']),
                    'missing': len(icon_validation['missing_files'])
                },
                'settings': {
                    'volume': self.get_volume_setting(),
                    'sound_enabled': self.NOTIFICATION_SETTINGS.get('sound_enabled', True),
                    'prevent_console_flash': self.is_console_flash_prevented(),
                    'audio_engine_priority': self.get_audio_engine_priority()
                }
            }
        except Exception as e:
            print(f"❌ 匯出配置摘要失敗: {e}")
            return {}