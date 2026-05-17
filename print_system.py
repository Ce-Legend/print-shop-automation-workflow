"""
打印系统核心类
整合所有模块，提供统一的接口
"""
import os
import logging
import threading
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

# 导入所有模块
from config_manager import ConfigManager
from folder_monitor import FolderMonitor, FolderInfo
from task_manager import TaskManager, TaskStatus, PrintTask
from info_page_generator import InfoPageGenerator
from printer_manager import PrinterManager, PrinterError
from print_executor import PrintExecutor
from log_manager import LogManager
from image_preprocessor import ImagePreprocessor
from voice_announcer import VoiceAnnouncer
from exception_handler import ExceptionHandler
from task_dispatcher import TaskDispatcher  # 新增任务分发器

# 新增第三阶段功能模块
from enhanced_exception_handler import EnhancedExceptionHandler
from batch_print_manager import BatchPrintManager
from independent_voice_system import IndependentVoiceSystem


class PrintSystem:
    """打印系统主类"""
    
    def __init__(self):
        """初始化打印系统"""
        self.logger = logging.getLogger(__name__)
        
        # 初始化所有模块
        self.config_manager = ConfigManager()
        self.folder_monitor = FolderMonitor()
        self.task_manager = TaskManager(self.config_manager)
        self.info_page_generator = InfoPageGenerator()
        self.printer_manager = PrinterManager()
        self.print_executor = PrintExecutor()
        self.log_manager = LogManager()
        self.image_preprocessor = ImagePreprocessor(self.config_manager)
        self.voice_announcer = VoiceAnnouncer()
        self.exception_handler = ExceptionHandler(
            self.config_manager.get_exception_folder()
        )
        
        # 新增任务分发器
        self.task_dispatcher = TaskDispatcher(self.config_manager, self.printer_manager)
        
        # 第三阶段新增功能模块
        self.enhanced_exception_handler = EnhancedExceptionHandler(self.config_manager)
        self.batch_print_manager = BatchPrintManager(
            config_manager=self.config_manager,
            print_executor=self.print_executor,
            voice_announcer=self.voice_announcer
        )
        self.independent_voice_system = IndependentVoiceSystem()
        
        # 系统状态
        self._running = False
        self._paused = False
        self._print_workers = {}  # 打印机工作线程
        
        # 设置回调
        self._setup_callbacks()
        
    def _setup_callbacks(self):
        """设置各模块的回调函数"""
        # 文件夹监控回调
        self.folder_monitor.set_callback(self._on_folder_detected)
        
        # 任务管理器回调
        self.task_manager.on_task_created = self._on_task_created
        self.task_manager.on_task_status_changed = self._on_task_status_changed
        
        # 打印机状态回调
        self.printer_manager.add_status_callback(self._on_printer_status_changed)
        
        # 打印执行器回调
        self.print_executor.add_job_callback(self._on_print_job_update)
        
    def start(self) -> bool:
        """启动系统"""
        if self._running:
            self.logger.warning("系统已经在运行")
            return False
            
        try:
            # 检查监控路径
            monitor_path = self.config_manager.get_monitor_path()
            if not monitor_path or not os.path.exists(monitor_path):
                self.logger.error("监控路径未设置或不存在")
                return False
                
            self._running = True
            self._paused = False
            
            # 启动语音播报
            self.voice_announcer.start()
            self.voice_announcer.announce_custom("打印系统已启动")
            
            # 启动打印机监控
            self.printer_manager.start_monitoring()
            
            # 启动新的任务分发系统
            self.task_dispatcher.start(monitor_path)
            
            # 启动第三阶段新功能
            self.enhanced_exception_handler.start()
            self.batch_print_manager.start()
            
            # 设置任务分发器的文件夹检测回调
            self.folder_monitor.set_callback(self.task_dispatcher.add_folder_task)
            
            # 启动文件夹监控
            self.folder_monitor.start(monitor_path)
            
            # 为每个启用的打印机启动工作线程（保留原有逻辑作为备份）
            enabled_printers = self.config_manager.get_enabled_printers()
            for printer_name, printer_config in enabled_printers.items():
                self._start_printer_worker(printer_name, printer_config)
                
            self.logger.info("打印系统已启动（包含新任务分发器）")
            return True
            
        except Exception as e:
            self.logger.error(f"启动系统失败: {e}")
            self._running = False
            return False
            
    def stop(self):
        """停止系统 - 增强版，支持超时和强制停止"""
        if not self._running:
            return
            
        self._running = False
        self.logger.info("🛑 开始停止系统...")
        
        import threading
        import time
        
        # 设置总超时时间
        total_timeout = 15  # 15秒总超时
        start_time = time.time()
        
        # 定义要停止的组件和超时时间
        stop_operations = [
            ("语音播报最后通知", lambda: self._safe_final_announcement()),
            ("任务分发器", lambda: self._safe_stop_component(self.task_dispatcher, "task_dispatcher")),
            ("异常处理器", lambda: self._safe_stop_component(self.enhanced_exception_handler, "enhanced_exception_handler")),
            ("批量打印管理器", lambda: self._safe_stop_component(self.batch_print_manager, "batch_print_manager")),
            ("打印机工作线程", lambda: self._safe_stop_print_workers()),
            ("文件夹监控", lambda: self._safe_stop_component(self.folder_monitor, "folder_monitor")),
            ("打印机监控", lambda: self._safe_stop_component(self.printer_manager, "printer_manager")),
            ("语音播报服务", lambda: self._safe_stop_component(self.voice_announcer, "voice_announcer")),
            ("临时文件清理", lambda: self._safe_cleanup())
        ]
        
        # 依次停止各组件
        for operation_name, operation_func in stop_operations:
            try:
                # 检查总超时
                elapsed = time.time() - start_time
                if elapsed > total_timeout:
                    self.logger.warning(f"⏰ 系统停止总超时({total_timeout}s)，强制结束")
                    break
                
                # 在单独线程中执行停止操作
                self.logger.debug(f"🔄 正在停止: {operation_name}")
                
                stop_thread = threading.Thread(target=operation_func, daemon=True)
                stop_thread.start()
                
                # 为每个操作设置3秒超时
                remaining_time = min(3, total_timeout - elapsed)
                stop_thread.join(timeout=remaining_time)
                
                if stop_thread.is_alive():
                    self.logger.warning(f"⚠️ {operation_name}停止超时，继续下一个")
                else:
                    self.logger.debug(f"✅ {operation_name}已停止")
                    
            except Exception as e:
                self.logger.error(f"❌ 停止{operation_name}时出错: {e}")
                continue
        
        self.logger.info("✅ 系统停止完成")
    
    def _safe_final_announcement(self):
        """安全的最后播报"""
        try:
            if hasattr(self, 'voice_announcer') and self.voice_announcer:
                self.voice_announcer.announce_custom("打印系统已停止")
                time.sleep(1.5)  # 等待播报完成
        except:
            pass  # 忽略播报错误
    
    def _safe_stop_component(self, component, component_name):
        """安全停止组件"""
        try:
            if component and hasattr(component, 'stop'):
                component.stop()
        except Exception as e:
            self.logger.warning(f"停止{component_name}失败: {e}")
    
    def _safe_stop_print_workers(self):
        """安全停止所有打印机工作线程"""
        try:
            worker_names = list(self._print_workers.keys())
            for printer_name in worker_names:
                try:
                    self._stop_printer_worker(printer_name)
                except Exception as e:
                    self.logger.warning(f"停止打印机{printer_name}工作线程失败: {e}")
        except Exception as e:
            self.logger.warning(f"停止打印机工作线程失败: {e}")
    
    def _safe_cleanup(self):
        """安全清理临时文件"""
        try:
            if hasattr(self, 'image_preprocessor') and self.image_preprocessor:
                self.image_preprocessor.cleanup()
        except Exception as e:
            self.logger.warning(f"清理临时文件失败: {e}")
        
    def pause(self):
        """暂停系统"""
        self._paused = True
        self.voice_announcer.announce_custom("打印系统已暂停")
        self.logger.info("打印系统已暂停")
        
    def resume(self):
        """恢复系统"""
        self._paused = False
        self.voice_announcer.announce_custom("打印系统已恢复")
        self.logger.info("打印系统已恢复")
        
    def is_running(self) -> bool:
        """检查系统是否在运行"""
        return self._running
        
    def is_paused(self) -> bool:
        """检查系统是否暂停"""
        return self._paused
        
    def _on_folder_detected(self, folder_info: FolderInfo):
        """文件夹检测回调"""
        if self._paused:
            self.logger.info(f"系统已暂停，忽略文件夹: {folder_info.name}")
            return
            
        self.logger.info(f"检测到新文件夹: {folder_info.name}")
        
        # 创建打印任务
        task = self.task_manager.create_task(folder_info)
        
        if task and task.status == TaskStatus.EXCEPTION:
            # 处理异常文件夹
            reason = task.error_message or "无法创建打印任务"
            self.exception_handler.handle_exception_folder(
                folder_info.path,
                reason,
                self.config_manager.get_monitor_path()
            )
            
    def _on_task_created(self, task: PrintTask):
        """任务创建回调"""
        self.logger.info(f"新任务创建: {task.task_id}")
        
    def _on_task_status_changed(self, task: PrintTask, old_status: TaskStatus, 
                               new_status: TaskStatus):
        """任务状态变化回调"""
        self.logger.info(
            f"任务 {task.task_id} 状态变化: "
            f"{old_status.value} -> {new_status.value}"
        )
        
        # 如果任务完成，记录日志并播报
        if new_status == TaskStatus.COMPLETED:
            self._log_completed_task(task)
            # 额外的播报逻辑，确保任务完成时能播报
            if task.printer:
                printer_config = self.config_manager.get_printer_config(task.printer)
                if printer_config and printer_config.get('enabled') and printer_config.get('printer_id'):
                    self.logger.info(f"任务完成播报: 任务={task.task_id}, 打印机={task.printer}, ID={printer_config['printer_id']}")
                    self.voice_announcer.announce_completion(printer_config['printer_id'])
                else:
                    self.logger.warning(f"任务完成但打印机配置异常: 打印机={task.printer}, 配置={printer_config}")
            
    def _on_printer_status_changed(self, printer, old_status, old_error):
        """打印机状态变化回调"""
        # 如果出现错误，语音播报
        if printer.error and printer.error.value != "无错误":
            self.voice_announcer.announce_error(printer.name, printer.error.value)
            
    def _on_print_job_update(self, event_type: str, job):
        """打印作业更新回调"""
        if event_type == 'complete':
            # 获取打印机配置
            printer_config = self.config_manager.get_printer_config(job.printer_name)
            if printer_config and printer_config.get('printer_id'):
                self.logger.info(f"打印作业完成，准备播报: 打印机={job.printer_name}, ID={printer_config['printer_id']}")
                self.voice_announcer.announce_completion(printer_config['printer_id'])
            else:
                self.logger.warning(f"打印完成但无法播报: 打印机={job.printer_name}, 配置={printer_config}")
                
    def _start_printer_worker(self, printer_name: str, printer_config: Dict[str, Any]):
        """启动打印机工作线程"""
        if printer_name in self._print_workers:
            return
            
        worker_thread = threading.Thread(
            target=self._printer_worker_loop,
            args=(printer_name, printer_config),
            daemon=True
        )
        worker_thread.start()
        self._print_workers[printer_name] = worker_thread
        self.logger.info(f"启动打印机工作线程: {printer_name}")
        
    def _stop_printer_worker(self, printer_name: str):
        """停止打印机工作线程"""
        if printer_name not in self._print_workers:
            return
            
        # 工作线程会自动退出
        del self._print_workers[printer_name]
        self.logger.info(f"停止打印机工作线程: {printer_name}")
        
    def _printer_worker_loop(self, printer_name: str, printer_config: Dict[str, Any]):
        """打印机工作线程循环"""
        continuous_mode = printer_config.get('continuous_mode', False)
        wait_time = self.config_manager.get_wait_time()
        
        while self._running:
            try:
                # 检查是否暂停
                if self._paused:
                    time.sleep(1)
                    continue
                    
                # 检查打印机是否可用
                if not self.printer_manager.is_printer_available(printer_name):
                    time.sleep(5)
                    continue
                    
                # 获取下一个任务
                task = self.task_manager.get_next_task(printer_name)
                if not task:
                    time.sleep(1)
                    continue
                    
                # 处理任务
                self._process_print_task(task)
                
                # 如果是连续模式，等待指定时间
                if continuous_mode and self._running:
                    self.logger.info(f"{printer_name} 等待 {wait_time} 秒后处理下一个任务")
                    time.sleep(wait_time)
                else:
                    # 非连续模式，启动倒计时
                    self.logger.info(f"{printer_name} 打印完成，启动{wait_time}秒倒计时")
                    self._start_printer_cooldown(printer_name, wait_time)
                    
            except Exception as e:
                self.logger.error(f"打印机工作线程错误 {printer_name}: {e}")
                time.sleep(5)
                
    def _process_print_task(self, task: PrintTask):
        """处理打印任务"""
        try:
            # 更新任务状态
            self.task_manager.update_task_status(task.task_id, TaskStatus.PREPROCESSING)
            
            # 预处理图片（如果需要）
            images_to_print = task.folder_info.images
            if self.image_preprocessor.is_preprocessing_needed(task.folder_info.mode):
                processed_images = self.image_preprocessor.preprocess_images(
                    task.folder_info.path,
                    task.folder_info.size,
                    task.folder_info.mode
                )
                if processed_images:
                    images_to_print = processed_images
                    task.preprocessed_images = processed_images
                    
            # 生成信息页
            info_page_path = self.info_page_generator.generate(task.folder_info)
            if info_page_path:
                task.info_page_path = info_page_path
                # 将信息页添加到打印列表末尾
                images_to_print = images_to_print + [info_page_path]
                
            # 更新任务状态为打印中
            self.task_manager.update_task_status(task.task_id, TaskStatus.PRINTING)
            
            # 使用批量打印处理
            if hasattr(self, 'batch_print_manager') and len(images_to_print) > 1:
                # 创建批量打印任务
                batch_id = f"batch_{task.task_id}_{int(time.time())}"
                info_page = info_page_path if info_page_path else None
                image_files = [img for img in images_to_print if img != info_page_path]
                
                batch_result = self.batch_print_manager.start_batch(
                    batch_id=batch_id,
                    image_files=image_files,
                    info_page_path=info_page,
                    printer_name=task.printer,
                    folder_name=task.folder_info.name
                )
                
                if batch_result:
                    self.logger.info(f"批量打印任务创建成功: {batch_id}")
                    job_id = batch_id  # 使用batch_id作为job_id跟踪
                else:
                    job_id = None
            else:
                # 单个或少量文件使用传统打印
                job_id = self.print_executor.print_images(
                    images_to_print,
                    task.printer,
                    task.preset,
                    f"订单_{task.folder_info.order_id or task.folder_info.name}"
                )
            
            if job_id:
                # 判断是批量打印还是传统打印
                if job_id.startswith('batch_'):
                    # 批量打印，等待批次完成
                    success = self._wait_for_batch_completion(job_id)
                else:
                    # 传统打印，等待打印作业完成
                    success = self.print_executor.wait_for_completion(job_id)
                
                if success:
                    task.actual_printed_count = len(images_to_print)
                    self.task_manager.update_task_status(task.task_id, TaskStatus.COMPLETED)
                    
                    # 移动文件夹到下发完成目录
                    self._move_folder_to_completed(task.folder_info)
                else:
                    self.task_manager.update_task_status(
                        task.task_id, 
                        TaskStatus.FAILED,
                        "打印超时或失败"
                    )
            else:
                self.task_manager.update_task_status(
                    task.task_id,
                    TaskStatus.FAILED,
                    "无法创建打印作业"
                )
                
        except Exception as e:
            self.logger.error(f"处理打印任务失败: {e}")
            self.task_manager.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                str(e)
            )
            
    def _log_completed_task(self, task: PrintTask):
        """记录完成的任务"""
        try:
            task_info = {
                'submitted_time': task.created_time,
                'start_time': task.start_time,
                'end_time': task.end_time,
                'folder_name': task.folder_info.name,
                'submitted_count': len(task.folder_info.images),
                'printed_count': task.actual_printed_count,
                'preset_name': task.preset,
                'printer_name': task.printer
            }
            
            self.log_manager.log_print_task(task_info)
            
        except Exception as e:
            self.logger.error(f"记录任务日志失败: {e}")
    
    def _move_folder_to_completed(self, folder_info: FolderInfo):
        """移动文件夹到下发完成目录"""
        try:
            import shutil
            from datetime import datetime
            
            # 创建下发完成目录
            monitor_path = self.config_manager.get_monitor_path()
            if not monitor_path:
                self.logger.warning("监控路径未设置，无法移动文件夹")
                return
                
            completed_dir = os.path.join(os.path.dirname(monitor_path), "下发完成")
            os.makedirs(completed_dir, exist_ok=True)
            
            # 添加时间戳避免重名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = os.path.basename(folder_info.path)
            dst_folder = os.path.join(completed_dir, f"{timestamp}_{folder_name}")
            
            # 移动文件夹
            if os.path.exists(folder_info.path):
                shutil.move(folder_info.path, dst_folder)
                self.logger.info(f"文件夹已移动到下发完成: {dst_folder}")
            else:
                self.logger.warning(f"源文件夹不存在: {folder_info.path}")
                
        except Exception as e:
            self.logger.error(f"移动文件夹到下发完成目录失败: {e}")
    
    def _start_printer_cooldown(self, printer_name: str, cooldown_seconds: int):
        """启动打印机冷却倒计时"""
        def cooldown_worker():
            try:
                self.logger.info(f"{printer_name} 开始{cooldown_seconds}秒冷却倒计时")
                
                for remaining in range(cooldown_seconds, 0, -1):
                    if not self._running:
                        break
                    
                    # 每10秒播报一次倒计时
                    if remaining % 10 == 0 or remaining <= 5:
                        from voice_announcer import voice_announcer
                        formatted_name = self._extract_printer_id_from_name(printer_name)
                        voice_announcer.announce_custom(f"{formatted_name}还有{remaining}秒重新启用")
                    
                    time.sleep(1)
                
                # 倒计时结束，重新启用打印机
                if self._running:
                    self.logger.info(f"{printer_name} 冷却完成，重新启用")
                    from voice_announcer import voice_announcer
                    formatted_name = self._extract_printer_id_from_name(printer_name)
                    voice_announcer.announce_custom(f"{formatted_name}已重新启用")
                    
            except Exception as e:
                self.logger.error(f"打印机冷却倒计时失败: {e}")
        
        # 启动倒计时线程
        cooldown_thread = threading.Thread(target=cooldown_worker, daemon=True)
        cooldown_thread.start()
    
    def _extract_printer_id_from_name(self, printer_name: str) -> str:
        """从打印机名称中提取编号"""
        try:
            import re
            # 查找数字编号
            match = re.search(r'(\d+)', printer_name)
            if match:
                return f"{match.group(1)}号机"
            elif "(虚拟)" in printer_name:
                # 虚拟打印机特殊处理
                if "1" in printer_name:
                    return "虚拟1号机"
                elif "2" in printer_name:
                    return "虚拟2号机"
                else:
                    return "虚拟打印机"
            else:
                return "打印机"
        except:
            return "打印机"
    
    def _wait_for_batch_completion(self, batch_id: str, timeout: int = 300) -> bool:
        """等待批量打印完成"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if not self._running:
                    return False
                
                # 检查批次状态
                batch_status = self.batch_print_manager.get_batch_status(batch_id)
                if not batch_status:
                    self.logger.error(f"批次不存在: {batch_id}")
                    return False
                
                status = batch_status['status']
                progress = batch_status['progress']
                
                # 记录进度
                self.logger.debug(f"批次 {batch_id} 进度: {progress:.1f}% ({status})")
                
                if status == "已完成":
                    self.logger.info(f"批次打印完成: {batch_id}")
                    return True
                elif status == "失败":
                    self.logger.error(f"批次打印失败: {batch_id}")
                    return False
                elif status == "已取消":
                    self.logger.warning(f"批次打印已取消: {batch_id}")
                    return False
                
                time.sleep(2)  # 每2秒检查一次
            
            self.logger.error(f"批次打印超时: {batch_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"等待批次完成失败: {e}")
            return False
            
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'running': self._running,
            'paused': self._paused,
            'monitor_path': self.config_manager.get_monitor_path(),
            'task_stats': self.task_manager.get_statistics(),
            'enabled_printers': list(self.config_manager.get_enabled_printers().keys()),
            'voice_queue_size': self.voice_announcer.get_queue_size()
        }
        
    def get_printer_list(self):
        """获取打印机列表"""
        return self.printer_manager.get_printer_list()
        
    def enable_printer(self, printer_name: str, paper_size: str, 
                      continuous_mode: bool = False, printer_id: int = None):
        """启用打印机"""
        # 如果没有指定printer_id，自动分配下一个可用ID
        if printer_id is None:
            enabled_printers = self.config_manager.get_enabled_printers()
            used_ids = set()
            for config in enabled_printers.values():
                if config.get('enabled') and config.get('printer_id'):
                    used_ids.add(config['printer_id'])
            
            # 找到第一个未使用的ID
            printer_id = 1
            while printer_id in used_ids:
                printer_id += 1
        
        config = {
            'enabled': True,
            'paper_size': paper_size,
            'continuous_mode': continuous_mode,
            'printer_id': printer_id
        }
        
        self.config_manager.set_printer_config(printer_name, config)
        self.logger.info(f"启用打印机: {printer_name}, 配置: {config}")
        
        # 如果系统正在运行，启动该打印机的工作线程
        if self._running:
            self._start_printer_worker(printer_name, config)
            
    def disable_printer(self, printer_name: str):
        """禁用打印机"""
        config = self.config_manager.get_printer_config(printer_name)
        if config:
            config['enabled'] = False
            self.config_manager.set_printer_config(printer_name, config)
            
        # 停止该打印机的工作线程
        if self._running:
            self._stop_printer_worker(printer_name) 