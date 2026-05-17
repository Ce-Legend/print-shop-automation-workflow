"""
爱普生8050打印机预设管理器 (增强版)
专门处理爱普生8050打印机的预设配置调用
增加了高级预设支持、配置检查和用户引导功能
"""
import os
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
import win32print
import subprocess
from datetime import datetime
import time


class PrinterPresetManager:
    """爱普生8050打印机预设管理器 (增强版)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 预设配置文件路径
        self.config_file = "printer_preset_config.json"
        self.mapping_file = "epson_8050_preset_mapping.json"
        
        # 爱普生8050支持的预设配置 (增强版)
        self.epson_8050_presets = {
            "3寸拍立得": {
                "paper_size": "3寸",
                "display_name": "3寸拍立得 (89×55mm)",
                "paper_code": 15,
                "quality": "高质量",
                "color_mode": "彩色",
                "orientation": "纵向",
                # 高级色彩设置
                "brightness": "+2",
                "contrast": "+8", 
                "saturation": "+3",
                "paper_type": "富士胶片超光泽纸",
                "color_management": "富士生动群",
                "description": "适用于标准3寸拍立得照片打印"
            },
            "4寸拍立得": {
                "paper_size": "4寸",
                "display_name": "4寸拍立得 (102×76mm)",
                "paper_code": 13,
                "quality": "高质量",
                "color_mode": "彩色",
                "orientation": "纵向",
                # 高级色彩设置
                "brightness": "+2",
                "contrast": "+8",
                "saturation": "+3", 
                "paper_type": "富士胶片超光泽纸",
                "color_management": "富士生动群",
                "description": "适用于标准4寸拍立得照片打印"
            },
            "5寸拍立得": {
                "paper_size": "5寸",
                "display_name": "5寸拍立得 (127×89mm)",
                "paper_code": 14,
                "quality": "高质量",
                "color_mode": "彩色",
                "orientation": "纵向",
                # 高级色彩设置
                "brightness": "+2",
                "contrast": "+8",
                "saturation": "+3",
                "paper_type": "富士胶片超光泽纸",
                "color_management": "富士生动群",
                "description": "适用于标准5寸拍立得照片打印"
            },
            "6寸拍立得": {
                "paper_size": "6寸", 
                "display_name": "6寸拍立得 (152×102mm)",
                "paper_code": 13,
                "quality": "高质量",
                "color_mode": "彩色",
                "orientation": "纵向",
                # 高级色彩设置
                "brightness": "+2",
                "contrast": "+8",
                "saturation": "+3",
                "paper_type": "富士胶片超光泽纸",
                "color_management": "富士生动群",
                "description": "适用于标准6寸拍立得照片打印"
            },
            "4寸全景": {
                "paper_size": "4寸",
                "display_name": "4寸全景 (102×76mm横向)",
                "paper_code": 13,
                "quality": "高质量", 
                "color_mode": "彩色",
                "orientation": "横向",
                # 高级色彩设置
                "brightness": "+2",
                "contrast": "+8",
                "saturation": "+3",
                "paper_type": "富士胶片超光泽纸",
                "color_management": "富士生动群",
                "description": "适用于4寸全景照片打印"
            },
            "5寸全景": {
                "paper_size": "5寸",
                "display_name": "5寸全景 (127×89mm横向)",
                "paper_code": 14,
                "quality": "高质量", 
                "color_mode": "彩色",
                "orientation": "横向",
                # 高级色彩设置
                "brightness": "+2",
                "contrast": "+8",
                "saturation": "+3",
                "paper_type": "富士胶片超光泽纸",
                "color_management": "富士生动群",
                "description": "适用于5寸全景照片打印"
            },
            "6寸全景": {
                "paper_size": "6寸",
                "display_name": "6寸全景 (152×102mm横向)",
                "paper_code": 13,
                "quality": "高质量",
                "color_mode": "彩色", 
                "orientation": "横向",
                # 高级色彩设置
                "brightness": "+2",
                "contrast": "+8",
                "saturation": "+3",
                "paper_type": "富士胶片超光泽纸",
                "color_management": "富士生动群",
                "description": "适用于6寸全景照片打印"
            }
        }
        
        # 加载用户配置状态
        self.user_config = self.load_user_config()
    
    def apply_preset(self, printer_name: str, preset_name: str) -> Tuple[bool, str]:
        """
        应用爱普生8050打印机预设 (增强版)
        
        Returns:
            (是否成功, 详细信息)
        """
        try:
            self.logger.info(f"为爱普生8050打印机 {printer_name} 应用预设: {preset_name}")
            
            # 检查预设是否存在
            if preset_name not in self.epson_8050_presets:
                available_presets = list(self.epson_8050_presets.keys())
                message = f"未找到预设配置: {preset_name}，可用预设: {available_presets}"
                self.logger.warning(message)
                return False, message
            
            preset_config = self.epson_8050_presets[preset_name]
            
            # 检查用户是否已完成高级配置
            if not self.is_advanced_config_completed():
                message = "检测到未完成高级预设配置，建议运行预设配置引导工具"
                self.logger.warning(message)
                return self._apply_basic_preset(printer_name, preset_config, message)
            
            # 尝试应用完整预设（基本参数 + 提醒用户高级设置已配置）
            success = self._apply_epson_8050_devmode(printer_name, preset_config)
            
            if success:
                message = f"✅ 成功应用预设: {preset_name}\n💡 高级色彩设置（亮度+2、对比度+8、饱和度+3）已在驱动中配置"
                self.logger.info(f"成功应用爱普生8050预设: {preset_name}")
                return True, message
            else:
                message = f"⚠️ 基本参数已设置，但建议检查驱动中的预设配置"
                return self._apply_basic_preset(printer_name, preset_config, message)
                
        except Exception as e:
            error_msg = f"应用爱普生8050预设失败: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _apply_basic_preset(self, printer_name: str, preset_config: Dict, additional_info: str = "") -> Tuple[bool, str]:
        """应用基本预设参数"""
        try:
            if self._apply_epson_8050_devmode(printer_name, preset_config):
                message = f"✅ 基本参数已应用: {preset_config['display_name']}\n"
                if additional_info:
                    message += f"💡 {additional_info}"
                return True, message
            else:
                message = f"⚠️ 无法自动应用预设，请手动在驱动中选择对应预设"
                return False, message
        except Exception as e:
            return False, f"应用基本预设失败: {e}"
    
    def _apply_epson_8050_devmode(self, printer_name: str, preset_config: Dict) -> bool:
        """为爱普生8050打印机应用设备模式配置 (增强版)"""
        try:
            # 检查是否是爱普生打印机
            if not self._is_epson_printer(printer_name):
                self.logger.warning(f"打印机 {printer_name} 不是爱普生品牌，可能无法正确应用预设")
            
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                printer_info = win32print.GetPrinter(hprinter, 2)
                pDevMode = printer_info.get('pDevMode')
                
                if pDevMode:
                    # 应用爱普生8050特定配置
                    self._configure_epson_8050_devmode(pDevMode, preset_config)
                    
                    # 尝试应用设备模式
                    win32print.DocumentProperties(
                        0, hprinter, printer_name,
                        pDevMode, pDevMode,
                        0x08 | 0x10  # DM_IN_BUFFER | DM_OUT_BUFFER
                    )
                    
                    self.logger.info(f"爱普生8050设备模式已配置: {preset_config['display_name']}")
                    return True
                
                self.logger.warning("无法获取打印机设备模式")
                return False
                
            finally:
                win32print.ClosePrinter(hprinter)
                
        except Exception as e:
            self.logger.debug(f"爱普生8050设备模式配置失败: {e}")
            return False
    
    def _configure_epson_8050_devmode(self, devmode, preset_config: Dict):
        """配置爱普生8050设备模式 (增强版)"""
        try:
            # 设置纸张大小
            paper_code = preset_config.get("paper_code", 13)
            if hasattr(devmode, 'PaperSize'):
                devmode.PaperSize = paper_code
            
            # 设置方向
            orientation = preset_config.get("orientation", "纵向")
            if hasattr(devmode, 'Orientation'):
                devmode.Orientation = 1 if orientation == "纵向" else 2
            
            # 设置质量 - 爱普生8050高质量设置
            if hasattr(devmode, 'PrintQuality'):
                devmode.PrintQuality = -4  # 高质量
            
            # 设置颜色模式 - 相纸打印必须彩色
            if hasattr(devmode, 'Color'):
                devmode.Color = 2  # 彩色
            
            # 爱普生8050特定设置
            if hasattr(devmode, 'MediaType'):
                devmode.MediaType = 1  # 相纸
                
            # 设置打印质量为照片模式
            if hasattr(devmode, 'ICMMethod'):
                devmode.ICMMethod = 1  # 启用色彩管理
            
            self.logger.debug(f"爱普生8050设备模式参数已设置: {preset_config['display_name']}")
            
        except Exception as e:
            self.logger.error(f"配置爱普生8050设备模式失败: {e}")
    
    def _is_epson_printer(self, printer_name: str) -> bool:
        """检查是否是爱普生打印机"""
        epson_keywords = ["epson", "爱普生", "l8058", "l1250", "l1800"]
        printer_lower = printer_name.lower()
        return any(keyword in printer_lower for keyword in epson_keywords)
    
    def check_preset_configuration_status(self, printer_name: str) -> Dict[str, Any]:
        """
        检查预设配置状态
        
        Returns:
            配置状态详情
        """
        try:
            status = {
                "printer_name": printer_name,
                "printer_connected": False,
                "is_epson": False,
                "basic_config_available": False,
                "advanced_config_completed": False,
                "available_presets": list(self.epson_8050_presets.keys()),
                "missing_presets": [],
                "recommendations": []
            }
            
            # 检查打印机连接
            try:
                hprinter = win32print.OpenPrinter(printer_name)
                win32print.ClosePrinter(hprinter)
                status["printer_connected"] = True
            except Exception as e:
                status["printer_connected"] = False
                status["recommendations"].append("检查打印机连接和驱动安装")
                
            # 检查是否是爱普生打印机
            status["is_epson"] = self._is_epson_printer(printer_name)
            if not status["is_epson"]:
                status["recommendations"].append("此管理器专为爱普生打印机优化")
                
            # 检查基本配置
            status["basic_config_available"] = True  # Windows API基本支持
            
            # 检查高级配置状态
            status["advanced_config_completed"] = self.is_advanced_config_completed()
            if not status["advanced_config_completed"]:
                status["recommendations"].append("运行预设配置引导工具完成高级色彩设置")
                
            # 检查预设映射
            for preset_name in self.epson_8050_presets.keys():
                mapped_preset = self.load_preset_mapping(printer_name, preset_name.split("寸")[0] + "寸", 
                                                       "全景" if "全景" in preset_name else "拍立得")
                if not mapped_preset:
                    status["missing_presets"].append(preset_name)
                    
            if status["missing_presets"]:
                status["recommendations"].append(f"配置缺失的预设: {', '.join(status['missing_presets'])}")
                
            return status
            
        except Exception as e:
            self.logger.error(f"检查预设配置状态失败: {e}")
            return {"error": str(e)}
    
    def is_advanced_config_completed(self) -> bool:
        """检查是否已完成高级配置"""
        return (self.user_config.get("presets_configured", False) and 
                self.user_config.get("verification_passed", False))
    
    def open_printer_settings(self, printer_name: str) -> bool:
        """打开打印机驱动设置"""
        try:
            cmd = f'rundll32 printui.dll,PrintUIEntry /e /n "{printer_name}"'
            subprocess.Popen(cmd, shell=True)
            self.logger.info(f"已打开 {printer_name} 的驱动设置")
            return True
        except Exception as e:
            self.logger.error(f"打开打印机设置失败: {e}")
            return False
    
    def open_preset_guide(self) -> bool:
        """打开预设配置引导工具"""
        try:
            guide_file = "预设配置引导工具.py"
            if os.path.exists(guide_file):
                subprocess.Popen(['python', guide_file], shell=True)
                self.logger.info("已启动预设配置引导工具")
                return True
            else:
                self.logger.warning(f"未找到引导工具文件: {guide_file}")
                return False
        except Exception as e:
            self.logger.error(f"启动预设配置引导工具失败: {e}")
            return False
    
    def get_preset_info(self, preset_name: str) -> Optional[Dict]:
        """获取详细的预设信息"""
        if preset_name in self.epson_8050_presets:
            preset_info = self.epson_8050_presets[preset_name].copy()
            preset_info["configured"] = self.is_advanced_config_completed()
            return preset_info
        return None
    
    def get_all_presets_info(self) -> Dict[str, Dict]:
        """获取所有预设的详细信息"""
        all_presets = {}
        for preset_name in self.epson_8050_presets.keys():
            all_presets[preset_name] = self.get_preset_info(preset_name)
        return all_presets
    
    def get_available_presets(self) -> List[str]:
        """获取爱普生8050支持的预设列表"""
        return list(self.epson_8050_presets.keys())
    
    def save_preset_mapping(self, printer_name: str, size: str, mode: str, preset_name: str):
        """保存预设映射关系 (增强版)"""
        try:
            mappings = {}
            
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    mappings = json.load(f)
            
            key = f"{printer_name}_{size}_{mode}"
            mappings[key] = {
                "preset_name": preset_name,
                "created_date": datetime.now().isoformat(),
                "printer_name": printer_name,
                "size": size,
                "mode": mode
            }
            
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"保存爱普生8050预设映射: {key} -> {preset_name}")
            
        except Exception as e:
            self.logger.error(f"保存预设映射失败: {e}")
    
    def load_preset_mapping(self, printer_name: str, size: str, mode: str) -> Optional[str]:
        """加载预设映射关系"""
        try:
            if not os.path.exists(self.mapping_file):
                return None
            
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
            
            key = f"{printer_name}_{size}_{mode}"
            mapping = mappings.get(key)
            
            if isinstance(mapping, str):
                # 兼容旧版本格式
                return mapping
            elif isinstance(mapping, dict):
                return mapping.get("preset_name")
            
            return None
            
        except Exception as e:
            self.logger.error(f"加载预设映射失败: {e}")
            return None
    
    def load_user_config(self) -> Dict:
        """加载用户配置状态"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"加载用户配置失败: {e}")
            
        return {"presets_configured": False, "verification_passed": False}
    
    def get_configuration_summary(self) -> str:
        """获取配置摘要信息"""
        try:
            summary = "🎯 爱普生L8058打印机预设配置摘要\n\n"
            
            # 基本信息
            summary += f"📋 基本信息:\n"
            summary += f"• 支持预设数量: {len(self.epson_8050_presets)}\n"
            summary += f"• 高级配置状态: {'✅ 已完成' if self.is_advanced_config_completed() else '❌ 未完成'}\n"
            summary += f"• 配置文件: {self.config_file}\n\n"
            
            # 预设列表
            summary += f"🎯 可用预设列表:\n"
            for i, (preset_name, preset_info) in enumerate(self.epson_8050_presets.items(), 1):
                summary += f"{i}. {preset_info['display_name']}\n"
                summary += f"   纸张类型: {preset_info['paper_type']}\n"
                summary += f"   色彩设置: 亮度{preset_info['brightness']}, 对比度{preset_info['contrast']}, 饱和度{preset_info['saturation']}\n"
                summary += f"   色彩管理: {preset_info['color_management']}\n\n"
            
            # 使用建议
            summary += f"💡 使用建议:\n"
            if not self.is_advanced_config_completed():
                summary += f"• 建议运行「预设配置引导工具.py」完成高级配置\n"
            summary += f"• 系统会自动识别文件夹类型并应用对应预设\n"
            summary += f"• 预设可通过打印机驱动随时调整\n"
            summary += f"• 建议保持预设名称不变以确保系统正确识别\n"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"生成配置摘要失败: {e}")
            return f"配置摘要生成失败: {e}"