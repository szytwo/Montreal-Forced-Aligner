import os
import subprocess
from pathlib import Path

from custom.SrtProcessor import SrtProcessor
from custom.TextProcessor import TextProcessor
from custom.file_utils import logging, get_full_path


class MfaAlignProcessor:
    def __init__(self,
                 model_dir="MFA/pretrained_models"
                 ):
        """
        初始化MFA音频与文本对齐处理器。
        :param model_dir: 模型文件目录
        """
        self.model_dir = model_dir

    def align_audio_with_text(
            self,
            audio_path,
            text,
            min_line_len=0,
            max_line_len=40,
            language=None,
            split_type="silence"
    ):
        """
        使用 MFA 进行音频与文本对齐
        :param audio_path: 包含音频文件的路径
        :param text: 文本
        :param min_line_len: 行最小长度
        :param max_line_len: 行最大长度
        :param language: 语言
        :param split_type: 分行方法："silence"静音，"punctuation"标点符号
        """
        if not language:
            language = TextProcessor.detect_language(text)
        # 根据语言选择模型和字典路径
        dictionary_name = 'mandarin_china_mfa.dict'
        acoustic_name = 'mandarin_mfa.zip'

        if language == 'en':
            dictionary_name = 'english_uk_mfa.dict'
            acoustic_name = 'english_mfa.zip'
        elif language == 'ja':
            dictionary_name = 'japanese_mfa.dict'
            acoustic_name = 'japanese_mfa.zip'
        elif language == 'ko':
            dictionary_name = 'korean_mfa.dict'
            acoustic_name = 'korean_mfa.zip'

        model_dir = get_full_path(self.model_dir)
        dictionary_path = os.path.join(model_dir, 'dictionary', dictionary_name)
        model_path = os.path.join(model_dir, 'acoustic', acoustic_name)
        # 构建保存路径
        audio_path = get_full_path(audio_path)
        audio_dir = Path(audio_path).parent
        audio_name = Path(audio_path).stem  # 获取音频文件名（不带扩展名）
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
            audio_dir,  # 输出结果目录
            f"--temporary_directory", audio_dir,  # 临时目录
            "--clean",  # 清理运行前的旧文件
            "--final_clean",  # 清理运行后的临时文件
            "--overwrite",  # 覆盖旧输出
            "--beam", "100",  # 扩大对齐搜索范围（默认10）
            "--retry_beam", "400",  # 重试时的搜索范围（默认400）
            "--textgrid_cleanup",  # 打开/关闭 TextGrids 的后处理，以清理静音并重新组合复合词和词语
            "--cleanup_textgrids",
            "--use_mp",  # 启用多进程
            "--no_use_threading",  # 禁用多线程
            "--single_speaker",  # 单说话人模式，禁用说话人自适应
            "--ignore_case", "false",  # 禁用转换为小写
            f"--num_jobs", str(num_jobs)  # 使用 CPU 核心数
        ]

        try:
            logging.info(f"正在使用 MFA 进行音频与文本对齐...")
            # 调用 MFA
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            # 打印 MFA 的输出日志
            logging.info("MFA 音频与文本对齐完成!")
            logging.info(f"Output Directory: {audio_dir}")
            logging.info(f"MFA Output:\n {result.stdout}")
            # 查找生成的 TextGrid 文件
            textgrid_file = os.path.join(audio_dir, f"{audio_name}.TextGrid")
            srt_file = os.path.join(audio_dir, f"{audio_name}.srt")
            json_file = os.path.join(audio_dir, f"{audio_name}.json")
            # 将 TextGrid 文件转换为 SRT 文件
            if split_type == "punctuation" and language in ['zh', 'zh-cn', 'en']:
                SrtProcessor.textgrid_to_srt_for_punctuation(
                    text=text,
                    textgrid_path=textgrid_file,
                    output_srt_path=srt_file,
                    output_json_path=json_file,
                    language=language
                )
            else:
                SrtProcessor.textgrid_to_srt_for_silence(
                    textgrid_path=textgrid_file,
                    output_srt_path=srt_file,
                    output_json_path=json_file,
                    min_line_len=min_line_len,
                    max_line_len=max_line_len,
                    language=language
                )

            return srt_file, json_file
        except subprocess.CalledProcessError as e:
            # 捕获任何在处理过程中发生的异常
            ex = Exception(f"Error during alignment: {e.stderr}")
            TextProcessor.log_error(ex)

        logging.error("MFA 音频与文本对齐失败!")
        return None, None
