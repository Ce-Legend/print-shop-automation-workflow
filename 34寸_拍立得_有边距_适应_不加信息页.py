import os
import re
import datetime
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
import time

# 获取当前文件夹路径
folder_path = os.getcwd()

# 定义画布尺寸
canvas_sizes = {
    "3寸": (121, 83),
    "三寸": (121, 83),
    "4寸": (146, 96),
    "四寸": (146, 96)
}

canvas_width_mm, canvas_height_mm = None, None

# 优先从环境变量获取尺寸信息
polaroid_size = os.environ.get('POLAROID_SIZE', '')
original_folder_path = os.environ.get('ORIGINAL_FOLDER_PATH', '')

if polaroid_size and polaroid_size in canvas_sizes:
    canvas_width_mm, canvas_height_mm = canvas_sizes[polaroid_size]
    print(f"从环境变量获取尺寸: {polaroid_size}")
    # 如果有原始路径，使用原始路径作为folder_path
    if original_folder_path:
        folder_path = original_folder_path
else:
    # 回退到原来的路径判断方式
for key in canvas_sizes:
    if key in folder_path:
        canvas_width_mm, canvas_height_mm = canvas_sizes[key]
        break

if canvas_width_mm is None:
    print("无法确定画布尺寸。")
    print(f"当前路径: {folder_path}")
    print(f"环境变量尺寸: {polaroid_size}")
    print("支持的尺寸: 3寸、三寸、4寸、四寸")
    # 在自动化环境中不要求用户输入
    if not os.environ.get('POLAROID_SIZE'):
    input("按任意键退出...")
    exit()

# 定义参数（单位：毫米）
top_reserved = 3
top_margin = 1

bottom_reserved = 3
bottom_margin = 4 * (top_margin + top_reserved) - bottom_reserved

left_reserved = 3
left_margin = 0.8

right_reserved = 3
right_margin = 1.2

# 计算间距和图片尺寸
middle_space = 2 * (left_margin + left_reserved)
image_width_mm = (canvas_width_mm - left_margin - right_margin - middle_space) / 2
image_height_mm = canvas_height_mm - top_margin - bottom_margin

# 将毫米转换为像素（DPI=254）
dpi = 254
mm_to_pixel = dpi / 25.4

canvas_width_pixel = int(canvas_width_mm * mm_to_pixel)
canvas_height_pixel = int(canvas_height_mm * mm_to_pixel)

top_margin_pixel = int(top_margin * mm_to_pixel)
bottom_margin_pixel = int(bottom_margin * mm_to_pixel)
left_margin_pixel = int(left_margin * mm_to_pixel)
right_margin_pixel = int(right_margin * mm_to_pixel)

middle_space_pixel = int(middle_space * mm_to_pixel)
image_width_pixel = int(image_width_mm * mm_to_pixel)
image_height_pixel = int(image_height_mm * mm_to_pixel)


# 1. 生成尺寸说明图片（使用单张图片尺寸）
def generate_size_info_image(output_folder):
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
    match = re.search(r'(\d{6}-\d{15})', folder_path)
    if match:
        barcode_text = match.group(1)

    # 如果有条形码信息，先绘制条形码
    if barcode_text:
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
            barcode_info = f"订单号: {barcode_text}"
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


