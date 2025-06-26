"""
📍 統一主程式（客戶使用）
整合專案授權系統，使用統一樣式
"""

import base64
import hashlib
import json
import os
import sys
import tkinter as tk
import uuid
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from views.base_window import BaseWindow
from views.dialogs import UnifiedMessageDialog


def fix_import_path():
    """修正模組導入路徑"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    if base_path not in sys.path:
        sys.path.insert(0, base_path)

    # 確保可以導入自訂義模組
    try:
        from views.base_window import BaseWindow
        from views.dialogs import UnifiedMessageDialog
        from config.settings import AppConfig
        globals()['BaseWindow'] = BaseWindow
        globals()['UnifiedMessageDialog'] = UnifiedMessageDialog
        globals()['AppConfig'] = AppConfig
    except ImportError as e:
        print(f"警告：無法導入自訂義模組，將使用預設樣式: {e}")
        # 設定預設值，避免程式崩潰
        globals()['BaseWindow'] = object
        globals()['UnifiedMessageDialog'] = None
        globals()['AppConfig'] = None

# 修正路徑並嘗試導入專案模組
fix_import_path()

try:
    from utils.hardware_utils import HardwareUtils
    from config.settings import AppConfig
    from views.dialogs import UnifiedMessageDialog
    USE_PROJECT_STYLE = True
except ImportError:
    # 如果無法導入專案模組，使用獨立實作
    import platform

    class HardwareUtils:
        @staticmethod
        def get_hardware_id():
            try:
                mac = uuid.getnode()
                computer_name = platform.node()
                unique_string = f"{mac}_{computer_name}"
                return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
            except:
                return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]

        @staticmethod
        def get_device_name():
            return f"{platform.node()}_{platform.system()}"

    class AppConfig:
        COLORS = {
            'window_bg': '#383838',
            'title_bg': '#8B8B8B',
            'title_fg': 'white',
            'button_bg': '#8B8B8B',
            'button_fg': 'white',
            'text_color': 'white'
        }
        FONTS = {
            'title': ('Microsoft JhengHei', 11, 'bold'),
            'button': ('Microsoft JhengHei', 9),
            'text': ('Microsoft JhengHei', 9)
        }

    USE_PROJECT_STYLE = False
class UnifiedLicenseManager:
    """統一授權管理器"""

    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.license_file = os.path.join(script_dir, ".license_data")
        self.secret_salt = "CaseManagement2024"
        self.hardware_id = HardwareUtils.get_hardware_id()  # 使用統一工具類

    def _get_device_name(self):
        """取得設備名稱"""
        return HardwareUtils.get_device_name()  # 使用統一工具類

    def _get_hardware_id(self):
        """取得硬體ID"""
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

    def parse_license_key(self, license_key):
        """解析授權碼並判斷類型"""
        try:
            decoded = base64.b64decode(license_key.encode())
            license_data = decoded.decode()
            parts = license_data.split('|')

            if len(parts) < 3:
                return None, "授權碼格式錯誤"

            license_type = parts[0]

            if license_type == "SINGLE":
                # 單設備授權: SINGLE|hardware_id|expire_date|checksum
                if len(parts) != 4:
                    return None, "單設備授權碼格式錯誤"

                _, hardware_id, expire_date_str, checksum = parts
                return {
                    'type': 'single',
                    'hardware_id': hardware_id,
                    'expire_date': expire_date_str,
                    'checksum': checksum
                }, None

            elif license_type == "MULTI":
                # 多設備授權: MULTI|license_id|max_devices|expire_date|checksum
                if len(parts) != 5:
                    return None, "多設備授權碼格式錯誤"

                _, license_id, max_devices, expire_date_str, checksum = parts
                return {
                    'type': 'multi',
                    'license_id': license_id,
                    'max_devices': int(max_devices),
                    'expire_date': expire_date_str,
                    'checksum': checksum
                }, None

            elif license_type == "UPGRADE":
                # 升級授權: UPGRADE|original_hardware_id|new_max_devices|checksum
                if len(parts) != 4:
                    return None, "升級授權碼格式錯誤"

                _, original_hardware_id, new_max_devices, checksum = parts
                return {
                    'type': 'upgrade',
                    'original_hardware_id': original_hardware_id,
                    'new_max_devices': int(new_max_devices),
                    'checksum': checksum
                }, None

            else:
                return None, "未知的授權類型"

        except Exception as e:
            return None, f"授權碼解析失敗: {str(e)}"

    def validate_and_activate_license(self, license_key):
        """驗證並激活授權"""
        license_info, error = self.parse_license_key(license_key)
        if not license_info:
            return False, error

        if license_info['type'] == 'single':
            return self._activate_single_license(license_key, license_info)
        elif license_info['type'] == 'multi':
            return self._activate_multi_license(license_key, license_info)
        elif license_info['type'] == 'upgrade':
            return self._activate_upgrade_license(license_key, license_info)
        else:
            return False, "未知的授權類型"

    def _activate_single_license(self, license_key, license_info):
        """激活單設備授權"""
        # 驗證硬體ID
        if license_info['hardware_id'] != self.hardware_id:
            return False, "授權碼與此電腦不匹配"

        # 驗證檢查碼
        expected_checksum = hashlib.sha256(
            f"SINGLE_{license_info['hardware_id']}_{license_info['expire_date']}_{self.secret_salt}".encode()
        ).hexdigest()[:8]

        if license_info['checksum'] != expected_checksum:
            return False, "授權碼已損壞或被篡改"

        # 驗證時間
        try:
            expire_date = datetime.fromisoformat(license_info['expire_date'])
            if datetime.now() > expire_date:
                return False, f"授權已於 {expire_date.strftime('%Y-%m-%d')} 過期"
        except:
            return False, "授權日期格式錯誤"

        # 儲存授權資訊
        license_data = {
            'type': 'single',
            'license_key': license_key,
            'hardware_id': self.hardware_id,
            'expire_date': license_info['expire_date'],
            'activation_date': datetime.now().isoformat(),
            'last_check': datetime.now().isoformat()
        }

        try:
            encrypted_data = self._encrypt_data(json.dumps(license_data))
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            return True, f"✅ 單設備授權激活成功！\n到期日：{expire_date.strftime('%Y-%m-%d')}"
        except Exception as e:
            return False, f"授權儲存失敗: {str(e)}"

    def _activate_multi_license(self, license_key, license_info):
        """激活多設備授權"""
        # 驗證檢查碼
        expected_checksum = hashlib.sha256(
            f"MULTI_{license_info['license_id']}_{license_info['max_devices']}_{license_info['expire_date']}_{self.secret_salt}".encode()
        ).hexdigest()[:8]

        if license_info['checksum'] != expected_checksum:
            return False, "授權碼已損壞或被篡改"

        # 驗證時間
        try:
            expire_date = datetime.fromisoformat(license_info['expire_date'])
            if datetime.now() > expire_date:
                return False, f"授權已於 {expire_date.strftime('%Y-%m-%d')} 過期"
        except:
            return False, "授權日期格式錯誤"

        # 儲存授權資訊
        license_data = {
            'type': 'multi',
            'license_key': license_key,
            'license_id': license_info['license_id'],
            'max_devices': license_info['max_devices'],
            'expire_date': license_info['expire_date'],
            'current_device': {
                'hardware_id': self.hardware_id,
                'device_name': self._get_device_name(),
                'registration_date': datetime.now().isoformat()
            },
            'activation_date': datetime.now().isoformat(),
            'last_check': datetime.now().isoformat()
        }

        try:
            encrypted_data = self._encrypt_data(json.dumps(license_data))
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            return True, f"✅ 多設備授權激活成功！\n最大設備數：{license_info['max_devices']} 台\n到期日：{expire_date.strftime('%Y-%m-%d')}"
        except Exception as e:
            return False, f"授權儲存失敗: {str(e)}"

    def _activate_upgrade_license(self, license_key, license_info):
        """激活升級授權"""
        # 驗證檢查碼
        expected_checksum = hashlib.sha256(
            f"UPGRADE_{license_info['original_hardware_id']}_{license_info['new_max_devices']}_{self.secret_salt}".encode()
        ).hexdigest()[:8]

        if license_info['checksum'] != expected_checksum:
            return False, "升級授權碼已損壞或被篡改"

        # 檢查是否為原設備或新設備
        if license_info['original_hardware_id'] == self.hardware_id:
            # 原設備升級
            return self._upgrade_original_device(license_key, license_info)
        else:
            # 新設備註冊
            return self._register_additional_device(license_key, license_info)

    def _upgrade_original_device(self, license_key, license_info):
        """原設備升級處理"""
        # 檢查是否有現有的單設備授權
        current_license = self._get_current_license()
        if current_license and current_license.get('type') == 'single':
            # 保持原有到期時間
            expire_date_str = current_license['expire_date']
            original_activation = current_license['activation_date']
        else:
            # 如果沒有現有授權，設定一個合理的到期時間（比如1年）
            expire_date_str = (datetime.now() + timedelta(days=365)).isoformat()
            original_activation = datetime.now().isoformat()

        # 建立升級後的授權資訊
        license_data = {
            'type': 'upgraded',
            'license_key': license_key,
            'original_hardware_id': license_info['original_hardware_id'],
            'max_devices': license_info['new_max_devices'],
            'expire_date': expire_date_str,
            'is_original_device': True,
            'original_activation_date': original_activation,
            'upgrade_date': datetime.now().isoformat(),
            'last_check': datetime.now().isoformat()
        }

        try:
            encrypted_data = self._encrypt_data(json.dumps(license_data))
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            expire_date = datetime.fromisoformat(expire_date_str)
            remaining_days = (expire_date - datetime.now()).days

            return True, f"🚀 升級成功！\n\n您的單設備授權已升級為多設備授權\n• 最大設備數：{license_info['new_max_devices']} 台\n• 剩餘時間：{remaining_days} 天\n• 到期日：{expire_date.strftime('%Y-%m-%d')}\n\n您現在可以在其他設備上使用相同的升級授權碼。"
        except Exception as e:
            return False, f"升級處理失敗: {str(e)}"

    def _register_additional_device(self, license_key, license_info):
        """註冊額外設備"""
        license_data = {
            'type': 'upgraded_device',
            'license_key': license_key,
            'original_hardware_id': license_info['original_hardware_id'],
            'current_hardware_id': self.hardware_id,
            'max_devices': license_info['new_max_devices'],
            'device_info': {
                'hardware_id': self.hardware_id,
                'device_name': self._get_device_name(),
                'registration_date': datetime.now().isoformat()
            },
            'is_original_device': False,
            'registration_date': datetime.now().isoformat(),
            'last_check': datetime.now().isoformat()
        }

        try:
            encrypted_data = self._encrypt_data(json.dumps(license_data))
            with open(self.license_file, 'wb') as f:
                f.write(encrypted_data)

            return True, f"✅ 設備註冊成功！\n\n此設備已註冊到升級授權\n• 原始設備：{license_info['original_hardware_id']}\n• 當前設備：{self.hardware_id}\n• 最大設備數：{license_info['new_max_devices']} 台\n\n請確保不超過授權的設備數量限制。"
        except Exception as e:
            return False, f"設備註冊失敗: {str(e)}"

    def _get_current_license(self):
        """取得當前授權資訊"""
        if not os.path.exists(self.license_file):
            return None

        try:
            with open(self.license_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self._decrypt_data(encrypted_data)
            if not decrypted_data:
                return None

            return json.loads(decrypted_data)
        except:
            return None

    def _get_device_name(self):
        """取得設備名稱"""
        import platform
        return f"{platform.node()}_{platform.system()}"

    def check_license_status(self):
        """檢查授權狀態"""
        current_license = self._get_current_license()
        if not current_license:
            return False, "未找到授權檔案，請輸入授權碼"

        license_type = current_license.get('type')

        if license_type == 'single':
            return self._check_single_license(current_license)
        elif license_type == 'multi':
            return self._check_multi_license(current_license)
        elif license_type == 'upgraded':
            return self._check_upgraded_license(current_license)
        elif license_type == 'upgraded_device':
            return self._check_upgraded_device_license(current_license)
        else:
            return False, "未知的授權類型"

    def _check_single_license(self, license_data):
        """檢查單設備授權"""
        if license_data['hardware_id'] != self.hardware_id:
            return False, "授權與此電腦不匹配"

        try:
            expire_date = datetime.fromisoformat(license_data['expire_date'])
            if datetime.now() > expire_date:
                return False, f"授權已於 {expire_date.strftime('%Y-%m-%d')} 過期"

            remaining_days = (expire_date - datetime.now()).days
            return True, {
                'type': 'single',
                'expire_date': expire_date,
                'remaining_days': remaining_days
            }
        except:
            return False, "授權日期格式錯誤"

    def _check_multi_license(self, license_data):
        """檢查多設備授權"""
        try:
            expire_date = datetime.fromisoformat(license_data['expire_date'])
            if datetime.now() > expire_date:
                return False, f"授權已於 {expire_date.strftime('%Y-%m-%d')} 過期"

            remaining_days = (expire_date - datetime.now()).days
            return True, {
                'type': 'multi',
                'expire_date': expire_date,
                'remaining_days': remaining_days,
                'max_devices': license_data['max_devices']
            }
        except:
            return False, "授權日期格式錯誤"

    def _check_upgraded_license(self, license_data):
        """檢查升級授權（原設備）"""
        try:
            expire_date = datetime.fromisoformat(license_data['expire_date'])
            if datetime.now() > expire_date:
                return False, f"授權已於 {expire_date.strftime('%Y-%m-%d')} 過期"

            remaining_days = (expire_date - datetime.now()).days
            return True, {
                'type': 'upgraded',
                'expire_date': expire_date,
                'remaining_days': remaining_days,
                'max_devices': license_data['max_devices'],
                'is_original_device': True
            }
        except:
            return False, "授權日期格式錯誤"

    def _check_upgraded_device_license(self, license_data):
        """檢查升級授權（額外設備）"""
        # 額外設備的授權檢查相對簡單，主要檢查註冊是否有效
        try:
            registration_date = datetime.fromisoformat(license_data['registration_date'])
            # 檢查註冊是否在合理時間範圍內（比如3年內）
            if (datetime.now() - registration_date).days > 3 * 365:
                return False, "設備註冊已過期，請重新註冊"

            return True, {
                'type': 'upgraded_device',
                'max_devices': license_data['max_devices'],
                'is_original_device': False,
                'original_hardware_id': license_data['original_hardware_id']
            }
        except:
            return False, "設備註冊資訊錯誤"

class UnifiedLicenseDialog(BaseWindow):
    """統一授權對話框"""

    def __init__(self, parent=None):
        self.result = None
        self.license_key = ""

        super().__init__(title="🎫 軟體授權驗證", width=600, height=500, resizable=False, parent=parent)

    def _create_layout(self):
        """建立授權對話框佈局"""
        super()._create_layout()
        self._create_license_content()

    def _create_license_content(self):
        """建立授權內容 - 使用統一樣式"""
        # 歡迎標籤
        welcome_label = tk.Label(
            self.content_frame,
            text="歡迎使用案件管理系統！",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['welcome']
        )
        welcome_label.pack(pady=20)

        # 說明文字
        info_text = """本系統支援三種授權類型，請輸入您的授權碼：

