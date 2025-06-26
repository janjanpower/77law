import hashlib
import base64
from datetime import datetime

class UpgradeLicenseGenerator:
    """升級授權碼生成器"""

    def __init__(self):
        self.secret_salt = "CaseManagement2024"

    def generate_upgrade_license(self, original_hardware_id, new_max_devices):
        """
        生成升級授權碼

        Args:
            original_hardware_id: 原始設備的硬體ID
            new_max_devices: 升級後的最大設備數

        Returns:
            tuple: (升級授權碼, 升級資訊)
        """
        # 生成檢查碼
        checksum = hashlib.sha256(
            f"UPGRADE_{original_hardware_id}_{new_max_devices}_{self.secret_salt}".encode()
        ).hexdigest()[:8]

        # 組合升級授權資料: UPGRADE|original_hardware_id|new_max_devices|checksum
        license_data = f"UPGRADE|{original_hardware_id}|{new_max_devices}|{checksum}"

        # Base64編碼
        upgrade_key = base64.b64encode(license_data.encode()).decode()

        upgrade_info = {
            'type': 'upgrade',
            'original_hardware_id': original_hardware_id,
            'new_max_devices': new_max_devices,
            'generated_date': datetime.now().isoformat()
        }

        return upgrade_key, upgrade_info

