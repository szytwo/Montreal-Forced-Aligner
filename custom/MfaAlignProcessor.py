import os
import subprocess
import re
from textgrid import TextGrid
from datetime import timedelta
from pathlib import Path
from custom.file_utils import logging, get_full_path
from custom.TextProcessor import TextProcessor

class MfaAlignProcessor:
    def __init__(self, 
                 model_dir="MFA/pretrained_models"
        ):
        """
        初始化MFA音频与文本对齐处理器。
        :param model_dir: 模型文件目录
        """
        self.model_dir = model_dir

    def align_audio_with_text(self, audio_path, text, min_line_length=0, max_line_length=40):
        """
        使用 MFA 进行音频与文本对齐
        :param audio_path: 包含音频文件的路径
        :param text: 文本
        """
        language = TextProcessor.detect_language(text)
        # 根据语言选择模型和字典路径
        if language == 'zh-cn':
            dictionary_name = 'mandarin_china_mfa.dict'
            acoustic_name = 'mandarin_mfa.zip'
        elif language == 'en':
            dictionary_name = 'english_uk_mfa.dict'
            acoustic_name = 'english_mfa.zip'
        else:
            raise ValueError(f"Unsupported language: {language}")
        
        model_dir = get_full_path(self.model_dir)
        dictionary_path = os.path.join(model_dir, 'dictionary', dictionary_name)
        model_path = os.path.join(model_dir, 'acoustic', acoustic_name)
        # 构建保存路径
        audio_path = get_full_path(audio_path)
        audio_dir = Path(audio_path).parent
        audio_name = Path(audio_path).stem # 获取音频文件名（不带扩展名）
        # 将文本写入到输入子目录
        text_path = os.path.join(audio_dir, f"{audio_name}.txt")
        with open(text_path, 'w', encoding='utf-8') as text_file:
            text_file.write(text)
        logging.info(f"audio_dir: {audio_dir}")
        # 获取 CPU 核心数
        num_jobs = os.cpu_count()
        logging.info(f"num_jobs: {num_jobs}")
        # 构造 MFA 命令，注意：在命令行参数解析时，每个选项与值应作为单独的列表项，否则不起作用
        command = [
            "mfa", "align",
            audio_dir,  # 音频文件目录
            dictionary_path,  # 字典文件路径
            model_path,  # 声学模型路径
            audio_dir,   # 输出结果目录
            f"--temporary_directory", audio_dir,  #临时目录
            "--clean", # 清理运行前的旧文件
            "--final_clean", # 清理运行后的临时文件
            "--overwrite", # 覆盖旧输出
            f"--num_jobs", str(num_jobs) # 使用 CPU 核心数
        ]

        try:
            # 调用 MFA
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            # 打印 MFA 的输出日志
            logging.info("Alignment completed successfully!")
            logging.info(f"Output Directory: {audio_dir}")
            logging.info(f"MFA Output:\n {result.stdout}")
            # 查找生成的 TextGrid 文件
            textgrid_file = os.path.join(audio_dir, f"{audio_name}.TextGrid")
            srt_file = os.path.join(audio_dir, f"{audio_name}.srt")
            # 将 TextGrid 文件转换为 SRT 文件
            self.textgrid_to_srt(textgrid_file, srt_file, min_line_length, max_line_length)

            return srt_file
        except subprocess.CalledProcessError as e:
            # 捕获并抛出任何在处理过程中发生的异常
            raise Exception(f"Error during alignment: {e.stderr}")

    # 格式化时间为 hh:mm:ss,SSS
    def format_time(self, seconds):
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        milliseconds = int((td.total_seconds() - total_seconds) * 1000)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    def is_english(self, word):
        """
        判断给定的单词是否为英文单词
        :param word: 输入的单词
        :return: 如果是英文返回 True，否则返回 False
        """
        # 判断是否包含英文字符 (使用正则表达式检查是否有英文字符)
        return bool(re.match(r'[A-Za-z0-9]+$', word))
    
    def remove_punctuation(text):
        """
        移除常用的中英文标点符号
        """
        punctuation_pattern = r'[，。！？；：、“”‘’（）《》【】,.!?;:"\'()<>[\]{}]'
        return re.sub(punctuation_pattern, '', text)

    def textgrid_to_srt(self, textgrid_path, output_srt_path, min_line_length=0, max_line_length=40):
        """
        将 TextGrid 文件转换为 SRT 字幕文件

        :param textgrid_path: 输入的 TextGrid 文件路径
        :param output_srt_path: 输出的 SRT 文件路径
        :param min_gap: 如果两个标注的时间间隔大于这个值，则开始新的字幕条目
        """
        tg = TextGrid.fromFile(textgrid_path)
        tier = tg[0]  # 假设对齐文本在第一个层级

        subtitles = []
        subtitle_id = 1
        current_subtitle = []
        current_length = 0  # 当前字幕的总字符长度
        start_time = None
        end_time = None

        for interval in tier.intervals:
            word = interval.mark.strip()
            word = self.remove_punctuation(word)  # 移除标点符号
            if start_time is None:
                start_time = interval.minTime
            end_time = interval.maxTime
            
            if word:
                # 判断是中文还是英文并处理
                if self.is_english(word) and current_length > 0:
                    word = ' ' + word  # 英文单词前加空格
                # 增加当前单词到字幕行
                current_subtitle.append(word)
                current_length += len(word)
            # 如果无文字或长度超出限制，则分行
            if (not word and current_length >=min_line_length) or current_length >= max_line_length:
                if current_subtitle:  # 确保当前字幕行非空
                    subtitle_text = ''.join(current_subtitle)
                    subtitles.append((subtitle_id, start_time, end_time, subtitle_text))
                    subtitle_id += 1
                    current_subtitle = []  # 重置当前字幕行
                    current_length = 0
                    start_time = None
        # 处理最后一个字幕条目
        if current_subtitle:
            subtitle_text = ''.join(current_subtitle)
            subtitles.append((subtitle_id, start_time, end_time, subtitle_text))
        # 写入 SRT 文件
        with open(output_srt_path, 'w', encoding='utf-8') as f:
            for subtitle in subtitles:
                subtitle_id, start_time, end_time, text = subtitle
                # 使用格式化函数
                start_time_str = self.format_time(start_time)
                end_time_str = self.format_time(end_time)
                f.write(f"{subtitle_id}\n")
                f.write(f"{start_time_str} --> {end_time_str}\n")
                f.write(f"{text}\n\n")

        logging.info(f"SRT file saved to {output_srt_path}")