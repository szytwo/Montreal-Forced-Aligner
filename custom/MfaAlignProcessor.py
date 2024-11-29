import os
import subprocess
from textgrid import TextGrid
from datetime import timedelta
from pathlib import Path
from custom.file_utils import logging
from custom.TextProcessor import TextProcessor

class MfaAlignProcessor:
    def __init__(self, 
                 input_dir="results/input", 
                 output_dir="results/output", 
                 model_dir="MFA/pretrained_models"
        ):
        """
        初始化MFA音频与文本对齐处理器。
        :param input_dir: 输入文件目录
        :param output_dir: 输出文件目录
        :param model_dir: 模型文件目录
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.model_dir = model_dir
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

    def align_audio_with_text(self, audio_path, text):
        """
        使用 MFA 进行音频与文本对齐
        :param audio_path: 包含音频文件的路径
        :param text: 文本
        """
        language = TextProcessor.detect_language(text)
        # 根据语言选择模型和字典路径
        if language == 'zh-cn':
            dictionary_path = os.path.join(self.model_dir, 'dictionary', 'mandarin_china_mfa.dict')
            model_path = os.path.join(self.model_dir, 'acoustic', 'mandarin_mfa.zip')
        elif language == 'en':
            dictionary_path = os.path.join(self.model_dir, 'dictionary', 'english_uk_mfa.dict')
            model_path = os.path.join(self.model_dir, 'acoustic', 'english_mfa.zip')
        else:
            raise ValueError(f"Unsupported language: {language}")
        # 获取音频文件名（不带扩展名）
        audio_name = Path(audio_path).stem
        # 创建输入和输出子目录
        input_subdir = os.path.join(self.input_dir, audio_name)
        output_subdir = os.path.join(self.output_dir, audio_name)
        os.makedirs(input_subdir, exist_ok=True)
        os.makedirs(output_subdir, exist_ok=True)
        # 将音频文件复制到输入子目录
        input_audio_path = os.path.join(input_subdir, Path(audio_path).name)
        if not os.path.exists(input_audio_path):
            os.system(f'copy "{audio_path}" "{input_audio_path}"') 
        # 将文本写入到输入子目录
        text_path = os.path.join(input_subdir, f"{audio_name}.txt")
        with open(text_path, 'w', encoding='utf-8') as text_file:
            text_file.write(text)
        # 构造 MFA 命令
        command = [
            "mfa", "align",
            input_subdir,  # 音频文件目录
            dictionary_path,  # 字典文件路径
            model_path,  # 声学模型路径
            output_subdir,   # 输出结果目录
            "--clean",
            "--final_clean",
            "--overwrite"
        ]

        try:
            # 调用 MFA
            result = subprocess.run(command, capture_output=True, text=True, check=True)

            # 打印 MFA 的输出日志
            logging.info("Alignment completed successfully!")
            logging.info("Output Directory:", self.output_dir)
            logging.info("MFA Output:\n", result.stdout)
            # 查找生成的 TextGrid 文件
            textgrid_file = os.path.join(output_subdir, f"{audio_name}.TextGrid")
            srt_file = os.path.join(output_subdir, f"{audio_name}.srt")
            # 将 TextGrid 文件转换为 SRT 文件
            self.textgrid_to_srt(textgrid_file, srt_file)

            return srt_file
        except subprocess.CalledProcessError as e:
            logging.error("Error during alignment:")
            logging.error(e.stderr)

    # 格式化时间为 hh:mm:ss,SSS
    def format_time(seconds):
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        milliseconds = int((td.total_seconds() - total_seconds) * 1000)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    def textgrid_to_srt(self, textgrid_path, output_srt_path, min_gap=2):
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
        start_time = None
        end_time = None

        for interval in tier.intervals:
            if interval.mark.strip():  # 仅处理非空标注
                word = interval.mark.strip()
                if start_time is None:
                    start_time = interval.minTime
                end_time = interval.maxTime
                current_subtitle.append(word)
                print(f"{interval.minTime} --> {interval.maxTime}")
                # 检查时间间隔是否超出 min_gap
                if end_time - start_time > min_gap:
                    subtitle_text = ''.join(current_subtitle)
                    subtitles.append((subtitle_id, start_time, end_time, subtitle_text))
                    subtitle_id += 1
                    current_subtitle = []
                    start_time = None
                    end_time = None

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
                #print(start_time_str)
                #print(end_time_str)
                f.write(f"{subtitle_id}\n")
                f.write(f"{start_time_str} --> {end_time_str}\n")
                f.write(f"{text}\n\n")

        logging.info(f"SRT file saved to {output_srt_path}")