# 获取当前文件夹中的图片文件
image_files = [f for f in os.listdir('.') if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.heif', '.heic', '.livp'))]

# 检查是否有足够的图片
if len(image_files) < 1:
    print("当前文件夹中图片数量不足一张，无法进行操作。")
    exit()

# 标志位，用于控制日志是否已经打印
log_printed = False


# 主进程中的日志打印
def print_log():
    global log_printed
    if not log_printed:
        print(f"画布宽度: {canvas_width_mm} mm ({canvas_width_pixel} 像素)")
        print(f"画布高度: {canvas_height_mm} mm ({canvas_height_pixel} 像素)")
        print(f"图片区域宽度: {image_width_mm} mm ({image_width_pixel} 像素)")
        print(f"图片区域高度: {image_height_mm} mm ({image_height_pixel} 像素)")
        print(f"左边距（上边距）: {top_margin} mm ({top_margin_pixel} 像素)")
        print(f"下边距（左边距）: {bottom_margin} mm ({bottom_margin_pixel} 像素)")
        print(f"中间距（行间距）: {middle_space} mm ({middle_space_pixel} 像素)\r\n")
        log_printed = True


# 加载图片并调整大小
def load_and_pad(image_path, target_width, target_height):
    with Image.open(image_path) as img:
        img = img.copy()  # 避免原图被修改
        if img.mode == 'CMYK':
            img = img.convert('RGB')  # 确保统一色彩空间

    print(f"正在处理图片: {image_path}")

    # 旋转
    if img.width > img.height:
        img = img.transpose(Image.ROTATE_90)  # ✅ 已用无损方法

    # 高质量缩放：仅一次LANCZOS插值
    img_ratio = img.width / img.height
    target_ratio = target_width / target_height
    if img_ratio > target_ratio:
        new_width = target_width
        new_height = int(img.height * (new_width / img.width))
    else:
        new_height = target_height
        new_width = int(img.width * (new_height / img.height))

    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 粘贴到目标画布（无质量损失）
    padded_img = Image.new('RGB', (target_width, target_height), 'white')
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    padded_img.paste(resized_img, (paste_x, paste_y))

    return padded_img


# 粘贴图片到画布
def process_images(image_pair, output_folder):
    # 创建画布
    canvas = Image.new('RGB', (canvas_width_pixel, canvas_height_pixel), color='white')

    img1 = load_and_pad(image_pair[0], image_width_pixel, image_height_pixel)
    img2 = load_and_pad(image_pair[1], image_width_pixel, image_height_pixel)

    # 粘贴第一张图片
    position1 = (left_margin_pixel, top_margin_pixel)
    canvas.paste(img1, position1)

    # 粘贴第二张图片
    position2 = (left_margin_pixel + image_width_pixel + middle_space_pixel, top_margin_pixel)
    canvas.paste(img2, position2)

    # 生成输出文件名
    output_filename = f"{os.path.splitext(image_pair[0])[0]}+{os.path.splitext(image_pair[1])[0]}.jpg"
    output_path = os.path.join(output_folder, output_filename)

    # 保存每一对图片的画布
    canvas.save(output_path, quality=95, subsampling=0)
    print(f"合并图片已生成：{output_path}\r\n")


# 创建保存最终图片的文件夹
def create_output_folder():
    output_folder = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_合并"
    os.makedirs(output_folder, exist_ok=True)
    print(f"创建输出文件夹：{output_folder}\r\n")
    return output_folder


if __name__ == "__main__":
    try:
        start_time = time.time()
        output_folder = create_output_folder()

        print_log()  # 打印日志

        # 优化9：减少不必要的循环
        image_pairs = [(image_files[i], image_files[i + 1]) for i in range(0, len(image_files) - 1, 2)]
        if len(image_files) % 2 != 0:
            image_pairs.append((image_files[-1], image_files[-1]))

        # 优化2：提前加载并缓存图片
        loaded_images = {f: load_and_pad(f, image_width_pixel, image_height_pixel) for f in image_files}

        # 优化3：减少文件 I/O 操作，批量处理
        processed_canvases = []
        for pair in image_pairs:
            canvas = Image.new('RGB', (canvas_width_pixel, canvas_height_pixel), color='white')
            img1 = loaded_images[pair[0]]
            img2 = loaded_images[pair[1]]
            canvas.paste(img1, (left_margin_pixel, top_margin_pixel))
            canvas.paste(img2, (left_margin_pixel + image_width_pixel + middle_space_pixel, top_margin_pixel))
            processed_canvases.append((canvas, pair))

        # 批量保存
        print("\r\n")
        for canvas, pair in processed_canvases:
            output_filename = f"{os.path.splitext(pair[0])[0]}+{os.path.splitext(pair[1])[0]}.jpg"
            print(f"正在保存图片: {output_filename}")
            output_path = os.path.join(output_folder, output_filename)
            canvas.save(output_path, quality=95, subsampling=0)

        #generate_size_info_image(output_folder)

        end_time = time.time()
        elapsed_time = round(end_time - start_time, 2)
        print("\r\n")
        print(f"处理了{len(processed_canvases)*2}张图片")
        print(f"\r\n总耗时: {elapsed_time:.2f} 秒")

    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        input("按任意键退出...")