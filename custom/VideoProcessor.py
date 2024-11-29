import os
from pathlib import Path
from fastapi import UploadFile
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
from custom.file_utils import logging
from custom.MfaAlignProcessor import MfaAlignProcessor

class VideoProcessor:
    def __init__(self,
                 temp_dir="results/"):
        """
        初始化视频频处理器。
        """
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)

    async def save_upload_to_video(
            self, 
            upload_file: UploadFile
        ):
        # 构造文件路径
        video_name = Path(upload_file.filename).stem # 获取视频文件名（不带扩展名）
        video_dir = os.path.join(self.temp_dir, video_name)
        os.makedirs(video_dir, exist_ok=True)
        upload_path = os.path.join(video_dir, upload_file.filename)
        # 删除同名已存在的文件
        if os.path.exists(upload_path):
            os.remove(upload_path)

        logging.info(f"接收上传{upload_file.filename}请求 {upload_path}")

        try:
            # 保存上传的音频文件
            with open(upload_path, "wb") as f:
                f.write(await upload_file.read())

            return upload_path
        except Exception as e:
            raise Exception(f"{upload_file.filename}视频文件保存失败: {str(e)}")

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
    ) -> list:
        """
        从字幕文件创建字幕片段。
        :param subtitle_file: SRT 文件路径
        :param video_width: 视频宽度，用于调整字幕宽度
        :param font: 字体文件路径
        :param font_size: 字体大小
        :param font_color: 字体颜色
        :param stroke_color: 描边颜色
        :param stroke_width: 描边宽度
        :return: 字幕片段列表
        """
        if not os.path.exists(subtitle_file):
            raise FileNotFoundError(f"字幕文件不存在: {subtitle_file}")
        
        subtitles = []
        try:
            with open(subtitle_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                it = iter(lines)
                for line in it:
                    if '-->' in line:
                        start, end = line.split(' --> ')
                        text = ''
                        # 使用迭代器读取直到下一个包含'-->'的行
                        for next_line in it:
                            if next_line.strip()=='':
                                break
                            if next_line.strip():  # 如果行不是空的或只包含空格
                                text += next_line.strip() + ' '  # 添加空格分隔单词
                        subtitles.append((start, end.strip(), text.strip()))  # 去除末尾的空格
        except Exception as e:
            raise RuntimeError(f"读取字幕文件失败: {subtitle_file}") from e

        # 创建字幕clips
        subtitle_clips = []
        for start, end, text in subtitles:
            try:
                # 解析时间戳为秒数
                start_seconds = self.parse_srt_timestamp(start)
                end_seconds = self.parse_srt_timestamp(end)

                text_clip = TextClip(text, fontsize=font_size, color=font_color, align='center', method='caption',stroke_color=stroke_color,stroke_width=stroke_width,font=font,size=(video_width,None))
                text_clip = text_clip.set_start(start)
                text_clip = text_clip.set_duration(end_seconds - start_seconds)
                text_clip = text_clip.set_position(('center', 'bottom')).margin(bottom=10, opacity=0)

                subtitle_clips.append(text_clip)
            except Exception as e:
                raise RuntimeError(f"创建字幕失败: {text} ({start} - {end})") from e

        return subtitle_clips
        
    def video_subtitle(
            self,
            video_file: str,
            audio_file: str,
            prompt_text: str,
            add_audio: bool = False,
            subtitle_file: str = None,
            font: str = "fonts/yahei.ttf",
            font_size: int = 70,
            font_color: str = "yellow",
            stroke_color: str = "yellow",
            stroke_width: int = 0,
        ):
            """
            给视频添加字幕并输出。
            :param video_file: 视频文件路径
            :param audio_file: 替换的音频文件路径
            :param prompt_text: 音频文本
            :param subtitle_file: SRT 字幕文件路径
            :param output_file: 输出视频文件路径
            :param font: 字体文件路径
            :param font_size: 字体大小
            :param font_color: 字体颜色
            :param stroke_color: 描边颜色
            :param stroke_width: 描边宽度
            """
            if not os.path.exists(video_file):
                raise FileNotFoundError(f"视频文件不存在: {video_file}")
            if audio_file and not os.path.exists(audio_file):
                raise FileNotFoundError(f"音频文件不存在: {audio_file}")
            # 加载视频
            video_clip = VideoFileClip(video_file)
            video_width = video_clip.w
            # 添加音频（可选）
            if add_audio:
                video_clip = video_clip.without_audio()
                audio_clip = AudioFileClip(audio_file)
                video_clip = video_clip.set_audio(audio_clip)

            if not subtitle_file:
                mfa_align_processor = MfaAlignProcessor()
                # 每行最大长度
                maxsize = video_width / font_size - 2
                # 调用对齐函数
                subtitle_file = mfa_align_processor.align_audio_with_text(
                            audio_path = audio_file,
                            text = prompt_text,
                            min_line_length = 0,
                            max_line_length = maxsize
                        )
            # 创建字幕片段
            subtitle_clips = self.create_subtitle_clip(
                                subtitle_file = subtitle_file, 
                                video_width = video_width, 
                                font = font,
                                font_size = font_size,
                                font_color = font_color,
                                stroke_color = stroke_color,
                                stroke_width = stroke_width,
                            )
            # 合成视频
            final_clip = CompositeVideoClip([video_clip] + subtitle_clips)
            # 输出视频
            video_dir =Path(video_file).parent
            os.makedirs(video_dir, exist_ok=True)
            output_video = os.path.join(video_dir, f"output_{Path(video_file).name}")

            final_clip.write_videofile(output_video, codec="libx264", audio_codec="aac", fps=video_clip.fps)

            return output_video

