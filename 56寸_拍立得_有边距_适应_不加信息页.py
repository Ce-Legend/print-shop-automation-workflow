import os
import re
import datetime
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import time



# 获取目标比例
def get_aspect_ratio(folder_name):
    """
    根据文件夹名称获取目标高宽比。
    支持3寸、4寸、5寸、6寸。
    """
    if "3寸" in folder_name or "三寸" in folder_name:
        return (8.9 - 0.6) / (6.35 - 0.6)  # 3寸的目标高宽比
    elif "4寸" in folder_name or "四寸" in folder_name:
        return (10.2 - 0.6) / (7.6 - 0.6)  # 4寸的目标高宽比
    elif "5寸" in folder_name or "五寸" in folder_name:
        return (12.7 - 0.6) / (8.9 - 0.6)  # 5寸的目标高宽比
    elif "6寸" in folder_name or "六寸" in folder_name:
        return (15.2 - 0.6) / (10.2 - 0.6)  # 6寸的目标高宽比
    else:
        return None

# 调整图片大小并扩充边框
def resize_and_pad(image, aspect_ratio):
    """
    调整图片大小并在底部扩充原图高度的10%。
    如果图片宽度大于高度，顺时针旋转90度。
    """
    width, height = image.size
    if width > height:  # 如果宽度大于高度，顺时针旋转90度
        image = image.transpose(Image.ROTATE_90)
        width, height = image.size

    up = 0.04  # 上边框扩充比例
    x = 4      # 下边框扩充上边框的倍数
    left_right = 0.02  # 左右边框扩充比例

    # 初始扩充
    top_pad = int(height * up)  # 上边框扩充
    bottom_pad = int(height * up * x)  # 下边框扩充
    left_pad = int(width * left_right)  # 左边框扩充
    right_pad = int(width * left_right)  # 右边框扩充

    new_width = width + left_pad + right_pad
    new_height = height + top_pad + bottom_pad

    # 创建临时图像（初始扩充）
    temp_image = Image.new("RGB", (new_width, new_height), "white")
    temp_image.paste(image, (left_pad, top_pad))

    # 检查比例
    temp_aspect_ratio = new_height / new_width

    # 如果比例小于目标比例，按x倍比例继续扩充上下边框
    if temp_aspect_ratio < aspect_ratio:
        additional_height = int((new_width * aspect_ratio) - new_height)
        top_pad += int(additional_height / (x + 1))  # 上边框扩充1倍
        bottom_pad += additional_height - int(additional_height / (x + 1))  # 下边框扩充x倍
        new_height += additional_height

    # 如果比例大于目标比例，按对等比例扩充左右边框
    elif temp_aspect_ratio > aspect_ratio:
        additional_width = int((new_height / aspect_ratio) - new_width)
        left_pad += int(additional_width / 2)
        right_pad += additional_width - int(additional_width / 2)
        new_width += additional_width

    # 最终扩充后的图像
    final_image = Image.new("RGB", (new_width, new_height), "white")
    final_image.paste(image, (left_pad, top_pad))

    return final_image

