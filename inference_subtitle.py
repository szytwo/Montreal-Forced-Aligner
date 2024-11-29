import argparse
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
from fastapi import FastAPI, File, UploadFile, Query, Form
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.middleware.cors import CORSMiddleware  #引入 CORS中间件模块
from contextlib import asynccontextmanager
from custom.file_utils import logging
from custom.AudioProcessor import AudioProcessor
from custom.MfaAlignProcessor import MfaAlignProcessor

# 需要安装ImageMagick并在环境变量中配置IMAGEMAGICK_BINARY的路径，或者运行时动态指定
# https://imagemagick.org/script/download.php
# os.environ['IMAGEMAGICK_BINARY'] = r"C:\Program Files\ImageMagick-7.1.0-Q16-HDRI\magick.exe"

# 初始化处理器
audio_processor = AudioProcessor()
#设置允许访问的域名
origins = ["*"]  #"*"，即为所有。

# 定义 FastAPI 应用
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时加载模型
    logging.info("Models loaded successfully!")
    yield  # 这里是应用运行的时间段
    logging.info("Application shutting down...")  # 在这里可以释放资源    
app = FastAPI(docs_url=None, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  #设置允许的origins来源
    allow_credentials=True,
    allow_methods=["*"],  # 设置允许跨域的http方法，比如 get、post、put等。
    allow_headers=["*"])  #允许跨域的headers，可以用来鉴别来源等作用。
# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
# 使用本地的 Swagger UI 静态资源
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    logging.info("Custom Swagger UI endpoint hit")
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Custom Swagger UI",
        swagger_js_url="/static/swagger-ui/5.9.0/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/5.9.0/swagger-ui.css",
    )

@app.get('/test')
async def test():
    """
    测试接口，用于验证服务是否正常运行。
    """
    return PlainTextResponse('success')

if(__name__=='__main__'):
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, default="./example/a/chouzhi.mp4")
    parser.add_argument("--audio", type=str, default="./example/a/a.wav")
    parser.add_argument("--prompt",type=str, default="《AI数字人：创业者私域IP打造新利器》，AI数字人正成为创业者塑造私域IP的强大力量。它可以全年无休地直播，持续向潜在用户传递创业者的品牌理念和产品优势，吸引流量，增加曝光度。数字人能依据创业者的个性特点和目标受众，定制独特的形象与话术，精准触达目标客户，比如时尚领域创业者就可打造时尚感十足的数字人。而且，它可以快速生成优质内容，无论是产品介绍还是知识分享，都能高效完成，保持私域内容的更新频率。在成本方面，相比真人团队，大大降低了人力、物力开支。不过，数字人也有局限。它缺乏真实情感，可能在深度互动上稍显不足。但只要创业者合理运用，AI数字人就能在私域IP打造中发挥巨大作用，开启创业新征程。")
    parser.add_argument("--srt", type=str, default="")
    parser.add_argument("--output", type=str, default="./results/output/chouzhi.mp4")
    parser.add_argument("--font", type=str, default='fonts/yahei.ttf')
    parser.add_argument("--font_size", type=int, default=70)
    parser.add_argument("--font_color", type=str, default='yellow')
    parser.add_argument("--stroke_color", type=str, default='yellow')
    parser.add_argument("--stroke_width", type=int, default=0)
    args = parser.parse_args()
    # 视频文件路径
    video = args.video
    # 加载视频
    clip = VideoFileClip(video).without_audio()
    # 获取视频宽度
    video_width = clip.w
    # 每行最大长度
    maxsize = video_width / args.font_size - 2
    # 字幕文件路径（假设是SRT格式）
    srt = args.srt

    if not srt:
        mfa_align_processor = MfaAlignProcessor()
        # 调用对齐函数
        srt = mfa_align_processor.align_audio_with_text(
                    audio_path = args.audio,
                    text = args.prompt,
                    min_line_length = 0,
                    max_line_length = maxsize
                )
    # 加载新的音频文件
    new_audio = AudioFileClip(args.audio)
    # 创建字幕clip
    subtitle_clips = create_subtitle_clip(args, srt)
    # 将字幕clip添加到视频
    final_clip = CompositeVideoClip([clip] + subtitle_clips).set_audio(new_audio)
    # 输出视频
    output_file = args.output
    
    final_clip.write_videofile(output_file, codec='libx264', audio_codec='aac', fps=clip.fps)