#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
改進的案件顯示格式化器
統一所有案件資訊的顯示格式，包含完整的進度階段歷程

位置：utils/case_display_formatter.py
"""

import os
from typing import List, Tuple
from datetime import datetime

class CaseDisplayFormatter:
    """案件顯示格式化器"""

    @staticmethod
    def format_case_detail_for_line(case, include_progress_timeline: bool = True,
                                   folder_manager=None) -> str:
        """
        為LINE BOT格式化案件詳細資訊 - 修正版本

        Args:
            case: 案件資料物件
            include_progress_timeline: 是否包含完整進度時間軸
            folder_manager: 資料夾管理器實例

        Returns:
            str: 格式化後的案件資訊
        """
        try:
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

            # 完整進度階段歷程
            if include_progress_timeline:
                response += CaseDisplayFormatter._format_progress_timeline_without_status(case)
            else:
                response += f"\n📊 當前狀態：{case.progress}\n"
                if case.progress_date:
                    response += f"📅 最新進度日期：{case.progress_date}\n"

            response += "－" * 15+ "\n"

            # 🔥 修正：資料夾顯示層級（確保正確傳遞 folder_manager）
            response += CaseDisplayFormatter._format_folder_structure(case, folder_manager)

            response += "－" * 15+ "\n"

            # 時間戳記
            response += f"\n🟥建立時間：{case.created_date.strftime('%Y-%m-%d %H:%M')}\n"
            response += f"🟩更新時間：{case.updated_date.strftime('%Y-%m-%d %H:%M')}\n"

            return response

        except Exception as e:
            print(f"格式化案件詳細資料失敗: {e}")
            return f"❌ 無法顯示案件 {getattr(case, 'case_id', '未知')} 的詳細資料"

    @staticmethod
    def _format_folder_structure(case, folder_manager=None) -> str:
        """格式化資料夾結構顯示 - 修正版本"""
        try:


            # 🔥 修正：更詳細的檢查和更友善的錯誤處理
            if not folder_manager:
                folder_text += "📂 資料夾功能暫時不可用\\n"
                folder_text += "💡 請檢查系統設定或聯繫管理員\\n"
                return folder_text

            # 檢查 folder_manager 是否有必要的方法
            if not hasattr(folder_manager, 'get_case_folder_path'):
                folder_text += "⚠️ 資料夾管理器版本不相容\\n"
                # 🔥 新增：嘗試使用備用方法
                try:
                    from config.settings import AppConfig
                    case_type_folder = AppConfig.CASE_TYPE_FOLDERS.get(case.case_type, case.case_type)
                    # 假設 folder_manager 有 base_data_folder 屬性
                    base_folder = getattr(folder_manager, 'base_data_folder', '.')
                    folder_path = os.path.join(base_folder, case_type_folder, case.client)

                    if os.path.exists(folder_path):
                        folder_text += f"📂 位置：{os.path.basename(folder_path)}\\n"
                        folder_text += "📊 統計：資料夾存在，詳細統計不可用\\n"
                    else:
                        folder_text += "📂 尚未建立案件資料夾\\n"
                        folder_text += "💡 輸入「建立資料夾」可建立資料夾結構\\n"
                    return folder_text
                except Exception as e:
                    print(f"備用方法失敗: {e}")
                    folder_text += "💡 請聯繫系統管理員更新資料夾管理模組\\n"
                    return folder_text

            # 取得案件資料夾路徑
            try:
                folder_path = folder_manager.get_case_folder_path(case)
            except Exception as e:
                print(f"取得案件資料夾路徑失敗: {e}")
                folder_text += "❌ 無法取得案件資料夾路徑\\n"
                folder_text += "💡 輸入「建立資料夾」可建立資料夾結構\\n"
                return folder_text

            # 檢查資料夾是否存在
            if not folder_path or not os.path.exists(folder_path):
                folder_text += "📂 尚未建立案件資料夾\\n"
                folder_text += "💡 輸入「建立資料夾」可建立資料夾結構\\n"
                return folder_text

            # 分析資料夾內容
            try:
                folder_info = CaseDisplayFormatter._analyze_folder_content(folder_path)

                folder_text += f"📂 位置：{os.path.basename(folder_path)}\\n"
                folder_text += f"📊 統計：{folder_info['total_files']} 個檔案 ({folder_info['total_size_mb']:.1f}MB)\\n"

                # 檔案分類顯示
                if folder_info['file_categories']:
                    category_text = CaseDisplayFormatter._format_file_categories(folder_info['file_categories'])
                    if category_text:
                        folder_text += f"📋 分類：{category_text}\\n"

                # 子資料夾顯示
                if folder_info['subfolders']:
                    folder_text += f"📁 子資料夾：{len(folder_info['subfolders'])} 個\\n"
                    for subfolder in folder_info['subfolders'][:3]:  # 最多顯示3個
                        folder_text += f"  ├ {subfolder}\\n"

            except Exception as e:
                print(f"分析資料夾內容失敗: {e}")
                folder_text += f"📂 位置：{os.path.basename(folder_path)}\\n"
                folder_text += "⚠️ 無法分析資料夾內容，但資料夾存在\\n"

            return folder_text

        except Exception as e:
            print(f"格式化資料夾結構失敗: {e}")
            return f"\\n📁 案件資料夾：\\n❌ 顯示資料夾資訊時發生錯誤\\n"

    @staticmethod
    def _format_progress_timeline_without_status(case) -> str:
        """格式化進度時間軸（移除當前狀態摘要）"""
        try:
            timeline_text = "\n📈 案件進度歷程：\n"

            if not case.progress_stages:
                timeline_text += "⚠️ 尚無進度階段記錄\n"
                # 只顯示最新進度，不標示為"當前狀態"
                if hasattr(case, 'progress') and case.progress:
                    timeline_text += f"📌 最新進度：{case.progress}"
                    if hasattr(case, 'progress_date') and case.progress_date:
                        timeline_text += f" ({case.progress_date})"
                    timeline_text += "\n"
                return timeline_text

            # 按日期排序進度階段
            sorted_stages = sorted(
                case.progress_stages.items(),
                key=lambda x: x[1] if x[1] else '9999-12-31'
            )

            for i, (stage_name, stage_date) in enumerate(sorted_stages, 1):
                # 階段序號、日期、名稱
                timeline_text += f"{i}. {stage_date}  {stage_name}"

                # 添加時間資訊（如果有）
                if hasattr(case, 'progress_times') and case.progress_times:
                    stage_time = case.progress_times.get(stage_name, "")
                    if stage_time:
                        timeline_text += f"  {stage_time}"

                timeline_text += "\n"

                # 添加備註資訊（如果有）
                if hasattr(case, 'progress_notes') and case.progress_notes:
                    stage_note = case.progress_notes.get(stage_name, "")
                    if stage_note:
                        timeline_text += f"   💭 備註：{stage_note}\n"

                # 空行分隔
                if i < len(sorted_stages):
                    timeline_text += "\n"

            # 🔥 重點修改：移除"當前狀態"摘要，改為進度統計
            timeline_text += f"\n📊 進度統計：共完成 {len(sorted_stages)} 個階段\n"
            if hasattr(case, 'progress_date') and case.progress_date:
                timeline_text += f"📅 最後更新：{case.progress_date}\n"

            return timeline_text

        except Exception as e:
            print(f"格式化進度時間軸失敗: {e}")
            return "\n❌ 無法顯示進度歷程\n"
    @staticmethod
    def _analyze_folder_content(folder_path: str) -> dict:
        """分析資料夾內容"""
        try:
            total_files = 0
            total_size = 0
            subfolders = []
            recent_files = []
            file_categories = {'document': 0, 'image': 0, 'audio': 0, 'video': 0, 'other': 0}

            # 檔案分類規則
            category_extensions = {
                'document': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.xlsx', '.xls', '.ppt', '.pptx'],
                'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tiff', '.webp'],
                'audio': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma'],
                'video': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
            }

            # 遍歷資料夾
            for root, dirs, files in os.walk(folder_path):
                # 子資料夾資訊（只處理第一層）
                if root == folder_path:
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            # 計算子資料夾大小和檔案數
                            dir_size = 0
                            dir_file_count = 0
                            for dirpath, dirnames, filenames in os.walk(dir_path):
                                for filename in filenames:
                                    try:
                                        file_path = os.path.join(dirpath, filename)
                                        dir_size += os.path.getsize(file_path)
                                        dir_file_count += 1
                                    except (OSError, IOError):
                                        continue

                            subfolders.append({
                                'name': dir_name,
                                'path': os.path.relpath(dir_path, folder_path),
                                'file_count': dir_file_count,
                                'size_mb': dir_size / (1024 * 1024)
                            })
                        except Exception as e:
                            print(f"分析子資料夾 {dir_name} 失敗: {e}")
                            continue

                # 檔案資訊
                for file_name in files:
                    try:
                        file_path = os.path.join(root, file_name)
                        if not os.path.exists(file_path):
                            continue

                        file_size = os.path.getsize(file_path)
                        total_files += 1
                        total_size += file_size

                        # 檔案分類
                        file_ext = os.path.splitext(file_name)[1].lower()
                        category = 'other'
                        for cat, extensions in category_extensions.items():
                            if file_ext in extensions:
                                category = cat
                                break
                        file_categories[category] += 1

                        # 收集最近檔案資訊
                        if len(recent_files) < 10:
                            try:
                                modified_time = os.path.getmtime(file_path)
                                recent_files.append({
                                    'name': file_name,
                                    'path': file_path,
                                    'size': file_size,
                                    'modified_time': modified_time,
                                    'category': category
                                })
                            except (OSError, IOError):
                                continue

                    except Exception as e:
                        print(f"分析檔案 {file_name} 失敗: {e}")
                        continue

            # 按修改時間排序最近檔案
            recent_files.sort(key=lambda x: x['modified_time'], reverse=True)
            recent_files = recent_files[:5]  # 只保留最近5個

            return {
                'total_files': total_files,
                'total_size_mb': total_size / (1024 * 1024),
                'subfolders': sorted(subfolders, key=lambda x: x['name']),
                'recent_files': recent_files,
                'file_categories': file_categories
            }

        except Exception as e:
            print(f"分析資料夾內容失敗: {e}")
            return {
                'total_files': 0,
                'total_size_mb': 0.0,
                'subfolders': [],
                'recent_files': [],
                'file_categories': {}
            }

    @staticmethod
    def _format_file_categories(file_categories: dict) -> str:
        """格式化檔案分類顯示"""
        try:
            category_icons = {
                'document': '📄',
                'image': '🖼️',
                'audio': '🎵',
                'video': '🎬',
                'other': '📎'
            }

            category_names = {
                'document': '文檔',
                'image': '圖片',
                'audio': '音檔',
                'video': '影片',
                'other': '其他'
            }

            categories = []
            for category, count in file_categories.items():
                if count > 0:
                    icon = category_icons.get(category, '📎')
                    name = category_names.get(category, category)
                    categories.append(f"{icon}{count}")

            return ' | '.join(categories) if categories else "無檔案"

        except Exception as e:
            print(f"格式化檔案分類失敗: {e}")
            return "分析失敗"

    @staticmethod
    def _get_file_icon(category: str) -> str:
        """取得檔案圖示"""
        icons = {
            'document': '📄',
            'image': '🖼️',
            'audio': '🎵',
            'video': '🎬',
            'other': '📎'
        }
        return icons.get(category, '📎')

    @staticmethod
    def _format_progress_timeline(case) -> str:
        """格式化進度時間軸"""
        try:
            timeline_text = "📆案件進度歷程：\n"

            if not case.progress_stages:
                timeline_text += "⚠️ 尚無進度階段記錄\n"
                return timeline_text

            # 按日期排序進度階段
            sorted_stages = sorted(
                case.progress_stages.items(),
                key=lambda x: x[1] if x[1] else '9999-12-31'
            )

            for i, (stage_name, stage_date) in enumerate(sorted_stages, 1):
                # 階段序號、日期、名稱
                timeline_text += f"{i}. {stage_date}  {stage_name}"

                # 添加時間資訊（如果有）
                if hasattr(case, 'progress_times') and case.progress_times:
                    stage_time = case.progress_times.get(stage_name, "")
                    if stage_time:
                        timeline_text += f"  {stage_time}"

                timeline_text += "\n"

                # 添加備註資訊（如果有）
                if hasattr(case, 'progress_notes') and case.progress_notes:
                    stage_note = case.progress_notes.get(stage_name, "")
                    if stage_note:
                        timeline_text += f"└ 💭 備註：{stage_note}\n"

            return timeline_text

        except Exception as e:
            print(f"格式化進度時間軸失敗: {e}")
            return "\n❌ 無法顯示進度歷程\n"

    @staticmethod
    def format_progress_summary(case) -> str:
        """格式化進度摘要（簡化版本，移除當前狀態標示）"""
        try:
            if not case.progress_stages:
                return f"📊 進度：{case.progress} (尚無詳細階段記錄)"

            total_stages = len(case.progress_stages)
            latest_progress = case.progress
            latest_date = case.progress_date or "未設定"

            # 🔥 修改：移除"當前狀態"字樣
            summary = f"📊 最新進度：{latest_progress} ({latest_date})\n"
            summary += f"📈 已完成 {total_stages} 個階段"

            return summary

        except Exception as e:
            print(f"格式化進度摘要失敗: {e}")
            return f"📊 進度：{getattr(case, 'progress', '未知')}"

    @staticmethod
    def format_stage_list(case, show_details: bool = True) -> str:
        """格式化階段列表"""
        try:
            if not case.progress_stages:
                return "⚠️ 此案件尚無進度階段記錄"

            stage_text = f"📈 {case.client} 的案件階段：\n\n"

            # 按日期排序
            sorted_stages = sorted(
                case.progress_stages.items(),
                key=lambda x: x[1] if x[1] else '9999-12-31'
            )

            for i, (stage_name, stage_date) in enumerate(sorted_stages, 1):
                stage_text += f"{i}. {stage_name}"

                if show_details:
                    stage_text += f" - {stage_date}"

                    # 時間
                    if hasattr(case, 'progress_times') and case.progress_times:
                        stage_time = case.progress_times.get(stage_name, "")
                        if stage_time:
                            stage_text += f" {stage_time}"

                    # 備註
                    if hasattr(case, 'progress_notes') and case.progress_notes:
                        stage_note = case.progress_notes.get(stage_name, "")
                        if stage_note:
                            stage_text += f"\n   💭 {stage_note}"

                stage_text += "\n"

            return stage_text

        except Exception as e:
            print(f"格式化階段列表失敗: {e}")
            return "❌ 無法顯示階段列表"

    @staticmethod
    def format_folder_file_list(case, folder_manager, subfolder: str = "") -> str:
        """格式化資料夾檔案列表顯示"""
        try:
            if not folder_manager:
                return "❌ 資料夾管理器不可用"

            folder_path = folder_manager.get_case_folder_path(case)
            if not folder_path:
                return "❌ 找不到案件資料夾"

            target_path = os.path.join(folder_path, subfolder) if subfolder else folder_path

            if not os.path.exists(target_path):
                return f"❌ 資料夾不存在：{subfolder or '根目錄'}"

            # 取得檔案列表
            files = []
            folders = []

            try:
                for item in os.listdir(target_path):
                    item_path = os.path.join(target_path, item)

                    if os.path.isdir(item_path):
                        # 計算子資料夾資訊
                        try:
                            file_count = sum(len(filenames) for _, _, filenames in os.walk(item_path))
                            folders.append({'name': item, 'file_count': file_count})
                        except:
                            folders.append({'name': item, 'file_count': 0})

                    elif os.path.isfile(item_path):
                        try:
                            file_size = os.path.getsize(item_path)
                            file_ext = os.path.splitext(item)[1].lower()

                            # 判斷檔案類型
                            if file_ext in ['.pdf', '.doc', '.docx', '.txt', '.xlsx', '.xls']:
                                icon = '📄'
                            elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                                icon = '🖼️'
                            elif file_ext in ['.mp3', '.wav', '.aac', '.flac']:
                                icon = '🎵'
                            elif file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
                                icon = '🎬'
                            else:
                                icon = '📎'

                            files.append({
                                'name': item,
                                'size': file_size,
                                'size_mb': file_size / (1024 * 1024),
                                'icon': icon
                            })
                        except:
                            files.append({'name': item, 'size': 0, 'size_mb': 0, 'icon': '📎'})

            except Exception as e:
                return f"❌ 無法讀取資料夾內容：{str(e)}"

            # 格式化顯示
            current_path = subfolder or "根目錄"
            response = f"📁 {case.client} - {current_path}\n"
            response += "=" * 30 + "\n"

            # 顯示子資料夾
            if folders:
                response += "📂 子資料夾：\n"
                for folder in sorted(folders, key=lambda x: x['name']):
                    response += f"├ {folder['name']} ({folder['file_count']}個檔案)\n"
                response += "\n"

            # 顯示檔案
            if files:
                response += f"📄 檔案列表 ({len(files)}個)：\n"
                # 按大小排序，大檔案在前
                sorted_files = sorted(files, key=lambda x: x['size'], reverse=True)

                for i, file_info in enumerate(sorted_files, 1):
                    size_text = f"({file_info['size_mb']:.1f}MB)" if file_info['size_mb'] > 0.1 else "(<0.1MB)"
                    response += f"{i}. {file_info['icon']} {file_info['name']} {size_text}\n"

                response += "\n💡 回覆檔案編號可選擇檔案進行傳輸\n"
                response += "💡 輸入「返回」可回到上層目錄\n"
            else:
                response += "📂 此資料夾為空\n"

            if not folders and not files:
                response += "📂 此資料夾為空\n"
                response += "💡 可上傳檔案到此資料夾\n"

            return response

        except Exception as e:
            print(f"格式化資料夾檔案列表失敗: {e}")
            return f"❌ 無法顯示資料夾內容：{str(e)}"

    @staticmethod
    def format_case_list_with_progress(cases: List, max_cases: int = 5) -> str:
        """格式化案件列表，包含進度摘要"""
        try:
            if not cases:
                return "❌ 沒有找到任何案件"

            result = f"📋 找到 {len(cases)} 筆案件：\n\n"

            for i, case in enumerate(cases[:max_cases], 1):
                result += f"{i}. {case.case_id} - {case.client}\n"
                result += f"   ⚖️ {case.case_type}"

                if case.case_reason:
                    result += f" - {case.case_reason}"

                result += f"\n   📊 {case.progress}"

                if case.progress_date:
                    result += f" ({case.progress_date})"

                # 顯示階段數量
                if case.progress_stages:
                    stage_count = len(case.progress_stages)
                    result += f"\n   📈 共 {stage_count} 個階段"

                result += "\n\n"

            if len(cases) > max_cases:
                result += f"... 還有 {len(cases) - max_cases} 筆案件\n"

            return result

        except Exception as e:
            print(f"格式化案件列表失敗: {e}")
            return "❌ 無法顯示案件列表"



# 🔥 為了向後相容，提供舊的函數名稱
def format_case_detail_response(case) -> str:
    """向後相容的案件詳細資訊格式化函數"""
    return CaseDisplayFormatter.format_case_detail_for_line(case, include_progress_timeline=True)

def format_case_detail(case) -> str:
    """向後相容的案件詳細資訊格式化函數"""
    return CaseDisplayFormatter.format_case_detail_for_line(case, include_progress_timeline=True)