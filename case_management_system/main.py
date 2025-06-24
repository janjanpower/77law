import sys

def main():
    """主程式入口"""
    try:
        # 確保模組可以導入
        from views.main_window import MainWindow
        from config.settings import AppConfig

        # 初始化主視窗
        app = MainWindow()

        # 啟動主迴圈
        app.run()

    except ImportError as e:
        print(f"模組導入錯誤: {e}")
        print("請確認所有檔案都已正確放置在對應目錄中")
        sys.exit(1)
    except Exception as e:
        print(f"程式執行錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()