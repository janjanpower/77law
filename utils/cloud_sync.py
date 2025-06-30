# utils/cloud_sync.py
"""
雲端同步核心功能 - 無需API，直接檔案操作
"""
import os
import json
import shutil
import threading
import time
from typing import Optional, Dict
from datetime import datetime
from config.settings import AppConfig

class CloudSync:
    """雲端同步管理器"""

    def __init__(self):
        self.cloud_path = None
        self.provider = None
        self.is_syncing = False
        self.last_sync = None

    def detect_cloud_services(self) -> Dict:
        """自動偵測雲端服務"""
        detected = {}

        for provider_id, config in AppConfig.CLOUD_SYNC['providers'].items():
            for path in config['paths']:
                if os.path.exists(path) and os.access(path, os.W_OK):
                    detected[provider_id] = {
                        'name': config['name'],
                        'path': path,
                        'app_folder': os.path.join(path, config['app_folder'])
                    }
                    break

        return detected

    def setup_cloud_sync(self, provider_id: str) -> bool:
        """設定雲端同步"""
        try:
            detected = self.detect_cloud_services()
            if provider_id not in detected:
                return False

            cloud_info = detected[provider_id]
            app_folder = cloud_info['app_folder']

            # 建立應用程式資料夾
            os.makedirs(app_folder, exist_ok=True)

            # 儲存同步設定
            sync_config = {
                'provider': provider_id,
                'cloud_path': app_folder,
                'setup_date': datetime.now().isoformat(),
                'enabled': True
            }

            with open('cloud_sync_config.json', 'w', encoding='utf-8') as f:
                json.dump(sync_config, f, ensure_ascii=False, indent=2)

            self.cloud_path = app_folder
            self.provider = provider_id
            return True

        except Exception as e:
            print(f"雲端同步設定失敗: {e}")
            return False

    def get_cloud_data_path(self) -> Optional[str]:
        """取得雲端資料檔案路徑"""
        if not self.cloud_path:
            return None
        return os.path.join(self.cloud_path, "cases_data.json")

    def sync_to_cloud(self, local_file: str) -> bool:
        """同步到雲端"""
        try:
            if not self.cloud_path:
                return False

            cloud_file = self.get_cloud_data_path()
            shutil.copy2(local_file, cloud_file)
            self.last_sync = datetime.now()
            return True

        except Exception as e:
            print(f"同步到雲端失敗: {e}")
            return False

    def sync_from_cloud(self, local_file: str) -> bool:
        """從雲端同步"""
        try:
            if not self.cloud_path:
                return False

            cloud_file = self.get_cloud_data_path()
            if os.path.exists(cloud_file):
                shutil.copy2(cloud_file, local_file)
                self.last_sync = datetime.now()
                return True
            return False

        except Exception as e:
            print(f"從雲端同步失敗: {e}")
            return False

    def auto_sync(self, local_file: str):
        """自動同步（比較檔案時間）"""
        try:
            cloud_file = self.get_cloud_data_path()
            if not cloud_file:
                return

            local_time = os.path.getmtime(local_file) if os.path.exists(local_file) else 0
            cloud_time = os.path.getmtime(cloud_file) if os.path.exists(cloud_file) else 0

            if local_time > cloud_time:
                self.sync_to_cloud(local_file)
            elif cloud_time > local_time:
                self.sync_from_cloud(local_file)

        except Exception as e:
            print(f"自動同步失敗: {e}")

    def load_config(self) -> bool:
        """載入同步設定"""
        try:
            with open('cloud_sync_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

            if config.get('enabled'):
                self.cloud_path = config.get('cloud_path')
                self.provider = config.get('provider')
                return os.path.exists(self.cloud_path) if self.cloud_path else False

        except:
            pass
        return False