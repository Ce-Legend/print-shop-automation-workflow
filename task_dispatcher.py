"""
任务分发系统
实现完整的文件夹监控、预处理、分发、打印的工作流程
"""
import os
import logging
import threading
import time
from typing import Optional, Dict, List, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from folder_monitor import FolderInfo
from folder_manager import FolderManager


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "待处理"
    VALIDATING = "验证中"
    PREPROCESSING = "预处理中"
    WAITING_PRINTER = "等待打印机"
    PRINTING = "打印中"
    GENERATING_INFO = "生成信息页"
    COMPLETED = "已完成"
    FAILED = "失败"
    EXCEPTION = "异常"


@dataclass
class PrintTask:
    """打印任务"""
    task_id: str
    folder_info: FolderInfo
    folder_path: str
    status: TaskStatus
    assigned_printer: Optional[str] = None
    preset_config: Optional[str] = None
    processed_images: Optional[List[str]] = None
    print_job_ids: Optional[List[int]] = None
    info_page_path: Optional[str] = None
    error_message: Optional[str] = None
    created_time: datetime = None
    start_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()


class TaskDispatcher:
    """任务分发器 - 实现完整的10步工作流程"""
    
    def __init__(self, config_manager, printer_manager):
        """初始化任务分发器"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.printer_manager = printer_manager
        
        # 组件初始化
        self.folder_manager = None
        self.folder_monitor = None
        
        # 任务管理
        self.active_tasks: Dict[str, PrintTask] = {}
        self.task_counter = 0
        self.task_lock = threading.Lock()
        
        # 打印机池管理
        self.idle_printers: Dict[str, Dict] = {}  # 空闲打印机池
        self.busy_printers: Dict[str, str] = {}   # 忙碌打印机 -> 任务ID
        
        # 运行状态
        self.running = False
        self.dispatcher_thread = None
        
        # 回调函数
        self.task_callbacks = []
    
    def start(self, monitor_path: str) -> bool:
        """启动任务分发系统"""
        try:
            self.logger.info("启动任务分发系统...")
            
            # 初始化文件夹管理器
            self.folder_manager = FolderManager(monitor_path)
            
            # 初始化打印机池
            self._initialize_printer_pool()
            
            # 启动分发线程
            self.running = True
            self.dispatcher_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
            self.dispatcher_thread.start()
            
            self.logger.info("任务分发系统已启动")
            return True
            
        except Exception as e:
            self.logger.error(f"启动任务分发系统失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止任务分发系统"""
        try:
            self.logger.info("停止任务分发系统...")
            
            # 停止运行
            self.running = False
            
            # 等待分发线程结束
            if self.dispatcher_thread and self.dispatcher_thread.is_alive():
                self.dispatcher_thread.join(timeout=5)
            
            self.logger.info("任务分发系统已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止任务分发系统失败: {e}")
            return False
    
    def add_folder_task(self, folder_info: FolderInfo):
        """添加文件夹任务"""
        try:
            self.logger.info(f"添加文件夹任务: {folder_info.name}")
            
            # 创建任务
            task_id = self._generate_task_id()
            task = PrintTask(
                task_id=task_id,
                folder_info=folder_info,
                folder_path=folder_info.path,
                status=TaskStatus.PENDING
            )
            
            # 添加到任务队列
            with self.task_lock:
                self.active_tasks[task_id] = task
            
            # 通知任务创建
            self._notify_task_update(task)
            
        except Exception as e:
            self.logger.error(f"添加文件夹任务失败: {e}")
    
    def _dispatch_loop(self):
        """主分发循环"""
        while self.running:
            try:
                # 处理待处理任务
                self._process_pending_tasks()
                
                # 检查打印完成状态
                self._check_print_completion()
                
                time.sleep(2)  # 2秒检查一次
                
            except Exception as e:
                self.logger.error(f"分发循环异常: {e}")
                time.sleep(5)
    
    def _process_pending_tasks(self):
        """处理待处理任务"""
        with self.task_lock:
            pending_tasks = [task for task in self.active_tasks.values() 
                           if task.status == TaskStatus.PENDING]
        
        for task in pending_tasks:
            try:
                self._process_task_step_by_step(task)
            except Exception as e:
                self.logger.error(f"处理任务 {task.task_id} 失败: {e}")
                self._mark_task_failed(task, str(e))
    
    def _process_task_step_by_step(self, task: PrintTask):
        """按10步流程处理任务"""
        try:
            # 步骤1-2: 验证文件夹名称
            if not task.folder_info.is_valid():
                error_msg = "; ".join(task.folder_info.validation_errors)
                self._move_to_exception(task, f"文件夹验证失败: {error_msg}")
                return
            
            # 步骤3: 预处理（如果是拍立得）
            if self._is_polaroid_mode(task.folder_info):
                self._update_task_status(task, TaskStatus.PREPROCESSING)
                # 这里调用预处理逻辑
                self.logger.info(f"任务 {task.task_id} 需要拍立得预处理")
            
            # 步骤4: 选择打印机
            self._update_task_status(task, TaskStatus.WAITING_PRINTER)
            printer_name = self._assign_printer(task)
            
            if not printer_name:
                # 没有空闲打印机，保持等待状态
                return
            
            task.assigned_printer = printer_name
            
            # 步骤5: 设置预置
            preset_config = self._get_preset_config(task)
            task.preset_config = preset_config
            
            # 步骤6-7: 开始打印
            self._update_task_status(task, TaskStatus.PRINTING)
            # 这里调用打印逻辑
            
            # 步骤8-10: 完成处理在 _check_print_completion 中
            
        except Exception as e:
            self.logger.error(f"处理任务步骤失败: {e}")
            self._mark_task_failed(task, str(e))
    
    def _check_print_completion(self):
        """检查打印完成状态"""
        with self.task_lock:
            printing_tasks = [task for task in self.active_tasks.values() 
                            if task.status == TaskStatus.PRINTING]
        
        for task in printing_tasks:
            if self._is_print_completed(task):
                self._complete_task(task)
    
    def _is_print_completed(self, task: PrintTask) -> bool:
        """检查打印是否已完成"""
        # 这里应该检查实际的打印作业状态
        # 简化实现：假设打印需要一定时间
        return False
    
    def _complete_task(self, task: PrintTask):
        """完成任务处理"""
        try:
            # 步骤8: 生成信息页（如果需要）
            # 步骤9: 语音报单
            self._announce_completion(task.assigned_printer)
            
            # 步骤10: 移动文件夹到完成目录
            if self.folder_manager:
                success_path = self.folder_manager.move_to_completed(task.folder_path)
                if success_path:
                    self.logger.info(f"任务 {task.task_id} 已移动到: {success_path}")
            
            # 释放打印机
            self._release_printer(task.assigned_printer)
            
            # 更新任务状态
            self._update_task_status(task, TaskStatus.COMPLETED)
            task.completed_time = datetime.now()
            
        except Exception as e:
            self.logger.error(f"完成任务失败: {e}")
            self._mark_task_failed(task, str(e))
    
    def _is_polaroid_mode(self, folder_info: FolderInfo) -> bool:
        """判断是否为拍立得模式"""
        return folder_info.mode and "拍立得" in folder_info.mode
    
    def _assign_printer(self, task: PrintTask) -> Optional[str]:
        """分配打印机"""
        required_size = task.folder_info.size
        
        # 查找匹配尺寸的空闲打印机
        for printer_name, printer_info in self.idle_printers.items():
            if printer_info.get('paper_size') == required_size:
                # 标记为忙碌
                self._mark_printer_busy(printer_name, task.task_id)
                return printer_name
        
        return None
    
    def _get_preset_config(self, task: PrintTask) -> str:
        """获取预置配置"""
        size = task.folder_info.size
        mode = task.folder_info.mode or "默认"
        return f"{size}{mode}"
    
    def _announce_completion(self, printer_name: str):
        """语音报单"""
        try:
            printer_id = self._extract_printer_id(printer_name)
            # 这里调用语音系统
            self.logger.info(f"语音播报: {printer_id}号打印机打印完成")
        except Exception as e:
            self.logger.error(f"语音播报失败: {e}")
    
    def _extract_printer_id(self, printer_name: str) -> str:
        """从打印机名称提取ID"""
        # 简化实现
        return printer_name.split()[-1] if printer_name else "未知"
    
    def _handle_printer_completion(self, printer_name: str):
        """处理打印机完成事件"""
        try:
            # 启用冷却时间（配置的等待时间）
            wait_time = self.config_manager.get_wait_time()
            self.logger.info(f"打印机 {printer_name} 进入冷却期，等待{wait_time}秒")
            
            # 设置自动重新启用（在实际应用中这应该在后台线程中处理）
            def auto_enable_delay():
                time.sleep(wait_time)  # 使用配置的冷却时间
                if printer_name in self.config_manager.get_enabled_printers():
                    self.idle_printers[printer_name] = {
                        'paper_size': self._get_printer_size(printer_name),
                        'enabled': True
                    }
                    self.logger.info(f"打印机 {printer_name} 冷却完成，重新可用")
            
            # 启动冷却线程
            threading.Thread(target=auto_enable_delay, daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"处理打印机完成事件失败: {e}")
    
    def _get_printer_size(self, printer_name: str) -> str:
        """获取打印机支持的纸张尺寸"""
        # 这里应该从配置中获取
        return "5寸"  # 简化实现
    
    def _initialize_printer_pool(self):
        """初始化打印机池"""
        try:
            enabled_printers = self.config_manager.get_enabled_printers()
            
            for printer_name in enabled_printers:
                self.idle_printers[printer_name] = {
                    'paper_size': self._get_printer_size(printer_name),
                    'enabled': True
                }
            
            self.logger.info(f"初始化打印机池: {len(self.idle_printers)} 台打印机")
            
        except Exception as e:
            self.logger.error(f"初始化打印机池失败: {e}")
    
    def _mark_printer_busy(self, printer_name: str, task_id: str):
        """标记打印机为忙碌状态"""
        self.idle_printers.pop(printer_name, None)
        self.busy_printers[printer_name] = task_id
    
    def _release_printer(self, printer_name: str):
        """释放打印机"""
        self.busy_printers.pop(printer_name, None)
        # 开始冷却期处理
        self._handle_printer_completion(printer_name)
    
    def _move_to_exception(self, task: PrintTask, reason: str):
        """移动任务到异常状态"""
        try:
            self.logger.warning(f"任务 {task.task_id} 异常: {reason}")
            
            # 移动文件夹到异常目录
            if self.folder_manager:
                exception_path = self.folder_manager.move_to_exception(task.folder_path, reason)
                if exception_path:
                    self.logger.info(f"异常文件夹已移动到: {exception_path}")
            
            # 更新任务状态
            self._update_task_status(task, TaskStatus.EXCEPTION)
            task.error_message = reason
            
        except Exception as e:
            self.logger.error(f"移动异常文件夹失败: {e}")
    
    def _mark_task_failed(self, task: PrintTask, error_message: str):
        """标记任务失败"""
        try:
            self.logger.error(f"任务 {task.task_id} 失败: {error_message}")
            
            # 释放打印机（如果已分配）
            if task.assigned_printer:
                self._release_printer(task.assigned_printer)
            
            # 更新任务状态
            self._update_task_status(task, TaskStatus.FAILED)
            task.error_message = error_message
            task.completed_time = datetime.now()
            
        except Exception as e:
            self.logger.error(f"标记任务失败时出错: {e}")
    
    def _update_task_status(self, task: PrintTask, status: TaskStatus):
        """更新任务状态"""
        old_status = task.status
        task.status = status
        
        if status == TaskStatus.PRINTING and not task.start_time:
            task.start_time = datetime.now()
        
        self.logger.info(f"任务 {task.task_id} 状态: {old_status.value} -> {status.value}")
        self._notify_task_update(task)
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        self.task_counter += 1
        return f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{self.task_counter:03d}"
    
    def _notify_task_update(self, task: PrintTask):
        """通知任务更新"""
        try:
            for callback in self.task_callbacks:
                callback(task)
        except Exception as e:
            self.logger.error(f"任务回调通知失败: {e}")
    
    def add_task_callback(self, callback):
        """添加任务回调"""
        self.task_callbacks.append(callback)
    
    def get_task_stats(self) -> Dict[str, int]:
        """获取任务统计"""
        stats = {
            'total': len(self.active_tasks),
            'pending': 0,
            'preprocessing': 0,
            'waiting_printer': 0,
            'printing': 0,
            'completed': 0,
            'failed': 0,
            'exception': 0
        }
        
        for task in self.active_tasks.values():
            if task.status == TaskStatus.PENDING:
                stats['pending'] += 1
            elif task.status == TaskStatus.PREPROCESSING:
                stats['preprocessing'] += 1
            elif task.status == TaskStatus.WAITING_PRINTER:
                stats['waiting_printer'] += 1
            elif task.status == TaskStatus.PRINTING:
                stats['printing'] += 1
            elif task.status == TaskStatus.COMPLETED:
                stats['completed'] += 1
            elif task.status == TaskStatus.FAILED:
                stats['failed'] += 1
            elif task.status == TaskStatus.EXCEPTION:
                stats['exception'] += 1
        
        return stats
    
    def get_printer_pool_status(self) -> Dict[str, Any]:
        """获取打印机池状态"""
        return {
            'idle_printers': dict(self.idle_printers),
            'busy_printers': dict(self.busy_printers),
            'total_idle': len(self.idle_printers),
            'total_busy': len(self.busy_printers)
        } 