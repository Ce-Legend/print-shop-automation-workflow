"""
信息页生成模块
负责生成包含订单信息和条形码的信息页
"""
import os
import logging
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
from typing import Optional, Tuple
import tempfile

from folder_monitor import FolderInfo


class InfoPageGenerator:
    """信息页生成器"""
    
    # 默认DPI
    DPI = 254
    
    # 页面尺寸（厘米）
    PAGE_WIDTH_CM = 10.2
    PAGE_HEIGHT_CM = 8.9
    
    # 页面尺寸（像素）
    PAGE_WIDTH_PX = int(PAGE_WIDTH_CM * DPI / 2.54)
    PAGE_HEIGHT_PX = int(PAGE_HEIGHT_CM * DPI / 2.54)
    
    # 红线参数
    LINE_WIDTH_RATIO = 1/20  # 线宽为高度的1/20
    TOP_LINE_POSITION_RATIO = 1/10  # 上边线距顶部1/10
    BOTTOM_LINE_POSITION_RATIO = 1/10  # 下边线距底部1/10
    
    def __init__(self):
        """初始化生成器"""
        self.logger = logging.getLogger(__name__)
        
    def _get_font_paths(self):
        """获取字体路径列表，支持打包后路径"""
        import sys
        
        font_paths = []
        
        # 如果是打包后的exe文件
        if getattr(sys, 'frozen', False):
            # 打包后的字体路径
            font_paths.extend([
                os.path.join(sys._MEIPASS, 'fonts', 'simhei.ttf'),
                os.path.join(sys._MEIPASS, 'fonts', 'msyh.ttc'),
            ])
        
        # 系统字体路径
        font_paths.extend([
            "simhei.ttf",  # 黑体
            "msyh.ttc",    # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyh.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc"  # Mac华文黑体
        ])
        
        return font_paths
        
    def generate(self, folder_info: FolderInfo, output_dir: str = None) -> Optional[str]:
        """
        生成信息页
        
        Args:
            folder_info: 文件夹信息
            output_dir: 输出目录，默认为临时目录
            
        Returns:
            生成的信息页文件路径，失败返回None
        """
        try:
            # 创建白色背景图片
            img = Image.new('RGB', (self.PAGE_WIDTH_PX, self.PAGE_HEIGHT_PX), 'white')
            draw = ImageDraw.Draw(img)
            
            # 绘制红线
            self._draw_red_lines(draw)
            
            # 加载字体
            title_font, text_font = self._load_fonts()
            
            # 计算内容区域
            line_width = int(self.PAGE_HEIGHT_PX * self.LINE_WIDTH_RATIO)
            top_margin = int(self.PAGE_HEIGHT_PX * self.TOP_LINE_POSITION_RATIO) + line_width
            bottom_margin = int(self.PAGE_HEIGHT_PX * self.BOTTOM_LINE_POSITION_RATIO) + line_width
            content_height = self.PAGE_HEIGHT_PX - top_margin - bottom_margin
            
            # 绘制内容
            current_y = top_margin + 50  # 内容起始位置
            
            # 如果有订单号，先绘制条形码
            if folder_info.order_id:
                barcode_height = self._draw_barcode(
                    img, draw, folder_info.order_id, 
                    current_y, text_font
                )
                current_y += barcode_height + 50
            
            # 绘制文件夹名称
            self._draw_folder_name(
                draw, folder_info.name, 
                current_y, title_font
            )
            
            # 保存图片
            if output_dir is None:
                output_dir = tempfile.mkdtemp()
            
            filename = f"info_page_{folder_info.order_id or 'unknown'}.jpg"
            output_path = os.path.join(output_dir, filename)
            
            img.save(output_path, 'JPEG', quality=95, subsampling=0)
            self.logger.info(f"信息页已生成: {output_path}")
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"生成信息页失败: {e}")
            return None
    
    def _draw_red_lines(self, draw: ImageDraw):
        """绘制红色横线"""
        line_width = int(self.PAGE_HEIGHT_PX * self.LINE_WIDTH_RATIO)
        
        # 上边线
        top_line_y = int(self.PAGE_HEIGHT_PX * self.TOP_LINE_POSITION_RATIO)
        draw.rectangle(
            [(0, top_line_y), (self.PAGE_WIDTH_PX, top_line_y + line_width)],
            fill='red'
        )
        
        # 下边线
        bottom_line_y = self.PAGE_HEIGHT_PX - int(self.PAGE_HEIGHT_PX * self.BOTTOM_LINE_POSITION_RATIO) - line_width
        draw.rectangle(
            [(0, bottom_line_y), (self.PAGE_WIDTH_PX, bottom_line_y + line_width)],
            fill='red'
        )
    
    def _load_fonts(self) -> Tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
        """加载中文字体"""
        title_font_size = 28  # 从40调整为28，避免裁切
        text_font_size = 20   # 从30调整为20，避免裁切
        
        font_paths = self._get_font_paths()
        
        for font_path in font_paths:
            try:
                title_font = ImageFont.truetype(font_path, title_font_size)
                text_font = ImageFont.truetype(font_path, text_font_size)
                self.logger.info(f"成功加载字体: {font_path}")
                return title_font, text_font
            except Exception as e:
                self.logger.debug(f"字体加载失败 {font_path}: {e}")
                continue
                
        # 如果都失败，使用默认字体
        self.logger.warning("未找到中文字体，使用默认字体")
        return ImageFont.load_default(), ImageFont.load_default()
    
    def _draw_barcode(self, img: Image, draw: ImageDraw, order_id: str, 
                      y_position: int, font: ImageFont.FreeTypeFont) -> int:
        """
        绘制条形码
        
        Returns:
            条形码占用的高度
        """
        try:
            # 生成条形码
            available_width = int(self.PAGE_WIDTH_PX * 0.8)
            barcode_height = int(available_width * 0.3)
            
            # 条形码配置
            barcode_options = {
                'module_width': 1.5,
                'module_height': 20,
                'font_size': 24,
                'text_distance': 10,
                'quiet_zone': 10,
                'dpi': 300
            }
            
            # 生成条形码图片
            code = barcode.get_barcode_class('code128')(order_id, writer=ImageWriter())
            barcode_img = code.render(barcode_options)
            
            # 调整大小
            barcode_img = barcode_img.resize(
                (available_width, barcode_height),
                Image.Resampling.LANCZOS
            )
            barcode_img = barcode_img.convert('RGB')
            
            # 粘贴条形码
            x_position = (self.PAGE_WIDTH_PX - available_width) // 2
            img.paste(barcode_img, (x_position, y_position))
            
            # 绘制订单号文本
            order_text = f"订单号：{order_id}"
            bbox = draw.textbbox((0, 0), order_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (self.PAGE_WIDTH_PX - text_width) // 2
            text_y = y_position + barcode_height + 20
            
            draw.text((text_x, text_y), order_text, fill='red', font=font)
            
            # 返回总高度
            return barcode_height + 40 + (bbox[3] - bbox[1])
            
        except Exception as e:
            self.logger.error(f"生成条形码失败: {e}")
            return 0
    
    def _draw_folder_name(self, draw: ImageDraw, folder_name: str, 
                          y_position: int, font: ImageFont.FreeTypeFont):
        """绘制文件夹名称"""
        # 将长文件夹名称分行
        max_chars_per_line = 25
        lines = []
        current_line = ""
        
        for char in folder_name:
            if len(current_line) >= max_chars_per_line:
                lines.append(current_line)
                current_line = char
            else:
                current_line += char
                
        if current_line:
            lines.append(current_line)
        
        # 绘制每一行
        line_height = 50
        available_width = int(self.PAGE_WIDTH_PX * 0.9)
        
        for i, line in enumerate(lines):
            # 获取文本宽度
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            
            # 如果文本太宽，缩小字体
            temp_font = font
            while text_width > available_width and temp_font.size > 10:
                temp_font = ImageFont.truetype(temp_font.path, temp_font.size - 2)
                bbox = draw.textbbox((0, 0), line, font=temp_font)
                text_width = bbox[2] - bbox[0]
            
            # 居中绘制
            x = (self.PAGE_WIDTH_PX - text_width) // 2
            y = y_position + i * line_height
            
            draw.text((x, y), line, fill='black', font=temp_font)


# 测试代码
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 测试数据
    test_folder = FolderInfo(
        path="test_path",
        name="5寸 【拍立得留白】,10张美照250530-620547284501157",
        size="5寸",
        mode="拍立得",
        count=10,
        order_id="250530-620547284501157"
    )
    
    # 生成信息页
    generator = InfoPageGenerator()
    output_path = generator.generate(test_folder, ".")
    
    if output_path:
        print(f"信息页已生成: {output_path}") 