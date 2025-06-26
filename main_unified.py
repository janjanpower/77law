"""
📍 3. 統一主程式（客戶使用）
客戶執行這個程式，系統自動識別授權類型
"""

import base64
import hashlib
import json
import os
import sys
import tkinter as tk
import uuid
from datetime import datetime, timedelta
from tkinter import messagebox

from cryptography.fernet import Fernet


def fix_import_path():
    """修正模組導入路徑"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    if base_path not in sys.path:
        sys.path.insert(0, base_path)

class UnifiedLicenseManager:
    """統一授權管理器"""

    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.license_file = os.path.join(script_dir, ".license_data")
        self.secret_salt = "CaseManagement2024"
        self.hardware_id = self._get_hardware_id()

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

class UnifiedLicenseDialog:
    """統一授權對話框"""

    def __init__(self, parent=None):
        self.result = None
        self.license_key = ""

        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("🎫 軟體授權驗證")
        self.window.geometry("700x600")
        self.window.resizable(False, False)

        # 置中顯示
        x = (self.window.winfo_screenwidth() // 2) - 350
        y = (self.window.winfo_screenheight() // 2) - 300
        self.window.geometry(f"700x1000+{x}+{y}")

        self._create_ui()

        if parent:
            self.window.transient(parent)
            self.window.grab_set()

    def _create_ui(self):
        """建立UI介面"""
        # 標題
        title_label = tk.Label(self.window, text="🎫 案件管理系統 - 授權驗證",
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=20)

        # 說明文字
        info_text = """
歡迎使用案件管理系統！

本系統支援三種授權類型，請輸入您的授權碼：

💻 單設備授權
   • 僅限一台電腦使用
   • 與硬體綁定，安全性高
   • 適合個人用戶

🖥️🖥️🖥️ 多設備授權
   • 可在多台電腦使用
   • 支援團隊協作
   • 靈活設備管理

🚀 升級授權
   • 單設備用戶升級專用
   • 保持原有授權時間
   • 平滑升級體驗

系統會自動識別您的授權類型並進行相應處理。
        """

        info_label = tk.Label(self.window, text=info_text, font=("Arial", 11),
                             justify='left', wraplength=650)
        info_label.pack(pady=10, padx=20)

        # 授權碼輸入區域
        input_frame = tk.Frame(self.window)
        input_frame.pack(pady=20)

        tk.Label(input_frame, text="請輸入授權碼：", font=("Arial", 12),
                fg='#2196F3').pack(anchor='w')

        self.license_entry = tk.Entry(input_frame, width=70, font=("Arial", 11))
        self.license_entry.pack(pady=10)
        self.license_entry.focus()

        # 授權碼格式示例
        example_frame = tk.LabelFrame(self.window, text="授權碼格式示例", font=("Arial", 10))
        example_frame.pack(pady=10, padx=40, fill='x')

        examples = [
            ("💻 單設備", "U0lOR0xFfEFCQ0RFRkdIMTIzNHwuLi4="),
            ("🖥️ 多設備", "TUNMVElmQUJDREVGRzEyMzR8M3wuLi4="),
            ("🚀 升級", "VVBHUkFERXxBQkNERUZHSDF8NXwuLi4=")
        ]

        for i, (type_name, example) in enumerate(examples):
            row_frame = tk.Frame(example_frame)
            row_frame.pack(fill='x', padx=10, pady=2)

            tk.Label(row_frame, text=f"{type_name}：",
                    font=("Arial", 9), width=8).pack(side='left')
            tk.Label(row_frame, text=example,
                    font=("Arial", 9), fg='blue').pack(side='left')

        # 按鈕區域
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=30)

        tk.Button(button_frame, text="🎫 驗證授權", command=self._validate_license,
                 width=15, height=2, font=("Arial", 12),
                 bg='#4CAF50', fg='white').pack(side='left', padx=10)

        tk.Button(button_frame, text="🔧 取得硬體ID", command=self._show_hardware_info,
                 width=15, height=2, font=("Arial", 12)).pack(side='left', padx=10)

        tk.Button(button_frame, text="❌ 取消", command=self._cancel,
                 width=15, height=2, font=("Arial", 12)).pack(side='left', padx=10)

        # 綁定Enter鍵
        self.license_entry.bind('<Return>', lambda e: self._validate_license())

    def _validate_license(self):
        """驗證授權碼"""
        license_key = self.license_entry.get().strip()

        if not license_key:
            messagebox.showerror("❌ 錯誤", "請輸入授權碼")
            return

        try:
            license_manager = UnifiedLicenseManager()
            success, message = license_manager.validate_and_activate_license(license_key)

            if success:
                messagebox.showinfo("✅ 授權成功", message)
                self.result = True
                self.license_key = license_key
                self.window.destroy()
            else:
                messagebox.showerror("❌ 授權失敗", message)

        except Exception as e:
            messagebox.showerror("❌ 錯誤", f"授權驗證過程發生錯誤：{str(e)}")

    def _show_hardware_info(self):
        """顯示硬體ID資訊"""
        try:
            license_manager = UnifiedLicenseManager()
            hardware_id = license_manager.hardware_id

            info_text = f"""
