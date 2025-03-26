import json
import re
from datetime import timedelta

from textgrid import TextGrid
from zhconv import convert

from custom.TextProcessor import TextProcessor
from custom.file_utils import logging

# 定义哪些标点作为换行符号
end_punctuations = ['，', '。', '！', '？', '；', ',', '.', '!', '?', ';']


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
    def remove_punctuation(text, rel_end=True):
        """
        移除常用的中英文标点符号
        :param text: 需要处理的文本
        :param rel_end: 是否移除句尾标点
        :return: 处理后的文本
        """
        punctuation_pattern = r'：、“”‘’（）《》【】:"\'()<>[\]{}▁'
        end_punctuation = ''.join(end_punctuations) if rel_end else ''
        punctuation_pattern = f"[{punctuation_pattern}{re.escape(end_punctuation)}]"

        return re.sub(punctuation_pattern, '', text)

    # noinspection PyTypeChecker
    @staticmethod
    def textgrid_to_srt_for_punctuation(
            text,
            textgrid_path,
            output_srt_path,
            output_json_path,
            language='auto'
    ):
        """
        将 TextGrid 文件转换为 SRT 字幕文件，按标点符号分行

        :param text: 原始文本
        :param textgrid_path: 输入的 TextGrid 文件路径
        :param output_srt_path: 输出的 SRT 文件路径
        :param output_json_path: 输出的 JSON 文件路径
        :param language: 语言代码
        """
        text = SrtProcessor.remove_punctuation(text, False)
        print(text)
        keywords = TextProcessor.get_keywords()
        exceptions = keywords["exceptions"]  # 获取例外单词列表
        tg = TextGrid.fromFile(textgrid_path)
        tier = tg[0]  # 假设对齐文本在第一个层级
        subtitles = []
        subtitle_id = 1
        current_subtitle = []  # 用于拼接字幕文本
        current_word_list = []  # 用于记录该字幕内所有单词及其时间，格式：(word, minTime, maxTime)
        current_length = 0  # 当前字幕的总字符长度
        start_time = None
        end_time = None
        # 为了根据原始文本的标点判断分行，维护一个指针记录在原始文本中的位置
        orig_idx = 0
        text_len = len(text)

        for index, interval in enumerate(tier.intervals):
            word = interval.mark.strip()
            word = SrtProcessor.remove_punctuation(word)  # 移除标点符号
            if start_time is None:
                start_time = interval.minTime
            end_time = interval.maxTime
            punctuation_break = False

            if word:
                is_en = SrtProcessor.is_english(word)
                if not is_en and (language == 'zh' or language == 'zh-cn'):
                    # 转换为简体中文
                    word = convert(word, 'zh-cn')
                # 记录当前单词及其时间
                current_word_list.append((word, interval.minTime, interval.maxTime))
                # 判断是中文还是英文并处理
                if is_en and len(word) >= 2 and current_length > 0:
                    # 判断单词是否在例外列表中
                    if (language == 'zh' or language == 'zh-cn') and word.lower() in exceptions:
                        word = word
                    else:
                        word = ' ' + word  # 英文单词前加空格
                # 增加当前单词到字幕行
                current_subtitle.append(word)
                current_length += len(word)
                # 使用原始文本中的标点信息判断是否需要换行：
                # 1. 将当前字幕拼接起来
                subtitle_text = ''.join(current_subtitle)
                # 2. 尝试在原始文本中找到匹配部分（假设顺序一致）
                #    忽略前导空格可能造成的问题
                search_text = subtitle_text.strip()
                if search_text:
                    print(search_text)
                    print(orig_idx)
                    pos = text.find(search_text, orig_idx)
                    print(pos)
                    if pos != -1:
                        # 将原指针移动到匹配结束的位置
                        end_pos = pos + len(search_text)
                        # 如果未到文本结尾，且下一个字符为标点，则认为此处应该分行
                        if end_pos < text_len and text[end_pos] in end_punctuations:
                            punctuation_break = True
                            orig_idx = end_pos  # 更新 orig_idx 为当前匹配结束

            # 如果无文字或长度超出限制，则分行
            if punctuation_break:
                if current_subtitle:  # 确保当前字幕行非空
                    subtitle_text = ''.join(current_subtitle)
                    subtitles.append((subtitle_id, start_time, end_time, subtitle_text, current_word_list))
                    subtitle_id += 1
                    # 重置当前字幕数据
                    current_subtitle = []
                    current_word_list = []
                    current_length = 0
                    start_time = None
        # 处理最后一个字幕条目
        if current_subtitle:
            subtitle_text = ''.join(current_subtitle)
            subtitles.append((subtitle_id, start_time, end_time, subtitle_text, current_word_list))
        # 写入 SRT 文件
        with open(output_srt_path, 'w', encoding='utf-8') as f:
            for subtitle in subtitles:
                subtitle_id, start_time, end_time, text, _ = subtitle
                # 使用格式化函数
                start_time_str = SrtProcessor.format_time(start_time)
                end_time_str = SrtProcessor.format_time(end_time)
                f.write(f"{subtitle_id}\n")
                f.write(f"{start_time_str} --> {end_time_str}\n")
                f.write(f"{text}\n\n")

        logging.info(f"SRT file saved: {output_srt_path}")
        # 生成 JSON 数据，每个字幕条目包含 id, 时间（字符串格式）、字幕文本及 word 列
        json_data = []
        for subtitle in subtitles:
            subtitle_id, start_time, end_time, text, word_list = subtitle
            json_data.append({
                "subtitle_id": subtitle_id,
                "start_time": SrtProcessor.format_time(start_time),
                "end_time": SrtProcessor.format_time(end_time),
                "text": text,
                "word_list": [
                    {
                        "word": word,
                        "start_time": SrtProcessor.format_time(word_start),
                        "end_time": SrtProcessor.format_time(word_end)
                    }
                    for word, word_start, word_end in word_list
                ]
            })
        # 写入 JSON 文件
        with open(output_json_path, 'w', encoding='utf-8') as jf:
            json.dump(json_data, jf, ensure_ascii=False, indent=4)
        logging.info(f"JSON file saved: {output_json_path}")

    # noinspection PyTypeChecker
    @staticmethod
    def textgrid_to_srt_for_silence(
            textgrid_path,
            output_srt_path,
            output_json_path,
            min_line_len=0,
            max_line_len=40,
            language='auto'
    ):
        """
        将 TextGrid 文件转换为 SRT 字幕文件，按静音分行

        :param textgrid_path: 输入的 TextGrid 文件路径
        :param output_srt_path: 输出的 SRT 文件路径
        :param output_json_path: 输出的 JSON 文件路径
        :param min_line_len: 行最小长度
        :param max_line_len: 行最大长度
        :param language: 语言代码
        """
        keywords = TextProcessor.get_keywords()
        exceptions = keywords["exceptions"]  # 获取例外单词列表
        tg = TextGrid.fromFile(textgrid_path)
        tier = tg[0]  # 假设对齐文本在第一个层级
        # 预扫描所有间隔，找到最后一个有实际内容的间隔的索引
        content_indices = []
        for idx, interval in enumerate(tier.intervals):
            word = interval.mark.strip()
            word = SrtProcessor.remove_punctuation(word)  # 保持处理一致性
            if word:  # 记录所有有实际内容的间隔索引
                content_indices.append(idx)
        last_content_index = -1
        if content_indices and len(content_indices) >= 2:
            last_content_index = content_indices[-2]  # 取倒数第二个元素
        subtitles = []
        subtitle_id = 1
        current_subtitle = []  # 用于拼接字幕文本
        current_word_list = []  # 用于记录该字幕内所有单词及其时间，格式：(word, minTime, maxTime)
        current_length = 0  # 当前字幕的总字符长度
        start_time = None
        end_time = None
        is_single_letter = False  # 是否为单字母

        for index, interval in enumerate(tier.intervals):
            word = interval.mark.strip()
            word = SrtProcessor.remove_punctuation(word)  # 移除标点符号
            is_last_content = (index == last_content_index)  # 是否倒数第二个有效内容
            if start_time is None:
                start_time = interval.minTime
            end_time = interval.maxTime

            if is_single_letter:  # 如果上一个是单字母，这次不分行
                allow_line = False
            else:
                allow_line = True  # 允许分行

            if word:
                is_en = SrtProcessor.is_english(word)
                if not is_en and (language == 'zh' or language == 'zh-cn'):
                    # 转换为简体中文
                    word = convert(word, 'zh-cn')
                is_single_letter = is_en and len(word) == 1
                # 记录当前单词及其时间
                current_word_list.append((word, interval.minTime, interval.maxTime))
                # 如果是单字母，不分行
                if is_single_letter:
                    allow_line = False
                # 判断是中文还是英文并处理
                if is_en and len(word) >= 2 and current_length > 0:
                    # 判断单词是否在例外列表中
                    if (language == 'zh' or language == 'zh-cn') and word.lower() in exceptions:
                        word = word
                    else:
                        word = ' ' + word  # 英文单词前加空格
                # 增加当前单词到字幕行
                current_subtitle.append(word)
                current_length += len(word)
            # 如果无文字或长度超出限制，则分行
            if (allow_line
                    and not is_last_content
                    and ((not word
                          and interval.maxTime - interval.minTime > 0.15
                          and current_length >= min_line_len
                         )
                         or current_length >= max_line_len
                    )
            ):
                if current_subtitle:  # 确保当前字幕行非空
                    subtitle_text = ''.join(current_subtitle)
                    subtitles.append((subtitle_id, start_time, end_time, subtitle_text, current_word_list))
                    subtitle_id += 1
                    # 重置当前字幕数据
                    current_subtitle = []
                    current_word_list = []
                    current_length = 0
                    start_time = None
        # 处理最后一个字幕条目
        if current_subtitle:
            subtitle_text = ''.join(current_subtitle)
            subtitles.append((subtitle_id, start_time, end_time, subtitle_text, current_word_list))
        # 写入 SRT 文件
        with open(output_srt_path, 'w', encoding='utf-8') as f:
            for subtitle in subtitles:
                subtitle_id, start_time, end_time, text, _ = subtitle
                # 使用格式化函数
                start_time_str = SrtProcessor.format_time(start_time)
                end_time_str = SrtProcessor.format_time(end_time)
                f.write(f"{subtitle_id}\n")
                f.write(f"{start_time_str} --> {end_time_str}\n")
                f.write(f"{text}\n\n")

        logging.info(f"SRT file saved: {output_srt_path}")
        # 生成 JSON 数据，每个字幕条目包含 id, 时间（字符串格式）、字幕文本及 word 列
        json_data = []
        for subtitle in subtitles:
            subtitle_id, start_time, end_time, text, word_list = subtitle
            json_data.append({
                "subtitle_id": subtitle_id,
                "start_time": SrtProcessor.format_time(start_time),
                "end_time": SrtProcessor.format_time(end_time),
                "text": text,
                "word_list": [
                    {
                        "word": word,
                        "start_time": SrtProcessor.format_time(word_start),
                        "end_time": SrtProcessor.format_time(word_end)
                    }
                    for word, word_start, word_end in word_list
                ]
            })
        # 写入 JSON 文件
        with open(output_json_path, 'w', encoding='utf-8') as jf:
            json.dump(json_data, jf, ensure_ascii=False, indent=4)
        logging.info(f"JSON file saved: {output_json_path}")

    # noinspection PyTypeChecker
    @staticmethod
    def textgrid_to_json(textgrid_path, output_json_path, language='auto'):
        """
        将 TextGrid 文件转换为 json 字幕文件

        :param textgrid_path: 输入的 TextGrid 文件路径
        :param output_json_path: 输出的 json 文件路径
        :param language: 语言代码
        """
        tg = TextGrid.fromFile(textgrid_path)
        tier = tg[0]  # 假设对齐文本在第一个层级
        words = []
        word_id = 1
        for idx, interval in enumerate(tier.intervals):
            word = interval.mark.strip()
            word = SrtProcessor.remove_punctuation(word)
            if word:
                start_time = interval.minTime
                end_time = interval.maxTime
                if language == 'zh' or language == 'zh-cn':
                    # 转换为简体中文
                    word = convert(word, 'zh-cn')
                words.append({
                    "word_id": word_id,
                    "start_time": SrtProcessor.format_time(start_time),
                    "end_time": SrtProcessor.format_time(end_time),
                    "word": word
                })
                word_id += 1
        # 写入JSON文件
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, indent=2)

        logging.info(f"JSON file saved to {output_json_path}")
