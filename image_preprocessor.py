#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图片预处理模块
处理拍立得模式的图片预处理
"""
import os
import logging
import tempfile
import shutil
import importlib.util
import sys
from typing import List, Optional
from config_manager import ConfigManager


class ImagePreprocessor:
    """图片预处理器"""
    
    def __init__(self, config_manager: ConfigManager = None):
        """初始化预处理器"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager or ConfigManager()
        
        # 预处理脚本路径
        self.script_34 = "34寸_拍立得_有边距_适应_不加信息页.py"
        self.script_56 = "56寸_拍立得_有边距_适应_不加信息页.py"
        
        # 临时目录列表
        self._temp_dirs = []
        
        # 检查脚本
        self._check_scripts()
        
    def _check_scripts(self):
        """检查预处理脚本是否存在"""
        for script in [self.script_34, self.script_56]:
            if not os.path.exists(script):
                self.logger.warning(f"预处理脚本不存在: {script}")
                
    def is_preprocessing_needed(self, mode: str) -> bool:
        """判断是否需要预处理"""
        if not mode:
            return False
        return "拍立得" in mode
    
    def preprocess_images(self, folder_path: str, size: str, mode: str) -> Optional[List[str]]:
        """
        预处理图片
        
        Args:
            folder_path: 原始图片文件夹路径
            size: 尺寸（3寸/4寸/5寸/6寸）
            mode: 模式（拍立得等）
            
        Returns:
            预处理后的图片路径列表，失败返回None
        """
        if not self.is_preprocessing_needed(mode):
            # 不需要预处理，返回原始图片
            return self._get_image_files(folder_path)
            
        # 确定使用哪个脚本
        if size in ["3寸", "4寸"]:
            script_path = self.script_34
        elif size in ["5寸", "6寸"]:
            script_path = self.script_56
        else:
            self.logger.warning(f"不支持的尺寸: {size}")
            return self._get_image_files(folder_path)
            
        try:
            # 检查特殊格式图片
            image_files = self._get_image_files(folder_path)
            unsupported_files = self._check_unsupported_formats(image_files)
            
            if unsupported_files:
                error_msg = f"检测到不支持的图片格式: {', '.join(unsupported_files)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # 创建临时工作目录
            temp_dir = tempfile.mkdtemp(prefix="preprocess_")
            self._temp_dirs.append(temp_dir)
            
            # 复制图片到临时目录
            work_dir = os.path.join(temp_dir, os.path.basename(folder_path))
            shutil.copytree(folder_path, work_dir)
            
            # 保存当前工作目录
            original_cwd = os.getcwd()
            
            try:
                # 切换到工作目录
                os.chdir(work_dir)
                
                # 设置环境变量，让脚本知道原始文件夹路径和尺寸信息
                original_path = os.environ.get('ORIGINAL_FOLDER_PATH', '')
                original_size = os.environ.get('POLAROID_SIZE', '')
                
                os.environ['ORIGINAL_FOLDER_PATH'] = folder_path
                os.environ['POLAROID_SIZE'] = size
                
                try:
                    # 动态加载并执行脚本
                    self._execute_script(script_path)
                finally:
                    # 恢复环境变量
                    if original_path:
                        os.environ['ORIGINAL_FOLDER_PATH'] = original_path
                    else:
                        os.environ.pop('ORIGINAL_FOLDER_PATH', None)
                    
                    if original_size:
                        os.environ['POLAROID_SIZE'] = original_size
                    else:
                        os.environ.pop('POLAROID_SIZE', None)
                
                # 查找处理后的图片
                processed_images = self._find_processed_images(work_dir)
                
                if processed_images:
                    self.logger.info(f"预处理完成，生成了 {len(processed_images)} 张图片")
                    return processed_images
                else:
                    self.logger.warning("预处理未生成任何图片，返回原始图片")
                    return self._get_image_files(folder_path)
                    
            finally:
                # 恢复工作目录
                os.chdir(original_cwd)
                
        except Exception as e:
            self.logger.error(f"预处理图片失败: {e}")
            # 预处理失败时抛出异常，让上层处理异常文件夹移动
            raise
    
    def _check_unsupported_formats(self, image_files: List[str]) -> List[str]:
        """检查不支持的图片格式"""
        unsupported = []
        unsupported_extensions = {'.heic', '.heif', '.livp'}  # 预处理脚本不支持的格式
        
        for image_file in image_files:
            ext = os.path.splitext(image_file)[1].lower()
            if ext in unsupported_extensions:
                unsupported.append(os.path.basename(image_file))
                
        return unsupported
    
    def _execute_script(self, script_path: str):
        """执行预处理脚本"""
        try:
            # 获取脚本路径（支持打包后路径）
            abs_script_path = self._get_script_path(script_path)
            if not abs_script_path or not os.path.exists(abs_script_path):
                raise FileNotFoundError(f"预处理脚本不存在: {script_path}")
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location("preprocess_module", abs_script_path)
            module = importlib.util.module_from_spec(spec)
            
            # 临时修改sys.argv，避免脚本解析命令行参数
            original_argv = sys.argv
            sys.argv = [abs_script_path]
            
            try:
                # 执行模块
                spec.loader.exec_module(module)
                
                # 如果模块有main函数，调用它
                if hasattr(module, 'main'):
                    module.main()
                else:
                    # 如果没有main函数，说明是直接执行型脚本
                    self.logger.info("脚本已执行完成（无main函数）")
                    
            finally:
                # 恢复sys.argv
                sys.argv = original_argv
                            
        except Exception as e:
            self.logger.error(f"执行预处理脚本失败: {e}")
            raise
    
    def _get_script_path(self, script_name: str) -> str:
        """获取脚本路径，支持打包后路径"""
        # 如果是打包后的exe文件
        if getattr(sys, 'frozen', False):
            # 打包后的脚本路径
            script_path = os.path.join(sys._MEIPASS, script_name)
            if os.path.exists(script_path):
                return script_path
        
        # 开发环境的脚本路径
        # 尝试当前目录中的脚本
        current_dir_script = os.path.join(os.path.dirname(__file__), script_name)
        if os.path.exists(current_dir_script):
            return os.path.abspath(current_dir_script)
        
        # 尝试相对路径
        if os.path.exists(script_name):
            return os.path.abspath(script_name)
            
        return None
    
    def _find_processed_images(self, work_dir: str) -> List[str]:
        """查找处理后的图片"""
        processed_images = []
        
        # 查找所有子目录中的图片
        for root, dirs, files in os.walk(work_dir):
            # 跳过原始目录
            if root == work_dir:
                continue
                
            for file in files:
                if self._is_image_file(file):
                    processed_images.append(os.path.join(root, file))
                    
        return sorted(processed_images)
    
    def _get_image_files(self, folder_path: str) -> List[str]:
        """获取文件夹中的所有图片文件 - 修复版"""
        images = []
        try:
            # 标准化路径格式，确保分隔符一致
            folder_path = os.path.normpath(folder_path)
            
            # 检查文件夹是否存在和可访问
            if not os.path.exists(folder_path):
                self.logger.error(f"文件夹不存在: {folder_path}")
                return images
                
            if not os.access(folder_path, os.R_OK):
                self.logger.error(f"无权限访问文件夹: {folder_path}")
                return images
            
            # 获取文件列表
            try:
                files = os.listdir(folder_path)
                self.logger.debug(f"文件夹 {folder_path} 包含 {len(files)} 个项目")
            except PermissionError:
                self.logger.error(f"没有权限读取文件夹: {folder_path}")
                return images
            except Exception as e:
                self.logger.error(f"读取文件夹内容失败: {folder_path}, 错误: {e}")
                return images
            
            # 检查每个文件
            for file in files:
                try:
                    # 使用normpath确保路径分隔符一致
                    file_path = os.path.normpath(os.path.join(folder_path, file))
                    
                    # 检查是否为文件
                    if not os.path.isfile(file_path):
                        self.logger.debug(f"跳过非文件项目: {file}")
                        continue
                    
                    # 检查文件扩展名
                    if self._is_image_file(file):
                        # 使用更可靠的文件检查方法
                        try:
                            # 尝试获取文件信息来确认文件可读
                            file_stat = os.stat(file_path)
                            if file_stat.st_size > 0:  # 文件大小大于0
                                images.append(file_path)
                                self.logger.debug(f"找到图片文件: {file} (大小: {file_stat.st_size} 字节)")
                            else:
                                self.logger.warning(f"图片文件为空: {file_path}")
                        except (OSError, IOError) as e:
                            self.logger.warning(f"无法访问图片文件: {file_path}, 错误: {e}")
                    else:
                        ext = os.path.splitext(file)[1].lower()
                        self.logger.debug(f"跳过非图片文件: {file} (扩展名: {ext})")
                        
                except Exception as e:
                    self.logger.warning(f"处理文件 {file} 时出错: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"读取文件夹 {folder_path} 失败: {e}")
        
        self.logger.info(f"文件夹 {folder_path} 共找到 {len(images)} 个图片文件")
        return sorted(images)
    
    def _is_image_file(self, filename: str) -> bool:
        """判断是否为图片文件"""
        extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.heif', '.heic', '.livp'}
        return os.path.splitext(filename)[1].lower() in extensions
    
    def cleanup(self):
        """清理临时文件"""
        for temp_dir in self._temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"清理临时目录: {temp_dir}")
            except Exception as e:
                self.logger.error(f"清理临时目录失败: {e}")
                
        self._temp_dirs.clear()
    
    def __del__(self):
        """析构函数，确保清理临时文件"""
        self.cleanup()


# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建预处理器
    preprocessor = ImagePreprocessor()
    
    # 测试判断是否需要预处理
    print("测试预处理判断:")
    test_modes = ["拍立得", "全景", "拍立得留白", None]
    for mode in test_modes:
        need = preprocessor.is_preprocessing_needed(mode)
        print(f"  模式 '{mode}': {'需要' if need else '不需要'}预处理")
    
    # 检查脚本
    print("\n检查预处理脚本:")
    for script in [preprocessor.script_34, preprocessor.script_56]:
        exists = os.path.exists(script)
        print(f"  {script}: {'存在' if exists else '不存在'}") 
