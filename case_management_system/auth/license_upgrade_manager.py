import os
from .license_generator import LicenseGenerator
import json

import base64
import uuid
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from typing import Dict, List, Tuple, Optional

class LicenseUpgradeManager:
    """授權升級管理器"""

    def __init__(self):
        self.license_file = ".license_data"
        self.secret_salt = "CaseManagement2024"
        self.hardware_id = self._get_hardware_id()

    def _get_hardware_id(self):
        """取得硬體特徵ID"""
        try:
            mac = uuid.getnode()
            import platform
            computer_name = platform.node()
            unique_string = f"{mac}_{computer_name}"
            return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
        except:
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]

    def _generate_key(self):
        """生成加密密鑰"""
        key_string = f"{self.hardware_id}_{self.secret_salt}"
        key_hash = hashlib.sha256(key_string.encode()).digest()
        return base64.urlsafe_b64encode(key_hash)

    def _encrypt_data(self, data):
        """加密資料"""
        key = self._generate_key()
        f = Fernet(key)
        return f.encrypt(data.encode())

    def _decrypt_data(self, encrypted_data):
        """解密資料"""
        try:
            key = self._generate_key()
            f = Fernet(key)
            return f.decrypt(encrypted_data).decode()
        except:
            return None

    def get_current_license_info(self):
        """取得當前授權資訊"""
        if not os.path.exists(self.license_file):
            return None, "未找到授權檔案"

        try:
            with open(self.license_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self._decrypt_data(encrypted_data)
            if not decrypted_data:
                return None, "授權檔案已損壞"

            license_data = json.loads(decrypted_data)
            return license_data, None

        except Exception as e:
            return None, f"讀取授權失敗: {str(e)}"

    def can_upgrade_to_multi_device(self):
        """檢查是否可以升級到多設備授權"""
        license_data, error = self.get_current_license_info()

        if not license_data:
            return False, error

        # 只有單設備授權可以升級
        if license_data.get('type') != 'single':
            if license_data.get('type') == 'multi':
                return False, "當前已是多設備授權，無需升級"
            elif license_data.get('type') == 'upgraded':
                return False, "當前已是升級版多設備授權"
            else:
                return False, "未知的授權類型"

        # 檢查是否已過期
        try:
            expire_date = datetime.fromisoformat(license_data['expire_date'])
            if datetime.now() > expire_date:
                return False, "授權已過期，無法升級"
        except:
            return False, "授權日期格式錯誤"

        return True, license_data

    def parse_upgrade_license_key(self, upgrade_key):
        """解析升級授權碼"""
        try:
            # 升級授權碼格式: UPGRADE|original_hardware_id|new_max_devices|checksum
            decoded = base64.b64decode(upgrade_key.encode())
            license_data = decoded.decode()

            parts = license_data.split('|')
            if len(parts) != 4:
                return None, "升級授權碼格式錯誤"

            license_type, original_hardware_id, new_max_devices, checksum = parts

            if license_type != "UPGRADE":
                return None, "不是升級授權碼"

            # 驗證檢查碼
            expected_checksum = hashlib.sha256(
                f"UPGRADE_{original_hardware_id}_{new_max_devices}_{self.secret_salt}".encode()
            ).hexdigest()[:8]

            if checksum != expected_checksum:
                return None, "升級授權碼已損壞或被篡改"

            return {
                'type': 'upgrade',
                'original_hardware_id': original_hardware_id,
                'new_max_devices': int(new_max_devices)
            }, None

        except Exception as e:
            return None, f"升級授權碼解析失敗: {str(e)}"

    def apply_upgrade(self, upgrade_key):
        """應用升級授權"""
        # 檢查當前授權是否可以升級
        can_upgrade, current_license = self.can_upgrade_to_multi_device()
        if not can_upgrade:
            return False, current_license

        # 解析升級授權碼
        upgrade_info, error = self.parse_upgrade_license_key(upgrade_key)
        if not upgrade_info:
            return False, error

        # 驗證原始硬體ID是否匹配
        if upgrade_info['original_hardware_id'] != self.hardware_id:
            return False, "升級授權碼與當前設備不匹配"

        try:
            # 建立升級後的授權資訊
            upgraded_license = {
                'type': 'upgraded',  # 標記為升級版授權
                'original_type': 'single',
                'original_license_key': current_license['license_key'],
                'original_hardware_id': self.hardware_id,
                'original_activation_date': current_license['activation_date'],

                # 多設備授權資訊
                'license_id': str(uuid.uuid4()).replace('-', '')[:16].upper(),
                'max_devices': upgrade_info['new_max_devices'],
                'expire_date': current_license['expire_date'],  # 保持原有到期時間

                # 設備管理
                'registered_devices': [{
                    'hardware_id': self.hardware_id,
                    'device_name': self._get_device_name(),
                    'registration_date': current_license['activation_date'],  # 使用原始激活時間
                    'is_original_device': True  # 標記為原始設備
                }],

                # 升級資訊
                'upgrade_key': upgrade_key,
                'upgrade_date': datetime.now().isoformat(),
                'last_check': datetime.now().isoformat()
            }

            # 儲存升級後的授權
            encrypted_data = self._encrypt_data(json.dumps(upgraded_license))
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            expire_date = datetime.fromisoformat(current_license['expire_date'])
            remaining_days = (expire_date - datetime.now()).days

            return True, f"""升級成功！

原單設備授權已升級為多設備授權
- 最大設備數：{upgrade_info['new_max_devices']} 台
- 剩餘時間：{remaining_days} 天（保持原有授權時間）
- 到期日：{expire_date.strftime('%Y-%m-%d')}
- 當前設備已自動註冊為第一台設備

您現在可以在其他設備上使用相同的升級授權碼來註冊額外設備。"""

        except Exception as e:
            return False, f"升級處理失敗: {str(e)}"

    def register_additional_device(self, upgrade_key):
        """在其他設備上註冊升級授權"""
        # 解析升級授權碼
        upgrade_info, error = self.parse_upgrade_license_key(upgrade_key)
        if not upgrade_info:
            return False, error

        try:
            # 建立新設備的授權資訊
            device_license = {
                'type': 'upgraded_device',  # 標記為升級授權的額外設備
                'original_hardware_id': upgrade_info['original_hardware_id'],
                'current_hardware_id': self.hardware_id,
                'license_id': f"UPGRADE_{upgrade_info['original_hardware_id']}",
                'max_devices': upgrade_info['new_max_devices'],

                # 設備資訊
                'device_info': {
                    'hardware_id': self.hardware_id,
                    'device_name': self._get_device_name(),
                    'registration_date': datetime.now().isoformat(),
                    'is_original_device': False
                },

                'upgrade_key': upgrade_key,
                'registration_date': datetime.now().isoformat(),
                'last_check': datetime.now().isoformat()
            }

            # 儲存設備授權
            encrypted_data = self._encrypt_data(json.dumps(device_license))
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            return True, f"""設備註冊成功！

此設備已成功註冊到升級授權
- 原始授權設備：{upgrade_info['original_hardware_id']}
- 當前設備：{self.hardware_id}
- 最大設備數：{upgrade_info['new_max_devices']} 台

請確保不超過授權的設備數量限制。"""

        except Exception as e:
            return False, f"設備註冊失敗: {str(e)}"

    def _get_device_name(self):
        """取得設備名稱"""
        import platform
        return f"{platform.node()}_{platform.system()}"

    def check_upgraded_license_status(self):
        """檢查升級授權狀態"""
        license_data, error = self.get_current_license_info()
        if not license_data:
            return False, error

        if license_data.get('type') == 'upgraded':
            # 原始設備的升級授權
            return self._check_original_upgraded_license(license_data)
        elif license_data.get('type') == 'upgraded_device':
            # 額外設備的升級授權
            return self._check_additional_device_license(license_data)
        else:
            return False, "不是升級授權"

    def _check_original_upgraded_license(self, license_data):
        """檢查原始設備的升級授權"""
        try:
            # 檢查到期時間（使用原始授權的到期時間）
            expire_date = datetime.fromisoformat(license_data['expire_date'])
            now = datetime.now()

            if now > expire_date:
                return False, f"授權已於 {expire_date.strftime('%Y-%m-%d')} 過期"

            # 更新最後檢查時間
            license_data['last_check'] = now.isoformat()
            encrypted_data = self._encrypt_data(json.dumps(license_data))
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            remaining_days = (expire_date - now).days
            registered_devices = len(license_data.get('registered_devices', []))

            return True, {
                'type': 'upgraded',
                'expire_date': expire_date,
                'remaining_days': remaining_days,
                'max_devices': license_data['max_devices'],
                'registered_devices': registered_devices,
                'is_original_device': True,
                'original_activation_date': license_data['original_activation_date']
            }

        except Exception as e:
            return False, f"升級授權檢查失敗: {str(e)}"

    def _check_additional_device_license(self, license_data):
        """檢查額外設備的升級授權"""
        try:
            # 額外設備需要驗證與原始設備的關聯
            # 這裡可以加入線上驗證邏輯，或使用簡化的本地驗證

            now = datetime.now()

            # 簡化驗證：檢查註冊時間是否合理（不超過3年前）
            registration_date = datetime.fromisoformat(license_data['registration_date'])
            if (now - registration_date).days > 3 * 365:
                return False, "設備註冊已過期，請重新註冊"

            # 更新最後檢查時間
            license_data['last_check'] = now.isoformat()
            encrypted_data = self._encrypt_data(json.dumps(license_data))
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            return True, {
                'type': 'upgraded_device',
                'max_devices': license_data['max_devices'],
                'is_original_device': False,
                'registration_date': license_data['registration_date'],
                'original_hardware_id': license_data['original_hardware_id']
            }

        except Exception as e:
            return False, f"額外設備授權檢查失敗: {str(e)}"

