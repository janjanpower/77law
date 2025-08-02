#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel讀取器 - 專責Excel檔案讀取功能
提供統一的Excel檔案讀取介面，支援多種格式和引擎
"""

import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# 安全的依賴導入
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    import xlrd
    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False

from utils.data_cleaner import DataCleaner
from .exceptions import (
    ExcelFileNotFoundError,
    ExcelEngineNotAvailableError,
    ExcelSheetNotFoundError,
    ExcelDependencyError
)


class ExcelReader:
    """Excel讀取器類別"""

    def __init__(self):
        """初始化Excel讀取器"""
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """檢查必要依賴"""
        if not PANDAS_AVAILABLE:
            raise ExcelDependencyError("pandas 不可用，無法讀取Excel檔案")

    def read_excel_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        讀取Excel檔案基本資訊

        Args:
            file_path: Excel檔案路徑

        Returns:
            檔案資訊字典

        Raises:
            ExcelFileNotFoundError: 檔案不存在
            ExcelEngineNotAvailableError: 沒有可用引擎
        """
        if not os.path.exists(file_path):
            raise ExcelFileNotFoundError(f"Excel檔案不存在: {file_path}")

        engine = self._get_best_engine(file_path)
        if not engine:
            raise ExcelEngineNotAvailableError(f"沒有可用的引擎處理檔案: {file_path}")

        try:
            with pd.ExcelFile(file_path, engine=engine) as excel_file:
                return {
                    'file_path': file_path,
                    'engine': engine,
                    'sheet_names': excel_file.sheet_names,
                    'sheet_count': len(excel_file.sheet_names),
                    'file_size_mb': round(os.path.getsize(file_path) / (1024 * 1024), 2)
                }

        except Exception as e:
            raise ExcelEngineNotAvailableError(f"讀取Excel檔案資訊失敗: {str(e)}")

    def read_sheet_data(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
        header: Union[int, None] = 0,
        nrows: Optional[int] = None,
        skiprows: Optional[int] = None,
        clean_data: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        讀取指定工作表的資料

        Args:
            file_path: Excel檔案路徑
            sheet_name: 工作表名稱，None表示第一個工作表
            header: 標題列位置
            nrows: 讀取的行數限制
            skiprows: 跳過的行數
            clean_data: 是否清理資料

        Returns:
            DataFrame或None

        Raises:
            ExcelFileNotFoundError: 檔案不存在
            ExcelSheetNotFoundError: 工作表不存在
        """
        if not os.path.exists(file_path):
            raise ExcelFileNotFoundError(f"Excel檔案不存在: {file_path}")

        engine = self._get_best_engine(file_path)
        if not engine:
            raise ExcelEngineNotAvailableError(f"沒有可用的引擎處理檔案: {file_path}")

        try:
            # 準備讀取參數
            read_params = {
                'io': file_path,
                'engine': engine,
                'header': header
            }

            if sheet_name is not None:
                read_params['sheet_name'] = sheet_name
            if nrows is not None:
                read_params['nrows'] = nrows
            if skiprows is not None:
                read_params['skiprows'] = skiprows

            # 讀取資料
            df = pd.read_excel(**read_params)

            if df is None or df.empty:
                print(f"⚠️ 工作表資料為空: {sheet_name}")
                return None

            # 清理資料
            if clean_data:
                df = self._clean_dataframe(df)

            print(f"✅ 成功讀取工作表: {sheet_name or '第一個工作表'}, 資料行數: {len(df)}")
            return df

        except Exception as e:
            if "No sheet named" in str(e):
                raise ExcelSheetNotFoundError(f"找不到工作表: {sheet_name}")
            raise ExcelEngineNotAvailableError(f"讀取工作表失敗: {str(e)}")

    def read_all_sheets(
        self,
        file_path: str,
        clean_data: bool = True,
        max_sheets: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        讀取所有工作表的資料

        Args:
            file_path: Excel檔案路徑
            clean_data: 是否清理資料
            max_sheets: 最大讀取工作表數量

        Returns:
            工作表名稱對應DataFrame的字典

        Raises:
            ExcelFileNotFoundError: 檔案不存在
        """
        if not os.path.exists(file_path):
            raise ExcelFileNotFoundError(f"Excel檔案不存在: {file_path}")

        try:
            file_info = self.read_excel_file_info(file_path)
            sheet_names = file_info['sheet_names']

            if max_sheets:
                sheet_names = sheet_names[:max_sheets]

            sheets_data = {}

            for sheet_name in sheet_names:
                try:
                    df = self.read_sheet_data(file_path, sheet_name, clean_data=clean_data)
                    if df is not None and not df.empty:
                        sheets_data[sheet_name] = df
                        print(f"    ✅ {sheet_name}: {len(df)} 行資料")
                    else:
                        print(f"    ⚠️ {sheet_name}: 空白工作表")

                except Exception as e:
                    print(f"    ❌ {sheet_name}: 讀取失敗 - {str(e)}")
                    continue

            print(f"✅ 成功讀取 {len(sheets_data)} 個工作表")
            return sheets_data

        except Exception as e:
            print(f"❌ 讀取所有工作表失敗: {e}")
            return {}

    def detect_header_row(self, file_path: str, sheet_name: Optional[str] = None) -> int:
        """
        自動檢測標題列位置

        Args:
            file_path: Excel檔案路徑
            sheet_name: 工作表名稱

        Returns:
            標題列位置（從0開始）
        """
        try:
            # 讀取前10列資料進行分析
            df = self.read_sheet_data(file_path, sheet_name, header=None, nrows=10, clean_data=False)

            if df is None or df.empty:
                return 0

            # 尋找最可能的標題列
            best_header_row = 0
            max_non_null_count = 0

            for row_idx in range(min(5, len(df))):  # 只檢查前5列
                row_data = df.iloc[row_idx]
                non_null_count = row_data.notna().sum()

                # 檢查是否包含常見的標題關鍵字
                text_values = [str(val).strip() for val in row_data if pd.notna(val)]
                has_header_keywords = any(
                    keyword in ' '.join(text_values)
                    for keyword in ['當事人', '案由', '案號', '法院', '律師', '客戶', '姓名']
                )

                score = non_null_count
                if has_header_keywords:
                    score += 10  # 加權分數

                if score > max_non_null_count:
                    max_non_null_count = score
                    best_header_row = row_idx

            print(f"🔍 檢測到標題列位置: 第 {best_header_row + 1} 行")
            return best_header_row

        except Exception as e:
            print(f"⚠️ 標題列檢測失敗，使用預設值: {e}")
            return 0

    def get_sheet_preview(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
        max_rows: int = 5
    ) -> Dict[str, Any]:
        """
        取得工作表預覽資訊

        Args:
            file_path: Excel檔案路徑
            sheet_name: 工作表名稱
            max_rows: 預覽行數

        Returns:
            預覽資訊字典
        """
        try:
            # 讀取預覽資料
            df = self.read_sheet_data(file_path, sheet_name, nrows=max_rows, clean_data=False)

            if df is None or df.empty:
                return {
                    'has_data': False,
                    'columns': [],
                    'preview_data': [],
                    'total_columns': 0,
                    'preview_rows': 0
                }

            # 準備預覽資料
            preview_data = []
            for _, row in df.head(max_rows).iterrows():
                preview_data.append([str(val) if pd.notna(val) else '' for val in row])

            return {
                'has_data': True,
                'columns': df.columns.tolist(),
                'preview_data': preview_data,
                'total_columns': len(df.columns),
                'preview_rows': len(preview_data)
            }

        except Exception as e:
            print(f"❌ 取得工作表預覽失敗: {e}")
            return {
                'has_data': False,
                'columns': [],
                'preview_data': [],
                'total_columns': 0,
                'preview_rows': 0,
                'error': str(e)
            }

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理DataFrame資料"""
        if df is None or df.empty:
            return df

        # 移除完全空白的列和欄
        df = df.dropna(how='all').dropna(axis=1, how='all')

        # 清理欄位名稱
        df.columns = [self._clean_column_name(col) for col in df.columns]

        # 清理字串資料中的換行符號和多餘空白
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(lambda x: DataCleaner.clean_text_data(x) if pd.notna(x) else None)

        return df

    def _clean_column_name(self, col_name: str) -> str:
        """清理欄位名稱"""
        if pd.isna(col_name):
            return "未知欄位"

        cleaned = DataCleaner.clean_text_data(col_name)
        return cleaned if cleaned else "未知欄位"

    def _get_best_engine(self, file_path: str) -> Optional[str]:
        """根據檔案格式選擇最佳引擎"""
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.xlsx':
            if OPENPYXL_AVAILABLE:
                return 'openpyxl'
            elif XLRD_AVAILABLE:
                return 'xlrd'
        elif file_ext == '.xls':
            if XLRD_AVAILABLE:
                return 'xlrd'
            elif OPENPYXL_AVAILABLE:
                return 'openpyxl'

        return None

    @staticmethod
    def get_dependency_status() -> Dict[str, bool]:
        """取得依賴狀態"""
        return {
            'pandas': PANDAS_AVAILABLE,
            'openpyxl': OPENPYXL_AVAILABLE,
            'xlrd': XLRD_AVAILABLE
        }