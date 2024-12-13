import os
from pathlib import Path
from fastapi import UploadFile
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
from custom.file_utils import logging, get_full_path
from custom.MfaAlignProcessor import MfaAlignProcessor

class VideoProcessor:
    def __init__(self,
                 temp_dir="results/"):
        """
        初始化视频处理器，设置临时文件目录。
        :param temp_dir: 临时目录，用于保存生成的中间文件或输出文件。
        """
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)  # 创建临时目录（如果不存在）

    async def save_upload_to_video(self, upload_file: UploadFile):
        """
        保存上传的文件到本地并返回路径。
        :param upload_file: FastAPI 的上传文件对象
        :return: 保存后的文件路径
        """
        # 从上传文件名提取基础名称（无扩展名）
        video_name = Path(upload_file.filename).stem
        # 构建保存路径
        video_dir = os.path.join(self.temp_dir, video_name)
        os.makedirs(video_dir, exist_ok=True)  # 创建目录（如果不存在）
        upload_path = os.path.join(video_dir, upload_file.filename)
        # 如果同名文件已存在，先删除
        if os.path.exists(upload_path):
            os.remove(upload_path)

        logging.info(f"接收上传 {upload_file.filename} 请求 {upload_path}")

        try:
            # 异步保存上传的文件内容
            with open(upload_path, "wb") as f:
                f.write(await upload_file.read())  # 异步读取并写入文件

            return upload_path
        except Exception as e:
            raise Exception(f"{upload_file.filename} 视频文件保存失败: {str(e)}")
        finally:
            await upload_file.close()  # 显式关闭上传文件
        
    async def save_upload_to_srt(self, upload_file: UploadFile):
        """
        保存上传的文件到本地并返回路径。
        :param upload_file: FastAPI 的上传文件对象
        :return: 保存后的文件路径
        """
        # 从上传文件名提取基础名称（无扩展名）
        srt_name = Path(upload_file.filename).stem
        # 构建保存路径
        srt_dir = os.path.join(self.temp_dir, srt_name)
        os.makedirs(srt_dir, exist_ok=True)  # 创建目录（如果不存在）
        upload_path = os.path.join(srt_dir, upload_file.filename)
        # 如果同名文件已存在，先删除
        if os.path.exists(upload_path):
            os.remove(upload_path)

        logging.info(f"接收上传 {upload_file.filename} 请求 {upload_path}")

        try:
            # 异步保存上传的文件内容
            with open(upload_path, "wb") as f:
                f.write(await upload_file.read())  # 异步读取并写入文件

            return upload_path
        except Exception as e:
            raise Exception(f"{upload_file.filename} 字幕文件保存失败: {str(e)}")
        finally:
            await upload_file.close()  # 显式关闭上传文件

    @staticmethod
    def parse_srt_timestamp(timestamp: str) -> float:
        """
        将 SRT 时间戳（如 00:01:02,500）转换为秒数。
        :param timestamp: 字符串格式的时间戳
        :return: 秒数（float）
        """
        try:
            h, m, s = timestamp.split(":")
            s, ms = s.split(",")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        except ValueError as e:
            raise ValueError(f"时间戳格式错误: {timestamp}") from e

    def create_subtitle_clip(
        self,
        subtitle_file: str,
        video_width: int,
        font: str = "fonts/yahei.ttf",
        font_size: int = 70,
        font_color: str = "yellow",
        stroke_color: str = "yellow",
        stroke_width: int = 0,
        bottom: int = 10, 
        opacity: int = 0
    ) -> list:
        """
        从 SRT 字幕文件创建字幕片段列表。
        :param subtitle_file: SRT 文件路径
        :param video_width: 视频宽度，用于调整字幕宽度
        :param font: 字体文件路径
        :param font_size: 字体大小
        :param font_color: 字体颜色
        :param stroke_color: 描边颜色
        :param stroke_width: 描边宽度
        :param bottom: 字幕与视频底部的距离
        :param opacity: 字幕透明度 (0-255)
        :return: 字幕片段列表
        """
        if not os.path.exists(subtitle_file):
            raise FileNotFoundError(f"字幕文件不存在: {subtitle_file}")
        
        # 以 1280px 宽度的视频为参照，自动适配字体大小
        reference_width = 1280
        font_size = int(font_size * (video_width / reference_width))
        # 自动根据字体大小设置高度
        line_height_ratio = 1.2  # 行间距比例，通常 1.2-1.5 比较合适
        single_line_height = int(font_size * line_height_ratio)  # 单行高度
        max_lines = 3  # 最大行数
        # 自动根据字体大小计算字幕高度
        calculated_height = single_line_height * max_lines
        min_bottom = 10  # 设定最小底部距离，避免过小或负数
        # 自动适应bottom兼容多行，并确保不为负数或过小
        bottom = max(min_bottom, bottom - (single_line_height * (max_lines - 1)))

        subtitles = []  # 用于存储解析后的字幕数据
        try:
            # 读取 SRT 文件内容并逐行解析
            with open(subtitle_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                it = iter(lines)
                for line in it:
                    if '-->' in line:  # 检测时间戳行
                        start, end = line.split(' --> ')
                        text = ''
                        # 收集当前时间段的字幕文本
                        for next_line in it:
                            if next_line.strip() == '':
                                break
                            text += next_line.strip() + ' '
                        subtitles.append((start, end.strip(), text.strip()))
        except Exception as e:
            raise RuntimeError(f"读取字幕文件失败: {subtitle_file}") from e
        # 创建字幕片段
        subtitle_clips = []
        for start, end, text in subtitles:
            try:
                start_seconds = self.parse_srt_timestamp(start)
                end_seconds = self.parse_srt_timestamp(end)
                # 创建单个字幕文本片段
                text_clip = TextClip(
                    text,
                    fontsize=font_size,
                    color=font_color,
                    align='center',
                    method='caption',
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    font=font,
                    size=(video_width, calculated_height),
                )
                text_clip = text_clip.set_start(start_seconds)
                text_clip = text_clip.set_duration(end_seconds - start_seconds)
                text_clip = text_clip.set_position(('center', 'bottom')).margin(bottom=bottom, opacity=opacity)

                subtitle_clips.append(text_clip)
            except Exception as e:
                raise RuntimeError(f"创建字幕失败: {text} ({start} - {end})") from e

        return subtitle_clips
        
    def video_subtitle(
        self,
        video_file: str,
        audio_file: str = None,
        prompt_text: str = None,
        add_audio: bool = False,
        subtitle_file: str = None,
        font: str = "fonts/yahei.ttf",
        font_size: int = 70,
        font_color: str = "yellow",
        stroke_color: str = "yellow",
        stroke_width: int = 0,
        bottom: int = 10, 
        opacity: int = 0
    ) -> str:
        """
        给视频添加字幕（以及可选的音频）并输出。
        :param video_file: 视频文件路径
        :param audio_file: 替换的音频文件路径
        :param prompt_text: 用于生成字幕的文本
        :param add_audio: 是否添加音频
        :param subtitle_file: SRT 字幕文件路径
        :param font: 字体文件路径
        :param font_size: 字体大小
        :param font_color: 字体颜色
        :param stroke_color: 描边颜色
        :param stroke_width: 描边宽度
        :param bottom: 字幕与视频底部的距离
        :param opacity: 字幕透明度 (0-255)
        :return: 输出视频的路径
        """

        if not os.path.exists(video_file):
            raise FileNotFoundError(f"视频文件不存在: {video_file}")
        if audio_file and not os.path.exists(audio_file):
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")
        
        video_clip = None
        audio_clip = None
        final_clip = None

        try:
            # 加载视频文件
            video_clip = VideoFileClip(video_file)
            video_width = video_clip.w  # 获取视频宽度
            # 如果没有提供字幕文件，使用 MFA 对齐生成
            if not subtitle_file and prompt_text:
                mfa_align_processor = MfaAlignProcessor()
                maxsize = video_width / font_size - 2  # 每行最大字符数
                subtitle_file = mfa_align_processor.align_audio_with_text(
                    audio_path=audio_file,
                    text=prompt_text,
                    min_line_length=0,
                    max_line_length=maxsize,
                )
            # 创建字幕片段
            subtitle_clips = self.create_subtitle_clip(
                subtitle_file=subtitle_file,
                video_width=video_width,
                font=font,
                font_size=font_size,
                font_color=font_color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                bottom = bottom, 
                opacity = opacity
            )
            # 合成视频
            final_clip = CompositeVideoClip([video_clip] + subtitle_clips)
            # 可选：替换音频
            if add_audio and audio_file:
                audio_clip = AudioFileClip(audio_file)
                final_clip = final_clip.without_audio().set_audio(audio_clip)
            # 输出文件路径
            video_dir = Path(video_file).parent
            os.makedirs(video_dir, exist_ok=True)
            output_video = os.path.join(video_dir, f"{Path(video_file).stem}_output{Path(video_file).suffix}")
            # 保存视频
            # # NVIDIA 编码器 codec="h264_nvenc"    CPU编码 codec="libx264"
            final_clip.write_videofile(output_video, codec="h264_nvenc", audio_codec="aac", fps=video_clip.fps)

            return output_video, subtitle_file
        except Exception as e:
            # 捕获异常并记录
            logging.error(f"处理视频时发生错误: {str(e)}")
            # 如果需要重新抛出以让外部感知异常
            raise e
        finally:
            # 确保资源被释放
            if final_clip:
                final_clip.close()
            if video_clip:
                video_clip.close()
            if audio_clip:
                audio_clip.close()
