#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
階梯式查詢邏輯 - 修改 webhook_routes.py
實現 1-2-3-4 步驟式查詢流程
"""
# ======= 📦 基礎導入 =======
import os
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

# ======= 📦 本地模組導入 =======
from api.services.line_service import LineService
from api.schemas.line_schemas import create_text_response
from api.models_control import LoginUser, TenantUser
from api.main import get_case_controller_extension

# ======= 🚀 初始化 =======
router = APIRouter()
line_service = LineService()
get_case_controller_extension = get_case_controller_extension()


# 添加專案根目錄到路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 導入控制器
try:
    from controllers.case_controller import CaseController
    CONTROLLER_AVAILABLE = True
except ImportError:
    print("⚠️ 警告：CaseController 不可用")
    CONTROLLER_AVAILABLE = False



# ==================== 階梯式查詢狀態管理 ====================

class StepwiseQueryState:
    """階梯式查詢狀態 - 新增資料夾瀏覽功能"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.step = 1  # 1: 等待當事人名稱, 2: 選擇案件類型, 3: 選擇案由, 4: 顯示詳細資訊
        self.client_name = ""
        self.found_cases = []
        self.case_types_summary = {}  # {案件類型: 數量}
        self.selected_case_type = ""
        self.filtered_cases = []  # 按類型篩選後的案件
        self.case_reasons = {}  # {序號: (案由, 案件物件)}
        self.selected_case = None

        # 🔥 新增：資料夾瀏覽相關狀態
        self.browsing_mode = False  # 是否在瀏覽模式
        self.browse_step = 0  # 0: 選擇資料夾, 1: 選擇檔案
        self.current_folder_path = ""  # 當前資料夾路徑
        self.available_folders = {}  # {序號: (資料夾名稱, 路徑)}
        self.current_files = {}  # {序號: (檔案名稱, 路徑)}

        self.last_activity = datetime.now()

    def reset(self):
        """重置狀態 - 包含資料夾瀏覽狀態"""
        self.step = 1
        self.client_name = ""
        self.found_cases = []
        self.case_types_summary = {}
        self.selected_case_type = ""
        self.filtered_cases = []
        self.case_reasons = {}
        self.selected_case = None

        # 🔥 重置資料夾瀏覽狀態
        self.browsing_mode = False
        self.browse_step = 0
        self.current_folder_path = ""
        self.available_folders = {}
        self.current_files = {}

        self.last_activity = datetime.now()

    def enter_browse_mode(self, case):
        """進入資料夾瀏覽模式"""
        self.browsing_mode = True
        self.browse_step = 0  # 開始選擇資料夾
        self.selected_case = case
        self.available_folders = {}
        self.current_files = {}
        self.current_folder_path = ""

    def exit_browse_mode(self):
        """退出資料夾瀏覽模式"""
        self.browsing_mode = False
        self.browse_step = 0
        self.current_folder_path = ""
        self.available_folders = {}
        self.current_files = {}


    def is_expired(self) -> bool:
        """檢查是否過期（10分鐘）"""
        return (datetime.now() - self.last_activity) > timedelta(minutes=10)

    def update_activity(self):
        """更新活動時間"""
        self.last_activity = datetime.now()

# 全域變數存儲用戶查詢狀態
user_query_states: Dict[str, StepwiseQueryState] = {}
controller = None

def get_controller():
    """取得控制器實例"""
    global controller
    if controller is None and CONTROLLER_AVAILABLE:
        try:
            controller = CaseController()
            print("✅ Webhook路由：控制器初始化成功")
        except Exception as e:
            print(f"❌ Webhook路由：控制器初始化失敗 - {e}")
    return controller

def get_user_state(user_id: str) -> StepwiseQueryState:
    """取得或建立用戶查詢狀態"""
    if user_id not in user_query_states:
        user_query_states[user_id] = StepwiseQueryState(user_id)

    state = user_query_states[user_id]

    # 檢查是否過期
    if state.is_expired():
        state.reset()
        print(f"🔄 用戶 {user_id} 查詢狀態已過期，重置")

    state.update_activity()
    return state

# ==================== 階梯式查詢邏輯 ====================

def handle_stepwise_query(message: str, user_id: str) -> str:
    """處理階梯式查詢邏輯 - 支援直接資料夾選擇"""
    try:
        ctrl = get_controller()
        if not ctrl:
            return "❌ 系統控制器不可用，請稍後再試"

        state = get_user_state(user_id)
        message = message.strip()

        # 處理重置指令
        if message.lower() in ["重置", "重新開始", "reset", "取消"]:
            state.reset()
            return "🔄 查詢已重置\n\n請輸入要查詢的當事人姓名："

        # 處理幫助指令
        if message.lower() in ["幫助", "help", "?"]:
            return get_help_message()

        # 🔥 新增：處理資料夾瀏覽模式
        if state.browsing_mode:
            return handle_folder_browsing_direct(message, state, ctrl)

        # 原有的階梯式查詢邏輯
        if state.step == 1:
            return handle_step1_client_input(message, state, ctrl)
        elif state.step == 2:
            return handle_step2_case_type_selection(message, state, ctrl)
        elif state.step == 3:
            return handle_step3_case_reason_selection(message, state, ctrl)
        elif state.step == 4:
            # 🔥 新增：在案件詳細資訊顯示後，處理資料夾選擇
            return handle_folder_selection_from_detail(message, state, ctrl)
        else:
            # 異常狀態，重置
            state.reset()
            return "❌ 查詢狀態異常，已重置\n\n請輸入要查詢的當事人姓名："

    except Exception as e:
        print(f"❌ 階梯式查詢處理失敗: {e}")
        return "❌ 系統發生錯誤，請稍後再試"

