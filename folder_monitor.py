"""
文件夹监控模块
负责监控指定文件夹的子文件夹变化，解析文件夹名称提取信息
"""
import os
import re
import logging
from typing import Dict, List, Optional, Tuple
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirCreatedEvent
from pathlib import Path
import time

class FolderInfo:
    """文件夹信息类"""
    def __init__(self, path: str, name: str, size: str = None, mode: str = None, 
                 count: int = None, order_id: str = None):
        self.path = path
        self.name = name
        self.size = size
        self.mode = mode
        self.count = count
        self.order_id = order_id
        self.images = []
        self.validation_errors = []  # 验证错误列表
        
    def is_valid(self) -> bool:
        """检查文件夹信息是否有效"""
        # 只有在没有严重错误的情况下才认为有效
        critical_errors = ["缺少尺寸信息", "缺少订单号", "文件夹中没有找到支持的图片文件"]
        return not any(error in critical_errors for error in self.validation_errors)
        
    def __repr__(self):
        return f"FolderInfo(name={self.name}, size={self.size}, mode={self.mode}, count={self.count}, order_id={self.order_id}, valid={self.is_valid()})"

class FolderNameParser:
    """文件夹名称解析器"""
    
    # 尺寸映射 - 支持更多格式
    SIZE_PATTERNS = {
        '3寸': ['3寸', '三寸', '3T', '3t', '3inch', '3INCH'],
        '4寸': ['4寸', '四寸', '4T', '4t', '4inch', '4INCH'],
        '5寸': ['5寸', '五寸', '5T', '5t', '5inch', '5INCH'],
        '6寸': ['6寸', '六寸', '6T', '6t', '6inch', '6INCH']
    }
    
    # 模式关键词
    MODE_KEYWORDS = ['拍立得', '全景']
    
    # 订单号正则
    ORDER_ID_PATTERN = re.compile(r'(\d{6}-\d{15})')
    
    # 张数正则
    COUNT_PATTERN = re.compile(r'(\d+)张')
    
    @classmethod
    def parse(cls, folder_name: str) -> FolderInfo:
        """
        解析文件夹名称，提取尺寸、模式、张数、订单号等信息
        
        Args:
            folder_name: 文件夹名称
            
        Returns:
            FolderInfo对象
        """
        folder_info = FolderInfo(path="", name=folder_name)
        
        # 解析尺寸
        folder_info.size = cls._parse_size(folder_name)
        
        # 解析模式
        folder_info.mode = cls._parse_mode(folder_name)
        
        # 解析张数
        folder_info.count = cls._parse_count(folder_name)
        
        # 解析订单号
        folder_info.order_id = cls._parse_order_id(folder_name)
        
        return folder_info
    
    @classmethod
    def _parse_size(cls, name: str) -> Optional[str]:
        """解析尺寸信息"""
        for standard_size, patterns in cls.SIZE_PATTERNS.items():
            for pattern in patterns:
                if pattern in name:
                    return standard_size
        return None
    
    @classmethod
    def _parse_mode(cls, name: str) -> Optional[str]:
        """解析模式信息"""
        for keyword in cls.MODE_KEYWORDS:
            if keyword in name:
                return keyword
        return None
    
    @classmethod
    def _parse_count(cls, name: str) -> Optional[int]:
        """解析张数信息"""
        match = cls.COUNT_PATTERN.search(name)
        if match:
            return int(match.group(1))
        return None
    
    @classmethod
    def _parse_order_id(cls, name: str) -> Optional[str]:
        """解析订单号"""
        match = cls.ORDER_ID_PATTERN.search(name)
        if match:
            return match.group(1)
        return None