💻 單設備授權 - 僅限一台電腦使用
🖥️🖥️🖥️ 多設備授權 - 可在多台電腦使用
🚀 升級授權 - 單設備用戶升級專用

系統會自動識別您的授權類型並進行相應處理。"""

        info_label = tk.Label(
            self.content_frame,
            text=info_text,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            justify='left',
            wraplength=650
        )
        info_label.pack(pady=10, padx=20)

        # 授權碼輸入區域
        input_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        input_frame.pack(pady=20)

        tk.Label(
            input_frame,
            text="請輸入授權碼：",
            bg=AppConfig.COLORS['window_bg'],
            fg='#2196F3',
            font=AppConfig.FONTS['button']
        ).pack(anchor='w')

        self.license_entry = tk.Entry(
            input_frame,
            width=70,
            font=AppConfig.FONTS['text'],
            bg='white',
            fg='black'
        )
        self.license_entry.pack(pady=10)
        self.license_entry.focus()

        # 按鈕區域
        self._create_license_buttons(input_frame)

        # 綁定Enter鍵
        self.license_entry.bind('<Return>', lambda e: self._validate_license())

    def _create_license_buttons(self, parent):
        """建立授權按鈕"""
        button_frame = tk.Frame(parent, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(pady=30)

        # 驗證授權按鈕
        verify_btn = tk.Button(
            button_frame,
            text='🎫 驗證授權',
            command=self._validate_license,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=15,
            height=2
        )
        verify_btn.pack(side='left', padx=10)

        # 取得硬體ID按鈕
        hardware_btn = tk.Button(
            button_frame,
            text='🔧 取得硬體ID',
            command=self._show_hardware_info,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=15,
            height=2
        )
        hardware_btn.pack(side='left', padx=10)

        # 取消按鈕
        cancel_btn = tk.Button(
            button_frame,
            text='❌ 取消',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=15,
            height=2
        )
        cancel_btn.pack(side='left', padx=10)

    def _validate_license(self):
        """驗證授權碼"""
        license_key = self.license_entry.get().strip()

        if not license_key:
            UnifiedMessageDialog.show_error(self.window, "請輸入授權碼")
            return

        try:
            license_manager = UnifiedLicenseManager()
            success, message = license_manager.validate_and_activate_license(license_key)

            if success:
                UnifiedMessageDialog.show_success(self.window, message)
                self.result = True
                self.license_key = license_key
                self.close()
            else:
                UnifiedMessageDialog.show_error(self.window, message)

        except Exception as e:
            UnifiedMessageDialog.show_error(self.window, f"授權驗證過程發生錯誤：{str(e)}")

    def _show_hardware_info(self):
        """顯示硬體ID資訊"""
        try:
            license_manager = UnifiedLicenseManager()
            hardware_id = license_manager.hardware_id

            info_text = f"""🖥️ 您的硬體ID：{hardware_id}

