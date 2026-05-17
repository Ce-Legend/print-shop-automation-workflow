"""
语音播报模块
使用Windows TTS进行语音播报
"""
import pyttsx3
import threading
import queue
import time
import logging
from typing import Optional


class VoiceAnnouncer:
    """语音播报类"""
    
    def __init__(self):
        """初始化语音播报"""
        self.logger = logging.getLogger(__name__)
        self.tts_engine: Optional[pyttsx3.Engine] = None
        self.announcement_queue = queue.Queue()
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # 初始化TTS引擎
        self._init_tts()
        
    def _init_tts(self):
        """初始化TTS引擎"""
        try:
            self.tts_engine = pyttsx3.init()
            
            # 设置语音属性
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # 尝试使用中文语音
                for voice in voices:
                    if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            # 设置语速和音量
            self.tts_engine.setProperty('rate', 200)
            self.tts_engine.setProperty('volume', 0.9)
            
            self.logger.info(" TTS引擎初始化成功")
            
        except Exception as e:
            self.logger.error(f" TTS引擎初始化失败: {e}")
            self.tts_engine = None
    
    def start(self):
        """启动语音播报服务"""
        if self.is_running:
            return
            
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("语音播报服务已启动")
    
    def stop(self):
        """停止语音播报服务"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        self.clear_queue()
        self.logger.info("语音播报服务已停止")
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.is_running:
            try:
                announcement_type, content = self.announcement_queue.get(timeout=1)
                if announcement_type == "STOP":
                    break
                self._speak(content)
                self.announcement_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"语音播报工作线程错误: {e}")
    
    def _speak(self, text: str):
        """执行语音播报"""
        if not self.tts_engine:
            self.logger.warning(" TTS引擎未初始化，无法播报")
            return
            
        try:
            self.logger.info(f" 播报: {text}")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            self.logger.error(f" 语音播报失败: {e}")
    
    def announce_error(self, printer_name: str, error_type: str):
        """播报打印机错误"""
        message = f"{printer_name}{error_type}，请检查"
        self._add_to_queue("error", message)
    
    def announce_completion(self, printer_id: int, printer_name: str = None):
        """播报任务完成"""
        if printer_name:
            message = f"{printer_name}打印完成"
        else:
            message = f"{printer_id}号打印机打印完成"
        self._add_to_queue("completion", message)
    
    def announce_task_start(self, printer_name: str, task_count: int):
        """播报任务开始"""
        message = f"{printer_name}开始打印，共{task_count}个任务"
        self._add_to_queue("task_start", message)
    
    def announce_system_status(self, status: str):
        """播报系统状态"""
        status_messages = {
            "启动": "打印系统已启动",
            "停止": "打印系统已停止",
            "暂停": "打印系统已暂停",
            "恢复": "打印系统已恢复"
        }
        message = status_messages.get(status, f"系统状态: {status}")
        self._add_to_queue("system", message)
    
    def announce_custom(self, message: str):
        """播报自定义消息"""
        self._add_to_queue("custom", message)
    
    def announce(self, message: str):
        """通用播报方法"""
        self.announce_custom(message)
    
    def _add_to_queue(self, announcement_type: str, content: str):
        """添加播报到队列"""
        if not self.is_running:
            return
        try:
            self.announcement_queue.put((announcement_type, content), timeout=1)
        except queue.Full:
            self.logger.warning("播报队列已满")
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.announcement_queue.qsize()
    
    def clear_queue(self):
        """清空播报队列"""
        try:
            while not self.announcement_queue.empty():
                self.announcement_queue.get_nowait()
                self.announcement_queue.task_done()
        except queue.Empty:
            pass
    
    def test_voice(self):
        """测试语音播报"""
        self.announce_custom("语音播报测试成功")


# 全局语音播报实例
_global_announcer = None

def announce_error(printer_name: str, error_type: str):
    """全局函数：播报错误"""
    global _global_announcer
    if _global_announcer:
        _global_announcer.announce_error(printer_name, error_type)

def announce_completion(printer_id: int):
    """全局函数：播报完成"""
    global _global_announcer
    if _global_announcer:
        _global_announcer.announce_completion(printer_id)

def announce_task_start(printer_name: str, task_count: int):
    """全局函数：播报任务开始"""
    global _global_announcer
    if _global_announcer:
        _global_announcer.announce_task_start(printer_name, task_count)

def announce_system_status(status: str):
    """全局函数：播报系统状态"""
    global _global_announcer
    if _global_announcer:
        _global_announcer.announce_system_status(status)

def start_voice_service():
    """启动全局语音服务"""
    global _global_announcer
    if not _global_announcer:
        _global_announcer = VoiceAnnouncer()
    _global_announcer.start()

def stop_voice_service():
    """停止全局语音服务"""
    global _global_announcer
    if _global_announcer:
        _global_announcer.stop()
        _global_announcer = None
