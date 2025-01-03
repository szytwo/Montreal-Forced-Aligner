import os
import requests
from pathlib import Path
from custom.file_utils import logging, get_full_path
from custom.SrtProcessor import SrtProcessor
from custom.TextProcessor import TextProcessor

class AsrProcessor:
    def __init__(self):
        """
        初始化ASR音频与文本对齐处理器。
        """
        asr_url = os.getenv("ASR_URL", "") #asr接口
        self.asr_url = asr_url

    def send_asr_request(self, audio_path, lang='auto'):
        # 发送 GET 请求
        params = {'audio_path': audio_path, 'lang': lang}
        headers = {'accept': 'application/json'}

        response = requests.get(self.asr_url, params=params, headers=headers)

        if response.status_code == 200:
            return response.json()  # 返回 JSON 响应
        else:
            logging.error(f"send_asr_request fail: {response.status_code}")
            return None

    @staticmethod
    def generate_textgrid(timestamp_data, output):
        # 生成 TextGrid 文件
        xmin = timestamp_data[0][1]  # 开始时间
        xmax = timestamp_data[-1][2]  # 结束时间

        # 创建 TextGrid 文件内容
        textgrid_content = (f'File type = "ooTextFile"\n'
                            f'Object class = "TextGrid"\n\n')
        textgrid_content += (f'xmin = {xmin}\n'
                             f'xmax = {xmax}\n'
                             f'tiers? <exists>\n'
                             f'size = 1\n'
                             f'item []:\n')
        textgrid_content += (f'    item [1]:\n'
                             f'        class = "IntervalTier"\n'
                             f'        name = "words"\n'
                             f'        xmin = {xmin}\n'
                             f'        xmax = {xmax}\n')
        textgrid_content += f'        intervals: size = {len(timestamp_data)}\n'

        # 添加每个时间戳对应的标注
        for i, (word, start, end) in enumerate(timestamp_data):
            text = f'"{word}"' if word else '""'  # 如果没有文本内容，设置为空字符串
            textgrid_content += f'        intervals [{i + 1}]:\n'
            textgrid_content += f'            xmin = {start}\n'
            textgrid_content += f'            xmax = {end}\n'
            textgrid_content += f'            text = {text}\n'

        # 写入到文件
        with open(output, 'w', encoding='utf-8') as f:
            f.write(textgrid_content)

        logging.info(f"TextGrid file saved to {output}")

    def asr_to_srt(self, audio_path, min_line_length=0, max_line_length=40):
        try:
            logging.info(f"正在使用 ASR 进行音频与文本对齐...")
            # 构建保存路径
            audio_path = get_full_path(audio_path)
            audio_dir = Path(audio_path).parent
            audio_name = Path(audio_path).stem  # 获取音频文件名（不带扩展名）
            # 发送 ASR 请求并获取识别结果
            result = self.send_asr_request(audio_path)

            if result:
                # 提取文本和时间戳数据
                timestamp_data = result['result'][0]['timestamp']
                # 生成 TextGrid 文件
                textgrid_file = os.path.join(audio_dir, f"{audio_name}.TextGrid")
                AsrProcessor.generate_textgrid(timestamp_data, textgrid_file)
                # 将 TextGrid 文件转换为 SRT 文件
                srt_file = os.path.join(audio_dir, f"{audio_name}.srt")
                SrtProcessor.textgrid_to_srt(textgrid_file, srt_file, min_line_length, max_line_length)

                logging.info("ASR 音频与文本对齐完成!")

                return srt_file
            else:
                logging.error("ASR 音频与文本对齐失败!")
                return None
        except Exception as e:
            TextProcessor.log_error(e)
            return None