如需申請單設備授權，請將此硬體ID提供給供應商
"""

            # 使用統一的訊息對話框
            UnifiedMessageDialog.show_info(self.window, info_text, "🔧 硬體ID資訊")

        except Exception as e:
            UnifiedMessageDialog.show_error(self.window, f"無法取得硬體ID：{str(e)}")

    def _cancel(self):
        """取消"""
        self.result = False
        self.window.destroy()

def check_license():
    """檢查授權狀態"""
    try:
        license_manager = UnifiedLicenseManager()
        is_valid, result = license_manager.check_license_status()

        if is_valid:
            info = result
            license_type = info['type']

            # 根據授權類型顯示不同的提醒
            if 'remaining_days' in info and info['remaining_days'] <= 30:
                type_display = {
                    'single': '單設備授權',
                    'multi': '多設備授權',
                    'upgraded': '升級多設備授權'
                }.get(license_type, '授權')

                warning_msg = f"⚠️ {type_display}提醒\n\n您的授權將在 {info['remaining_days']} 天後到期"

                if 'expire_date' in info:
                    warning_msg += f"\n到期日：{info['expire_date'].strftime('%Y-%m-%d')}"

                if 'max_devices' in info:
                    warning_msg += f"\n授權設備數：{info['max_devices']} 台"

                warning_msg += "\n\n請及時聯繫供應商續期"

                # 建立臨時父視窗用於顯示統一樣式對話框
                temp_root = tk.Tk()
                temp_root.withdraw()

                UnifiedMessageDialog.show_warning(temp_root, warning_msg, "授權提醒")
                temp_root.destroy()

            return True, "授權有效"
        else:
            return False, result

    except Exception as e:
        return False, f"授權檢查失敗：{str(e)}"

def show_license_input():
    """顯示授權輸入對話框"""
    dialog = UnifiedLicenseDialog()
    dialog.window.wait_window()
    return dialog.result

# main_unified.py - 新增授權檢查對話框類別

class LicenseCheckDialog(BaseWindow):
    """授權檢查對話框"""

    def __init__(self, message):
        self.message = message
        self.result = False

        super().__init__(title="🎫 授權檢查", width=450, height=250, resizable=False, parent=None)

    def _create_layout(self):
        """建立對話框佈局"""
        super()._create_layout()
        self._create_check_content()

    def _create_check_content(self):
        """建立授權檢查內容"""
        # 主容器
        main_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 訊息顯示
        message_label = tk.Label(
            main_frame,
            text=self.message,
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['text'],
            wraplength=400,
            justify='center'
        )
        message_label.pack(expand=True, pady=(0, 10))

        # 詢問文字
        question_label = tk.Label(
            main_frame,
            text="是否要輸入授權碼？",
            bg=AppConfig.COLORS['window_bg'],
            fg='#4CAF50',
            font=AppConfig.FONTS['button']
        )
        question_label.pack(pady=(0, 20))

        # 按鈕區域
        button_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        button_frame.pack(side='bottom')

        # 是按鈕
        yes_btn = tk.Button(
            button_frame,
            text='是',
            command=self._on_yes,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=1
        )
        yes_btn.pack(side='left', padx=5)

        # 否按鈕
        no_btn = tk.Button(
            button_frame,
            text='否',
            command=self._on_no,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=8,
            height=1
        )
        no_btn.pack(side='left', padx=5)

    def _on_yes(self):
        """是按鈕事件"""
        self.result = True
        self.close()

    def _on_no(self):
        """否按鈕事件"""
        self.result = False
        self.close()

def show_license_check_dialog(message):
    """顯示授權檢查對話框"""
    dialog = LicenseCheckDialog(message)
    dialog.window.wait_window()
    return dialog.result

# main_unified.py - 新增退出對話框類別

class ExitDialog(BaseWindow):
    """程式退出對話框"""

    def __init__(self):
        super().__init__(title="提示", width=350, height=200, resizable=False, parent=None)

    def _create_layout(self):
        """建立對話框佈局"""
        super()._create_layout()
        self._create_exit_content()

    def _create_exit_content(self):
        """建立退出內容"""
        # 主容器
        main_frame = tk.Frame(self.content_frame, bg=AppConfig.COLORS['window_bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # 圖示和訊息
        icon_frame = tk.Frame(main_frame, bg=AppConfig.COLORS['window_bg'])
        icon_frame.pack(expand=True)

        # 退出圖示
        icon_label = tk.Label(
            icon_frame,
            text="👋",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=('Arial', 24)
        )
        icon_label.pack(pady=(0, 10))

        # 退出訊息
        message_label = tk.Label(
            icon_frame,
            text="程式已退出",
            bg=AppConfig.COLORS['window_bg'],
            fg=AppConfig.COLORS['text_color'],
            font=AppConfig.FONTS['button']
        )
        message_label.pack()

        # 確定按鈕
        ok_btn = tk.Button(
            main_frame,
            text='確定',
            command=self.close,
            bg=AppConfig.COLORS['button_bg'],
            fg=AppConfig.COLORS['button_fg'],
            font=AppConfig.FONTS['button'],
            width=10,
            height=1
        )
        ok_btn.pack(side='bottom', pady=(20, 0))

def show_exit_dialog():
    """顯示退出對話框"""
    dialog = ExitDialog()
    dialog.window.wait_window()

def main():
    """統一主程式入口"""
    try:
        # 修正模組路徑
        fix_import_path()

        # 檢查授權
        is_valid, message = check_license()

        if not is_valid:
            # 使用自訂義確認對話框
            result = show_license_check_dialog(message)

            if result:
                # 顯示授權輸入對話框
                if not show_license_input():
                    show_exit_dialog()
                    return

                # 重新檢查授權
                is_valid, new_message = check_license()
                if not is_valid:
                    # 建立臨時父視窗用於錯誤顯示
                    temp_root = tk.Tk()
                    temp_root.withdraw()
                    UnifiedMessageDialog.show_error(temp_root, f"授權驗證失敗：{new_message}")
                    temp_root.destroy()
                    return
            else:
                show_exit_dialog()
                return

        # 授權有效，載入主程式
        try:
            from views.main_window import MainWindow
            app = MainWindow()
            app.run()
        except ImportError:
            # 如果找不到主程式，顯示成功訊息
            temp_root = tk.Tk()
            temp_root.withdraw()
            UnifiedMessageDialog.show_success(
                temp_root,
                "授權驗證成功！\n\n您現在可以正常使用軟體了。\n\n（註：此為演示版本，請將此檔案與您的主程式整合）"
            )
            temp_root.destroy()

    except Exception as e:
        print(f"程式執行錯誤: {e}")
        import traceback
        traceback.print_exc()
        input("按任意鍵退出...")

if __name__ == "__main__":
    main()