def handle_folder_browsing_direct(message: str, state: StepwiseQueryState, ctrl) -> str:
    """處理直接資料夾瀏覽模式"""
    try:
        message_lower = message.strip().lower()

        # 處理重置指令
        if message_lower in ["重置", "重新開始", "reset"]:
            state.reset()
            return "🔄 查詢已重置\n\n請輸入要查詢的當事人姓名："

        # 處理下載指令
        if message_lower.startswith("下載") or message_lower == "全部下載":
            return handle_file_download_from_state(message, state, ctrl)

        # 如果在檔案選擇步驟，處理其他指令
        if state.browse_step == 1:
            # 處理檔案查看
            try:
                file_index = int(message)
                return show_file_detail_from_state(file_index, state)
            except ValueError:
                return "❌ 請輸入檔案編號查看詳細資訊，或使用下載指令"

        # 如果在資料夾選擇步驟（browse_step = 0）
        return handle_folder_selection_from_detail(message, state, ctrl)

    except Exception as e:
        print(f"處理直接資料夾瀏覽失敗: {e}")
        return "❌ 資料夾瀏覽處理失敗"

def handle_file_download_from_state(message: str, state: StepwiseQueryState, ctrl) -> str:
    """從狀態處理檔案下載"""
    try:
        if not state.current_files:
            return "❌ 請先選擇資料夾和檔案"

        message_lower = message.lower()

        # 處理全部下載
        if message_lower in ["全部下載", "下載全部"]:
            selected_indices = list(range(1, len(state.current_files) + 1))
        else:
            # 解析下載指令
            import re
            numbers_match = re.search(r'下載\s*(.+)', message)
            if not numbers_match:
                return "❌ 下載指令格式錯誤，請使用「下載 1,3,5」格式"

            numbers_str = numbers_match.group(1).strip()

            try:
                selected_indices = []
                for num_str in numbers_str.split(','):
                    num = int(num_str.strip())
                    if str(num) in state.current_files:
                        selected_indices.append(num)
                    else:
                        return f"❌ 檔案編號 {num} 不存在 (有效範圍: 1-{len(state.current_files)})"

                if not selected_indices:
                    return "❌ 沒有選擇有效的檔案"

            except ValueError:
                return "❌ 檔案編號格式錯誤，請使用「下載 1,3,5」格式"

        # 準備檔案路徑列表
        try:
            case_folder_path = ctrl.folder_manager.get_case_folder_path(state.selected_case)
            selected_file_paths = []

            for index in selected_indices:
                file_info = state.current_files[str(index)]
                file_path = file_info['path']

                # 計算相對路徑
                if case_folder_path:
                    try:
                        relative_path = os.path.relpath(file_path, case_folder_path)
                    except Exception:
                        relative_path = file_info['name']
                else:
                    relative_path = file_info['name']

                selected_file_paths.append(relative_path)

            # 使用現有的檔案傳輸邏輯
            from api.schemas.file_schemas import CaseControllerExtension
            extension = get_case_controller_extension()

            transfer_result = extension.prepare_files_for_client(
                state.selected_case.case_id,
                selected_file_paths,
                {
                    "source": "line_bot_direct_browser",
                    "user_id": state.user_id,
                    "folder": os.path.basename(state.current_folder_path),
                    "timestamp": datetime.now().isoformat()
                }
            )

            if not transfer_result['success']:
                return f"❌ 檔案下載準備失敗：{transfer_result.get('message', '未知錯誤')}"

            transfer_response = transfer_result['transfer_response']

            response = f"✅ 已準備 {len(selected_indices)} 個檔案進行下載\n\n"
            response += f"📦 總大小：{transfer_response.total_size_mb:.1f}MB\n"
            response += f"⏰ 連結有效期：24小時\n\n"

            # 提供下載連結
            if transfer_response.zip_download_url:
                response += f"📥 打包下載：\n{transfer_response.zip_download_url}\n\n"

            if transfer_response.download_links and len(transfer_response.download_links) <= 3:
                response += "📄 個別下載：\n"
                for link in transfer_response.download_links:
                    response += f"• {link['file_name']}\n  {link['download_url']}\n"
            elif transfer_response.download_links:
                response += f"📄 個別下載：{len(transfer_response.download_links)} 個檔案\n"

            response += "\n🔒 連結安全加密，僅限您使用"
            response += "\n💡 輸入「重置」重新查詢案件"

            return response

        except Exception as e:
            print(f"準備檔案下載失敗: {e}")
            return "❌ 檔案下載準備失敗"

    except Exception as e:
        print(f"處理檔案下載失敗: {e}")
        return "❌ 檔案下載處理失敗"



def show_file_detail_from_state(file_index: int, state: StepwiseQueryState) -> str:
    """從狀態顯示檔案詳細資訊"""
    try:
        file_key = str(file_index)

        if file_key not in state.current_files:
            return f"❌ 檔案編號 {file_index} 不存在 (有效範圍: 1-{len(state.current_files)})"

        file_info = state.current_files[file_key]
        file_name = file_info['name']
        file_size_mb = file_info['size_mb']
        modified_time = file_info['modified']

        response = f"📄 檔案詳細資訊\n"
        response += "=" * 30 + "\n\n"
        response += f"📝 檔案名稱：{file_name}\n"
        response += f"📦 檔案大小：{file_size_mb:.2f}MB\n"
        response += f"🕒 修改時間：{modified_time.strftime('%Y-%m-%d %H:%M')}\n"
        response += f"📂 所在資料夾：{os.path.basename(state.current_folder_path)}\n\n"

        response += f"💡 下載選項：\n"
        response += f"• 輸入「下載 {file_index}」下載此檔案\n"
        response += f"• 輸入「重置」重新查詢案件"

        return response

    except Exception as e:
        print(f"顯示檔案詳細資訊失敗: {e}")
        return "❌ 無法顯示檔案詳細資訊"

