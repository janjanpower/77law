"""
硬體工具模組 - 統一硬體ID相關功能
"""
import hashlib

import platform
import uuid


class HardwareUtils:
    """硬體工具類"""

    @staticmethod
    def get_hardware_id() -> str:
        """
        取得硬體ID - 統一實作

        Returns:
            str: 16位硬體ID
        """
        try:
            mac = uuid.getnode()
            computer_name = platform.node()
            unique_string = f"{mac}_{computer_name}"
            return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
        except:
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]

    @staticmethod
    def get_device_name() -> str:
        """
        取得設備名稱

        Returns:
            str: 設備名稱
        """
        return f"{platform.node()}_{platform.system()}"

    @staticmethod
    def get_system_info() -> dict:
        """
        取得系統資訊

        Returns:
            dict: 系統資訊
        """
        return {
            'computer_name': platform.node(),
            'system': platform.system(),
            'release': platform.release(),
            'hardware_id': HardwareUtils.get_hardware_id()
        }