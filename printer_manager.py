"""
打印机管理模块
负责获取系统打印机列表、管理打印机状态、检测打印机异常
"""
import win32print
import win32api
import win32con
import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum
import time
import threading


class PrinterStatus(Enum):
    """打印机状态枚举"""
    READY = "就绪"
    PRINTING = "打印中"
    OFFLINE = "离线"
    ERROR = "错误"
    PAPER_OUT = "缺纸"
    PAPER_JAM = "卡纸"
    TONER_LOW = "墨量低"
    UNKNOWN = "未知"


class PrinterError(Enum):
    """打印机错误类型"""
    NONE = "无错误"
    PAPER_OUT = "缺纸"
    PAPER_JAM = "卡纸"
    TONER_LOW = "缺墨"
    OFFLINE = "离线"
    DOOR_OPEN = "盖板打开"
    UNKNOWN = "未知错误"


class PrinterInfo:
    """打印机信息类"""
    def __init__(self, name: str, driver: str = None, port: str = None):
        self.name = name
        self.driver = driver
        self.port = port
        self.status = PrinterStatus.UNKNOWN
        self.error = PrinterError.NONE
        self.job_count = 0
        self.is_default = False
        
    def __repr__(self):
        return f"PrinterInfo(name={self.name}, status={self.status.value}, error={self.error.value})"


