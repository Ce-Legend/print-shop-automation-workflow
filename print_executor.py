"""
打印执行模块 (增强版)
负责调用Windows打印API执行打印任务，管理打印队列
集成增强版预设管理器，支持高级预设配置
"""
import os
import win32print
import win32api
import win32ui
import win32con
from PIL import Image, ImageWin
import logging
import time
import threading
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import tempfile
from printer_preset_manager import PrinterPresetManager


@dataclass
class PrintJob:
    """打印作业信息"""
    job_id: int
    printer_name: str
    document_name: str
    status: str
    pages_printed: int
    total_pages: int
    submitted_time: datetime


class PrintExecutor:
    """打印执行器 (增强版)"""
    
    def __init__(self):
        """初始化打印执行器"""
        self.logger = logging.getLogger(__name__)
        self.active_jobs: Dict[int, PrintJob] = {}
        self._job_callbacks = []
        
        # 初始化增强版预设管理器
        self.preset_manager = PrinterPresetManager()
        self.logger.info("打印执行器已初始化，集成增强版预设管理器")
        
    def print_images(self, images: List[str], printer_name: str, 
                    preset: str = None, document_name: str = None) -> Optional[int]:
        """
        打印多张图片
        
        Args:
            images: 图片文件路径列表
            printer_name: 打印机名称
            preset: 打印预置（暂未实现，需要打印机驱动支持）
            document_name: 文档名称
            
        Returns:
            打印作业ID，失败返回None
        """
        if not images:
            self.logger.warning("没有要打印的图片")
            return None
            
        if not document_name:
            document_name = f"打印任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        try:
            # 打开打印机
            hprinter = win32print.OpenPrinter(printer_name)
            
            # 开始文档
            hjob = win32print.StartDocPrinter(hprinter, 1, (document_name, None, "RAW"))
            
            # 记录作业信息
            job = PrintJob(
                job_id=hjob,
                printer_name=printer_name,
                document_name=document_name,
                status="打印中",
                pages_printed=0,
                total_pages=len(images),
                submitted_time=datetime.now()
            )
            self.active_jobs[hjob] = job
            
            # 逐个打印图片
            for i, image_path in enumerate(images):
                try:
                    self._print_single_image(hprinter, image_path, printer_name)
                    job.pages_printed += 1
                    self._notify_job_progress(job)
                except Exception as e:
                    self.logger.error(f"打印图片 {image_path} 失败: {e}")
                    
            # 结束文档
            win32print.EndDocPrinter(hprinter)
            win32print.ClosePrinter(hprinter)
            
            # 更新作业状态
            job.status = "已完成"
            self._notify_job_complete(job)
            
            return hjob
            
        except Exception as e:
            self.logger.error(f"打印失败: {e}")
            try:
                win32print.ClosePrinter(hprinter)
            except:
                pass
            return None
    
    def _print_single_image(self, hprinter: Any, image_path: str, printer_name: str):
        """打印单张图片"""
        # 加载图片
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 获取打印机DC
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
        
        # 获取打印机页面尺寸
        printable_area = hdc.GetDeviceCaps(win32con.HORZRES), hdc.GetDeviceCaps(win32con.VERTRES)
        printer_size = hdc.GetDeviceCaps(win32con.PHYSICALWIDTH), hdc.GetDeviceCaps(win32con.PHYSICALHEIGHT)
        printer_margins = hdc.GetDeviceCaps(win32con.PHYSICALOFFSETX), hdc.GetDeviceCaps(win32con.PHYSICALOFFSETY)
        
        # 计算缩放比例（保持纵横比）
        scale_x = printable_area[0] / img.width
        scale_y = printable_area[1] / img.height
        scale = min(scale_x, scale_y)
        
        # 调整图片大小
        scaled_width = int(img.width * scale)
        scaled_height = int(img.height * scale)
        img = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
        
        # 开始页面
        hdc.StartDoc(os.path.basename(image_path))
        hdc.StartPage()
        
        # 绘制图片
        dib = ImageWin.Dib(img)
        # 居中打印
        x = (printable_area[0] - scaled_width) // 2
        y = (printable_area[1] - scaled_height) // 2
        dib.draw(hdc.GetHandleOutput(), (x, y, x + scaled_width, y + scaled_height))
        
        # 结束页面
        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()
    
    def print_with_preset(self, file_path: str, printer_name: str, 
                         preset_name: str) -> Tuple[Optional[int], str]:
        """
        使用预置配置打印文件 (增强版)
        
        Args:
            file_path: 图片文件路径
            printer_name: 打印机名称
            preset_name: 预置名称
            
        Returns:
            (打印作业ID, 详细信息)，失败返回(None, 错误信息)
        """
        try:
            self.logger.info(f"使用预置 '{preset_name}' 打印文件: {file_path}")
            
            # 使用增强版预设管理器应用预置
            preset_success, preset_message = self.preset_manager.apply_preset(printer_name, preset_name)
            
            if not preset_success:
                self.logger.warning(f"预设应用失败: {preset_message}")
                # 即使预设失败，仍然尝试打印（使用默认设置）
                job_id = self.print_images([file_path], printer_name, preset_name)
                if job_id:
                    return job_id, f"⚠️ 使用默认设置打印: {preset_message}"
                else:
                    return None, f"❌ 打印失败: {preset_message}"
            
            # 预设应用成功，执行打印
            job_id = self.print_images([file_path], printer_name, preset_name)
            
            if job_id:
                success_message = f"✅ 打印任务已提交\n{preset_message}"
                self.logger.info(f"预置打印成功: 作业ID {job_id}")
                return job_id, success_message
            else:
                return None, f"❌ 打印任务提交失败，但预设已正确应用"
            
        except Exception as e:
            error_msg = f"预置打印失败: {e}"
            self.logger.error(error_msg)
            return None, error_msg
    
    def check_printer_preset_status(self, printer_name: str) -> Dict[str, Any]:
        """
        检查打印机预设配置状态
        
        Args:
            printer_name: 打印机名称
            
        Returns:
            预设配置状态详情
        """
        try:
            return self.preset_manager.check_preset_configuration_status(printer_name)
        except Exception as e:
            self.logger.error(f"检查预设配置状态失败: {e}")
            return {"error": str(e)}
    
    def get_available_presets(self) -> List[str]:
        """获取可用预设列表"""
        return self.preset_manager.get_available_presets()
    
    def get_preset_info(self, preset_name: str) -> Optional[Dict]:
        """获取预设详细信息"""
        return self.preset_manager.get_preset_info(preset_name)
    
    def open_preset_guide(self) -> bool:
        """打开预设配置引导工具"""
        return self.preset_manager.open_preset_guide()
    
    def get_configuration_summary(self) -> str:
        """获取配置摘要"""
        return self.preset_manager.get_configuration_summary()
    
    def batch_print_with_preset(self, file_paths: List[str], printer_name: str, 
                               preset_name: str) -> List[Tuple[str, Optional[int], str]]:
        """
        批量使用预设打印文件
        
        Args:
            file_paths: 图片文件路径列表
            printer_name: 打印机名称
            preset_name: 预置名称
            
        Returns:
            [(文件路径, 作业ID, 状态信息), ...]
        """
        results = []
        
        try:
            self.logger.info(f"批量预设打印: {len(file_paths)} 个文件，预设: {preset_name}")
            
            # 先检查预设状态
            status = self.check_printer_preset_status(printer_name)
            if not status.get("printer_connected", False):
                error_msg = f"打印机 {printer_name} 未连接"
                return [(path, None, error_msg) for path in file_paths]
            
            # 逐个打印文件
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    results.append((file_path, None, f"❌ 文件不存在: {file_path}"))
                    continue
                
                try:
                    job_id, message = self.print_with_preset(file_path, printer_name, preset_name)
                    results.append((file_path, job_id, message))
                    
                    # 短暂延迟，避免打印队列拥堵
                    time.sleep(0.5)
                    
                except Exception as e:
                    error_msg = f"❌ 打印失败: {e}"
                    results.append((file_path, None, error_msg))
                    self.logger.error(f"批量打印文件 {file_path} 失败: {e}")
            
            success_count = sum(1 for _, job_id, _ in results if job_id is not None)
            self.logger.info(f"批量预设打印完成: {success_count}/{len(file_paths)} 成功")
            
        except Exception as e:
            error_msg = f"批量预设打印失败: {e}"
            self.logger.error(error_msg)
            results = [(path, None, error_msg) for path in file_paths]
        
        return results
    
    def _apply_printer_preset(self, printer_name: str, preset_name: str) -> bool:
        """
        应用打印机预置配置
        
        Args:
            printer_name: 打印机名称
            preset_name: 预置名称
            
        Returns:
            是否成功应用预置
        """
        try:
            # 虚拟打印机特殊处理
            if "(虚拟)" in printer_name:
                self.logger.info(f"虚拟打印机 {printer_name} 应用预置: {preset_name}")
                return True
            
            # 方案1：通过Windows API设置打印机属性
            hprinter = win32print.OpenPrinter(printer_name)
            
            try:
                # 获取打印机默认属性
                printer_info = win32print.GetPrinter(hprinter, 2)
                devmode = printer_info.get('pDevMode')
                
                if devmode:
                    # 这里需要根据具体打印机驱动设置预置
                    # 不同品牌的打印机预置设置方式可能不同
                    self.logger.info(f"正在应用预置 '{preset_name}' 到打印机 '{printer_name}'")
                    
                    # 方案2：通过注册表或配置文件查找预置设置
                    preset_settings = self._get_preset_settings(printer_name, preset_name)
                    if preset_settings:
                        self._apply_preset_settings(devmode, preset_settings)
                        return True
                    else:
                        self.logger.warning(f"未找到预置配置: {preset_name}")
                        return False
                else:
                    self.logger.warning(f"无法获取打印机 '{printer_name}' 的设备模式")
                    return False
                    
            finally:
                win32print.ClosePrinter(hprinter)
                
        except Exception as e:
            self.logger.error(f"应用打印机预置失败: {e}")
            return False
    
    def _get_preset_settings(self, printer_name: str, preset_name: str) -> Optional[Dict]:
        """
        获取预置设置（从注册表或配置文件）
        
        Args:
            printer_name: 打印机名称
            preset_name: 预置名称
            
        Returns:
            预置设置字典
        """
        try:
            # 方案1：从注册表查找预置
            import winreg
            
            # 典型的打印机预置注册表路径
            registry_paths = [
                rf"SYSTEM\CurrentControlSet\Control\Print\Printers\{printer_name}\PrinterDriverData",
                rf"SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3",
            ]
            
            for reg_path in registry_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                        # 尝试查找预置相关的键值
                        self.logger.debug(f"搜索预置设置: {reg_path}")
                        # 这里需要根据具体打印机驱动的注册表结构实现
                        pass
                except WindowsError:
                    continue
            
            # 方案2：基于预置名称的简单映射
            preset_mappings = {
                "5寸拍立得": {
                    "paper_size": "5寸",
                    "quality": "高质量",
                    "color_mode": "彩色"
                },
                "6寸拍立得": {
                    "paper_size": "6寸", 
                    "quality": "高质量",
                    "color_mode": "彩色"
                },
                "5寸全景": {
                    "paper_size": "5寸",
                    "quality": "高质量",
                    "color_mode": "彩色",
                    "layout": "全景"
                },
                "6寸全景": {
                    "paper_size": "6寸",
                    "quality": "高质量", 
                    "color_mode": "彩色",
                    "layout": "全景"
                }
            }
            
            return preset_mappings.get(preset_name)
            
        except Exception as e:
            self.logger.error(f"获取预置设置失败: {e}")
            return None
    
    def _apply_preset_settings(self, devmode, settings: Dict) -> bool:
        """
        应用预置设置到设备模式
        
        Args:
            devmode: 设备模式对象
            settings: 设置字典
            
        Returns:
            是否成功应用
        """
        try:
            # 这里需要根据具体的打印机驱动API实现
            # 不同品牌的打印机设置方式不同
            
            self.logger.info(f"应用预置设置: {settings}")
            
            # 示例：设置基本属性
            if "paper_size" in settings:
                # 设置纸张大小（需要根据具体驱动实现）
                pass
                
            if "quality" in settings:
                # 设置打印质量（需要根据具体驱动实现）
                pass
                
            if "color_mode" in settings:
                # 设置颜色模式（需要根据具体驱动实现）
                pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"应用预置设置失败: {e}")
            return False
    
    def wait_for_completion(self, job_id: int, timeout: int = 300) -> bool:
        """
        等待打印任务完成
        
        Args:
            job_id: 打印作业ID
            timeout: 超时时间（秒）
            
        Returns:
            是否成功完成
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            job = self.active_jobs.get(job_id)
            if not job:
                return False
                
            if job.status == "已完成":
                return True
            elif job.status == "失败":
                return False
                
            time.sleep(1)
            
        return False
    
    def cancel_job(self, printer_name: str, job_id: int) -> bool:
        """
        取消打印作业
        
        Args:
            printer_name: 打印机名称
            job_id: 作业ID
            
        Returns:
            是否成功取消
        """
        try:
            hprinter = win32print.OpenPrinter(printer_name)
            win32print.SetJob(hprinter, job_id, 0, None, win32print.JOB_CONTROL_DELETE)
            win32print.ClosePrinter(hprinter)
            
            # 更新作业状态
            if job_id in self.active_jobs:
                self.active_jobs[job_id].status = "已取消"
                
            return True
            
        except Exception as e:
            self.logger.error(f"取消打印作业失败: {e}")
            return False
    
    def get_printer_jobs(self, printer_name: str) -> List[Dict[str, Any]]:
        """
        获取打印机的所有作业
        
        Args:
            printer_name: 打印机名称
            
        Returns:
            作业列表
        """
        jobs = []
        
        try:
            hprinter = win32print.OpenPrinter(printer_name)
            print_jobs = win32print.EnumJobs(hprinter, 0, -1, 1)
            win32print.ClosePrinter(hprinter)
            
            for job_info in print_jobs:
                jobs.append({
                    'job_id': job_info['JobId'],
                    'document': job_info['pDocument'],
                    'status': self._parse_job_status(job_info['Status']),
                    'pages_printed': job_info['PagesPrinted'],
                    'total_pages': job_info['TotalPages'],
                    'submitted': job_info['Submitted']
                })
                
        except Exception as e:
            self.logger.error(f"获取打印作业列表失败: {e}")
            
        return jobs
    
    def _parse_job_status(self, status_code: int) -> str:
        """解析作业状态码"""
        status_map = {
            win32print.JOB_STATUS_PAUSED: "已暂停",
            win32print.JOB_STATUS_ERROR: "错误",
            win32print.JOB_STATUS_DELETING: "正在删除",
            win32print.JOB_STATUS_SPOOLING: "正在后台处理",
            win32print.JOB_STATUS_PRINTING: "正在打印",
            win32print.JOB_STATUS_OFFLINE: "离线",
            win32print.JOB_STATUS_PAPEROUT: "缺纸",
            win32print.JOB_STATUS_PRINTED: "已打印",
            win32print.JOB_STATUS_DELETED: "已删除",
            win32print.JOB_STATUS_BLOCKED_DEVQ: "被阻塞",
            win32print.JOB_STATUS_USER_INTERVENTION: "需要用户干预"
        }
        
        for code, name in status_map.items():
            if status_code & code:
                return name
                
        return "未知"
    
    def add_job_callback(self, callback):
        """添加作业状态回调"""
        if callback not in self._job_callbacks:
            self._job_callbacks.append(callback)
    
    def remove_job_callback(self, callback):
        """移除作业状态回调"""
        if callback in self._job_callbacks:
            self._job_callbacks.remove(callback)
    
    def _notify_job_progress(self, job: PrintJob):
        """通知作业进度"""
        for callback in self._job_callbacks:
            try:
                callback('progress', job)
            except Exception as e:
                self.logger.error(f"作业进度回调失败: {e}")
    
    def _notify_job_complete(self, job: PrintJob):
        """通知作业完成"""
        for callback in self._job_callbacks:
            try:
                callback('complete', job)
            except Exception as e:
                self.logger.error(f"作业完成回调失败: {e}")
    
    def print_test_page(self, printer_name: str) -> bool:
        """
        打印测试页
        
        Args:
            printer_name: 打印机名称
            
        Returns:
            是否成功
        """
        try:
            # 创建测试图片
            test_img = Image.new('RGB', (800, 600), 'white')
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(test_img)
            
            # 绘制测试内容
            draw.text((50, 50), f"打印机测试页", fill='black', font=None)
            draw.text((50, 100), f"打印机: {printer_name}", fill='black')
            draw.text((50, 150), f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill='black')
            draw.rectangle([40, 40, 760, 560], outline='black', width=2)
            
            # 保存临时文件
            temp_file = os.path.join(tempfile.gettempdir(), "test_page.jpg")
            test_img.save(temp_file)
            
            # 打印
            result = self.print_images([temp_file], printer_name, document_name="测试页")
            
            # 删除临时文件
            try:
                os.remove(temp_file)
            except:
                pass
                
            return result is not None
            
        except Exception as e:
            self.logger.error(f"打印测试页失败: {e}")
            return False


# 测试代码
if __name__ == "__main__":
    import sys
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建打印执行器
    executor = PrintExecutor()
    
    # 获取默认打印机
    try:
        default_printer = win32print.GetDefaultPrinter()
        print(f"默认打印机: {default_printer}")
        
        # 打印测试页
        print("\n正在打印测试页...")
        if executor.print_test_page(default_printer):
            print("测试页打印成功")
        else:
            print("测试页打印失败")
            
    except Exception as e:
        print(f"错误: {e}") 
    def _handle_virtual_printer(self, images: List[str], printer_name: str, 
                              preset: str = None, document_name: str = None) -> int:
        """
        处理虚拟打印机的打印请求
        
        Args:
            images: 图片文件路径列表
            printer_name: 虚拟打印机名称
            preset: 打印预置
            document_name: 文档名称
            
        Returns:
            模拟的打印作业ID
        """
        import random
        from datetime import datetime
        
        # 生成模拟的作业ID
        job_id = random.randint(1000, 9999)
        
        # 创建虚拟打印作业
        job = PrintJob(
            job_id=job_id,
            printer_name=printer_name,
            document_name=document_name or f"虚拟打印_{datetime.now().strftime('%H%M%S')}",
            status="正在打印",
            pages_printed=0,
            total_pages=len(images),
            submitted_time=datetime.now()
        )
        
        self.active_jobs[job_id] = job
        
        # 模拟打印过程
        import threading
        threading.Thread(target=self._simulate_virtual_printing, args=(job, images, preset), daemon=True).start()
        
        self.logger.info(f"虚拟打印机 {printer_name} 开始打印 {len(images)} 张图片，作业ID: {job_id}")
        self.logger.info(f"使用预置: {preset}")
        
        return job_id
    
    def _simulate_virtual_printing(self, job: PrintJob, images: List[str], preset: str):
        """
        模拟虚拟打印机的打印过程
        
        Args:
            job: 打印作业对象
            images: 图片列表
            preset: 打印预置
        """
        import time
        
        try:
            # 模拟打印每一页
            for i, image_path in enumerate(images):
                # 模拟打印时间（每页2-5秒）
                import random
                print_time = random.uniform(2, 5)
                time.sleep(print_time)
                
                # 更新进度
                job.pages_printed = i + 1
                job.status = f"正在打印第 {i + 1}/{len(images)} 页"
                
                self.logger.info(f"虚拟打印机 {job.printer_name} 完成第 {i + 1} 页: {os.path.basename(image_path)}")
                
                # 通知进度更新
                self._notify_job_progress(job)
            
            # 打印完成
            job.status = "已完成"
            job.pages_printed = len(images)
            
            self.logger.info(f"虚拟打印机 {job.printer_name} 打印完成，作业ID: {job.job_id}")
            
            # 通知完成
            self._notify_job_complete(job)
            
            # 几秒后从活跃作业中移除
            time.sleep(3)
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
                
        except Exception as e:
            job.status = "失败"
            job.error_message = str(e)
            self.logger.error(f"虚拟打印失败: {e}")