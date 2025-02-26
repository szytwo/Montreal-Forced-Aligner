import os

from PIL import ImageColor


# 颜色和透明度转换函数
def color_to_ass(color_str, alpha):
    try:
        rgb = ImageColor.getrgb(color_str)
        bbggrr = f"{rgb[2]:02X}{rgb[1]:02X}{rgb[0]:02X}"
        return f"&H{alpha:02X}{bbggrr}"
    except:
        return "&H00FFFFFF"  # 默认白色


# 转换时间格式并添加事件行
def srt_time_to_ass(srt_time):
    time_str, millis = srt_time.replace(',', '.').split('.')
    h, m, s = time_str.split(':')
    millis = millis.ljust(3, '0')[:3]
    cs = f"{int(millis) // 10:02d}"
    return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs}"


def create_subtitle_ass(
        subtitle_file: str,
        video_width: int,
        video_height: int,  # 新增视频高度参数
        font: str = "微软雅黑",  # 改为字体名称，而非文件路径
        font_size: int = 70,
        font_color: str = "yellow",
        stroke_color: str = "black",
        stroke_width: int = 1,
        bottom: int = 10,
        opacity: int = 0
) -> str:
    """
    从 SRT 字幕文件创建 ASS 字幕文件。
    :param subtitle_file: SRT 文件路径
    :param video_width: 视频宽度
    :param video_height: 视频高度（新增参数，用于计算位置）
    :param font: 字体名称（如 "Arial"）
    :param font_size: 字体大小
    :param font_color: 字体颜色（名称或十六进制，如 "#FFFFFF"）
    :param stroke_color: 描边颜色
    :param stroke_width: 描边宽度
    :param bottom: 字幕距底部距离
    :param opacity: 透明度（0-255，0=不透明）
    :return: ASS 文件路径
    """
    if not os.path.exists(subtitle_file):
        raise FileNotFoundError(f"字幕文件不存在: {subtitle_file}")

    # 生成 ASS 文件路径
    base_path = os.path.splitext(subtitle_file)[0]
    ass_path = f"{base_path}.ass"

    # 根据视频宽度调整字体大小（示例逻辑，按需调整）
    reference_width = 1280
    font_size = int(font_size * (video_width / reference_width))

    # 解析 SRT 文件
    subtitles = []
    try:
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n\n')
            for block in lines:
                if not block.strip():
                    continue
                parts = block.strip().split('\n')
                if len(parts) < 3:
                    continue
                time_line = parts[1]
                text = '\\N'.join(parts[2:])  # 保留换行并转换为 ASS 的 \N
                start, end = time_line.split(' --> ')
                subtitles.append((start, end, text))
    except Exception as e:
        raise RuntimeError(f"解析 SRT 失败: {e}")

    # 生成 ASS 内容
    ass_content = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {video_width}",
        f"PlayResY: {video_height}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font},{font_size},"
        f"{color_to_ass(font_color, opacity)},"
        f"{color_to_ass(font_color, opacity)},"
        f"{color_to_ass(stroke_color, 0)},"
        "&H00000000,0,0,0,0,100,100,0,0,1,"
        f"{stroke_width},0,2,0,0,{bottom},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    for start, end, text in subtitles:
        ass_start = srt_time_to_ass(start)
        ass_end = srt_time_to_ass(end)
        ass_content.append(f"Dialogue: 0,{ass_start},{ass_end},Default,,0,0,0,,{text}")

    # 写入 ASS 文件
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ass_content))

    return ass_path