🖥️ 您的硬體ID：{hardware_id}

💡 使用說明：
• 如需申請單設備授權，請將此硬體ID提供給供應商
• 如需升級授權，也需要提供此硬體ID
• 多設備授權不需要硬體ID

📋 您也可以執行「硬體ID查詢工具」來取得此資訊
            """

            # 建立硬體ID顯示視窗
            hw_window = tk.Toplevel(self.window)
            hw_window.title("🔧 硬體ID資訊")
            hw_window.geometry("500x300")
            hw_window.resizable(False, False)

            # 置中顯示
            x = (hw_window.winfo_screenwidth() // 2) - 250
            y = (hw_window.winfo_screenheight() // 2) - 150
            hw_window.geometry(f"500x300+{x}+{y}")

            tk.Label(hw_window, text=info_text, font=("Arial", 11),
                    justify='left').pack(pady=20, padx=20)

            # 硬體ID複製區域
            copy_frame = tk.Frame(hw_window)
            copy_frame.pack(pady=10)

            id_entry = tk.Entry(copy_frame, width=25, font=("Arial", 12, "bold"),
                               justify='center', state='readonly', bg='#f0f0f0')
            id_entry.pack(side='left', padx=5)

            id_entry.config(state='normal')
            id_entry.insert(0, hardware_id)
            id_entry.config(state='readonly')

            def copy_hardware_id():
                hw_window.clipboard_clear()
                hw_window.clipboard_append(hardware_id)
                messagebox.showinfo("✅ 成功", "硬體ID已複製到剪貼簿", parent=hw_window)

            tk.Button(copy_frame, text="📋 複製", command=copy_hardware_id,
                     font=("Arial", 10)).pack(side='left', padx=5)

            tk.Button(hw_window, text="關閉", command=hw_window.destroy,
                     width=10, font=("Arial", 11)).pack(pady=20)

        except Exception as e:
            messagebox.showerror("❌ 錯誤", f"無法取得硬體ID：{str(e)}")

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

                root = tk.Tk()
                root.withdraw()
                messagebox.showwarning("授權提醒", warning_msg)
                root.destroy()

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

def main():
    """統一主程式入口"""
    try:
        # 修正模組路徑
        fix_import_path()

        # 檢查授權
        is_valid, message = check_license()

        if not is_valid:
            # 建立臨時根視窗
            temp_root = tk.Tk()
            temp_root.withdraw()

            # 顯示授權狀態訊息
            result = messagebox.askyesno("🎫 授權檢查",
                f"{message}\n\n是否要輸入授權碼？",
                parent=temp_root)

            if result:
                # 顯示授權輸入對話框
                if not show_license_input():
                    messagebox.showinfo("提示", "程式將退出", parent=temp_root)
                    temp_root.destroy()
                    return

                # 重新檢查授權
                is_valid, new_message = check_license()
                if not is_valid:
                    messagebox.showerror("❌ 錯誤", f"授權驗證失敗：{new_message}", parent=temp_root)
                    temp_root.destroy()
                    return
            else:
                messagebox.showinfo("提示", "程式將退出", parent=temp_root)
                temp_root.destroy()
                return

            temp_root.destroy()

        # 授權有效，載入主程式
        try:
            # 嘗試載入您的主程式
            from views.main_window import MainWindow
            app = MainWindow()
            app.run()
        except ImportError:
            # 如果找不到主程式，顯示成功訊息
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("✅ 授權成功",
                "授權驗證成功！\n\n您現在可以正常使用軟體了。\n\n（註：此為演示版本，請將此檔案與您的主程式整合）")
            root.destroy()

    except Exception as e:
        print(f"程式執行錯誤: {e}")
        import traceback
        traceback.print_exc()
        input("按任意鍵退出...")

if __name__ == "__main__":
    main()