class FolderMonitorHandler(FileSystemEventHandler):
    """文件夹监控事件处理器"""
    
    # 支持的图片格式
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.heif', '.heic', '.livp'}
    
    def __init__(self, callback=None):
        """
        初始化处理器
        
        Args:
            callback: 发现新文件夹时的回调函数
        """
        super().__init__()
        self.callback = callback
        self.logger = logging.getLogger(__name__)
        self.processed_folders = set()  # 记录已处理的文件夹，避免重复
        
    def on_created(self, event):
        """处理创建事件"""
        if isinstance(event, DirCreatedEvent):
            # 新文件夹创建
            folder_path = event.src_path
            self._process_folder(folder_path)
    
    def _process_folder(self, folder_path: str):
        """处理文件夹"""
        try:
            # 检查是否已处理
            if folder_path in self.processed_folders:
                return
                
            # 检查是否为直接子文件夹（不处理次级文件夹）
            parent_dir = os.path.dirname(folder_path)
            if parent_dir != self.monitor_path:
                return
                
            folder_name = os.path.basename(folder_path)
            
            # 扩展系统目录列表，避免误判
            system_folders = {
                "异常文件夹", "下发完成", "已完成", "temp", "logs", "config", "exceptions",
                "__pycache__", ".git", ".svn", "node_modules", "venv", "env",
                "打印店系统_用户发布包", "jiaofu", "test", "backup", "备份"
            }
            
            # 系统文件夹检查（包含关键字）
            system_keywords = ["__pycache__", "backup", "temp", "log", "config", "system", "bin"]
            is_system_folder = (
                folder_name in system_folders or
                folder_name.startswith('.') or
                folder_name.startswith('_') or
                any(keyword in folder_name.lower() for keyword in system_keywords)
            )
            
            if is_system_folder:
                self.logger.debug(f"跳过系统目录: {folder_name}")
                self.processed_folders.add(folder_path)  # 标记为已处理
                return
            
            self.logger.info(f"发现新文件夹: {folder_name}")
            
            # 解析文件夹名称
            folder_info = FolderNameParser.parse(folder_name)
            folder_info.path = folder_path
            
            # 验证文件夹名称
            validation_result = self._validate_folder_name(folder_name)
            if not validation_result["valid"]:
                self.logger.warning(f"文件夹名称验证失败: {folder_name}, 错误: {validation_result['errors']}")
                # 标记为已处理并触发异常处理
                self.processed_folders.add(folder_path)
                folder_info.validation_errors = validation_result["errors"]
                if self.callback:
                    self.callback(folder_info)
                return
            
            # 获取图片文件
            folder_info.images = self._get_image_files(folder_path)
            
            # 检查图片文件
            if not folder_info.images:
                self.logger.warning(f"文件夹 {folder_name} 中没有找到图片文件")
                folder_info.validation_errors = ["文件夹中没有找到支持的图片文件"]
            else:
                self.logger.info(f"文件夹 {folder_name} 找到 {len(folder_info.images)} 个图片文件")
            
            # 标记为已处理
            self.processed_folders.add(folder_path)
                
            # 触发回调
            if self.callback:
                try:
                    self.callback(folder_info)
                except Exception as e:
                    self.logger.error(f"回调处理文件夹 {folder_name} 时出错: {e}")
                    
        except Exception as e:
            self.logger.error(f"处理文件夹 {folder_path} 时发生异常: {e}")
            # 即使出错也要标记为已处理，避免重复
            self.processed_folders.add(folder_path)
    
    def _validate_folder_name(self, folder_name: str) -> Dict[str, any]:
        """验证文件夹名称是否符合规范 - 增强版"""
        result = {"valid": True, "errors": []}
        
        # 检查尺寸信息 - 支持更多格式
        size_patterns = [
            "3寸", "三寸", "3T", "3t", "3inch", "3INCH",
            "4寸", "四寸", "4T", "4t", "4inch", "4INCH", 
            "5寸", "五寸", "5T", "5t", "5inch", "5INCH",
            "6寸", "六寸", "6T", "6t", "6inch", "6INCH"
        ]
        
        has_size = any(pattern in folder_name for pattern in size_patterns)
        if not has_size:
            result["valid"] = False
            result["errors"].append("缺少尺寸信息（支持格式：3寸/4寸/5寸/6寸 或 3T/4T/5T/6T）")
        
        # 检查订单号 - 支持更灵活的格式
        order_patterns = [
            r'\d{6}-\d{15}',  # 标准格式：250701-000000000000001
            r'\d{6}-\d{12,18}',  # 灵活格式：允许12-18位数字
            r'\d{4,8}-\d{10,20}',  # 更灵活：4-8位-10-20位
        ]
        
        has_order = any(re.search(pattern, folder_name) for pattern in order_patterns)
        if not has_order:
            result["valid"] = False
            result["errors"].append("缺少订单号（格式：6位数字-15位数字，如：250701-000000000000001）")
        
        # 检查模式信息（可选警告，不影响valid状态）
        mode_patterns = ["拍立得", "全景", "立得", "panorama"]
        if not any(pattern in folder_name.lower() for pattern in mode_patterns):
            result["errors"].append("建议添加模式信息（拍立得/全景）")
        
        return result
    
    def _get_image_files(self, folder_path: str) -> List[str]:
        """获取文件夹中的图片文件 - 修复版"""
        images = []
        try:
            # 标准化路径格式，确保分隔符一致
            folder_path = os.path.normpath(folder_path)
            
            # 检查文件夹是否存在和可访问
            if not os.path.exists(folder_path):
                self.logger.error(f"文件夹不存在: {folder_path}")
                return images
                
            if not os.access(folder_path, os.R_OK):
                self.logger.error(f"无权限访问文件夹: {folder_path}")
                return images
            
            # 获取文件列表
            try:
                files = os.listdir(folder_path)
                self.logger.debug(f"文件夹 {folder_path} 包含 {len(files)} 个项目")
            except PermissionError:
                self.logger.error(f"没有权限读取文件夹: {folder_path}")
                return images
            except Exception as e:
                self.logger.error(f"读取文件夹内容失败: {folder_path}, 错误: {e}")
                return images
            
            # 检查每个文件
            for file in files:
                try:
                    # 使用normpath确保路径分隔符一致
                    file_path = os.path.normpath(os.path.join(folder_path, file))
                    
                    # 检查是否为文件 - 使用更可靠的方法
                    if not os.path.isfile(file_path):
                        self.logger.debug(f"跳过非文件项目: {file}")
                        continue
                    
                    # 检查文件扩展名 - 支持大小写
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.IMAGE_EXTENSIONS:
                        # 使用更可靠的文件检查方法
                        try:
                            # 尝试获取文件信息来确认文件可读
                            file_stat = os.stat(file_path)
                            if file_stat.st_size > 0:  # 文件大小大于0
                                images.append(file_path)
                                self.logger.debug(f"找到图片文件: {file} (大小: {file_stat.st_size} 字节)")
                            else:
                                self.logger.warning(f"图片文件为空: {file_path}")
                        except (OSError, IOError) as e:
                            self.logger.warning(f"无法访问图片文件: {file_path}, 错误: {e}")
                    else:
                        self.logger.debug(f"跳过非图片文件: {file} (扩展名: {ext})")
                        
                except Exception as e:
                    self.logger.warning(f"处理文件 {file} 时出错: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"读取文件夹 {folder_path} 失败: {e}")
        
        self.logger.info(f"文件夹 {folder_path} 共找到 {len(images)} 个图片文件")
        return sorted(images)  # 按文件名排序
    
    def set_monitor_path(self, path: str):
        """设置监控路径"""
        self.monitor_path = path

class FolderMonitor:
    """文件夹监控器"""
    
    def __init__(self, monitor_path: str = None, callback=None):
        """
        初始化监控器
        
        Args:
            monitor_path: 监控的文件夹路径
            callback: 发现新文件夹时的回调函数
        """
        self.monitor_path = monitor_path
        self.callback = callback
        self.observer = None
        self.handler = FolderMonitorHandler(callback)
        self.logger = logging.getLogger(__name__)
        
    def start(self, path: str = None):
        """开始监控"""
        if path:
            self.monitor_path = path
            
        if not self.monitor_path:
            raise ValueError("监控路径不能为空")
            
        if not os.path.exists(self.monitor_path):
            raise ValueError(f"监控路径不存在: {self.monitor_path}")
            
        self.handler.set_monitor_path(self.monitor_path)
        
        # 先扫描现有文件夹
        self._scan_existing_folders()
        
        # 启动监控
        self.observer = Observer()
        self.observer.schedule(self.handler, self.monitor_path, recursive=False)
        self.observer.start()
        
        self.logger.info(f"开始监控文件夹: {self.monitor_path}")
        
    def _scan_existing_folders(self):
        """扫描现有文件夹"""
        try:
            self.logger.info(f"开始扫描现有文件夹: {self.monitor_path}")
            count = 0
            
            # 检查目录是否可访问
            if not os.access(self.monitor_path, os.R_OK):
                self.logger.error(f"无法访问监控路径: {self.monitor_path}")
                return
                
            # 获取目录列表
            try:
                items = os.listdir(self.monitor_path)
            except PermissionError:
                self.logger.error(f"没有权限访问: {self.monitor_path}")
                return
            except Exception as e:
                self.logger.error(f"读取目录失败: {e}")
                return
                
            # 处理每个子目录
            for item in items:
                try:
                    item_path = os.path.join(self.monitor_path, item)
                    if os.path.isdir(item_path):
                        self.handler._process_folder(item_path)
                        count += 1
                        
                        # 每处理10个文件夹暂停一下，避免长时间阻塞
                        if count % 10 == 0:
                            time.sleep(0.01)  # 10ms延迟
                            
                except Exception as e:
                    self.logger.warning(f"处理文件夹 {item} 时出错: {e}")
                    continue
                    
            self.logger.info(f"扫描完成，共发现 {count} 个子文件夹")
            
        except Exception as e:
            self.logger.error(f"扫描现有文件夹失败: {e}")
            # 不抛出异常，允许监控继续启动
    
    def stop(self):
        """停止监控"""
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            self.logger.info("文件夹监控已停止")
    
    def set_callback(self, callback):
        """设置回调函数"""
        self.callback = callback
        self.handler.callback = callback
        
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.observer is not None and self.observer.is_alive()


# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 测试文件夹名称解析
    test_names = [
        "5寸 【拍立得留白】,10张美照250530-620547284501157",
        "3寸 【拍立得留白+塑封防水】,20张PYT250530-114724707961924",
        "【3寸】超清冲印+塑封,10张250424-261693182383496",
        "100张【收藏关注送15张】,3寸【高清打印250516-362178168341431",
        "250406-081138870630593；5寸【拍立得INS】,10张高清升级版+塑封",
        "3寸【拍立得超清速印】,20张250524-581540329770257"
    ]
    
    print("测试文件夹名称解析:")
    for name in test_names:
        info = FolderNameParser.parse(name)
        print(f"\n原始名称: {name}")
        print(f"解析结果: {info}") 
