import json
import subprocess
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from moviepy.editor import *
from tqdm import tqdm

from custom.AsrProcessor import AsrProcessor
from custom.AssProcessor import AssProcessor
from custom.MfaAlignProcessor import MfaAlignProcessor
from custom.TextProcessor import TextProcessor
from custom.file_utils import logging, add_suffix_to_filename


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
    def convert_video_fps(video_path: str, target_fps: int = 25):
        """ 将视频转换为 指定 FPS """
        # 检查视频帧率
        original_fps = VideoProcessor.get_video_frame_rate(video_path)

        if original_fps != target_fps:
            logging.info(f"视频帧率为 {original_fps} FPS，转换为 {target_fps} FPS")
            converted_video_path = add_suffix_to_filename(video_path, f"_{target_fps}")

            # 使用 FFmpeg 转换帧率
            try:
                # NVIDIA 编码器 codec="h264_nvenc"    CPU编码 codec="libx264"
                # 创建 FFmpeg 命令来合成视频
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-r", f"{target_fps}",  # 设置输出帧率
                    "-c:v", "libx264",  # 使用 libx264 编码器
                    "-crf", "18",  # 设置压缩质量
                    "-preset", "slow",  # 设置编码速度/质量平衡
                    "-c:a", "aac",  # 设置音频编码器
                    "-b:a", "192k",  # 设置音频比特率
                    "-ar", "44100",
                    "-ac", "2",
                    "-y",
                    converted_video_path
                ]
                # 执行 FFmpeg 命令
                subprocess.run(cmd, capture_output=True, text=True, check=True)

                logging.info(f"视频转换完成: {converted_video_path}")
                return converted_video_path, target_fps
            except subprocess.CalledProcessError as e:
                # 捕获任何在处理过程中发生的异常
                ex = Exception(f"Error ffmpeg: {e.stderr}")
                TextProcessor.log_error(ex)
                return None, None
        else:
            logging.info(f"视频帧率已经是 {target_fps} FPS，无需转换")
            return video_path, original_fps

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

        logging.info(f"正在创建字幕片段...")
        subtitle_clips = []
        for start, end, text in tqdm(subtitles):
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
            prompt_text: str = None,
            subtitle_file: str = None,
            font: str = "fonts/yahei.ttf",
            font_size: int = 70,
            font_color: str = "yellow",
            stroke_color: str = "yellow",
            stroke_width: int = 0,
            bottom: int = 10,
            opacity: int = 0,
            fps: int = 25,
            isass: bool = False,
            language: str = None
    ) -> tuple[str | None | Any, str | None | Any, str | None | Any, str | None | Any] | None:
        """
        给视频添加字幕（以及可选的音频）并输出。
        :param video_file: 视频文件路径
        :param prompt_text: 用于生成字幕的文本
        :param subtitle_file: SRT 字幕文件路径
        :param font: 字体文件路径
        :param font_size: 字体大小
        :param font_color: 字体颜色
        :param stroke_color: 描边颜色
        :param stroke_width: 描边宽度
        :param bottom: 字幕与视频底部的距离
        :param opacity: 字幕透明度 (0-255)
        :param fps: 目标帧率
        :param isass: 是否使用ASS
        :param language: 语言
        :return: 输出视频的路径
        """

        if not os.path.exists(video_file):
            raise FileNotFoundError(f"视频文件不存在: {video_file}")

        audio_file = VideoProcessor.extract_audio(video_file)
        video_clip = None
        final_clip = None
        output_video = video_file

        if not language:
            language = TextProcessor.detect_language(prompt_text)

        if language == 'ja' and not font.startswith("fonts/JA/"):
            font = "fonts/JA/Noto_Sans_JP/static/NotoSansJP-Black.ttf"
        elif language == 'ko' and not font.startswith("fonts/KO/"):
            font = "fonts/KO/Noto_Sans_KR/static/NotoSansKR-Black.ttf"
        ass_path = ""
        font_dir = ""

        try:
            video_file, fps = VideoProcessor.convert_video_fps(video_file, fps)
            video_clip = VideoFileClip(video_file)
            video_width = video_clip.w  # 获取视频宽度
            video_height = video_clip.h  # 获取视频高度
            max_line_len = TextProcessor.calc_max_line_len(video_width, font_size, language)  # 每行最大字符数
            min_line_len = 12 if language == 'en' else 4
            # 如果没有提供字幕文件，使用 MFA 对齐生成
            if not subtitle_file and prompt_text:
                mfa_align_processor = MfaAlignProcessor()
                subtitle_file, json_file = mfa_align_processor.align_audio_with_text(
                    audio_path=audio_file,
                    text=prompt_text,
                    min_line_len=min_line_len,
                    max_line_len=max_line_len,
                    language=language
                )
                # MFA失败，则使用ASR
                if not subtitle_file:
                    asr_processor = AsrProcessor()
                    subtitle_file, json_file = asr_processor.asr_to_srt(
                        audio_path=audio_file,
                        min_line_len=min_line_len,
                        max_line_len=max_line_len,
                    )

            if isass:
                ass_processor = AssProcessor()
                ass_path, font_dir = ass_processor.create_subtitle_ass(
                    subtitle_file=subtitle_file,
                    video_width=video_width,
                    video_height=video_height,
                    font_path=font,
                    font_size=font_size,
                    font_color=font_color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    bottom=bottom,
                    opacity=opacity,
                    max_line_len=max_line_len
                )

                output_video = ass_processor.subtitle_with_ffmpeg(
                    video_path=video_file,
                    ass_path=ass_path,
                    font_dir=font_dir  # 字体文件所在目录
                )
            else:
                # 创建字幕片段
                subtitle_clips = self.create_subtitle_clip(
                    subtitle_file=subtitle_file,
                    video_width=video_width,
                    font=font,
                    font_size=font_size,
                    font_color=font_color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    bottom=bottom,
                    opacity=opacity
                )
                # 合成视频
                final_clip = CompositeVideoClip([video_clip] + subtitle_clips).set_duration(video_clip.duration)
                audio_clip = AudioFileClip(audio_file)
                # 获取视频和音频的持续时间
                video_duration = final_clip.duration
                audio_duration = audio_clip.duration
                logging.info(f"检查音频与视频长度：video_duration {video_duration} audio_duration {audio_duration}")

                if audio_duration < video_duration:
                    logging.info(f"视频更短，裁剪视频...")
                    final_clip = final_clip.subclip(0, audio_duration)
                elif audio_duration > video_duration:
                    logging.info(f"音频更短，裁剪音频...")
                    audio_clip = audio_clip.subclip(0, video_duration)
                # 添加音频淡出效果，防止尾音
                audio_clip = audio_clip.fx(afx.audio_fadeout, duration=0.2)
                # 将处理后的音频设置到最终视频中
                final_clip = final_clip.without_audio().set_audio(audio_clip)

                logging.info(f"Video Duration: {video_clip.duration}, Final Clip Duration: {final_clip.duration}")
                # 输出文件路径
                video_dir = Path(video_file).parent
                os.makedirs(video_dir, exist_ok=True)
                output_video = os.path.join(video_dir, f"{Path(video_file).stem}_output{Path(video_file).suffix}")
                # 提取关键颜色信息
                pix_fmt, color_range, color_space, color_transfer, color_primaries = VideoProcessor.get_video_colorinfo(
                    video_file)
                # 保存视频
                # NVIDIA 编码器 codec="h264_nvenc"    CPU编码 codec="libx264"
                final_clip.write_videofile(
                    output_video,
                    codec="libx264",
                    fps=final_clip.fps,
                    audio_codec="aac",
                    audio_bitrate="192k",
                    preset="slow",
                    ffmpeg_params=[
                        "-crf", "18",
                        "-pix_fmt", pix_fmt,  # 设置像素格式
                        "-color_range", color_range,  # 设置色彩范围
                        "-colorspace", color_space,  # 设置色彩空间
                        "-color_trc", color_transfer,  # 设置色彩传递特性
                        "-color_primaries", color_primaries,  # 设置色彩基准
                    ]
                )
        except Exception as e:
            TextProcessor.log_error(e)
        finally:
            # 确保资源被释放
            if final_clip:
                final_clip.close()
            if video_clip:
                video_clip.close()

        return output_video, subtitle_file, ass_path, font_dir

    @staticmethod
    def get_media_metadata(media_path):
        """
        使用 ffprobe 提取媒体文件的元数据，并以 JSON 格式返回。
        """
        cmd = [
            "ffprobe",
            "-i", media_path,
            "-show_streams",
            "-show_format",
            "-print_format", "json",
            "-hide_banner",
            "-loglevel", "error"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

        try:
            metadata = json.loads(result.stdout)
        except json.JSONDecodeError:
            metadata = {}

        return metadata

    @staticmethod
    def get_video_metadata(media_path):
        """获取视频文件的元数据信息"""
        metadata = VideoProcessor.get_media_metadata(media_path)
        # 查找第一个视频流
        video_stream = next((stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "video"),
                            None)
        if not video_stream:
            raise ValueError("未找到视频流")

        return video_stream

    @staticmethod
    def get_video_frame_rate(media_path):
        """获取视频文件的帧率"""
        video_metadata = VideoProcessor.get_video_metadata(media_path)
        # 获取 r_frame_rate
        r_frame_rate = video_metadata.get("r_frame_rate", "0/1")
        # 计算帧率
        num, denom = map(int, r_frame_rate.split('/'))
        frame_rate = num / denom if denom != 0 else 0

        return frame_rate

    @staticmethod
    def get_video_colorinfo(media_path):
        """获取视频文件的颜色信息"""
        # 获取原视频元数据
        video_metadata = VideoProcessor.get_video_metadata(media_path)
        # 提取关键颜色信息
        pix_fmt = video_metadata.get("pix_fmt", "yuv420p")
        color_range = video_metadata.get("color_range", "1")
        color_space = video_metadata.get("color_space", "1")
        color_transfer = video_metadata.get("color_transfer", "1")
        color_primaries = video_metadata.get("color_primaries", "1")

        if color_space.lower() == "reserved":
            color_space = "bt709"
            logging.warning(f"检测到 color_space 为 'reserved'，已替换为默认值 'bt709'")

        if color_primaries.lower() == "reserved":
            color_primaries = "bt709"
            logging.warning(f"检测到 color_primaries 为 'reserved'，已替换为默认值 'bt709'")

        return pix_fmt, color_range, color_space, color_transfer, color_primaries

    @staticmethod
    def extract_audio(video_path, audio_format="wav"):
        """
        从视频文件中提取音频，并保存为指定格式的音频文件。

        :param video_path: 输入视频文件路径
        :param audio_format: 输出音频格式（支持 'mp3', 'wav', 'aac', 'flac' 等）
        :return: 提取的音频文件路径
        """

        base_name = os.path.splitext(video_path)[0]  # 去掉扩展名
        output_audio_path = f"{base_name}.{audio_format}"

        # 设置不同格式的 ffmpeg 参数
        if audio_format == "mp3":
            codec = ["-q:a", "0"]  # 最高质量
        elif audio_format == "wav":
            codec = ["-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2"]  # WAV 格式参数
        elif audio_format == "aac":
            codec = ["-c:a", "aac"]
        elif audio_format == "flac":
            codec = ["-c:a", "flac"]
        else:
            raise ValueError(f"不支持的音频格式: {audio_format}")

        # 运行 ffmpeg 提取音频
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,  # 输入视频
            "-vn",  # 去除视频流
            *codec,  # 音频编码参数
            output_audio_path  # 输出音频文件
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)

        logging.info(f"音频已提取: {output_audio_path}")

        return output_audio_path
