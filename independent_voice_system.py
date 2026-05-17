"""
独立语音系统
完整实现，包含语音播报功能
"""
import logging
from voice_announcer import VoiceAnnouncer


class IndependentVoiceSystem:
    """独立语音系统"""
    
    def __init__(self, config_manager=None):
        """初始化语音系统"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self._running = False
        
        # 创建语音播报器
        try:
            self.voice_announcer = VoiceAnnouncer()
            self.logger.info("语音播报器初始化成功")
        except Exception as e:
            self.logger.error(f"语音播报器初始化失败: {e}")
            self.voice_announcer = None
    
    def start(self):
        """启动语音系统"""
        try:
            if self.voice_announcer:
                self.voice_announcer.start()
            self._running = True
            self.logger.info("语音系统已启动")
            return True
        except Exception as e:
            self.logger.error(f"启动语音系统失败: {e}")
            self._running = False
            return False
    
    def stop(self):
        """停止语音系统"""
        try:
            if self.voice_announcer:
                self.voice_announcer.stop()
            self._running = False
            self.logger.info("语音系统已停止")
            return True
        except Exception as e:
            self.logger.error(f"停止语音系统失败: {e}")
            self._running = False
            return False
    
    def is_running(self):
        """检查语音系统是否正在运行"""
        return self._running
    
    def announce(self, message: str):
        """语音播报"""
        try:
            if self.voice_announcer and self._running:
                self.voice_announcer.announce_custom(message)
            else:
                self.logger.info(f"语音播报（无声音）: {message}")
        except Exception as e:
            self.logger.error(f"语音播报失败: {e}")
    
    def test_voice(self):
        """测试语音"""
        try:
            if self.voice_announcer:
                if not self._running:
                    self.start()
                self.voice_announcer.test_voice()
                return True
            else:
                self.logger.warning("语音播报器未初始化，无法测试")
                return False
        except Exception as e:
            self.logger.error(f"语音测试失败: {e}")
            return False 