def generate_size_info_image(output_folder, canvas_height_pixel, canvas_width_pixel):
    # 创建白色背景图片（使用计算出的单张图片尺寸）
    size_img = Image.new('RGB', (canvas_height_pixel, canvas_width_pixel), color='white')
    draw = ImageDraw.Draw(size_img)

    try:
        # 使用支持中文的字体
        font_path = "simhei.ttf"  # 黑体
        title_font = ImageFont.truetype(font_path, 40)  # 标题大一些
        text_font = ImageFont.truetype(font_path, 30)
    except:
        try:
            font_path = "msyh.ttc"  # 微软雅黑
            title_font = ImageFont.truetype(font_path, 40)
            text_font = ImageFont.truetype(font_path, 30)
        except:
            try:
                font_path = "/System/Library/Fonts/STHeiti Medium.ttc"  # 华文黑体
                title_font = ImageFont.truetype(font_path, 40)
                text_font = ImageFont.truetype(font_path, 30)
            except:
                title_font = ImageFont.load_default()
                text_font = ImageFont.load_default()
                print("警告：未找到中文字体，中文可能显示为方框")

    # 计算可用宽度（图片宽度的80%）
    available_width = int(canvas_height_pixel * 0.8)

    # 检查文件夹路径中是否包含6位数字-15位数字的格式
    barcode_text = None
    folder_path = os.getcwd()  # 获取当前文件夹路径
    match = re.search(r'(\d{6}-\d{15})', folder_path)
    if match:
        barcode_text = match.group(1)

    # 如果有条形码信息，先绘制条形码
    if barcode_text:
        # 生成条形码（宽度为可用宽度）
        try:
            # 计算条形码高度（保持宽高比）
            barcode_height = int(available_width * 0.3)  # 高度为宽度的30%

            # 高质量条形码参数
            barcode_options = {
                'module_width': 1.5,  # 增加模块宽度
                'module_height': 20,  # 增加高度
                'font_size': 24,
                'text_distance': 10,
                'quiet_zone': 10,
                'dpi': 300  # 提高DPI
            }

            # 条形码的Y位置在图片顶部
            barcode_position_y = 50  # 与图片顶部间隔50像素
            barcode_position = ((canvas_height_pixel - available_width) // 2, barcode_position_y)

            # 高质量条形码调整大小
            code = barcode.get_barcode_class('code128')(barcode_text, writer=ImageWriter())
            barcode_img = code.render(barcode_options)
            barcode_img = barcode_img.resize(
                (available_width, barcode_height),
                Image.Resampling.LANCZOS
            )
            barcode_img = barcode_img.convert('RGB')
            size_img.paste(barcode_img, barcode_position)

            # 添加条形码文本（红色文字）
            barcode_info = f"订单号：{barcode_text}"
            bbox = draw.textbbox((0, 0), barcode_info, font=text_font)
            text_width = bbox[2] - bbox[0]

            # 如果文字宽度超过可用宽度，调整字体大小
            while text_width > available_width and text_font.size > 10:
                text_font = ImageFont.truetype(text_font.path, text_font.size - 2) if hasattr(text_font, 'path') else ImageFont.load_default()
                bbox = draw.textbbox((0, 0), barcode_info, font=text_font)
                text_width = bbox[2] - bbox[0]

            # 条形码文本的Y位置在条形码下方
            barcode_text_y = barcode_position_y + barcode_height + 20  # 与条形码间隔20像素
            draw.text(((canvas_height_pixel - text_width) // 2, barcode_text_y), barcode_info, fill="red", font=text_font)

            # 文件夹路径的起始Y位置在条形码文本下方
            start_y = barcode_text_y + 50  # 与条形码文本间隔50像素
        except Exception as e:
            print(f"生成条形码时出错: {e}")
            start_y = 50  # 如果条形码生成失败，从图片顶部开始绘制文件夹路径
    else:
        start_y = 50  # 如果没有条形码信息，从图片顶部开始绘制文件夹路径

    # 将文件夹路径分割为每行最多20个字符
    lines = []
    current_line = ""
    for char in folder_path:
        if len(current_line) >= 30:
            lines.append(current_line)
            current_line = char
        else:
            current_line += char
    if current_line:
        lines.append(current_line)

    # 动态调整标题字体大小直到适合可用宽度
    line_height = 50  # 每行的高度
    for i, line in enumerate(lines):
        title_bbox = draw.textbbox((0, 0), line, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]

        while title_width > available_width and title_font.size > 10:
            title_font = ImageFont.truetype(title_font.path, title_font.size - 2) if hasattr(title_font, 'path') else ImageFont.load_default()
            title_bbox = draw.textbbox((0, 0), line, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]

        draw.text(((canvas_height_pixel - title_width) // 2, start_y + i * line_height+50), line, fill="red", font=title_font)

    # 保存图片
    output_filename = "生成的信息页.jpg"
    output_path = os.path.join(output_folder, output_filename)
    size_img.save(output_path)
    print(f"\r\n已生成信息页: {output_path}")

# 主程序
def main():
    try:
        start_time = time.time()
        folder_name = os.path.basename(os.getcwd())
        aspect_ratio = get_aspect_ratio(folder_name)

        if aspect_ratio is None:
            print("文件夹名称不符合要求")
            return

        images = [f for f in os.listdir() if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.heif', '.heic', '.livp'))]
        resized_images = []

        current_time = time.strftime("%Y%m%d_%H%M%S")
        resized_folder = f"{current_time}_拍立得"
        os.makedirs(resized_folder, exist_ok=True)

        # 批量处理图片
        for image_file in images:
            print(f"正在处理图片：{image_file}")
            image = Image.open(image_file)
            resized_image = resize_and_pad(image, aspect_ratio)
            resized_images.append((image_file, resized_image))

        # 统一保存图片
        print("\r\n")
        for image_file, resized_image in resized_images:
            resized_image_path = os.path.join(resized_folder, f"{os.path.splitext(image_file)[0]}_pld.jpg")
            print(f"正在保存图片：{resized_image_path}")
            resized_image.save(resized_image_path, quality=95, subsampling=0)

        canvas_width_pixel = 1000
        canvas_height_pixel = int(canvas_width_pixel / aspect_ratio)

        #generate_size_info_image(resized_folder, canvas_height_pixel, canvas_width_pixel)

        end_time = time.time()
        print("\r\n")
        print(f"处理了{len(resized_images)}张图片")
        print(f"\r\n总耗时: {end_time - start_time:.2f} 秒")

    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        input("按任意键退出...")

if __name__ == "__main__":
    main()