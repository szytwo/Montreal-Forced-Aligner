import re
from datetime import timedelta

from textgrid import TextGrid
from zhconv import convert

from custom.TextProcessor import TextProcessor
from custom.file_utils import logging


class SrtProcessor:
    @staticmethod
    def format_time(seconds):
        # 格式化时间为 hh:mm:ss,SSS
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        milliseconds = int((td.total_seconds() - total_seconds) * 1000)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    @staticmethod
    def is_english(word):
        """
        判断给定的单词是否为英文单词
        :param word: 输入的单词
        :return: 如果是英文返回 True，否则返回 False
        """
        # 判断是否包含英文字符 (使用正则表达式检查是否有英文字符)
        return bool(re.match(r'[A-Za-z0-9]+$', word))

    @staticmethod
    def remove_punctuation(text):
        """
        移除常用的中英文标点符号
        """
        punctuation_pattern = r'[，。！？；：、“”‘’（）《》【】,.!?;:"\'()<>[\]{}▁]'
        return re.sub(punctuation_pattern, '', text)

    @staticmethod
    def textgrid_to_srt(textgrid_path, output_srt_path, min_line_length=0, max_line_length=40, language='auto'):
        """
        将 TextGrid 文件转换为 SRT 字幕文件

        :param textgrid_path: 输入的 TextGrid 文件路径
        :param output_srt_path: 输出的 SRT 文件路径
        :param min_line_length: 行最小长度
        :param max_line_length: 行最大长度
        :param language: 语言代码
        """
        keywords = TextProcessor.get_keywords()
        exceptions = keywords["exceptions"]  # 获取例外单词列表
        tg = TextGrid.fromFile(textgrid_path)
        tier = tg[0]  # 假设对齐文本在第一个层级

        subtitles = []
        subtitle_id = 1
        current_subtitle = []
        current_length = 0  # 当前字幕的总字符长度
        start_time = None
        end_time = None

        is_single_letter = False  # 单字母

        for interval in tier.intervals:
            word = interval.mark.strip()
            word = SrtProcessor.remove_punctuation(word)  # 移除标点符号
            if start_time is None:
                start_time = interval.minTime
            end_time = interval.maxTime

            if is_single_letter:  # 如果上一个是单字母，这次不分行
                allow_line = False
            else:
                allow_line = True  # 允许分行

            if word:
                is_en = SrtProcessor.is_english(word)

                is_single_letter = is_en and len(word) == 1

                if is_single_letter:  # 如果是单字母，不分行
                    allow_line = False
                # 判断是中文还是英文并处理
                if is_en and len(word) >= 2 and current_length > 0:
                    if (language == 'zh' or language == 'zh-cn') and word.lower() in exceptions:  # 判断单词是否在例外列表中
                        word = word
                    else:
                        word = ' ' + word  # 英文单词前加空格
                # 增加当前单词到字幕行
                current_subtitle.append(word)
                current_length += len(word)
            # 如果无文字或长度超出限制，则分行
            if (allow_line
                    and ((not word
                          and interval.maxTime - interval.minTime > 0.15
                          and current_length >= min_line_length
                         )
                         or current_length >= max_line_length
                    )
            ):
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
                if language == 'zh' or language == 'zh-cn':
                    # 转换为简体中文
                    text = convert(text, 'zh-cn')
                # 使用格式化函数
                start_time_str = SrtProcessor.format_time(start_time)
                end_time_str = SrtProcessor.format_time(end_time)
                f.write(f"{subtitle_id}\n")
                f.write(f"{start_time_str} --> {end_time_str}\n")
                f.write(f"{text}\n\n")

        logging.info(f"SRT file saved to {output_srt_path}")