class PrinterManager:
    """打印机管理器"""
    
    # Windows打印机状态标志位
    PRINTER_STATUS_FLAGS = {
        win32print.PRINTER_STATUS_BUSY: PrinterStatus.PRINTING,
        win32print.PRINTER_STATUS_ERROR: PrinterStatus.ERROR,
        win32print.PRINTER_STATUS_OFFLINE: PrinterStatus.OFFLINE,
        win32print.PRINTER_STATUS_PAPER_JAM: PrinterStatus.PAPER_JAM,
        win32print.PRINTER_STATUS_PAPER_OUT: PrinterStatus.PAPER_OUT,
        win32print.PRINTER_STATUS_TONER_LOW: PrinterStatus.TONER_LOW,
    }
    
    def __init__(self):
        """初始化打印机管理器"""
        self.logger = logging.getLogger(__name__)
        self.printers: Dict[str, PrinterInfo] = {}
        self._refresh_printers()
        self._monitoring = False
        self._monitor_thread = None
        self._status_callbacks = []
        
    def _refresh_printers(self):
        """刷新打印机列表"""
        try:
            # 获取默认打印机
            try:
                default_printer = win32print.GetDefaultPrinter()
            except:
                default_printer = None
            
            # 获取所有打印机
            try:
                printers = win32print.EnumPrinters(
                    win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                )
            except:
                printers = []
            
            self.printers.clear()
            
            for flags, description, name, comment in printers:
                # 获取打印机详细信息
                try:
                    handle = win32print.OpenPrinter(name)
                    printer_info = win32print.GetPrinter(handle, 2)
                    win32print.ClosePrinter(handle)
                    
                    # 创建打印机对象
                    printer = PrinterInfo(
                        name=name,
                        driver=printer_info.get('pDriverName', ''),
                        port=printer_info.get('pPortName', '')
                    )
                    
                    # 设置默认打印机标志
                    printer.is_default = (name == default_printer)
                    
                    # 更新状态
                    self._update_printer_status(printer, printer_info)
                    
                    self.printers[name] = printer
                    
                except Exception as e:
                    self.logger.warning(f"无法获取打印机 {name} 的详细信息: {e}")
            
            # 根据配置决定是否添加虚拟打印机
            try:
                from config_manager import ConfigManager
                config = ConfigManager()
                create_virtual = config.get_config().get('create_virtual_printers', False)
                debug_mode = config.get_config().get('debug_mode', False)
                
                if create_virtual or debug_mode:
                    virtual_printer_names = ['Test Printer 1 (虚拟)', 'Test Printer 2 (虚拟)']
                    
                    for i, vp_name in enumerate(virtual_printer_names):
                        if vp_name not in self.printers:
                            virtual_printer = PrinterInfo(
                                name=vp_name,
                                driver='Virtual Driver',
                                port='TEST:'
                            )
                            virtual_printer.status = PrinterStatus.READY
                            virtual_printer.error = PrinterError.NONE
                            virtual_printer.is_default = (i == 0)  # 第一台设为默认
                            self.printers[vp_name] = virtual_printer
                            self.logger.info(f"🎯 调试模式：添加虚拟打印机: {vp_name}")
                else:
                    self.logger.info("🏭 生产模式：跳过虚拟打印机创建")
            except Exception as e:
                self.logger.warning(f"配置虚拟打印机时出错: {e}")
                # 默认不创建虚拟打印机
                    
            self.logger.info(f"发现 {len(self.printers)} 台打印机")
            
        except Exception as e:
            self.logger.error(f"刷新打印机列表失败: {e}")
            # 在出现错误时也创建虚拟打印机
            if not self.printers:
                self.logger.info("创建虚拟打印机用于测试")
                
                virtual_printer1 = PrinterInfo(
                    name='Test Printer 1 (虚拟)',
                    driver='Virtual Driver',
                    port='TEST:'
                )
                virtual_printer1.status = PrinterStatus.READY
                virtual_printer1.error = PrinterError.NONE
                virtual_printer1.is_default = True
                self.printers['Test Printer 1 (虚拟)'] = virtual_printer1
                
                virtual_printer2 = PrinterInfo(
                    name='Test Printer 2 (虚拟)',
                    driver='Virtual Driver',
                    port='TEST:'
                )
                virtual_printer2.status = PrinterStatus.READY
                virtual_printer2.error = PrinterError.NONE
                virtual_printer2.is_default = False
                self.printers['Test Printer 2 (虚拟)'] = virtual_printer2
    
    def _update_printer_status(self, printer: PrinterInfo, printer_info: dict):
        """更新打印机状态"""
        status_flags = printer_info.get('Status', 0)
        attributes = printer_info.get('Attributes', 0)
        
        # 检查打印机状态
        printer.status = PrinterStatus.READY
        printer.error = PrinterError.NONE
        
        # 检查各种状态标志
        for flag, status in self.PRINTER_STATUS_FLAGS.items():
            if status_flags & flag:
                printer.status = status
                
                # 设置对应的错误类型
                if status == PrinterStatus.PAPER_OUT:
                    printer.error = PrinterError.PAPER_OUT
                elif status == PrinterStatus.PAPER_JAM:
                    printer.error = PrinterError.PAPER_JAM
                elif status == PrinterStatus.TONER_LOW:
                    printer.error = PrinterError.TONER_LOW
                elif status == PrinterStatus.OFFLINE:
                    printer.error = PrinterError.OFFLINE
                break
        
        # 检查打印队列
        printer.job_count = printer_info.get('cJobs', 0)
        
        # 如果有打印任务且没有其他错误，设置为打印中
        if printer.job_count > 0 and printer.status == PrinterStatus.READY:
            printer.status = PrinterStatus.PRINTING
    
    def get_printer_list(self) -> List[PrinterInfo]:
        """获取所有打印机列表"""
        self._refresh_printers()
        return list(self.printers.values())
    
    def get_all_printers(self) -> List[str]:
        """获取所有打印机名称列表（兼容UI接口）"""
        self._refresh_printers()
        return list(self.printers.keys())
    
    def get_enabled_printers(self) -> List[str]:
        """获取启用的打印机列表"""
        # 这里返回所有可用的打印机，在实际应用中可以从配置中读取启用状态
        self._refresh_printers()
        available_printers = []
        for name, printer in self.printers.items():
            if printer.status not in [PrinterStatus.OFFLINE, PrinterStatus.ERROR]:
                available_printers.append(name)
        return available_printers
    
    def get_printer_info(self, name: str) -> Optional[PrinterInfo]:
        """获取指定打印机信息"""
        return self.printers.get(name)
    
    def get_printer_status(self, name: str) -> Optional[PrinterStatus]:
        """获取打印机状态"""
        printer = self.printers.get(name)
        if printer:
            # 更新状态
            self._refresh_printer_status(name)
            return printer.status
        return None
    
    def _refresh_printer_status(self, name: str):
        """刷新单个打印机状态"""
        try:
            # 对虚拟打印机特殊处理
            if "(虚拟)" in name:
                if name in self.printers:
                    # 虚拟打印机总是保持在线状态
                    self.printers[name].status = PrinterStatus.READY
                    self.printers[name].error = PrinterError.NONE
                    self.printers[name].job_count = 0
                return
            
            handle = win32print.OpenPrinter(name)
            printer_info = win32print.GetPrinter(handle, 2)
            win32print.ClosePrinter(handle)
            
            if name in self.printers:
                self._update_printer_status(self.printers[name], printer_info)
                
        except Exception as e:
            if "(虚拟)" not in name:  # 只对真实打印机记录错误
                self.logger.error(f"刷新打印机 {name} 状态失败: {e}")
            if name in self.printers:
                if "(虚拟)" in name:
                    # 虚拟打印机保持在线
                    self.printers[name].status = PrinterStatus.READY
                    self.printers[name].error = PrinterError.NONE
                else:
                    self.printers[name].status = PrinterStatus.OFFLINE
                    self.printers[name].error = PrinterError.OFFLINE
    
    def check_printer_error(self, name: str) -> PrinterError:
        """检查打印机错误"""
        printer = self.printers.get(name)
        if printer:
            self._refresh_printer_status(name)
            return printer.error
        return PrinterError.UNKNOWN
    
    def get_printer_job_count(self, name: str) -> int:
        """获取打印机任务数量"""
        printer = self.printers.get(name)
        if printer:
            self._refresh_printer_status(name)
            return printer.job_count
        return 0
    
    def is_printer_available(self, name: str) -> bool:
        """检查打印机是否可用"""
        printer = self.printers.get(name)
        if printer:
            self._refresh_printer_status(name)
            return (printer.status == PrinterStatus.READY and 
                   printer.error == PrinterError.NONE)
        return False
    
    def start_monitoring(self, interval: int = 5):
        """
        开始监控打印机状态
        
        Args:
            interval: 监控间隔（秒）
        """
        if self._monitoring:
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        self.logger.info("打印机状态监控已启动")
    
    def stop_monitoring(self):
        """停止监控打印机状态"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("打印机状态监控已停止")
    
    def _monitor_loop(self, interval: int):
        """监控循环"""
        while self._monitoring:
            try:
                # 记录当前状态
                old_states = {}
                for name, printer in self.printers.items():
                    old_states[name] = (printer.status, printer.error)
                
                # 刷新所有打印机状态
                for name in list(self.printers.keys()):
                    self._refresh_printer_status(name)
                
                # 检查状态变化
                for name, printer in self.printers.items():
                    old_status, old_error = old_states.get(name, (None, None))
                    if old_status != printer.status or old_error != printer.error:
                        self._notify_status_change(printer, old_status, old_error)
                
            except Exception as e:
                self.logger.error(f"监控打印机状态时出错: {e}")
            
            time.sleep(interval)
    
    def _notify_status_change(self, printer: PrinterInfo, 
                             old_status: PrinterStatus, 
                             old_error: PrinterError):
        """通知状态变化"""
        self.logger.info(
            f"打印机 {printer.name} 状态变化: "
            f"{old_status.value if old_status else '未知'} -> {printer.status.value}, "
            f"错误: {old_error.value if old_error else '无'} -> {printer.error.value}"
        )
        
        # 检查是否需要播报
        self._check_and_announce(printer, old_status, old_error)
        
        # 触发回调
        for callback in self._status_callbacks:
            try:
                callback(printer, old_status, old_error)
            except Exception as e:
                self.logger.error(f"状态回调失败: {e}")
    
    def _check_and_announce(self, printer: PrinterInfo, 
                           old_status: PrinterStatus, 
                           old_error: PrinterError):
        """检查并播报状态变化"""
        try:
            # 导入语音播报模块（避免循环导入）
            from voice_announcer import voice_announcer
            
            # 播报错误状态
            if printer.error != PrinterError.NONE and printer.error != old_error:
                error_type_map = {
                    PrinterError.PAPER_OUT: "缺纸",
                    PrinterError.PAPER_JAM: "卡纸", 
                    PrinterError.TONER_LOW: "缺墨",
                    PrinterError.OFFLINE: "离线"
                }
                error_type = error_type_map.get(printer.error, "错误")
                voice_announcer.announce_error(printer.name, error_type)
            
            # 播报打印完成（从打印中变为就绪，且没有错误）
            if (old_status == PrinterStatus.PRINTING and 
                printer.status == PrinterStatus.READY and 
                printer.error == PrinterError.NONE and
                printer.job_count == 0):
                
                # 延迟一小段时间确保打印确实完成
                import threading
                def delayed_announce():
                    import time
                    time.sleep(1)  # 等待1秒确认状态稳定
                    # 再次检查状态
                    self._refresh_printer_status(printer.name)
                    current_printer = self.printers.get(printer.name)
                    if (current_printer and 
                        current_printer.status == PrinterStatus.READY and
                        current_printer.error == PrinterError.NONE and
                        current_printer.job_count == 0):
                        voice_announcer.announce_completion(0, printer.name)
                
                threading.Thread(target=delayed_announce, daemon=True).start()
                
        except Exception as e:
            self.logger.error(f"播报状态变化失败: {e}")
    
    def add_status_callback(self, callback):
        """添加状态变化回调函数"""
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback):
        """移除状态变化回调函数"""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def get_printer_capabilities(self, name: str) -> Dict[str, any]:
        """获取打印机能力信息"""
        capabilities = {
            "paper_sizes": [],
            "color_support": False,
            "duplex_support": False,
            "resolution": []
        }
        
        try:
            # 获取打印机DC
            hdc = win32api.CreateDC(None, name, None)
            
            # 检查颜色支持
            color_bits = win32api.GetDeviceCaps(hdc, win32con.BITSPIXEL)
            capabilities["color_support"] = color_bits > 1
            
            # 获取分辨率
            x_res = win32api.GetDeviceCaps(hdc, win32con.LOGPIXELSX)
            y_res = win32api.GetDeviceCaps(hdc, win32con.LOGPIXELSY)
            capabilities["resolution"] = [x_res, y_res]
            
            win32api.DeleteDC(hdc)
            
        except Exception as e:
            self.logger.error(f"获取打印机 {name} 能力信息失败: {e}")
        
        return capabilities

    def _discover_printers(self) -> List[Dict[str, str]]:
        """发现可用的打印机"""
        printers = []
        try:
            # 获取系统中的打印机
            printer_names = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
            
            for name in printer_names:
                try:
                    hprinter = win32print.OpenPrinter(name)
                    printer_info = win32print.GetPrinter(hprinter, 2)
                    
                    printer_data = {
                        'name': name,
                        'driver': printer_info.get('pDriverName', '未知'),
                        'port': printer_info.get('pPortName', '未知'),
                        'status': self._get_printer_status(hprinter),
                        'is_default': name == win32print.GetDefaultPrinter()
                    }
                    printers.append(printer_data)
                    win32print.ClosePrinter(hprinter)
                    
                except Exception as e:
                    self.logger.warning(f"获取打印机 {name} 信息失败: {e}")
                    
        except Exception as e:
            self.logger.error(f"枚举打印机失败: {e}")
            
        # 如果没有发现打印机，添加虚拟打印机用于测试
        if not printers:
            self.logger.info("未发现真实打印机，添加虚拟打印机用于测试")
            virtual_printers = [
                {
                    'name': 'Test Printer 1 (虚拟)',
                    'driver': 'Virtual Driver',
                    'port': 'TEST:',
                    'status': '就绪',
                    'is_default': True,
                    'is_virtual': True
                },
                {
                    'name': 'Test Printer 2 (虚拟)',
                    'driver': 'Virtual Driver',
                    'port': 'TEST:',
                    'status': '就绪',
                    'is_default': False,
                    'is_virtual': True
                }
            ]
            printers.extend(virtual_printers)
            
        self.logger.info(f"发现 {len(printers)} 台打印机")
        return printers


# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建打印机管理器
    manager = PrinterManager()
    
    # 获取打印机列表
    printers = manager.get_printer_list()
    print("\n系统中的打印机:")
    for printer in printers:
        print(f"  {printer.name}")
        print(f"    状态: {printer.status.value}")
        print(f"    错误: {printer.error.value}")
        print(f"    任务数: {printer.job_count}")
        print(f"    默认: {'是' if printer.is_default else '否'}")
        print()
    
    # 测试状态监控
    def on_status_change(printer, old_status, old_error):
        print(f"状态变化: {printer.name} - {printer.status.value}")
    
    manager.add_status_callback(on_status_change)
    manager.start_monitoring(interval=3)
    
    print("正在监控打印机状态，按Ctrl+C退出...")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    
    manager.stop_monitoring() 