import argparse
import time
from pathlib import Path

import hanlp
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, Query
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import PlainTextResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware  # 引入 CORS中间件模块

from custom.AsrProcessor import AsrProcessor
from custom.AssProcessor import AssProcessor
from custom.AudioProcessor import AudioProcessor
from custom.MfaAlignProcessor import MfaAlignProcessor
from custom.TextProcessor import TextProcessor
from custom.VideoProcessor import VideoProcessor
from custom.file_utils import logging, delete_old_files_and_folders
from custom.model.ProcessAudioModel import ProcessAudioResponse
from custom.model.ProcessTokModel import ProcessTokRequest, ProcessTokResponse
from custom.model.ProcessVideoModel import ProcessVideoResponse

# 需要安装ImageMagick并在环境变量中配置IMAGEMAGICK_BINARY的路径，或者运行时动态指定
# https://imagemagick.org/script/download.php
# os.environ['IMAGEMAGICK_BINARY'] = r"C:\Program Files\ImageMagick-7.1.0-Q16-HDRI\magick.exe"
# mfa model download dictionary mandarin_china_mfa
# mfa model download acoustic mandarin_mfa

result_dir = './results'

# 设置允许访问的域名
origins = ["*"]  # "*"，即为所有。

app = FastAPI(docs_url=None)
# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 设置允许的origins来源
    allow_credentials=True,
    allow_methods=["*"],  # 设置允许跨域的http方法，比如 get、post、put等。
    allow_headers=["*"])  # 允许跨域的headers，可以用来鉴别来源等作用。
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


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset=utf-8>
            <title>Api information</title>
        </head>
        <body>
            <a href='./docs'>Documents of API</a>
        </body>
    </html>
    """


@app.get('/test')
async def test():
    """
    测试接口，用于验证服务是否正常运行。
    """
    return PlainTextResponse('success')


@app.post(
    "/process_tok/",
    response_model=ProcessTokResponse
)
async def process_tok(request: ProcessTokRequest):
    """
    处理中文分词。
    """
    response = ProcessTokResponse()
    # 记录开始时间
    start_time = time.time()

    try:
        tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
        if len(request.dict_force) > 0:
            tokenizer.dict_force = request.dict_force
        tokens = tokenizer(request.text)
        response.tokens = tokens
    except Exception as ex:
        TextProcessor.log_error(ex)
        response.errcode = -1
        response.errmsg = f"处理失败：{str(ex)}"

    # 计算耗时
    elapsed = time.time() - start_time
    logging.info(f"分词生成完成，用时: {elapsed}")

    return response


@app.post(
    "/process_video/",
    response_model=ProcessVideoResponse
)
async def process_video(
        video: UploadFile = File(..., description="上传的视频文件"),
        prompt_text: str = Form(..., description="提供的文本提示，必填"),
        font: str = Form(default='fonts/yahei.ttf', description="字体路径"),
        font_size: int = Form(default=70, description="字体大小"),
        font_color: str = Form(default='yellow', description="字体颜色"),
        stroke_color: str = Form(default='yellow', description="描边颜色"),
        stroke_width: int = Form(default=0, description="描边宽度"),
        bottom: int = Form(default=10, description="字幕与视频底部的距离"),
        opacity: int = Form(default=0, description="字幕透明度 (0-255)"),
        fps: int = Form(default=25, description="目标帧率"),
        srt: UploadFile = File(default=None, description="上传的字幕文件(可选，不传则自动生成)"),
        isass: bool = Form(default=True, description="是否使用ass文件"),
):
    """
    处理视频和音频，生成带有字幕的视频。
    """
    response = ProcessVideoResponse()
    # 记录开始时间
    start_time = time.time()

    try:
        prompt_text, language = TextProcessor.clear_text(prompt_text)
        # 初始化处理器
        video_processor = VideoProcessor()
        subtitle_file = None

        video_upload = await video_processor.save_upload_to_video(
            upload_file=video
        )

        if srt is not None and not isinstance(srt, UploadFile):  # 检查是否上传了文件
            subtitle_file = await video_processor.save_upload_to_srt(
                upload_file=srt
            )

        (response.video_path,
         response.subtitle_path,
         response.ass_path,
         response.font_dir) = video_processor.video_subtitle(
            video_file=video_upload,
            prompt_text=prompt_text,
            subtitle_file=subtitle_file,
            font=font,
            font_size=font_size,
            font_color=font_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            bottom=bottom,
            opacity=opacity,
            fps=fps,
            isass=isass,
            language=language
        )
        # 返回视频响应
    except Exception as ex:
        TextProcessor.log_error(ex)
        response.errcode = -1
        response.errmsg = str(ex)
    finally:
        # 删除过期文件
        delete_old_files_and_folders(result_dir, 1)

    # 计算耗时
    elapsed = time.time() - start_time
    logging.info(f"字幕生成完成，用时: {elapsed}")

    return response


@app.post(
    "/process_audio/",
    response_model=ProcessAudioResponse
)
async def process_audio(
        audio: UploadFile = File(..., description="上传的音频文件"),
        prompt_text: str = Form(..., description="提供的文本提示，必填"),
        video_width: int = Form(default=0, description="视频宽度"),
        video_height: int = Form(default=0, description="视频高度"),
        font: str = Form(default='fonts/yahei.ttf', description="字体路径"),
        font_size: int = Form(default=70, description="字体大小"),
        font_color: str = Form(default='yellow', description="字体颜色"),
        stroke_color: str = Form(default='yellow', description="描边颜色"),
        stroke_width: int = Form(default=0, description="描边宽度"),
        bottom: int = Form(default=10, description="字幕与视频底部的距离"),
        opacity: int = Form(default=0, description="字幕透明度 (0-255)"),
        isass: bool = Form(default=True, description="是否使用ass文件"),
):
    """
    处理音频，生成带有字幕的视频。
    """
    response = ProcessAudioResponse()
    # 记录开始时间
    start_time = time.time()

    try:
        prompt_text, language = TextProcessor.clear_text(prompt_text)
        # 初始化处理器
        audio_processor = AudioProcessor()

        audio_file = await audio_processor.save_upload_to_wav(
            upload_file=audio,
            prefix="",
            volume_multiplier=1.0,
            nonsilent=False,
            reduce_noise_enabled=False
        )

        if language == 'ja' and not font.startswith("fonts/JA/"):
            font = "fonts/JA/Noto_Sans_JP/static/NotoSansJP-Black.ttf"
        elif language == 'ko' and not font.startswith("fonts/KO/"):
            font = "fonts/KO/Noto_Sans_KR/static/NotoSansKR-Black.ttf"
        min_line_len = 12 if language == 'en' else 4
        # 每行最大字符数
        max_line_len = 40
        if video_width > 0 and font_size > 0:
            max_line_len = TextProcessor.calc_max_line_len(video_width, font_size, language)

        mfa_align_processor = MfaAlignProcessor()
        subtitle_file, json_file = mfa_align_processor.align_audio_with_text(
            audio_path=audio_file,
            text=prompt_text,
            min_line_len=min_line_len,
            max_line_len=max_line_len,
            language=language
        )
        # MFA失败，则使用ASR
        if not subtitle_file:
            asr_processor = AsrProcessor()
            subtitle_file, json_file = asr_processor.asr_to_srt(
                audio_path=audio_file,
                min_line_len=min_line_len,
                max_line_len=max_line_len
            )

        if isass:
            ass_processor = AssProcessor()
            response.ass_path, response.font_dir = ass_processor.create_subtitle_ass(
                subtitle_file=subtitle_file,
                video_width=video_width,
                video_height=video_height,
                font_path=font,
                font_size=font_size,
                font_color=font_color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                bottom=bottom,
                opacity=opacity,
                max_line_len=max_line_len
            )

        response.subtitle_path = subtitle_file
        response.json_path = json_file
    except Exception as ex:
        TextProcessor.log_error(ex)
        response.errcode = -1
        response.errmsg = str(ex)
    finally:
        # 删除过期文件
        delete_old_files_and_folders(result_dir, 1)

    # 计算耗时
    elapsed = time.time() - start_time
    logging.info(f"字幕生成完成，用时: {elapsed}")

    return response


@app.get('/download')
async def download(
        file_path: str = Query(..., description="输入文件路径"),
):
    """
    文件下载接口。
    """
    file_name = Path(file_path).name
    return FileResponse(path=file_path, filename=file_name, media_type='application/octet-stream')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',
                        type=int,
                        default=8119)
    args = parser.parse_args()
    try:
        uvicorn.run(app="api:app", host="0.0.0.0", port=args.port, workers=1, reload=False, log_level="info")
    except Exception as e:
        TextProcessor.log_error(e)
        print(e)
        exit(0)
