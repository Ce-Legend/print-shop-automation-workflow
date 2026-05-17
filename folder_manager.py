"""
文件夹管理器
负责管理打印完成后的文件夹移动和异常处理
"""
import os
import shutil
import logging
from datetime import datetime
from typing import Optional


class FolderManager:
    """文件夹管理器"""
    
    def __init__(self, base_path: str):
        """初始化文件夹管理器"""
        self.logger = logging.getLogger(__name__)
        self.base_path = base_path
        
        # 创建目标目录
        self.completed_dir = os.path.join(base_path, "下发完成")
        self.exception_dir = os.path.join(base_path, "异常文件夹")
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保目标目录存在"""
        try:
            os.makedirs(self.completed_dir, exist_ok=True)
            os.makedirs(self.exception_dir, exist_ok=True)
            self.logger.info(f"文件夹管理器初始化完成: {self.base_path}")
        except Exception as e:
            self.logger.error(f"创建目标目录失败: {e}")
    
    def move_to_completed(self, folder_path: str) -> Optional[str]:
        """移动文件夹到完成目录"""
        try:
            if not os.path.exists(folder_path):
                self.logger.warning(f"源文件夹不存在: {folder_path}")
                return None
            
            folder_name = os.path.basename(folder_path)
            target_path = os.path.join(self.completed_dir, folder_name)
            
            # 如果目标已存在，添加时间戳
            if os.path.exists(target_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = os.path.splitext(folder_name)[0]
                target_path = os.path.join(self.completed_dir, f"{base_name}_{timestamp}")
            
            shutil.move(folder_path, target_path)
            self.logger.info(f"文件夹已移动到完成目录: {target_path}")
            return target_path
            
        except Exception as e:
            self.logger.error(f"移动文件夹到完成目录失败: {e}")
            return None
    
    def move_to_exception(self, folder_path: str, reason: str) -> Optional[str]:
        """移动文件夹到异常目录"""
        try:
            if not os.path.exists(folder_path):
                self.logger.warning(f"源文件夹不存在: {folder_path}")
                return None
            
            folder_name = os.path.basename(folder_path)
            
            # 检查是否是系统目录本身，避免自我移动
            system_folders = {"异常文件夹", "下发完成", "已完成", "temp", "logs", "config", "exceptions"}
            if folder_name in system_folders:
                self.logger.warning(f"不能移动系统目录: {folder_name}")
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_name = f"{folder_name}_{timestamp}"
            target_path = os.path.join(self.exception_dir, target_name)
            
            shutil.move(folder_path, target_path)
            
            # 创建异常信息文件
            self._create_exception_log(target_path, reason)
            
            self.logger.warning(f"异常文件夹已移动: {target_path}, 原因: {reason}")
            return target_path
            
        except Exception as e:
            self.logger.error(f"移动文件夹到异常目录失败: {e}")
            return None
    
    def _create_exception_log(self, folder_path: str, reason: str):
        """创建异常日志文件"""
        try:
            log_file = os.path.join(folder_path, "异常信息.txt")
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"异常时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"异常原因: {reason}\n")
                f.write(f"文件夹路径: {folder_path}\n")
        except Exception as e:
            self.logger.error(f"创建异常日志失败: {e}")
    
    def cleanup_old_folders(self, days: int = 30):
        """清理旧的文件夹"""
        try:
            import time
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            for directory in [self.completed_dir, self.exception_dir]:
                if not os.path.exists(directory):
                    continue
                    
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    if os.path.isdir(item_path):
                        stat = os.stat(item_path)
                        if stat.st_mtime < cutoff_time:
                            shutil.rmtree(item_path)
                            self.logger.info(f"清理旧文件夹: {item_path}")
                            
        except Exception as e:
            self.logger.error(f"清理旧文件夹失败: {e}") 