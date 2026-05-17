"""
配置管理模块
负责管理系统的所有配置信息，包括打印机配置、监控路径、预置规则等
"""
import json
import os
from typing import Dict, Any, Optional
import logging

class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        "monitor_path": "",
        "exception_folder": "异常文件夹",
        "wait_time": 60,
        "enable_preprocessing": True,
        "printers": {},
        "presets": {
            "3寸": {"default": "5寸拍立得"},
            "三寸": {"default": "5寸拍立得"},
            "4寸": {"default": "6寸拍立得"},
            "四寸": {"default": "6寸拍立得"},
            "5寸": {
                "全景": "5寸全景",
                "拍立得": "5寸拍立得",
                "default": "5寸拍立得"
            },
            "五寸": {
                "全景": "5寸全景",
                "拍立得": "5寸拍立得", 
                "default": "5寸拍立得"
            },
            "6寸": {
                "全景": "6寸全景",
                "拍立得": "6寸拍立得",
                "default": "6寸拍立得"
            },
            "六寸": {
                "全景": "6寸全景",
                "拍立得": "6寸拍立得",
                "default": "6寸拍立得"
            }
        }
    }
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)  # 先初始化logger
        self.config = self._load_config()
        # 验证和修复监控路径
        self._validate_and_fix_monitor_path()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置，确保所有必需的键都存在
                return self._merge_config(self.DEFAULT_CONFIG, config)
            except Exception as e:
                logging.error(f"加载配置文件失败: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            # 创建默认配置文件
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
    
    def _merge_config(self, default: Dict, custom: Dict) -> Dict:
        """合并配置，保留用户配置的同时确保默认值存在"""
        result = default.copy()
        for key, value in custom.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self, config: Optional[Dict[str, Any]] = None):
        """保存配置到文件"""
        if config is None:
            config = self.config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            self.logger.info("配置已保存")
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        self.config[key] = value
        self._save_config()
    
    def get_monitor_path(self) -> str:
        """获取监控文件夹路径 - 增强版"""
        monitor_path = self.config.get("monitor_path", "")
        
        # 实时验证路径是否存在
        if not os.path.exists(monitor_path):
            self.logger.warning(f"监控路径不存在，尝试重新检测: {monitor_path}")
            self._validate_and_fix_monitor_path()
            monitor_path = self.config.get("monitor_path", "")
        
        return monitor_path
    
    def set_monitor_path(self, path: str):
        """设置监控文件夹路径"""
        self.set("monitor_path", path)
    
    def get_exception_folder(self) -> str:
        """获取异常文件夹名称"""
        return self.config.get("exception_folder", "异常文件夹")
    
    def get_wait_time(self) -> int:
        """获取等待时间（秒）"""
        return self.config.get("wait_time", 60)
    
    def set_wait_time(self, seconds: int):
        """设置等待时间"""
        self.set("wait_time", seconds)
    
    def is_preprocessing_enabled(self) -> bool:
        """检查是否启用预处理"""
        return self.config.get("enable_preprocessing", True)
    
    def set_preprocessing_enabled(self, enabled: bool):
        """设置预处理开关"""
        self.set("enable_preprocessing", enabled)
    
    def get_printer_config(self, printer_name: str) -> Optional[Dict[str, Any]]:
        """获取打印机配置"""
        return self.config.get("printers", {}).get(printer_name)
    
    def set_printer_config(self, printer_name: str, config: Dict[str, Any]):
        """设置打印机配置"""
        if "printers" not in self.config:
            self.config["printers"] = {}
        self.config["printers"][printer_name] = config
        self._save_config()
    
    def get_enabled_printers(self) -> Dict[str, Dict[str, Any]]:
        """获取所有启用的打印机"""
        return {
            name: config 
            for name, config in self.config.get("printers", {}).items() 
            if config.get("enabled", False)
        }
    
    def get_preset_for_size_mode(self, size: str, mode: str = None) -> Optional[str]:
        """根据尺寸和模式获取预置名称"""
        size_presets = self.config.get("presets", {}).get(size, {})
        if mode and mode in size_presets:
            return size_presets[mode]
        return size_presets.get("default")
    
    def save_config(self):
        """保存配置（公共方法）"""
        self._save_config()
        
    def set_enabled_printers(self, enabled_printers: Dict[str, Dict[str, Any]]):
        """设置启用的打印机列表"""
        self.config["printers"] = enabled_printers
        self._save_config()
        
    def reload(self):
        """重新加载配置"""
        self.config = self._load_config()
        self.logger.info("配置已重新加载")
    
    def _validate_and_fix_monitor_path(self):
        """验证和修复监控路径"""
        monitor_path = self.config.get('monitor_path', '')
        
        # 如果路径不存在，尝试自动修复
        if not os.path.exists(monitor_path):
            self.logger.warning(f"配置的监控路径不存在: {monitor_path}")
            
            # 尝试几种可能的路径
            possible_paths = [
                os.getcwd(),  # 当前工作目录
                os.path.dirname(os.path.abspath(__file__)),  # 脚本所在目录
                os.path.join(os.getcwd(), "自动打印监控文件夹"),  # 当前目录下的标准文件夹
                "D:/自动打印监控文件夹",  # 原始配置路径
                "C:/自动打印监控文件夹"   # 备用路径
            ]
            
            for path in possible_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    # 检查路径中是否有图片文件夹（简单验证）
                    if self._path_contains_image_folders(path):
                        self.logger.info(f"自动修复监控路径为: {path}")
                        self.config['monitor_path'] = path
                        self._save_config()
                        return
            
            # 如果都不存在，使用当前目录
            current_dir = os.getcwd()
            self.logger.warning(f"无法找到合适的监控路径，使用当前目录: {current_dir}")
            self.config['monitor_path'] = current_dir
            self._save_config()
    
    def _path_contains_image_folders(self, path: str) -> bool:
        """检查路径是否包含可能的订单文件夹"""
        try:
            items = os.listdir(path)
            # 查找包含订单号格式或尺寸信息的文件夹
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    # 检查文件夹名称是否包含订单特征
                    if any(size in item for size in ['3寸', '4寸', '5寸', '6寸']) or \
                       '拍立得' in item or \
                       self._contains_order_pattern(item):
                        return True
            return False
        except:
            return False
    
    def _contains_order_pattern(self, folder_name: str) -> bool:
        """检查文件夹名是否包含订单号模式"""
        import re
        # 检查订单号格式 YYMMDD-15位数字
        pattern = r'\d{6}-\d{15}'
        return bool(re.search(pattern, folder_name)) 