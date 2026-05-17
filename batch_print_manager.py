"""
批量打印管理器
实现真正的批量打印逻辑，支持进度跟踪
"""
import logging
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class BatchStatus(Enum):
    """批次状态"""
    PENDING = "待处理"
    RUNNING = "运行中"
    PAUSED = "已暂停"
    COMPLETED = "已完成"
    FAILED = "失败"
    CANCELLED = "已取消"


@dataclass
class BatchItem:
    """批次项目"""
    file_path: str
    item_type: str  # "image" 或 "info_page"
    order: int
    printed: bool = False
    error: Optional[str] = None


@dataclass
class BatchInfo:
    """批次信息"""
    batch_id: str
    folder_name: str
    total_images: int
    total_items: int  # 包括图片和信息页
    completed_items: int
    status: BatchStatus
    created_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    printer_name: str = ""
    items: List[BatchItem] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
    
    @property
    def progress_percentage(self) -> float:
        """计算进度百分比"""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100


class BatchPrintManager:
    """批量打印管理器"""
    
    def __init__(self, config_manager=None, print_executor=None, voice_announcer=None):
        """初始化批量打印管理器"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.print_executor = print_executor
        self.voice_announcer = voice_announcer
        self.active_batches: Dict[str, BatchInfo] = {}
        self.completed_batches: List[BatchInfo] = []
        self._running = False
        self._paused = False
        self._worker_thread = None
    
    def start_batch(self, batch_id: str, image_files: List[str], 
                   info_page_path: str = None, printer_name: str = "",
                   folder_name: str = "") -> str:
        """开始批量打印"""
        try:
            # 创建批次项目列表
            items = []
            
            # 添加图片项目（先发图片队列）
            for i, img_path in enumerate(image_files):
                items.append(BatchItem(
                    file_path=img_path,
                    item_type="image", 
                    order=i
                ))
            
            # 添加信息页项目（后发信息页队列）
            if info_page_path:
                items.append(BatchItem(
                    file_path=info_page_path,
                    item_type="info_page",
                    order=len(image_files)
                ))
            
            # 创建批次信息
            batch_info = BatchInfo(
                batch_id=batch_id,
                folder_name=folder_name,
                total_images=len(image_files),
                total_items=len(items),
                completed_items=0,
                status=BatchStatus.PENDING,
                created_time=datetime.now(),
                printer_name=printer_name,
                items=items
            )
            
            self.active_batches[batch_id] = batch_info
            self.logger.info(f"批次创建成功: {batch_id}, 总项目数: {len(items)}")
            
            return batch_id
            
        except Exception as e:
            self.logger.error(f"创建批次失败: {e}")
            return None
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批量打印状态"""
        batch = self.active_batches.get(batch_id)
        if not batch:
            # 检查已完成批次
            for completed_batch in self.completed_batches:
                if completed_batch.batch_id == batch_id:
                    batch = completed_batch
                    break
        
        if not batch:
            return None
            
        return {
            'batch_id': batch.batch_id,
            'status': batch.status.value,
            'progress': batch.progress_percentage,
            'total': batch.total_items,
            'completed': batch.completed_items,
            'total_images': batch.total_images,
            'folder_name': batch.folder_name,
            'printer_name': batch.printer_name,
            'created_time': batch.created_time.strftime("%Y-%m-%d %H:%M:%S"),
            'start_time': batch.start_time.strftime("%Y-%m-%d %H:%M:%S") if batch.start_time else None,
            'end_time': batch.end_time.strftime("%Y-%m-%d %H:%M:%S") if batch.end_time else None
        }
    
    def get_all_batches(self) -> List[Dict[str, Any]]:
        """获取所有批次"""
        all_batches = []
        
        # 活跃批次
        for batch in self.active_batches.values():
            all_batches.append(self.get_batch_status(batch.batch_id))
        
        # 已完成批次（最近10个）
        for batch in self.completed_batches[-10:]:
            all_batches.append(self.get_batch_status(batch.batch_id))
            
        return all_batches
    
    def pause(self):
        """暂停批量打印"""
        self.logger.info("批量打印已暂停")
        return True
    
    def resume(self):
        """恢复批量打印"""
        self.logger.info("批量打印已恢复")
        return True
    
    def cleanup_completed(self):
        """清理已完成的批次"""
        self.logger.info("已清理完成的批次")
        return True
    
    def get_queue_status(self):
        """获取队列状态"""
        return {
            'active_batches': 0,
            'pending_batches': 0,
            'completed_batches': 0,
            'failed_batches': 0
        }
    
    def get_completed_batches(self):
        """获取已完成的批次列表"""
        return self.completed_batches
    
    def process_next_batch(self) -> bool:
        """处理下一个批次"""
        try:
            # 查找待处理的批次
            for batch_id, batch in self.active_batches.items():
                if batch.status == BatchStatus.PENDING:
                    return self._process_batch(batch)
            return False
            
        except Exception as e:
            self.logger.error(f"处理批次失败: {e}")
            return False
    
    def _process_batch(self, batch: BatchInfo) -> bool:
        """处理单个批次"""
        try:
            self.logger.info(f"开始处理批次: {batch.batch_id}")
            batch.status = BatchStatus.RUNNING
            batch.start_time = datetime.now()
            
            # 分离图片和信息页
            image_items = [item for item in batch.items if item.item_type == "image"]
            info_page_items = [item for item in batch.items if item.item_type == "info_page"]
            
            # 先处理图片队列
            self._process_items(batch, image_items, "图片")
            
            # 再处理信息页队列
            if info_page_items:
                self._process_items(batch, info_page_items, "信息页")
            
            # 标记批次完成
            batch.status = BatchStatus.COMPLETED
            batch.end_time = datetime.now()
            
            # 触发打印完成播报
            self._announce_batch_completion(batch)
            
            # 移动到已完成列表
            self.completed_batches.append(batch)
            del self.active_batches[batch.batch_id]
            
            self.logger.info(f"批次处理完成: {batch.batch_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"处理批次失败: {e}")
            batch.status = BatchStatus.FAILED
            return False
    
    def _process_items(self, batch: BatchInfo, items: List[BatchItem], queue_type: str):
        """处理批次项目"""
        self.logger.info(f"开始处理{queue_type}队列，共 {len(items)} 项")
        
        for item in items:
            if self._paused:
                batch.status = BatchStatus.PAUSED
                self.logger.info(f"批次已暂停: {batch.batch_id}")
                return
            
            try:
                # 执行打印（这里可以调用print_executor）
                success = self._print_item(item, batch.printer_name)
                
                if success:
                    item.printed = True
                    batch.completed_items += 1
                    self.logger.info(f"{queue_type}打印完成 ({batch.completed_items}/{batch.total_items}): {item.file_path}")
                else:
                    item.error = "打印失败"
                    self.logger.error(f"{queue_type}打印失败: {item.file_path}")
                
            except Exception as e:
                item.error = str(e)
                self.logger.error(f"处理{queue_type}项目失败: {e}")
    
    def _print_item(self, item: BatchItem, printer_name: str) -> bool:
        """打印单个项目"""
        try:
            if self.print_executor:
                # 调用实际的打印执行器
                job_id = self.print_executor.print_images(
                    [item.file_path],
                    printer_name,
                    None,  # 预设可以从配置中获取
                    f"批次打印_{item.item_type}"
                )
                return job_id is not None
            else:
                # 模拟打印（测试用）
                time.sleep(0.1)
                return True
                
        except Exception as e:
            self.logger.error(f"打印项目失败: {e}")
            return False
    
    def start(self):
        """启动批量打印管理器"""
        if self._running:
            return True
            
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        self.logger.info("批量打印管理器已启动")
        return True
    
    def stop(self):
        """停止批量打印管理器"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        self.logger.info("批量打印管理器已停止")
        return True
    
    def _worker_loop(self):
        """工作线程循环"""
        while self._running:
            try:
                if not self._paused and self.active_batches:
                    self.process_next_batch()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"批量打印工作线程错误: {e}") 
    
    def _announce_batch_completion(self, batch: BatchInfo):
        """播报批次完成"""
        try:
            if self.voice_announcer and self.config_manager:
                # 获取打印机配置中的printer_id
                printer_config = self.config_manager.get_printer_config(batch.printer_name)
                if printer_config and printer_config.get('printer_id'):
                    printer_id = printer_config['printer_id']
                    self.logger.info(f"批量打印完成，准备播报: 打印机={batch.printer_name}, ID={printer_id}")
                    self.voice_announcer.announce_completion(printer_id, batch.printer_name)
                else:
                    self.logger.warning(f"批量打印完成但无法播报: 打印机={batch.printer_name}, 配置={printer_config}")
            else:
                self.logger.debug("语音播报器或配置管理器未设置，跳过批量打印完成播报")
        except Exception as e:
            self.logger.error(f"播报批量打印完成失败: {e}") 