import os
import numpy as np
from pathlib import Path
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from noisereduce import reduce_noise
from fastapi import UploadFile
from custom.file_utils import logging, add_suffix_to_filename

class AudioProcessor:
    def __init__(self, 
                 temp_dir="results/"):
        """
        初始化音频处理器，设置临时文件目录。
        :param temp_dir: 临时目录，用于保存生成的中间文件或输出文件。
        """
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)  # 创建临时目录（如果不存在）
    
    @staticmethod
    def volume_safely(audio: AudioSegment, volume_multiplier: float = 1.0) -> AudioSegment:
        """
        安全地调整音频音量。
        :param audio: AudioSegment 对象，音频数据。
        :param volume_multiplier: float，音量倍数，1.0 为原音量，大于 1 提高音量，小于 1 降低音量。
        :return: 调整后的 AudioSegment 对象。
        """
        logging.info(f"volume_multiplier: {volume_multiplier}")
        if volume_multiplier <= 0:
            raise ValueError("volume_multiplier 必须大于 0")

        # 计算增益（分贝），根据倍数调整
        gain_in_db = 20 * np.log10(volume_multiplier)

        # 应用增益调整音量
        audio = audio.apply_gain(gain_in_db)

        # 确保音频不削波（归一化到峰值 -0.1 dB 以下）
        audio = audio.normalize(headroom=0.1)

        return audio

    def generate_wav(self, audio_name , audio_data, sample_rate, delay=0.0, volume_multiplier = 1.0):
        """
        使用 pydub 将音频数据转换为 WAV 格式，并支持添加延迟。
        :param audio_data: numpy 数组，音频数据
        :param sample_rate: int，采样率
        :param delay: float，延迟时间（单位：秒），默认为 0
        :param volume_multiplier: float，音量倍数，默认为 1.0
        :return: 文件路径，生成的 WAV 文件路径
        """
        # 确保 audio_data 是 numpy 数组
        if not isinstance(audio_data, np.ndarray):
            raise ValueError("audio_data 必须是 numpy 数组。")
        # 生成静音数据（如果有延迟需求）
        if delay > 0:
            num_silence_samples = int(delay * sample_rate)
            silence = np.zeros(num_silence_samples, dtype=audio_data.dtype)
            audio_data = np.concatenate((silence, audio_data), axis=0)

        # 检测音频数据类型并转换
        sample_width = 2
        if audio_data.dtype == np.float32:
            # 如果是 float32 数据，量化到 int16
            audio_data = (audio_data * 32767).astype(np.int16)
            sample_width = 2  # 16-bit (2 bytes per sample)
        elif audio_data.dtype == np.int16:
            sample_width = 2  # 16-bit (2 bytes per sample)
        elif audio_data.dtype == np.int8:
            audio_data = audio_data.astype(np.int16) * 256  # 转换为 int16
            sample_width = 2  # 16-bit
        else:
            raise ValueError("audio_data.dtype 不正确。")
        # 检测声道数
        if len(audio_data.shape) == 1:  # 单声道
            channels = 1
        elif len(audio_data.shape) == 2:  # 多声道
            channels = audio_data.shape[1]
        else:
            raise ValueError("audio_data.shape 格式不正确，必须是 1D 或 2D numpy 数组。")
        # 使用 pydub 生成音频段
        audio_segment = AudioSegment(
            audio_data.tobytes(),
            frame_rate=sample_rate,
            sample_width=sample_width,
            channels=channels
        )
        if volume_multiplier != 1.0:
            # 安全地增加音量
            audio_segment = self.volume_safely(audio_segment, volume_multiplier)
        # 构建保存路径
        audio_dir = os.path.join(self.temp_dir, audio_name)
        os.makedirs(audio_dir, exist_ok=True)  # 创建目录（如果不存在）
        wav_path = os.path.join(audio_dir, f"{audio_name}_output.wav")
        # 如果文件已存在，先删除
        if os.path.exists(wav_path):
            os.remove(wav_path)
        # 导出 WAV 文件
        audio_segment.export(wav_path, format="wav")

        return wav_path        
    
    @staticmethod
    def audio_to_np_array(audio: AudioSegment):
        """将 AudioSegment 转换为 NumPy 数组"""
        return np.array(audio.get_array_of_samples())
    
    @staticmethod
    def np_array_to_audio(np_array, audio: AudioSegment):
        """将 NumPy 数组转换回 AudioSegment"""
        return AudioSegment(
            np_array.tobytes(),
            frame_rate=audio.frame_rate,
            sample_width=audio.sample_width,
            channels=audio.channels
        )
    
    async def save_upload_to_wav(
            self, 
            upload_file: UploadFile, 
            prefix: str = "", 
            volume_multiplier: float = 1.0, 
            nonsilent: bool = False, 
            reduce_noise_enabled: bool = True
        ):
        """
        保存上传文件并转换为 WAV 格式（如果需要）

        参数：
            upload_file (UploadFile): FastAPI 上传的音频文件对象
            prefix (str): 文件名前缀（默认值为空字符串）
            volume_multiplier (float): 音量调整倍数，默认为 1.0 表示不调整音量
            nonsilent (bool): 是否去除音频前后的静音部分，默认为 False
            reduce_noise_enabled (bool): 是否启用降噪处理，默认为 True

        返回：
            Path: 处理后保存的 WAV 文件路径

        异常：
            Exception: 在文件保存或处理过程中可能引发异常
        """
        # 提取上传文件的基础名称（去除扩展名）
        audio_name = Path(upload_file.filename).stem
        # 构建保存音频文件的目录路径
        audio_dir = os.path.join(self.temp_dir, audio_name)
        os.makedirs(audio_dir, exist_ok=True)  # 如果目录不存在，则创建
        # 构建保存文件的完整路径
        upload_path = os.path.join(audio_dir, f'{prefix}{upload_file.filename}')
        # 如果目标文件已存在，删除旧文件以避免冲突
        if os.path.exists(upload_path):
            os.remove(upload_path)
        # 将路径对象化，方便后续操作
        upload_path = Path(upload_path)
        # 如果文件格式不是 WAV，准备转换为 WAV 格式
        if upload_path.suffix.lower() != ".wav":
            # 创建转换后的 WAV 文件路径
            wav_path = str(upload_path.with_stem(f"{upload_path.stem}_new").with_suffix(".wav"))
        else:
            wav_path = str(upload_path)
        # 返回字符串路径
        upload_path = str(upload_path)  

        logging.info(f"接收上传{upload_file.filename}请求 {upload_path}")

        try:
            # 保存上传的原始音频文件
            with open(upload_path, "wb") as f:
                f.write(await upload_file.read())
            
            # 加载音频文件为 AudioSegment 对象（支持多种格式）
            audio = AudioSegment.from_file(upload_path)        

            # 如果启用了降噪处理
            if reduce_noise_enabled:
                logging.info("reduce noise start")
                # 将音频转换为 NumPy 数组格式
                audio_np = self.audio_to_np_array(audio)
                # 使用音频开头的 0.3 秒作为背景噪声参考
                noise_duration = int(audio.frame_rate * 0.3)  # 计算 0.3 秒的采样点数量
                noise_profile = audio_np[:noise_duration]  # 提取噪声样本
                # 调用降噪算法并进行处理
                reduced_audio_np = reduce_noise(
                    y=audio_np,
                    sr=audio.frame_rate,
                    y_noise=noise_profile,
                    n_std_thresh_stationary=2.0,  # 设置较温和的噪声阈值
                    prop_decrease=0.8  # 降低噪声衰减比例
                )
                # 将降噪后的音频数据转换回 AudioSegment 对象
                audio = self.np_array_to_audio(reduced_audio_np, audio)

            # 如果需要去除前后的静音部分
            if nonsilent:
                logging.info("nonsilent start")
                # 检测音频中非静音的区间
                nonsilent_ranges = detect_nonsilent(audio, min_silence_len=300, silence_thresh=audio.dBFS - 16)
                if nonsilent_ranges:
                    # 提取第一个和最后一个非静音区间的起始和结束位置
                    start_trim = nonsilent_ranges[0][0]
                    end_trim = nonsilent_ranges[-1][1]
                    # 截取非静音部分的音频
                    audio = audio[start_trim:end_trim]

            # 如果音量调整倍数不是 1.0，进行音量调整
            if volume_multiplier != 1.0:
                audio = self.volume_safely(audio, volume_multiplier=volume_multiplier)

            # 导出处理后的音频文件为 WAV 格式
            audio.export(wav_path, format="wav")

            return wav_path
        except Exception as e:
            # 捕获并抛出任何在处理过程中发生的异常
            raise Exception(f"{upload_file.filename}音频文件保存或转换失败: {str(e)}")
        finally:
            await upload_file.close()  # 显式关闭上传文件

    @staticmethod
    def generate_add_silent(duration, audio_path):
        """
        将 音频文件延长，多余用静音填充
        :param duration: float，延迟时间（单位：秒），默认为 0
        :param audio_path: str，文件路径
        :return: 文件路径，生成的 WAV 文件路径
        """
        logging.info(f"duration {duration} audio_path {audio_path}")
        # 加载音频文件为 AudioSegment 对象（支持多种格式）
        audio = AudioSegment.from_file(audio_path)
        # 生成静音数据（如果有延迟需求）
        if duration > 0:
            logging.info(f"生成静音数据...")
            # 将音频转换为 NumPy 数组格式
            audio_np = AudioProcessor.audio_to_np_array(audio)
            # 生成静音数据
            num_silence_samples = int(duration * audio.frame_rate)
            silence = np.zeros(num_silence_samples, dtype=audio_np.dtype)
            # 静音数据拼接后面
            audio_np = np.concatenate((audio_np, silence), axis=0)
            # 将音频数据转换回 AudioSegment 对象
            audio = AudioProcessor.np_array_to_audio(audio_np, audio)

        # 将静音片段保存为临时文件
        silent_file = add_suffix_to_filename(audio_path, "_silent")

        audio.export(silent_file, format="wav")

        return silent_file