def handle_folder_selection_from_detail(message: str, state: StepwiseQueryState, ctrl) -> str:
    """處理從案件詳細資訊頁面的資料夾選擇"""
    try:
        # 檢查是否為數字輸入（資料夾選擇）
        try:
            folder_index = int(message)
            folder_key = str(folder_index)
        except ValueError:
            # 不是數字，可能是其他指令
            if message.lower() in ["重置", "重新開始"]:
                state.reset()
                return "🔄 查詢已重置\n\n請輸入要查詢的當事人姓名："
            else:
                available_count = len(state.available_folders) if state.available_folders else 0
                if available_count > 0:
                    return f"❌ 請輸入有效的資料夾編號 (1-{available_count})\n💡 或輸入「重置」重新查詢"
                else:
                    return "❌ 沒有可用的資料夾選項\n💡 輸入「重置」重新查詢"

        # 檢查資料夾編號是否有效
        if not state.available_folders or folder_key not in state.available_folders:
            available_count = len(state.available_folders) if state.available_folders else 0
            return f"❌ 請輸入有效的資料夾編號 (1-{available_count})"

        # 取得選擇的資料夾
        folder_name, folder_path = state.available_folders[folder_key]

        # 讀取資料夾內的檔案
        try:
            files = []
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    file_size = os.path.getsize(item_path)
                    file_size_mb = file_size / (1024 * 1024)
                    modified_time = datetime.fromtimestamp(os.path.getmtime(item_path))

                    files.append({
                        'name': item,
                        'path': item_path,
                        'size': file_size,
                        'size_mb': round(file_size_mb, 2),
                        'extension': os.path.splitext(item)[1].lower(),
                        'modified': modified_time
                    })

            # 按修改時間排序（最新的在前）
            files.sort(key=lambda x: x['modified'], reverse=True)

        except Exception as e:
            print(f"讀取資料夾檔案失敗: {e}")
            return f"❌ 無法讀取資料夾「{folder_name}」的內容"

        if not files:
            response = f"📂 資料夾「{folder_name}」為空\n\n"
            response += "💡 輸入「重置」重新查詢案件\n"
            response += "💡 或請先上傳檔案到此資料夾"
            return response

        # 🔥 格式化檔案列表並提供選擇
        response = f"📁 資料夾：{folder_name}\n"
        response += "=" * 30 + "\n\n"
        response += f"📄 檔案列表 ({len(files)} 個檔案)：\n\n"

        # 更新狀態 - 儲存檔案資訊供下載使用
        state.current_files = {}
        state.current_folder_path = folder_path
        state.browse_step = 1  # 設定為檔案選擇步驟

        for i, file_info in enumerate(files, 1):
            file_name = file_info['name']
            file_size_mb = file_info['size_mb']
            file_ext = file_info['extension']

            # 取得檔案圖示
            icon = get_file_icon(file_ext)

            state.current_files[str(i)] = file_info

            size_text = f"({file_size_mb:.1f}MB)" if file_size_mb >= 0.1 else "(<0.1MB)"
            response += f"{i}. {icon} {file_name} {size_text}\n"

        response += f"\n💡 檔案操作選項：\n"
        response += f"• 輸入「下載 1」下載單個檔案\n"
        response += f"• 輸入「下載 1,3,5」下載多個檔案\n"
        response += f"• 輸入「全部下載」下載所有檔案\n"
        response += f"• 輸入「重置」重新查詢案件"

        return response

    except Exception as e:
        print(f"處理資料夾選擇失敗: {e}")
        return "❌ 資料夾選擇處理失敗"


def enter_folder_browsing_mode(state: StepwiseQueryState, ctrl) -> str:
    """進入資料夾瀏覽模式"""
    try:
        if not state.selected_case:
            return "❌ 請先選擇案件"

        case = state.selected_case

        # 進入瀏覽模式
        state.enter_browse_mode(case)

        # 取得案件資料夾路徑
        folder_manager = ctrl.folder_manager
        if not folder_manager:
            return "❌ 資料夾管理器不可用"

        case_folder_path = folder_manager.get_case_folder_path(case)
        if not case_folder_path or not os.path.exists(case_folder_path):
            return f"❌ 找不到案件「{case.client}」的資料夾\n💡 輸入「建立資料夾」可建立資料夾結構"

        # 取得子資料夾列表
        try:
            subfolders = []
            for item in os.listdir(case_folder_path):
                item_path = os.path.join(case_folder_path, item)
                if os.path.isdir(item_path):
                    # 計算資料夾內檔案數量
                    file_count = sum(len(files) for _, _, files in os.walk(item_path))
                    subfolders.append({
                        'name': item,
                        'path': item_path,
                        'file_count': file_count
                    })

            if not subfolders:
                return f"📂 案件「{case.client}」的資料夾為空\n💡 請先上傳檔案到案件資料夾"

            # 建立資料夾選擇列表
            response = f"📁 {case.client} 的案件資料夾\n"
            response += "=" * 30 + "\n\n"
            response += "📂 請選擇要瀏覽的資料夾：\n\n"

            state.available_folders = {}
            for i, folder in enumerate(subfolders, 1):
                folder_name = folder['name']
                file_count = folder['file_count']
                state.available_folders[str(i)] = (folder_name, folder['path'])
                response += f"{i}. 📁 {folder_name} ({file_count} 個檔案)\n"

            response += f"\n💡 請輸入資料夾編號 (1-{len(subfolders)})"
            response += "\n💡 輸入「返回」回到案件詳細資訊"

            return response

        except Exception as e:
            print(f"列舉資料夾失敗: {e}")
            return f"❌ 無法讀取案件資料夾內容"

    except Exception as e:
        print(f"進入資料夾瀏覽模式失敗: {e}")
        return "❌ 進入資料夾瀏覽模式失敗"

