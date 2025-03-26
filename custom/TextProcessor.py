import datetime
import json
import os
import re
import traceback

import fasttext
from PIL import ImageFont
from fontTools.ttLib import TTFont
from zhconv import convert

from custom.file_utils import logging


class TextProcessor:
    """
    文本处理工具类，提供多种文本相关功能。
    """

    @staticmethod
    def clear_text(text):
        text = text.replace("\n", "")
        if TextProcessor.contains_chinese(text):
            text = convert(text, 'zh-cn')
            text = TextProcessor.replace_blank(text)
            text = TextProcessor.replace_corner_mark(text)
            text = text.replace("—", "，")
        else:
            text = text.replace("-", " ")
        return text

    # whether contain chinese character
    @staticmethod
    def contains_chinese(text):
        chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]+')
        return bool(chinese_char_pattern.search(text))

    # noinspection PyTypeChecker
    # remove blank between chinese character
    @staticmethod
    def replace_blank(text: str):
        out_str = []
        for i, c in enumerate(text):
            if c == " ":
                if ((text[i + 1].isascii() and text[i + 1] != " ") and
                        (text[i - 1].isascii() and text[i - 1] != " ")):
                    out_str.append(c)
            else:
                out_str.append(c)
        return "".join(out_str)

    # replace special symbol
    @staticmethod
    def replace_corner_mark(text):
        text = text.replace('²', '平方')
        text = text.replace('³', '立方')
        return text

    @staticmethod
    def detect_language(text):
        """
        检测输入文本的语言。
        :param text: 输入文本
        :return: 返回检测到的语言代码（如 'en', 'zh', 'ja', 'ko'）
        """

        # 加载预训练的语言检测模型
        fasttext_model = fasttext.load_model("./fasttext/lid.176.bin")

        try:
            lang = None
            text = text.strip()
            if text:
                predictions = fasttext_model.predict(text, k=1)  # 获取 top-1 语言预测
                lang = predictions[0][0].replace("__label__", "")  # 解析语言代码
                confidence = predictions[1][0]  # 置信度
                lang = lang if confidence > 0.6 else None

            logging.info(f'Detected language: {lang}')
            return lang
        except Exception as e:
            logging.error(f"Language detection failed: {e}")
            return None

    @staticmethod
    def ensure_sentence_ends_with_period(text):
        """
        确保输入文本以适当的句号结尾。
        :param text: 输入文本
        :return: 修改后的文本
        """
        if not text.strip():
            return text  # 空文本直接返回
        # 判断是否已经以句号结尾
        if text[-1] in ['.', '。', '！', '!', '？', '?']:
            return text
        # 根据文本内容添加适当的句号
        lang = TextProcessor.detect_language(text)
        if lang == 'zh' or lang == 'zh-cn':  # 中文文本
            return text + '。'
        else:  # 英文或其他
            return text + '.'

    @staticmethod
    def log_error(exception: Exception, log_dir='error'):
        """
        记录错误信息到指定目录，并按日期小时命名文件。

        :param exception: 捕获的异常对象
        :param log_dir: 错误日志存储的目录，默认为 'error'
        """
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        # 获取当前日期和小时，作为日志文件名的一部分
        timestamp_hour = datetime.datetime.now().strftime('%Y-%m-%d_%H')  # 到小时
        # 获取当前时间戳，格式化为 YYYY-MM-DD_HH-MM-SS
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # 创建日志文件路径
        log_file_path = os.path.join(log_dir, f'error_{timestamp_hour}.log')
        # 使用 traceback 模块获取详细的错误信息
        error_traceback = traceback.format_exc()
        # 写入错误信息到文件，使用追加模式 'a'
        with open(log_file_path, 'a') as log_file:
            log_file.write(f"错误发生时间: {timestamp}\n")
            log_file.write(f"错误信息: {str(exception)}\n")
            log_file.write("堆栈信息:\n")
            log_file.write(error_traceback + '\n')

        logging.info(f"发生错误: {str(exception)}\n错误信息已保存至: {log_file_path}")

    @staticmethod
    def get_keywords(config_file='.\custom\keywords.json'):
        with open(config_file, 'r', encoding='utf-8') as file:
            words_list = json.load(file)
        return words_list

    @staticmethod
    def get_font_name(font_path: str) -> str:
        """从字体文件中提取字体名称（改进版）"""
        try:
            font = TTFont(font_path)
            # 优先获取 Windows 平台的英文名称
            for entry in font["name"].names:
                if entry.platformID == 3 and entry.nameID in [1, 4]:  # Win Unicode 平台
                    return entry.toUnicode()
            # 次选 Mac 平台名称
            for entry in font["name"].names:
                if entry.platformID == 1 and entry.nameID in [1, 4]:  # Mac 平台
                    return entry.toUnicode()
            return os.path.splitext(os.path.basename(font_path))[0]
        except Exception as e:
            TextProcessor.log_error(e)
            logging.error(f"路径：{font_path}，提取字体名称异常，使用默认字体 Arial")
            return "Arial"  # 回退默认字体

    @staticmethod
    def get_font_size(font_path, font_size, token):
        """
        获取精确字体参数。

        :param font_path: 字体路径
        :param font_size: 字体大小
        :param token: 文本
        """

        try:
            font = ImageFont.truetype(font_path, font_size)  # 加载字体
            token_width = font.getlength(token)

            ascent, descent = font.getmetrics()  # 获取字体基线上下高度
            line_height = ascent + descent  # 计算理论行高
        except Exception as e:
            TextProcessor.log_error(e)
            logging.error(f"路径：{font_path}，大小：{font_size}，获取精确字体参数异常，使用估算")
            avg_char_width = font_size * 0.6  # 根据经验调整
            token_width = len(token) * avg_char_width
            line_height = font_size * 1.2  # 或其他经验值

        return token_width, line_height

    @staticmethod
    def calc_max_line_len(video_width, font_size, language):
        """
        估算每行最大字符数
        :param video_width: 视频宽度（像素）
        :param font_size: 字体大小（像素）
        :param language: 语言类型
        :return: 每行最大字符数
        """
        if language == 'en':
            # 英文字符：宽度为 font_size * 0.5
            max_line_len = int(video_width * 0.9 // (font_size * 0.5))
        else:
            # 中文字符：等宽，宽度为 font_size
            max_line_len = int(video_width * 0.9 // font_size)

        logging.info(f"max_line_len: {max_line_len}")
        return max_line_len
