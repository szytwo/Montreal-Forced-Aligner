import os
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip

class VideoProcessor:
    def __init__(self, input_dir="results/input", output_dir="results/output"):
        """
        初始化视频频处理器。
        :param input_dir: 输入文件目录
        :param output_dir: 输出文件目录
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

    # 辅助函数：解析 SRT 时间戳为秒数
    def parse_srt_timestamp(timestamp):
        """将 SRT 时间戳（如 00:01:02,500）转换为秒数"""
        h, m, s = timestamp.split(":")
        s, ms = s.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    # 读取字幕文件并创建字幕clip
    def create_subtitle_clip(self, 
                            subtitle_file,
                            video_width:int,
                            font:str='fonts/yahei.ttf', 
                            font_size:int=70,
                            font_color:str='yellow',
                            stroke_color:str='yellow', 
                            stroke_width:int=0
        ):
        subtitles = []
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

        # 创建字幕clips
        subtitle_clips = []
        for start, end, text in subtitles:
            # 解析时间戳为秒数
            start_seconds = self.parse_srt_timestamp(start)
            end_seconds = self.parse_srt_timestamp(end)

            text_clip = TextClip(text, fontsize=font_size, color=font_color, align='center', method='caption',stroke_color=stroke_color,stroke_width=stroke_width,font=font,size=(video_width,None))
            text_clip = text_clip.set_start(start)
            text_clip = text_clip.set_duration(end_seconds - start_seconds)
            text_clip = text_clip.set_position(('center', 'bottom')).margin(bottom=10, opacity=0)

            subtitle_clips.append(text_clip)

        return subtitle_clips
