import argparse
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from itertools import islice
from custom.MfaAlignProcessor import MfaAlignProcessor

# 读取字幕文件并创建字幕clip
def create_subtitle_clip(args):
    subtitle_file=args.srt
    font_size=args.font_size
    color=args.font_color
    font=args.font
    stroke_color=args.stroke_color
    stroke_width=args.stroke_width
    subtitles = []
    with open(subtitle_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        it = iter(lines)
        for line in it:
            if '-->' in line:
                start, end = line.split(' --> ')
                text = ''
                # 使用迭代器读取直到下一个包含'-->'的行
                for next_line in it:
                    if next_line.strip()=='':
                        break
                    if next_line.strip():  # 如果行不是空的或只包含空格
                        text += next_line.strip() + ' '  # 添加空格分隔单词
                subtitles.append((start, end.strip(), text.strip()))  # 去除末尾的空格

    # 创建字幕clips
    subtitle_clips = []
    for start, end, text in subtitles:
        text_clip = TextClip(text, fontsize=font_size, color=color, align='center', method='caption',stroke_color=stroke_color,stroke_width=stroke_width,font=font,size=(clip.w,None))
        text_clip = text_clip.set_start(start)
        text_clip = text_clip.set_duration(float(end) - float(start))
        text_clip = text_clip.set_position(('center', 'bottom')).margin(bottom=10, opacity=0)
        subtitle_clips.append(text_clip)

    return subtitle_clips

if(__name__=='__main__'):
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, default="")
    parser.add_argument("--audio", type=str, default="")
    parser.add_argument("--prompt",type=str, default="")
    parser.add_argument("--srt", type=str, default="")
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--font", type=str, default='fonts/yahei.ttf')
    parser.add_argument("--font_size", type=int, default=100)
    parser.add_argument("--font_color", type=str, default='yellow')
    parser.add_argument("--stroke_color", type=str, default='yellow')
    parser.add_argument("--stroke_width", type=int, default=0)
    args = parser.parse_args()
    # 视频文件路径
    video = args.video
    # 字幕文件路径（假设是SRT格式）
    srt = args.srt

    if not srt:
        mfa_align_processor = MfaAlignProcessor()
        # 调用对齐函数
        srt = mfa_align_processor.align_audio_with_text(args.audio, args.prompt)
    # 加载视频
    clip = VideoFileClip(video)
    # 创建字幕clip
    subtitle_clips = create_subtitle_clip(args)
    # 将字幕clip添加到视频
    final_clip = CompositeVideoClip([clip] + subtitle_clips)
    # 输出视频
    output_file = args.output
    
    final_clip.write_videofile(output_file, codec='libx264', audio_codec='aac', fps=clip.fps)