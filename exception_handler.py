"""
异常处理模块
负责处理无法匹配预置的文件夹，移动到异常文件夹并记录日志
"""
import os
import shutil
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path


class ExceptionHandler:
    """异常处理器"""
    
    def __init__(self, exception_folder: str = "异常文件夹"):
        """
        初始化异常处理器
        
        Args:
            exception_folder: 异常文件夹名称
        """
        self.logger = logging.getLogger(__name__)
        self.exception_folder = exception_folder
        
    def handle_exception_folder(self, folder_path: str, reason: str, 
                               monitor_path: str = None) -> bool:
        """
        处理异常文件夹
        
        Args:
            folder_path: 要处理的文件夹路径
            reason: 异常原因
            monitor_path: 监控根目录路径
            
        Returns:
            是否处理成功
        """
        try:
            # 确定异常文件夹路径
            if monitor_path:
                exception_path = os.path.join(monitor_path, self.exception_folder)
            else:
                exception_path = os.path.join(os.path.dirname(folder_path), self.exception_folder)
                
            # 确保异常文件夹存在
            os.makedirs(exception_path, exist_ok=True)
            
            # 获取文件夹名称
            folder_name = os.path.basename(folder_path)
            
            # 目标路径
            target_path = os.path.join(exception_path, folder_name)
            
            # 如果目标已存在，添加时间戳
            if os.path.exists(target_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                folder_name_with_time = f"{folder_name}_{timestamp}"
                target_path = os.path.join(exception_path, folder_name_with_time)
                
            # 移动文件夹
            shutil.move(folder_path, target_path)
            self.logger.info(f"已将文件夹移动到异常目录: {folder_name}")
            
            # 创建异常日志
            self.create_exception_log(target_path, reason)
            
            return True
            
        except Exception as e:
            self.logger.error(f"处理异常文件夹失败: {e}")
            return False
            
    def create_exception_log(self, folder_path: str, reason: str):
        """
        创建异常日志文件
        
        Args:
            folder_path: 文件夹路径
            reason: 异常原因
        """
        try:
            # 日志文件路径
            log_file = os.path.join(folder_path, "异常说明.txt")
            
            # 获取文件夹信息
            folder_name = os.path.basename(folder_path)
            
            # 统计文件夹内容
            total_files = 0
            image_files = 0
            other_files = 0
            subdirs = 0
            
            image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.heif', '.heic', '.livp'}
            
            for root, dirs, files in os.walk(folder_path):
                if root == folder_path:  # 只统计第一层
                    subdirs = len(dirs)
                    for file in files:
                        total_files += 1
                        ext = os.path.splitext(file)[1].lower()
                        if ext in image_extensions:
                            image_files += 1
                        else:
                            other_files += 1
                            
            # 构建日志内容
            log_content = f"""打印店自动化系统 - 异常文件夹处理记录
========================================

处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
文件夹名称: {folder_name}

异常原因:
{reason}

文件夹内容统计:
- 图片文件: {image_files} 个
- 其他文件: {other_files} 个
- 子文件夹: {subdirs} 个
- 文件总数: {total_files} 个

处理建议:
1. 检查文件夹名称是否包含正确的尺寸信息（3寸/4寸/5寸/6寸）
2. 确认打印预置配置是否正确
3. 如果是新的打印需求，请联系管理员添加相应的预置配置

注意事项:
- 此文件夹已被移动到异常文件夹目录
- 处理完成后可以将文件夹移回监控目录重新处理
- 如需手动打印，请使用常规打印方式

========================================
"""
            
            # 写入日志文件
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)
                
            self.logger.info(f"已创建异常日志: {log_file}")
            
        except Exception as e:
            self.logger.error(f"创建异常日志失败: {e}")
            
    def get_exception_folders(self, monitor_path: str) -> list:
        """
        获取异常文件夹列表
        
        Args:
            monitor_path: 监控根目录路径
            
        Returns:
            异常文件夹信息列表
        """
        exception_folders = []
        exception_path = os.path.join(monitor_path, self.exception_folder)
        
        if not os.path.exists(exception_path):
            return exception_folders
            
        try:
            for item in os.listdir(exception_path):
                item_path = os.path.join(exception_path, item)
                if os.path.isdir(item_path):
                    # 检查是否有异常日志
                    log_file = os.path.join(item_path, "异常说明.txt")
                    has_log = os.path.exists(log_file)
                    
                    # 获取文件夹修改时间
                    mtime = os.path.getmtime(item_path)
                    
                    exception_folders.append({
                        'name': item,
                        'path': item_path,
                        'has_log': has_log,
                        'time': datetime.fromtimestamp(mtime)
                    })
                    
            # 按时间排序（最新的在前）
            exception_folders.sort(key=lambda x: x['time'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"获取异常文件夹列表失败: {e}")
            
        return exception_folders
        
    def restore_folder(self, folder_path: str, monitor_path: str) -> bool:
        """
        恢复异常文件夹到监控目录
        
        Args:
            folder_path: 异常文件夹路径
            monitor_path: 监控根目录路径
            
        Returns:
            是否恢复成功
        """
        try:
            folder_name = os.path.basename(folder_path)
            target_path = os.path.join(monitor_path, folder_name)
            
            # 如果目标已存在，添加时间戳
            if os.path.exists(target_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                folder_name_with_time = f"{folder_name}_{timestamp}"
                target_path = os.path.join(monitor_path, folder_name_with_time)
                
            # 删除异常日志文件
            log_file = os.path.join(folder_path, "异常说明.txt")
            if os.path.exists(log_file):
                os.remove(log_file)
                
            # 移动文件夹
            shutil.move(folder_path, target_path)
            self.logger.info(f"已恢复文件夹到监控目录: {folder_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"恢复文件夹失败: {e}")
            return False
            
    def clean_old_exceptions(self, monitor_path: str, days: int = 7) -> int:
        """
        清理超过指定天数的异常文件夹
        
        Args:
            monitor_path: 监控根目录路径
            days: 保留天数
            
        Returns:
            清理的文件夹数量
        """
        cleaned_count = 0
        exception_path = os.path.join(monitor_path, self.exception_folder)
        
        if not os.path.exists(exception_path):
            return cleaned_count
            
        try:
            current_time = datetime.now()
            
            for item in os.listdir(exception_path):
                item_path = os.path.join(exception_path, item)
                if os.path.isdir(item_path):
                    # 获取文件夹修改时间
                    mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                    
                    # 计算天数差
                    days_diff = (current_time - mtime).days
                    
                    if days_diff > days:
                        # 删除文件夹
                        shutil.rmtree(item_path)
                        cleaned_count += 1
                        self.logger.info(f"已清理过期异常文件夹: {item}")
                        
        except Exception as e:
            self.logger.error(f"清理异常文件夹失败: {e}")
            
        return cleaned_count


# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建异常处理器
    handler = ExceptionHandler()
    
    # 测试创建异常日志
    test_folder = "./test_exception_folder"
    os.makedirs(test_folder, exist_ok=True)
    
    # 创建一些测试文件
    with open(os.path.join(test_folder, "test.jpg"), 'w') as f:
        f.write("test image")
        
    with open(os.path.join(test_folder, "test.txt"), 'w') as f:
        f.write("test text")
        
    # 测试处理异常文件夹
    print("测试处理异常文件夹...")
    success = handler.handle_exception_folder(
        test_folder,
        "无法匹配预置：文件夹名称中未找到有效的尺寸信息",
        "./"
    )
    
    if success:
        print("异常文件夹处理成功")
        
        # 获取异常文件夹列表
        exceptions = handler.get_exception_folders("./")
        print(f"\n异常文件夹列表 ({len(exceptions)} 个):")
        for exc in exceptions:
            print(f"  - {exc['name']} (有日志: {'是' if exc['has_log'] else '否'})")
    else:
        print("异常文件夹处理失败") 