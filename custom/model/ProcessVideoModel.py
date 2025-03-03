from typing import Optional

from pydantic import Field

from custom.model.APIBaseModel import ResponseBaseModel


class ProcessVideoResponse(ResponseBaseModel):
    video_path: Optional[str] = Field(
        default="",
        description="视频文件路径",
    )
    subtitle_path: Optional[str] = Field(
        default="",
        description="srt文件路径",
    )
    ass_path: Optional[str] = Field(
        default="",
        description="ass文件路径",
    )
    font_dir: Optional[str] = Field(
        default="",
        description="字体文件目录",
    )

    class Config:
        json_schema_extra = {
            "description": "字幕处理的响应结果",
            "example": {
                "errcode": 0,
                "errmsg": "ok",
                "video_path": "",
                "subtitle_path": "",
                "ass_path": "",
                "font_dir": ""
            }
        }
