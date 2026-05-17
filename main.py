"""
打印店自动化打印系统
主程序入口
"""
import sys
import logging
import os
from logging.handlers import RotatingFileHandler

# 确保程序目录在Python路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui_main import MainWindow


def setup_logging():
    """设置日志系统"""
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # 设置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # 设置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除已有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 文件处理器（带日志轮转）
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'print_system.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 设置第三方库日志级别
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('watchdog').setLevel(logging.WARNING)
    

def check_dependencies():
    """检查依赖项"""
    required_modules = [
        ('PIL', 'Pillow'),
        ('barcode', 'python-barcode'),
        ('watchdog', 'watchdog'),
        ('win32print', 'pywin32'),
        ('pyttsx3', 'pyttsx3')
    ]
    
    missing = []
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)
            
    if missing:
        print("缺少必要的依赖包，请安装：")
        print(f"pip install {' '.join(missing)}")
        return False
        
    return True


def show_error_dialog(title: str, message: str):
    """显示错误对话框"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        messagebox.showerror(title, message)
        root.destroy()
    except:
        # 如果tkinter不可用，使用控制台输出
        print(f"错误: {message}")


def main():
    """主函数"""
    # 检查是否为打包后的exe文件
    is_packaged = getattr(sys, 'frozen', False)
    
    if not is_packaged:
        # 开发环境下显示启动信息
        print("=" * 50)
        print("打印店自动化打印系统")
        print("版本: 1.4.1")
        print("=" * 50)
    
    # 检查操作系统
    if sys.platform != 'win32':
        error_msg = "本系统仅支持Windows操作系统"
        if is_packaged:
            show_error_dialog("系统错误", error_msg)
        else:
            print(f"错误：{error_msg}")
        return
        
    # 检查依赖项
    if not is_packaged:
        print("检查依赖项...")
        
    if not check_dependencies():
        error_msg = "缺少必要的依赖包，请参考安装说明"
        if is_packaged:
            show_error_dialog("依赖错误", error_msg)
        else:
            print(error_msg)
        return
        
    # 设置日志
    if not is_packaged:
        print("初始化日志系统...")
        
    setup_logging()
    
    # 记录启动信息
    logger = logging.getLogger(__name__)
    logger.info("="*50)
    logger.info("打印店自动化打印系统启动")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"打包模式: {'是' if is_packaged else '否'}")
    logger.info("="*50)
    
    try:
        # 创建并运行主窗口
        if not is_packaged:
            print("启动用户界面...")
            
        app = MainWindow()
        app.run()
        
    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)
        error_msg = f"程序运行出错: {e}\n详细错误信息已记录到日志文件"
        
        if is_packaged:
            show_error_dialog("运行错误", error_msg)
        else:
            print(f"\n{error_msg}")
        
    finally:
        logger.info("打印店自动化打印系统关闭")
        

if __name__ == "__main__":
    main()
