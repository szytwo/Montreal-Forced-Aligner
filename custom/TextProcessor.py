import datetime
import json
import os
import traceback

import fasttext
from PIL import ImageFont
from fontTools.ttLib import TTFont

from custom.file_utils import logging


class TextProcessor:
    """
    文本处理工具类，提供多种文本相关功能。
    """

    @staticmethod
    def clear_text(text):
        text = text.replace("\n", "")
        text = TextProcessor.replace_corner_mark(text)
        return text

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
        if lang == 'zh-cn':  # 中文文本
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
            raise ValueError(f"字体解析失败: {font_path} - {str(e)}")

    @staticmethod
    def get_font_size(font_path, font_size, token):
        """
        获取精确字体参数。

        :param font_path: 字体路径
        :param font_size: 字体大小
        :param token: 文本
        """
        font = ImageFont.truetype(font_path, font_size)  # 加载字体
        token_width = font.getlength(token)

        ascent, descent = font.getmetrics()  # 获取字体基线上下高度
        line_height = ascent + descent  # 计算理论行高

        return token_width, line_height