def handle_folder_browsing(message: str, state: StepwiseQueryState, ctrl) -> str:
    """處理資料夾瀏覽邏輯"""
    try:
        message = message.strip()

        # 處理返回指令
        if message.lower() in ["返回", "back", "上一步"]:
            if state.browse_step == 0:
                # 從資料夾選擇返回案件詳細資訊
                state.exit_browse_mode()
                return format_case_detail(state.selected_case)
            elif state.browse_step == 1:
                # 從檔案列表返回資料夾選擇
                state.browse_step = 0
                state.current_folder_path = ""
                state.current_files = {}
                return enter_folder_browsing_mode(state, ctrl)

        # 處理重置指令
        if message.lower() in ["重置", "重新開始", "reset", "取消"]:
            state.reset()
            return "🔄 查詢已重置\n\n請輸入要查詢的當事人姓名："

        # 根據瀏覽步驟處理
        if state.browse_step == 0:
            # 選擇資料夾
            return handle_folder_selection(message, state, ctrl)
        elif state.browse_step == 1:
            # 選擇檔案
            return handle_file_selection(message, state, ctrl)
        else:
            # 異常狀態，回到資料夾選擇
            state.browse_step = 0
            return enter_folder_browsing_mode(state, ctrl)

    except Exception as e:
        print(f"資料夾瀏覽處理失敗: {e}")
        return "❌ 資料夾瀏覽發生錯誤"
def handle_folder_selection(message: str, state: StepwiseQueryState, ctrl) -> str:
    """處理資料夾選擇"""
    try:
        # 檢查輸入是否為有效的資料夾編號
        try:
            folder_index = int(message)
            if str(folder_index) not in state.available_folders:
                return f"❌ 請輸入有效的資料夾編號 (1-{len(state.available_folders)})"
        except ValueError:
            return f"❌ 請輸入數字編號 (1-{len(state.available_folders)})"

        # 取得選擇的資料夾
        folder_name, folder_path = state.available_folders[str(folder_index)]
        state.current_folder_path = folder_path
        state.browse_step = 1  # 進入檔案選擇步驟

        # 讀取資料夾內的檔案
        try:
            files = []
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    file_size = os.path.getsize(item_path)
                    file_size_mb = file_size / (1024 * 1024)
                    files.append({
                        'name': item,
                        'path': item_path,
                        'size': file_size,
                        'size_mb': round(file_size_mb, 2),
                        'extension': os.path.splitext(item)[1].lower()
                    })

            if not files:
                response = f"📂 資料夾「{folder_name}」為空\n\n"
                response += "💡 輸入「返回」選擇其他資料夾"
                return response

            # 建立檔案列表
            response = f"📁 資料夾：{folder_name}\n"
            response += "=" * 30 + "\n\n"
            response += f"📄 檔案列表 ({len(files)} 個檔案)：\n\n"

            state.current_files = {}
            for i, file_info in enumerate(files, 1):
                file_name = file_info['name']
                file_size_mb = file_info['size_mb']
                file_ext = file_info['extension']

                # 取得檔案圖示
                icon = get_file_icon(file_ext)

                state.current_files[str(i)] = (file_name, file_info['path'])

                size_text = f"({file_size_mb:.1f}MB)" if file_size_mb >= 0.1 else "(<0.1MB)"
                response += f"{i}. {icon} {file_name} {size_text}\n"

            response += f"\n💡 請輸入檔案編號 (1-{len(files)}) 查看詳細資訊"
            response += "\n💡 輸入「下載 1,3,5」選擇多個檔案下載"
            response += "\n💡 輸入「全部下載」下載所有檔案"
            response += "\n💡 輸入「返回」回到資料夾選擇"

            return response

        except Exception as e:
            print(f"讀取資料夾內容失敗: {e}")
            return f"❌ 無法讀取資料夾「{folder_name}」的內容"

    except Exception as e:
        print(f"處理資料夾選擇失敗: {e}")
        return "❌ 資料夾選擇處理失敗"

def handle_file_selection(message: str, state: StepwiseQueryState, ctrl) -> str:
    """處理檔案選擇"""
    try:
        message_lower = message.lower()

        # 處理下載指令
        if message_lower.startswith("下載") or message_lower.startswith("download"):
            return handle_file_download_request(message, state, ctrl)
        elif message_lower in ["全部下載", "下載全部", "all"]:
            return handle_all_files_download(state, ctrl)

        # 處理單一檔案查看
        try:
            file_index = int(message)
            if str(file_index) not in state.current_files:
                return f"❌ 請輸入有效的檔案編號 (1-{len(state.current_files)})"
        except ValueError:
            return f"❌ 請輸入檔案編號 (1-{len(state.current_files)}) 或下載指令"

        # 顯示檔案詳細資訊
        file_name, file_path = state.current_files[str(file_index)]

        try:
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            file_size_mb = file_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(file_stat.st_mtime)

            response = f"📄 檔案詳細資訊\n"
            response += "=" * 30 + "\n\n"
            response += f"📝 檔案名稱：{file_name}\n"
            response += f"📦 檔案大小：{file_size_mb:.2f}MB\n"
            response += f"🕒 修改時間：{modified_time.strftime('%Y-%m-%d %H:%M')}\n"
            response += f"📂 位置：{os.path.basename(state.current_folder_path)}\n\n"

            response += f"💡 輸入「下載 {file_index}」下載此檔案\n"
            response += "💡 輸入「返回」回到檔案列表"

            return response

        except Exception as e:
            print(f"取得檔案資訊失敗: {e}")
            return f"❌ 無法取得檔案「{file_name}」的詳細資訊"

    except Exception as e:
        print(f"處理檔案選擇失敗: {e}")
        return "❌ 檔案選擇處理失敗"
