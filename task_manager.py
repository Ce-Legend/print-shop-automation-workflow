"""
打印任务管理模块
负责维护打印任务队列、匹配打印预置、分发任务到打印机
"""
import os
import uuid
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from queue import Queue, PriorityQueue
from enum import Enum
from dataclasses import dataclass, field

from config_manager import ConfigManager
from folder_monitor import FolderInfo


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "等待中"
    PREPROCESSING = "预处理中"
    PRINTING = "打印中"
    COMPLETED = "已完成"
    FAILED = "失败"
    EXCEPTION = "异常"


@dataclass
class PrintTask:
    """打印任务类"""
    task_id: str
    folder_info: FolderInfo
    preset: str = None
    printer: str = None
    status: TaskStatus = TaskStatus.PENDING
    created_time: datetime = field(default_factory=datetime.now)
    start_time: datetime = None
    end_time: datetime = None
    error_message: str = None
    priority: int = 0  # 优先级，数字越小优先级越高
    actual_printed_count: int = 0  # 实际打印数量
    info_page_path: str = None  # 信息页路径
    preprocessed_images: List[str] = field(default_factory=list)  # 预处理后的图片
    
    def __lt__(self, other):
        """用于优先队列排序"""
        return self.priority < other.priority


class TaskManager:
    """任务管理器"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化任务管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 任务队列（按打印机分组）
        self.printer_queues: Dict[str, PriorityQueue] = {}
        
        # 当前正在处理的任务
        self.active_tasks: Dict[str, PrintTask] = {}
        
        # 所有任务记录
        self.all_tasks: Dict[str, PrintTask] = {}
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 任务分配策略
        self.round_robin_index = 0
        
        # 回调函数
        self.on_task_created = None
        self.on_task_status_changed = None
        
    def create_task(self, folder_info: FolderInfo) -> Optional[PrintTask]:
        """
        创建打印任务
        
        Args:
            folder_info: 文件夹信息
            
        Returns:
            创建的打印任务，如果无法匹配预置则返回None
        """
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务
        task = PrintTask(
            task_id=task_id,
            folder_info=folder_info
        )
        
        # 匹配预置
        preset = self._match_preset(folder_info)
        if not preset:
            self.logger.warning(f"无法为文件夹 {folder_info.name} 匹配预置")
            task.status = TaskStatus.EXCEPTION
            task.error_message = "无法匹配预置"
            return task
            
        task.preset = preset
        
        # 分配打印机
        printer = self._assign_printer(task)
        if not printer:
            self.logger.error(f"没有可用的打印机")
            task.status = TaskStatus.EXCEPTION
            task.error_message = "没有可用的打印机"
            return task
            
        task.printer = printer
        
        # 添加到队列
        with self.lock:
            if printer not in self.printer_queues:
                self.printer_queues[printer] = PriorityQueue()
            
            self.printer_queues[printer].put(task)
            self.all_tasks[task_id] = task
            
        self.logger.info(f"创建任务 {task_id}: {folder_info.name} -> {printer}")
        
        # 触发回调
        if self.on_task_created:
            self.on_task_created(task)
            
        return task
    
    def _match_preset(self, folder_info: FolderInfo) -> Optional[str]:
        """
        根据文件夹信息匹配预置
        
        匹配规则：
        1. 3寸/三寸 -> 5寸拍立得
        2. 4寸/四寸 -> 6寸拍立得
        3. 5寸/五寸 + 全景 -> 5寸全景
        4. 5寸/五寸 + 拍立得 -> 5寸拍立得
        5. 6寸/六寸 + 全景 -> 6寸全景
        6. 6寸/六寸 + 拍立得 -> 6寸拍立得
        """
        if not folder_info.size:
            return None
            
        # 获取预置
        preset = self.config_manager.get_preset_for_size_mode(
            folder_info.size, 
            folder_info.mode
        )
        
        return preset
    
    def _assign_printer(self, task: PrintTask) -> Optional[str]:
        """
        为任务分配打印机
        优先分配虚拟打印机（便于测试），然后使用轮询策略
        """
        enabled_printers = list(self.config_manager.get_enabled_printers().keys())
        
        if not enabled_printers:
            return None
        
        # 优先分配虚拟打印机（便于测试）
        virtual_printers = [p for p in enabled_printers if "(虚拟)" in p]
        if virtual_printers:
            # 在虚拟打印机中轮询
            printer = virtual_printers[self.round_robin_index % len(virtual_printers)]
            self.round_robin_index += 1
            self.logger.info(f"任务 {task.task_id} 分配给虚拟打印机: {printer}")
            return printer
        
        # 没有虚拟打印机时，分配给真实打印机
        printer = enabled_printers[self.round_robin_index % len(enabled_printers)]
        self.round_robin_index += 1
        
        return printer
    
    def get_next_task(self, printer_name: str) -> Optional[PrintTask]:
        """
        获取指定打印机的下一个任务
        
        Args:
            printer_name: 打印机名称
            
        Returns:
            下一个待处理的任务，如果没有则返回None
        """
        with self.lock:
            if printer_name not in self.printer_queues:
                return None
                
            queue = self.printer_queues[printer_name]
            if queue.empty():
                return None
                
            task = queue.get()
            self.active_tasks[printer_name] = task
            
        return task
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          error_message: str = None):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            error_message: 错误信息（可选）
        """
        with self.lock:
            if task_id not in self.all_tasks:
                self.logger.error(f"任务 {task_id} 不存在")
                return
                
            task = self.all_tasks[task_id]
            old_status = task.status
            task.status = status
            
            if error_message:
                task.error_message = error_message
                
            # 更新时间戳
            if status == TaskStatus.PRINTING and task.start_time is None:
                task.start_time = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.end_time = datetime.now()
                # 从活动任务中移除
                if task.printer in self.active_tasks:
                    del self.active_tasks[task.printer]
                    
        self.logger.info(f"任务 {task_id} 状态更新: {old_status.value} -> {status.value}")
        
        # 触发回调
        if self.on_task_status_changed:
            self.on_task_status_changed(task, old_status, status)
    
    def get_task(self, task_id: str) -> Optional[PrintTask]:
        """获取任务信息"""
        return self.all_tasks.get(task_id)
    
    def get_printer_queue_size(self, printer_name: str) -> int:
        """获取打印机队列大小"""
        with self.lock:
            if printer_name not in self.printer_queues:
                return 0
            return self.printer_queues[printer_name].qsize()
    
    def get_active_task(self, printer_name: str) -> Optional[PrintTask]:
        """获取打印机当前正在处理的任务"""
        return self.active_tasks.get(printer_name)
    
    def get_all_tasks(self, status: TaskStatus = None) -> List[PrintTask]:
        """
        获取所有任务
        
        Args:
            status: 筛选状态，None表示所有状态
            
        Returns:
            任务列表
        """
        tasks = list(self.all_tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_time, reverse=True)
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        with self.lock:
            completed_ids = [
                task_id for task_id, task in self.all_tasks.items()
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            ]
            for task_id in completed_ids:
                del self.all_tasks[task_id]
                
        self.logger.info(f"清理了 {len(completed_ids)} 个已完成任务")
    
    def requeue_task(self, task_id: str):
        """
        重新排队任务
        
        Args:
            task_id: 任务ID
        """
        with self.lock:
            if task_id not in self.all_tasks:
                self.logger.error(f"任务 {task_id} 不存在")
                return
                
            task = self.all_tasks[task_id]
            if task.status == TaskStatus.COMPLETED:
                self.logger.warning(f"任务 {task_id} 已完成，不能重新排队")
                return
                
            # 重置状态
            task.status = TaskStatus.PENDING
            task.start_time = None
            task.end_time = None
            task.error_message = None
            
            # 重新加入队列
            if task.printer and task.printer in self.printer_queues:
                self.printer_queues[task.printer].put(task)
                
        self.logger.info(f"任务 {task_id} 已重新排队")
        
    def get_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        stats = {
            "total": len(self.all_tasks),
            "pending": 0,
            "preprocessing": 0,
            "printing": 0,
            "completed": 0,
            "failed": 0,
            "exception": 0,
            "printer_stats": {}
        }
        
        for task in self.all_tasks.values():
            stats[task.status.name.lower()] += 1
            
            if task.printer:
                if task.printer not in stats["printer_stats"]:
                    stats["printer_stats"][task.printer] = {
                        "total": 0,
                        "completed": 0,
                        "failed": 0,
                        "queue_size": self.get_printer_queue_size(task.printer)
                    }
                    
                stats["printer_stats"][task.printer]["total"] += 1
                if task.status == TaskStatus.COMPLETED:
                    stats["printer_stats"][task.printer]["completed"] += 1
                elif task.status == TaskStatus.FAILED:
                    stats["printer_stats"][task.printer]["failed"] += 1
                    
        return stats 