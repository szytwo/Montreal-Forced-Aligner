import os
import subprocess

from PIL import ImageColor

from custom.TextProcessor import TextProcessor
from custom.file_utils import logging, add_suffix_to_filename


class AssProcessor:
    def __init__(self):
        """
        初始化ASR音频与文本对齐处理器。
        """
        ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")  # Fmpeg 的路径
        self.ffmpeg_path = ffmpeg_path

    # 颜色和透明度转换函数
    # noinspection PyTypeChecker
    @staticmethod
    def color_to_ass(color_str, alpha):
        try:
            rgb = ImageColor.getrgb(color_str)
            bbggrr = f"{rgb[2]:02X}{rgb[1]:02X}{rgb[0]:02X}"

            return f"&H{alpha:02X}{bbggrr}"
        except Exception as e:
            TextProcessor.log_error(e)
            return "&H00FFFFFF"  # 默认白色

    # 转换时间格式并添加事件行
    @staticmethod
    def srt_time_to_ass(srt_time):
        time_str, millis = srt_time.replace(',', '.').split('.')
        h, m, s = time_str.split(':')
        millis = millis.ljust(3, '0')[:3]
        cs = f"{int(millis) // 10:02d}"

        return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs}"

    def create_subtitle_ass(self,
                            subtitle_file: str,
                            video_width: int,
                            video_height: int,  # 新增视频高度参数
                            font_path: str = "fonts/yahei.ttf",
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
        :param font_path: 字体文件路径
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
        # 提取字体名称
        font_name = TextProcessor.get_font_name(font_path)
        # 自动从字体路径提取字体目录
        font_dir = os.path.dirname(os.path.abspath(font_path))
        # 生成 ASS 文件路径
        base_path = os.path.splitext(subtitle_file)[0]
        ass_path = f"{base_path}.ass"
        # 以 1280px 宽度的视频为参照，自动适配字体大小
        reference_width = 1280
        font_size = int(font_size * (video_width / reference_width))
        _, line_height = TextProcessor.get_font_size(font_path, font_size, "字幕字体")
        # 自动适应bottom，并确保不为负数或过小
        bottom = max(line_height, bottom)
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
            f"Style: Default,{font_name},{line_height},"
            f"{self.color_to_ass(font_color, opacity)},"
            f"{self.color_to_ass(font_color, opacity)},"
            f"{self.color_to_ass(stroke_color, 0)},"
            "&H00000000,0,0,0,0,100,100,0,0,1,"
            f"{stroke_width},0,2,0,0,{bottom},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        for start, end, text in subtitles:
            ass_start = self.srt_time_to_ass(start)
            ass_end = self.srt_time_to_ass(end)
            ass_content.append(f"Dialogue: 0,{ass_start},{ass_end},Default,,0,0,0,,{text}")

        # 写入 ASS 文件
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ass_content))

        logging.info(f"Ass file saved: {ass_path}，{font_dir}")

        return ass_path, font_dir

    @staticmethod
    def ffmpeg_safe_path(path: str, relcolon: bool = False) -> str:
        """将路径转换为 FFmpeg 安全的格式"""
        # 转换为绝对路径并统一正斜杠
        abs_path = os.path.abspath(path).replace("\\", "/")
        # 方案1：转换为类 Unix 风格（需 FFmpeg 支持）
        # 示例：D:/AI/project → /D/AI/project
        # unix_style = abs_path.replace(":/", "/", 1).replace(":", "", 1)
        # return f"'{unix_style}'"
        # 方案2：直接使用正斜杠并转义冒号（通用）
        # 示例：D:/AI/project → D\:/AI/project
        if relcolon:
            abs_path = abs_path.replace(':', '\\\\:')

        return abs_path

    def subtitle_with_ffmpeg(
            self,
            video_path: str,
            ass_path: str,
            font_dir: str = "fonts"  # 字体文件所在目录
    ) -> str:
        """使用 FFmpeg 烧录字幕到视频"""
        video_output = add_suffix_to_filename(video_path, f"_ass")
        video_path = self.ffmpeg_safe_path(video_path)
        video_output = self.ffmpeg_safe_path(video_output)
        ass_path = self.ffmpeg_safe_path(ass_path, True)
        font_dir = self.ffmpeg_safe_path(font_dir, True)
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,  # 输入视频
            "-vf", f"subtitles={ass_path}:fontsdir={font_dir}",  # 指定字体目录
            '-c:a', "copy",  # 保持音频流不变
            "-crf", "18",  # 设置压缩质量
            "-preset", "slow",  # 设置编码速度/质量平衡
            "-y",
            video_output
        ]

        ffmpeg_cmd = " ".join(cmd)  # 打印实际执行的命令（调试用）
        logging.info(f"cmd: {ffmpeg_cmd}")
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",  # 指定 UTF-8 编码
            check=True
        )
        logging.info(f"字幕已到烧录视频: {video_output}")

        return video_output