@router.post("/webhook/line")
async def handle_line_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    events = payload.get("events", [])
    if not events:
        return JSONResponse(content={"error": "No events received"}, status_code=400)

    event = events[0]
    user_id = event.get("source", {}).get("userId", "UNKNOWN")

    # ✅ 使用 controller extension
    controller = get_case_controller_extension()
    case_data = controller.get_case_by_user_id(user_id)

    return JSONResponse(content={
        "message": f"✅ 查詢成功，案件編號：{case_data['case_id']}",
        "download_url": case_data["file_url"]
    })

def handle_file_download_request(message: str, state: StepwiseQueryState, ctrl) -> str:
    """處理檔案下載請求"""
    try:
        # 解析下載指令 (例如: "下載 1,3,5")
        import re
        numbers_match = re.search(r'下載\s*(.+)', message)
        if not numbers_match:
            return "❌ 下載指令格式錯誤，請使用「下載 1,3,5」格式"

        numbers_str = numbers_match.group(1).strip()

        try:
            # 解析檔案編號
            file_indices = []
            for num_str in numbers_str.split(','):
                num = int(num_str.strip())
                if str(num) in state.current_files:
                    file_indices.append(num)
                else:
                    return f"❌ 檔案編號 {num} 不存在 (有效範圍: 1-{len(state.current_files)})"

            if not file_indices:
                return "❌ 沒有選擇有效的檔案"

            # 準備檔案下載
            selected_files = []
            total_size = 0

            for index in file_indices:
                file_name, file_path = state.current_files[str(index)]
                try:
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    selected_files.append({
                        'name': file_name,
                        'path': file_path,
                        'size': file_size,
                        'relative_path': os.path.relpath(file_path, ctrl.folder_manager.get_case_folder_path(state.selected_case))
                    })
                except Exception as e:
                    print(f"取得檔案資訊失敗: {file_name} - {e}")

            if not selected_files:
                return "❌ 無法準備下載檔案"

            # 🔥 使用現有的檔案傳輸邏輯
            try:
                from api.schemas.file_schemas import CaseControllerExtension
                extension = get_case_controller_extension()

                file_paths = [f['relative_path'] for f in selected_files]
                transfer_result = extension.prepare_files_for_client(
                    state.selected_case.case_id,
                    file_paths,
                    {
                        "source": "line_bot_browser",
                        "user_id": state.user_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )

                if transfer_result['success']:
                    transfer_response = transfer_result['transfer_response']

                    response = f"✅ 已準備 {len(selected_files)} 個檔案進行下載\n\n"
                    response += f"📦 總大小：{transfer_response.total_size_mb:.1f}MB\n"
                    response += f"⏰ 連結有效期：24小時\n\n"

                    # 提供下載連結
                    if transfer_response.zip_download_url:
                        response += f"📥 打包下載：\n{transfer_response.zip_download_url}\n\n"

                    if transfer_response.download_links:
                        response += "📄 個別下載：\n"
                        for link in transfer_response.download_links[:3]:  # 最多顯示3個
                            response += f"• {link['file_name']}\n"

                        if len(transfer_response.download_links) > 3:
                            response += f"... 還有 {len(transfer_response.download_links) - 3} 個檔案\n"

                    response += "\n🔒 連結安全加密，僅限您使用"
                    response += "\n💡 輸入「返回」繼續瀏覽檔案"

                    return response
                else:
                    return f"❌ 檔案下載準備失敗：{transfer_result.get('message', '未知錯誤')}"

            except Exception as e:
                print(f"準備檔案下載失敗: {e}")
                return "❌ 檔案下載準備失敗，請稍後再試"

        except ValueError:
            return "❌ 檔案編號格式錯誤，請使用「下載 1,3,5」格式"

    except Exception as e:
        print(f"處理檔案下載請求失敗: {e}")
        return "❌ 檔案下載請求處理失敗"

def handle_all_files_download(state: StepwiseQueryState, ctrl) -> str:
    """處理全部檔案下載"""
    try:
        if not state.current_files:
            return "❌ 當前資料夾沒有檔案可下載"

        # 準備所有檔案
        all_indices = list(range(1, len(state.current_files) + 1))
        download_command = f"下載 {','.join(map(str, all_indices))}"

        return handle_file_download_request(download_command, state, ctrl)

    except Exception as e:
        print(f"處理全部檔案下載失敗: {e}")
        return "❌ 全部檔案下載處理失敗"

def get_file_icon(file_ext: str) -> str:
    """取得檔案圖示"""
    icons = {
        '.pdf': '📄', '.doc': '📄', '.docx': '📄', '.txt': '📄',
        '.xlsx': '📊', '.xls': '📊', '.csv': '📊',
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.bmp': '🖼️',
        '.mp3': '🎵', '.wav': '🎵', '.aac': '🎵', '.flac': '🎵',
        '.mp4': '🎬', '.avi': '🎬', '.mov': '🎬', '.mkv': '🎬',
        '.zip': '📦', '.rar': '📦', '.7z': '📦'
    }
    return icons.get(file_ext.lower(), '📎')

def handle_step1_client_input(message: str, state: StepwiseQueryState, ctrl) -> str:
    """步驟1：處理當事人姓名輸入"""
    try:
        client_name = message.strip()

        if not client_name:
            return "⚠️ 請輸入有效的當事人姓名"

        # 搜尋案件
        all_cases = ctrl.get_cases()
        found_cases = [
            case for case in all_cases
            if client_name in case.client
        ]

        if not found_cases:
            return f"❌ 沒有找到當事人「{client_name}」的案件"

        # 更新狀態
        state.client_name = client_name
        state.found_cases = found_cases

        # 統計案件類型
        case_types_count = {}
        for case in found_cases:
            case_type = case.case_type
            case_types_count[case_type] = case_types_count.get(case_type, 0) + 1

        state.case_types_summary = case_types_count

        # 如果只有一個案件類型且只有一件案件，直接顯示詳細資訊
        if len(found_cases) == 1:
            state.selected_case = found_cases[0]
            return format_case_detail(found_cases[0])

        # 如果只有一個案件類型但有多件案件，跳到步驟3
        if len(case_types_count) == 1:
            case_type = list(case_types_count.keys())[0]
            state.selected_case_type = case_type
            state.filtered_cases = found_cases
            state.step = 3
            return format_step3_case_reason_selection(state)

        # 多個案件類型，進入步驟2
        state.step = 2
        return format_step2_case_type_selection(state)

    except Exception as e:
        print(f"❌ 步驟1處理失敗: {e}")
        return "❌ 查詢過程發生錯誤"

def handle_step2_case_type_selection(message: str, state: StepwiseQueryState, ctrl) -> str:
    """步驟2：處理案件類型選擇"""
    try:
        user_choice = message.strip()

        # 嘗試解析用戶選擇
        selected_type = None

        # 檢查是否為數字選擇
        if user_choice.isdigit():
            choice_num = int(user_choice)
            case_types = list(state.case_types_summary.keys())
            if 1 <= choice_num <= len(case_types):
                selected_type = case_types[choice_num - 1]

        # 檢查是否直接輸入案件類型名稱
        if not selected_type:
            for case_type in state.case_types_summary.keys():
                if case_type in user_choice or user_choice in case_type:
                    selected_type = case_type
                    break

        if not selected_type:
            return f"⚠️ 請輸入有效的選項號碼 (1-{len(state.case_types_summary)}) 或案件類型名稱\n\n" + format_step2_case_type_selection(state)

        # 篩選該類型的案件
        state.selected_case_type = selected_type
        state.filtered_cases = [
            case for case in state.found_cases
            if case.case_type == selected_type
        ]

        # 如果只有一件案件，直接顯示詳細資訊
        if len(state.filtered_cases) == 1:
            state.selected_case = state.filtered_cases[0]
            return format_case_detail(state.filtered_cases[0])

        # 多件案件，進入步驟3選擇案由
        state.step = 3
        return format_step3_case_reason_selection(state)

    except Exception as e:
        print(f"❌ 步驟2處理失敗: {e}")
        return "❌ 選擇處理過程發生錯誤"

def handle_step3_case_reason_selection(message: str, state: StepwiseQueryState, ctrl) -> str:
    """步驟3：處理案由選擇 - 修改為直接進入資料夾瀏覽準備狀態"""
    try:
        # 檢查輸入是否為有效數字
        try:
            choice = int(message)
            choice_key = str(choice)
        except ValueError:
            return f"⚠️ 請輸入有效的選項號碼 (1-{len(state.case_reasons)})"

        if choice_key not in state.case_reasons:
            return f"⚠️ 請輸入有效的選項號碼 (1-{len(state.case_reasons)})"

        # 取得選擇的案件
        case_reason, selected_case = state.case_reasons[choice_key]
        state.selected_case = selected_case
        state.step = 4  # 完成查詢

        # 🔥 重點：準備資料夾瀏覽狀態
        try:
            # 取得並儲存資料夾資訊到狀態中
            folder_manager = ctrl.folder_manager
            if folder_manager:
                case_folder_path = folder_manager.get_case_folder_path(selected_case)
                if case_folder_path and os.path.exists(case_folder_path):
                    # 預先載入資料夾資訊
                    subfolders = []
                    for item in os.listdir(case_folder_path):
                        item_path = os.path.join(case_folder_path, item)
                        if os.path.isdir(item_path):
                            file_count = sum(len(files) for _, _, files in os.walk(item_path))
                            subfolders.append({
                                'name': item,
                                'path': item_path,
                                'file_count': file_count
                            })

                    # 🔥 儲存到狀態中，準備接收資料夾選擇
                    state.available_folders = {}
                    for i, folder in enumerate(subfolders, 1):
                        state.available_folders[str(i)] = (folder['name'], folder['path'])

                    # 設定為資料夾瀏覽準備狀態
                    state.browsing_mode = True
                    state.browse_step = 0  # 等待資料夾選擇

        except Exception as e:
            print(f"準備資料夾瀏覽狀態失敗: {e}")

        # 格式化並回傳案件詳細資訊（現在包含資料夾選項）
        return format_case_detail_with_folder_options(selected_case, ctrl.folder_manager)

    except Exception as e:
        print(f"處理案由選擇失敗: {e}")
        return "❌ 案由選擇處理失敗"

# ==================== 格式化回應函數 ====================

def format_step2_case_type_selection(state: StepwiseQueryState) -> str:
    """格式化步驟2：案件類型選擇"""
    response = f"🔍 找到當事人「{state.client_name}」的案件\n\n"
    response += "📋 請選擇要查看的案件類型：\n\n"

    for i, (case_type, count) in enumerate(state.case_types_summary.items(), 1):
        response += f"{i}. {case_type} ({count} 件)\n"

    response += f"\n💡 請輸入選項號碼 (1-{len(state.case_types_summary)})"
    return response

def format_step3_case_reason_selection(state: StepwiseQueryState) -> str:
    """格式化步驟3：案由選擇"""
    response = f"📂 {state.selected_case_type}案件列表\n\n"

    # 建立案由對應表
    state.case_reasons = {}
    for i, case in enumerate(state.filtered_cases, 1):
        case_reason = case.case_reason or "未指定案由"
        case_id = case.case_id
        state.case_reasons[str(i)] = (case_reason, case)
        response += f"{i}. {case_reason} (案件編號: {case_id})\n"

    response += f"\n💡 請輸入選項號碼 (1-{len(state.case_reasons)})"
    return response

def format_case_detail(case) -> str:
    """格式化案件詳細資訊 - 直接包含資料夾選項"""
    try:
        from utils.case_display_formatter import CaseDisplayFormatter

        # 取得控制器和 folder_manager
        from api.main import get_controller

        try:
            controller = get_controller()
            folder_manager = controller.folder_manager if controller else None
            print(f"📁 取得 folder_manager: {folder_manager is not None}")
        except Exception as e:
            print(f"取得控制器失敗: {e}")
            folder_manager = None

        # 🔥 使用新的格式化方法，直接包含資料夾選項
        result = format_case_detail_with_folder_options(case, folder_manager)

        print(f"✅ 案件詳細資訊格式化完成，包含資料夾選項")
        return result

    except Exception as e:
        print(f"格式化案件詳細資料失敗: {e}")
        return f"❌ 無法顯示案件詳細資料：{str(e)}"

def format_case_detail_with_folder_options(case, folder_manager=None) -> str:
    """格式化案件詳細資訊並直接顯示資料夾選項"""
    try:
        # 🔥 先顯示基本案件資訊（不包含原本的資料夾區塊）
        response = "ℹ️案件詳細資訊\n"
        response += "－" * 15 + "\n"

        # 基本資訊
        response += f"📌案件編號：{case.case_id}\n"
        response += f"👤  當事人：{case.client}\n"

        response += "－" * 15 + "\n"

        response += f"案件類型：{case.case_type}\n"

        if case.case_reason:
            response += f"案由：{case.case_reason}\n"

        if case.case_number:
            response += f"案號：{case.case_number}\n"

        if case.lawyer:
            response += f"委任律師：{case.lawyer}\n"

        if case.legal_affairs:
            response += f"法務：{case.legal_affairs}\n"

        if case.opposing_party:
            response += f"對造：{case.opposing_party}\n"

        if case.court:
            response += f"負責法院：{case.court}\n"

        if hasattr(case, 'division') and case.division:
            response += f"負責股別：{case.division}\n"

        response += "－" * 15

        # 🔥 顯示進度資訊（保持原有邏輯）
        from utils.case_display_formatter import CaseDisplayFormatter
        response += CaseDisplayFormatter._format_progress_timeline_without_status(case)

        response += "－" * 15

        # 🔥 新增：直接顯示資料夾選項（取代原本的資料夾資訊）
        response += format_folder_selection_menu(case, folder_manager)

        response += "－" * 15

        # 時間戳記
        response += f"\n🟥建立時間：{case.created_date.strftime('%Y-%m-%d %H:%M')}\n"
        response += f"🟩更新時間：{case.updated_date.strftime('%Y-%m-%d %H:%M')}\n"

        return response

    except Exception as e:
        print(f"格式化案件詳細資料失敗: {e}")
        return f"❌ 無法顯示案件 {getattr(case, 'case_id', '未知')} 的詳細資料"

def format_folder_selection_menu(case, folder_manager=None) -> str:
    """格式化資料夾選擇選單 - 直接嵌入案件詳細資訊中"""
    try:
        folder_text = "\n📁 案件資料夾：\n"

        # 檢查 folder_manager 可用性
        if not folder_manager:
            folder_text += "📂 資料夾功能暫時不可用\n"
            folder_text += "💡 請檢查系統設定\n"
            return folder_text

        # 檢查必要方法
        if not hasattr(folder_manager, 'get_case_folder_path'):
            folder_text += "⚠️ 資料夾管理器版本不相容\n"
            return folder_text

        # 取得案件資料夾路徑
        try:
            folder_path = folder_manager.get_case_folder_path(case)
        except Exception as e:
            print(f"取得案件資料夾路徑失敗: {e}")
            folder_text += "❌ 無法取得案件資料夾路徑\n"
            folder_text += "💡 輸入「建立資料夾」可建立資料夾結構\n"
            return folder_text

        # 檢查資料夾是否存在
        if not folder_path or not os.path.exists(folder_path):
            folder_text += "📂 尚未建立案件資料夾\n"
            folder_text += "💡 輸入「建立資料夾」可建立資料夾結構\n"
            return folder_text

        # 🔥 重點：列舉並顯示資料夾選項
        try:
            subfolders = []
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    # 計算檔案數量
                    file_count = 0
                    try:
                        file_count = sum(len(files) for _, _, files in os.walk(item_path))
                    except Exception:
                        pass

                    subfolders.append({
                        'name': item,
                        'path': item_path,
                        'file_count': file_count
                    })

            if not subfolders:
                folder_text += "📂 資料夾為空，請先上傳檔案\n"
                return folder_text

            folder_text += f"💡 輸入編號瀏覽 (1-{len(subfolders)}) 檔案\n\n"

            for i, folder in enumerate(subfolders, 1):
                folder_name = folder['name']
                file_count = folder['file_count']
                folder_text += f"{i}. 📁 {folder_name} ({file_count} 個檔案)\n"

            # 🔥 新增：將資料夾資訊儲存到用戶狀態（需要在調用處處理）
            # 這部分需要在 handle_stepwise_query 中處理狀態更新

            return folder_text

        except Exception as e:
            print(f"列舉資料夾失敗: {e}")
            folder_text += f"📂 位置：{os.path.basename(folder_path)}\n"
            folder_text += "⚠️ 無法讀取資料夾內容\n"
            return folder_text

    except Exception as e:
        print(f"格式化資料夾選擇選單失敗: {e}")
        return f"\n📁 案件資料夾：\n❌ 顯示資料夾選項時發生錯誤\n"



def get_help_message() -> str:
    """取得幫助訊息 - 新增資料夾瀏覽說明"""
    return """📋 階梯式案件查詢系統

🔍 查詢流程：
1️⃣ 輸入當事人姓名
2️⃣ 選擇案件類型（如有多種）
3️⃣ 選擇具體案件（如有多件）
4️⃣ 查看案件詳細資訊

📁 資料夾瀏覽：
5️⃣ 輸入「資料夾」進入檔案瀏覽
6️⃣ 選擇要瀏覽的資料夾
7️⃣ 選擇要查看或下載的檔案

💡 指令說明：
• 重置 - 重新開始查詢
• 返回 - 回到上一步
• 幫助 - 顯示此說明
• 資料夾 - 瀏覽案件檔案
• 下載 1,3,5 - 下載指定檔案
• 全部下載 - 下載所有檔案

🚀 開始使用：
直接輸入要查詢的當事人姓名即可！"""

# ==================== Webhook端點 ====================

@router.post("/line", response_model=LineWebhookResponse)
async def webhook_line(request: Dict[str, Any]):
    """
    LINE Webhook 處理端點 - 階梯式查詢版本
    """
    try:
        # 解析請求資料
        message = request.get("message", "").strip()
        user_id = request.get("user_id", "")

        print(f"📨 階梯式查詢收到訊息: '{message}' (用戶: {user_id})")

        if not message or not user_id:
            return create_text_response(
                "訊息格式錯誤，請提供有效的訊息和用戶ID",
                user_id,
                success=False
            )

        # 檢查系統可用性
        if not CONTROLLER_AVAILABLE:
            return create_text_response(
                "系統模組不可用，請稍後再試",
                user_id,
                success=False
            )

        # 處理階梯式查詢
        response_text = handle_stepwise_query(message, user_id)

        return create_text_response(response_text, user_id)

    except Exception as e:
        print(f"❌ Webhook處理失敗: {e}")
        return create_text_response(
            "系統發生錯誤，請稍後再試",
            request.get("user_id", "unknown"),
            success=False
        )

# ==================== 管理端點 ====================

@router.get("/query-state/{user_id}")
async def get_query_state(user_id: str):
    """取得用戶查詢狀態"""
    try:
        if user_id in user_query_states:
            state = user_query_states[user_id]
            return {
                "user_id": user_id,
                "step": state.step,
                "client_name": state.client_name,
                "found_cases_count": len(state.found_cases),
                "case_types_summary": state.case_types_summary,
                "selected_case_type": state.selected_case_type,
                "last_activity": state.last_activity.isoformat()
            }
        else:
            return {"user_id": user_id, "status": "no_active_query"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得查詢狀態失敗: {str(e)}")

@router.delete("/query-state/{user_id}")
async def clear_query_state(user_id: str):
    """清除用戶查詢狀態"""
    try:
        if user_id in user_query_states:
            del user_query_states[user_id]
            return {"success": True, "message": f"已清除用戶 {user_id} 的查詢狀態"}
        else:
            return {"success": False, "message": f"用戶 {user_id} 沒有查詢狀態"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除查詢狀態失敗: {str(e)}")

@router.get("/query-states/active")
async def get_active_query_states():
    """取得所有活躍查詢狀態"""
    try:
        active_states = []
        for user_id, state in user_query_states.items():
            if not state.is_expired():
                active_states.append({
                    "user_id": user_id,
                    "step": state.step,
                    "client_name": state.client_name,
                    "last_activity": state.last_activity.isoformat()
                })

        return {
            "total_active": len(active_states),
            "query_states": active_states
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得活躍查詢狀態失敗: {str(e)}")

@router.post("/test-stepwise")
async def test_stepwise_query():
    """測試階梯式查詢功能"""
    return {
        "status": "success",
        "message": "階梯式查詢功能正常",
        "controller_available": CONTROLLER_AVAILABLE,
        "active_queries": len(user_query_states),
        "features": [
            "1. 當事人姓名查詢",
            "2. 案件類型選擇",
            "3. 案由選擇",
            "4. 詳細資訊顯示"
        ]
    }


# ======= 🔗 LINE 綁定 API =======
@router.post("/line/bind")
async def bind_line_user(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        client_id = data.get("client_id")

        if not user_id or not client_id:
            raise HTTPException(status_code=400, detail="缺少必要參數")

        # 取得事務所帳號
        login_user = LoginUser.filter(LoginUser.client_id == client_id).first()
        if not login_user:
            raise HTTPException(status_code=404, detail="找不到對應的事務所")

        # 人數限制判斷
        if login_user.current_users >= login_user.max_users:
            return JSONResponse(status_code=403, content={"detail": "綁定人數已達上限"})

        # 檢查是否已綁定
        existing = TenantUser.filter(
            TenantUser.client_id == client_id,
            TenantUser.line_user_id == user_id
        ).first()

        if existing:
            return JSONResponse(content={"detail": "此 LINE 已綁定過"})

        # 寫入綁定
        tenant_user = TenantUser(
            client_id=client_id,
            line_user_id=user_id,
            created_at=datetime.utcnow()
        )
        tenant_user.save()

        # 更新使用者數量
        login_user.current_users += 1
        login_user.save()

        return {"message": "✅ 綁定成功"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"綁定過程發生錯誤: {str(e)}"})

# ======= 📊 綁定人數查詢 API =======
@router.get("/line/bind/status")
def get_bind_status(client_id: str):
    try:
        login_user = LoginUser.filter(LoginUser.client_id == client_id).first()
        if not login_user:
            raise HTTPException(status_code=404, detail="找不到事務所")

        return {
            "client_id": login_user.client_id,
            "綁定人數": login_user.current_users,
            "上限": login_user.max_users,
            "可用名額": login_user.max_users - login_user.current_users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")

# ======= 🧪 測試 Webhook Endpoint（選用） =======
@router.get("/test")
def test_webhook():
    return {"message": "Webhook OK 🚀"}