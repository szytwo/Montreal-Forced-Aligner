import argparse
import uvicorn
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.middleware.cors import CORSMiddleware  #引入 CORS中间件模块
from contextlib import asynccontextmanager
from custom.file_utils import logging
from custom.TextProcessor import TextProcessor
from custom.AudioProcessor import AudioProcessor
from custom.VideoProcessor import VideoProcessor

# 需要安装ImageMagick并在环境变量中配置IMAGEMAGICK_BINARY的路径，或者运行时动态指定
# https://imagemagick.org/script/download.php
# os.environ['IMAGEMAGICK_BINARY'] = r"C:\Program Files\ImageMagick-7.1.0-Q16-HDRI\magick.exe"
# mfa model download dictionary mandarin_china_mfa
# mfa model download acoustic mandarin_mfa


#设置允许访问的域名
origins = ["*"]  #"*"，即为所有。

# 定义 FastAPI 应用
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 在应用启动时加载模型
    logging.info("Application loaded successfully!")
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

@app.post("/process_video/")
async def process_video(
    video: UploadFile = File(..., description="上传的视频文件"),
    audio: UploadFile = File(..., description="上传的音频文件"),
    prompt_text: str = Form(..., description="提供的文本提示，必填"),
    font: str = Form(default='fonts/yahei.ttf', description="字体路径"),
    font_size: int = Form(default=70, description="字体大小"),
    font_color: str = Form(default='yellow', description="字体颜色"),
    stroke_color: str = Form(default='yellow', description="描边颜色"),
    stroke_width: int = Form(default=0, description="描边宽度"),
    bottom: int = Form(default=10, description="字幕与视频底部的距离"),
    opacity: int = Form(default=0, description="字幕透明度 (0-255)"),
    srt: UploadFile = File(default=None, description="上传的字幕文件(可选，不传则自动生成)"),
    add_audio: bool = Form(default=False, description="是否添加音频到视频"),
):
    """
    处理视频和音频，生成带有字幕的视频。
    返回：
        JSONResponse: 包含处理结果的 JSON 响应。
    """
    # 初始化处理器
    video_processor = VideoProcessor()
    audio_processor = AudioProcessor()
    subtitle_file = None

    try:
        video_upload = await video_processor.save_upload_to_video(
                                upload_file = video
                            )
        
        if srt is not None and not isinstance(srt, UploadFile):  # 检查是否上传了文件
            subtitle_file = await video_processor.save_upload_to_srt(
                                    upload_file = srt
                                )
        
        audio_upload = await audio_processor.save_upload_to_wav(
                                upload_file = audio, 
                                prefix = "", 
                                volume_multiplier = 1.0, 
                                nonsilent = False,
                                reduce_noise_enabled = False
                            )
    except Exception as e:
        TextProcessor.log_error(e)
        return JSONResponse({"errcode": -1, "errmsg": str(e)})

    video_path =video_processor.video_subtitle(
        video_file = video_upload,
        audio_file = audio_upload,
        prompt_text = prompt_text,
        add_audio = add_audio,
        subtitle_file = subtitle_file,
        font = font,
        font_size = font_size,
        font_color = font_color,
        stroke_color = stroke_color,
        stroke_width = stroke_width,
        bottom = bottom, 
        opacity = opacity
    ) 
    # 返回视频响应
    return JSONResponse({"errcode": 0, "errmsg": "ok", "video_path": video_path})

@app.get('/download')
async def download(
    file_path:str = Query(..., description="输入文件路径"), 
):    
    """
    文件下载接口。
    """
    file_name = Path(file_path).name
    return FileResponse(path=file_path, filename=file_name, media_type='application/octet-stream')

if(__name__=='__main__'):
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',
                        type=int,
                        default=8119)
    args = parser.parse_args()
    try:
        uvicorn.run(app="api:app", host="0.0.0.0", port=args.port, workers=1, reload=True, log_level="info")
    except Exception as e:
        TextProcessor.log_error(e)
        print(e)
        exit(0)