# 在Python控制台測試
try:
    from utils.excel import ExcelHandler
    print("✅ 新模組載入成功")
except ImportError as e:
    print(f"❌ 新模組載入失敗: {e}")

try:
    from utils.excel_handler import ExcelHandler
    print("✅ 橋接模組載入成功")
except ImportError as e:
    print(f"❌ 橋接模組載入失敗: {e}")