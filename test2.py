import subprocess
import os

from textgrid import TextGrid
from datetime import timedelta

def textgrid_to_srt(textgrid_path, output_srt_path, min_gap=0.5):
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

            # 检查时间间隔是否超出 min_gap
            if interval.maxTime - interval.minTime > min_gap:
                subtitle_text = ' '.join(current_subtitle)
                subtitles.append((subtitle_id, start_time, end_time, subtitle_text))
                subtitle_id += 1
                current_subtitle = []
                start_time = None
                end_time = None

    # 处理最后一个字幕条目
    if current_subtitle:
        subtitle_text = ' '.join(current_subtitle)
        subtitles.append((subtitle_id, start_time, end_time, subtitle_text))

    # 写入 SRT 文件
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        for subtitle in subtitles:
            subtitle_id, start_time, end_time, text = subtitle
            start_time_str = str(timedelta(seconds=start_time))
            end_time_str = str(timedelta(seconds=end_time))
            start_time_str = start_time_str[2:7]  # 转换为小时:分钟:秒,毫秒格式
            end_time_str = end_time_str[2:7]
            f.write(f"{subtitle_id}\n")
            f.write(f"{start_time_str.replace('.', ',')} --> {end_time_str.replace('.', ',')}\n")
            f.write(f"{text}\n\n")

    print(f"SRT file saved to {output_srt_path}")

def align_audio_with_text(audio_path,text_path, dictionary_path, model_path, output_path):
    """
    使用 MFA 进行音频与文本对齐并生成 SRT 字幕文件

    :param audio_path: 音频文件路径
    :param text_path: 文本文件路径
    :param dictionary_path: 字典文件路径
    :param model_path: 声学模型文件路径
    :param output_path: 对齐结果输出路径（包含生成的 TextGrid 文件）
    """
    # 提取 output_path 的目录路径
    output_dir = os.path.dirname(output_path)

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 构造 MFA 命令
    command = [
        "mfa", "align_one",
        audio_path,  # 音频文件目录
        text_path,
        dictionary_path,  # 字典文件路径
        model_path,  # 声学模型路径
        output_path,   # 输出结果目录
        "--clean",
        "--final_clean",
        "--overwrite"
    ]

    try:
        # 调用 MFA
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # 打印 MFA 的输出日志
        print("Alignment completed successfully!")
        print("Output Directory:", output_path)
        print("MFA Output:\n", result.stdout)

        # 设置 SRT 文件的路径（与 output_path 同名，只是扩展名不同）
        srt_file = os.path.splitext(output_path)[0] + ".srt"

        # 将 TextGrid 文件转换为 SRT 文件
        textgrid_to_srt(output_path, srt_file)

        print(f"SRT 文件已生成: {srt_file}")
    except subprocess.CalledProcessError as e:
        print("Error during alignment:")
        print(e.stderr)

# 参数定义
audio_path = r"D:\AI\Montreal-Forced-Aligner\input\a.wav"  # 音频文件的路径
text_path = r"D:\AI\Montreal-Forced-Aligner\input\aa.txt"  # 文本文件的路径
dictionary_path = r"C:\Users\Administrator\Documents\MFA\pretrained_models\dictionary\mandarin_china_mfa.dict"  # 字典文件路径
model_path = r"C:\Users\Administrator\Documents\MFA\pretrained_models\acoustic\mandarin_mfa.zip"  # 声学模型路径
output_path = r"D:\AI\Montreal-Forced-Aligner\output\a.TextGrid"  # 输出结果目录

# 调用对齐函数
align_audio_with_text(audio_path,text_path, dictionary_path, model_path, output_path)
