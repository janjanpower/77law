# utils/google_drive_sync.py
"""
Google Drive 專用同步模組 - 無需API，直接檔案操作
"""
import os
import json
import shutil
import threading
import time
from typing import Optional, Dict, Tuple
from datetime import datetime
from config.settings import AppConfig

class GoogleDriveSync:
    """Google Drive 同步管理器"""

    def __init__(self):
        self.google_drive_path = None
        self.app_folder_path = None
        self.is_enabled = False
        self.last_sync = None
        self.sync_thread = None
        self.is_syncing = False

    def detect_google_drive(self) -> Tuple[bool, str, str]:
        """偵測 Google Drive 安裝路徑"""
        possible_paths = AppConfig.GOOGLE_DRIVE_SYNC['possible_paths']

        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                # 檢查是否可寫入
                try:
                    test_file = os.path.join(path, '.write_test')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)

                    # 檢查是否為活躍的 Google Drive 資料夾
                    if self._is_active_google_drive(path):
                        return True, path, "Google Drive 已就緒"

                except Exception:
                    continue

        return False, "", "未找到 Google Drive 或無存取權限"

    def _is_active_google_drive(self, path: str) -> bool:
        """檢查是否為活躍的 Google Drive 資料夾"""
        try:
            # 檢查常見的 Google Drive 標識
            indicators = [
                '.tmp.drivedownload',
                '.tmp.driveupload',
                'desktop.ini'
            ]

            # 或者檢查資料夾內是否有 Google Drive 的特徵
            for item in os.listdir(path):
                if any(indicator in item.lower() for indicator in indicators):
                    return True

            # 基本檢查：能否正常讀寫
            return os.access(path, os.R_OK | os.W_OK)

        except Exception:
            return False

    def setup_google_drive_sync(self) -> Tuple[bool, str]:
        """設定 Google Drive 同步"""
        try:
            # 偵測 Google Drive
            found, drive_path, message = self.detect_google_drive()

            if not found:
                return False, message

            # 建立應用程式資料夾
            app_folder_name = AppConfig.GOOGLE_DRIVE_SYNC['app_folder_name']
            app_folder_path = os.path.join(drive_path, app_folder_name)

            os.makedirs(app_folder_path, exist_ok=True)

            # 建立說明檔案
            readme_content = f"""
# 案件管理系統 - Google Drive 同步資料夾

此資料夾由「案件管理系統」自動建立，用於在多台電腦間同步案件資料。

建立時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
同步路徑：{app_folder_path}

⚠️ 請勿手動修改此資料夾內的檔案，以免造成資料不一致。
"""

            readme_path = os.path.join(app_folder_path, 'README.txt')
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)

            # 儲存同步設定
            sync_config = {
                'enabled': True,
                'google_drive_path': drive_path,
                'app_folder_path': app_folder_path,
                'setup_date': datetime.now().isoformat(),
                'version': '1.0'
            }

            config_file = 'google_drive_sync_config.json'
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(sync_config, f, ensure_ascii=False, indent=2)

            # 更新實例變數
            self.google_drive_path = drive_path
            self.app_folder_path = app_folder_path
            self.is_enabled = True

            return True, f"Google Drive 同步已設定完成\n同步資料夾：{app_folder_path}"

        except Exception as e:
            return False, f"設定失敗：{str(e)}"

    def load_config(self) -> bool:
        """載入同步設定"""
        try:
            config_file = 'google_drive_sync_config.json'
            if not os.path.exists(config_file):
                return False

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if config.get('enabled'):
                app_folder_path = config.get('app_folder_path')

                # 驗證路徑是否仍然有效
                if app_folder_path and os.path.exists(app_folder_path):
                    self.google_drive_path = config.get('google_drive_path')
                    self.app_folder_path = app_folder_path
                    self.is_enabled = True
                    return True

        except Exception as e:
            print(f"載入設定失敗: {e}")

        return False

    def get_sync_data_path(self) -> Optional[str]:
        """取得同步資料檔案路徑"""
        if not self.app_folder_path:
            return None
        return os.path.join(self.app_folder_path, "cases_data.json")

    def sync_to_google_drive(self, local_file: str) -> bool:
        """同步到 Google Drive"""
        try:
            if not self.is_enabled or not self.app_folder_path:
                return False

            sync_file = self.get_sync_data_path()
            if not sync_file:
                return False

            # 備份現有檔案
            if os.path.exists(sync_file):
                backup_file = sync_file + '.backup'
                shutil.copy2(sync_file, backup_file)

            # 複製檔案到 Google Drive
            shutil.copy2(local_file, sync_file)

            # 更新同步時間
            self.last_sync = datetime.now()

            print(f"已同步到 Google Drive: {datetime.now().strftime('%H:%M:%S')}")
            return True

        except Exception as e:
            print(f"同步到 Google Drive 失敗: {e}")
            return False

    def sync_from_google_drive(self, local_file: str) -> bool:
        """從 Google Drive 同步"""
        try:
            if not self.is_enabled or not self.app_folder_path:
                return False

            sync_file = self.get_sync_data_path()
            if not sync_file or not os.path.exists(sync_file):
                return False

            # 備份本地檔案
            if os.path.exists(local_file):
                backup_file = local_file + '.backup'
                shutil.copy2(local_file, backup_file)

            # 從 Google Drive 複製檔案
            shutil.copy2(sync_file, local_file)

            # 更新同步時間
            self.last_sync = datetime.now()

            print(f"已從 Google Drive 同步: {datetime.now().strftime('%H:%M:%S')}")
            return True

        except Exception as e:
            print(f"從 Google Drive 同步失敗: {e}")
            return False

    def auto_sync(self, local_file: str) -> bool:
        """自動同步（比較檔案時間）"""
        try:
            if not self.is_enabled:
                return False

            sync_file = self.get_sync_data_path()
            if not sync_file:
                return False

            local_exists = os.path.exists(local_file)
            sync_exists = os.path.exists(sync_file)

            if not local_exists and not sync_exists:
                return False
            elif not local_exists and sync_exists:
                # 只有雲端檔案，下載
                return self.sync_from_google_drive(local_file)
            elif local_exists and not sync_exists:
                # 只有本地檔案，上傳
                return self.sync_to_google_drive(local_file)
            else:
                # 兩個檔案都存在，比較時間
                local_time = os.path.getmtime(local_file)
                sync_time = os.path.getmtime(sync_file)

                if local_time > sync_time:
                    return self.sync_to_google_drive(local_file)
                elif sync_time > local_time:
                    return self.sync_from_google_drive(local_file)
                else:
                    # 檔案時間相同，無需同步
                    return True

        except Exception as e:
            print(f"自動同步失敗: {e}")
            return False

    def start_auto_sync(self, local_file: str, interval: int = 30):
        """啟動自動同步背景執行緒"""
        if self.is_syncing:
            return

        def sync_worker():
            self.is_syncing = True
            try:
                while self.is_syncing and self.is_enabled:
                    self.auto_sync(local_file)
                    time.sleep(interval)
            except Exception as e:
                print(f"背景同步錯誤: {e}")
            finally:
                self.is_syncing = False

        self.sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self.sync_thread.start()

    def stop_auto_sync(self):
        """停止自動同步"""
        self.is_syncing = False

    def get_sync_status(self) -> Dict:
        """取得同步狀態"""
        return {
            'enabled': self.is_enabled,
            'google_drive_path': self.google_drive_path,
            'app_folder_path': self.app_folder_path,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'is_syncing': self.is_syncing,
            'sync_file_exists': os.path.exists(self.get_sync_data_path()) if self.get_sync_data_path() else False
        }

    def disable_sync(self) -> bool:
        """停用同步"""
        try:
            self.stop_auto_sync()
            self.is_enabled = False

            # 更新設定檔
            config_file = 'google_drive_sync_config.json'
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                config['enabled'] = False
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"停用同步失敗: {e}")
            return False