from typing import List

from pydantic import BaseModel, Field


# 定义请求体模型
class ProcessTokRequest(BaseModel):
    text: str = Field(
        ...,
        description="提供的文本提示，必填",
        example="欢迎使用我趣玩AI的数字人服务"
    )
    dict_force: List[str] = Field(
        default=[],
        description="强制自定义词条列表，例如：['我趣玩', '我趣玩AI', '数字人']",
        example=["我趣玩", "我趣玩AI", "数字人"]
    )


# 定义响应体模型
class ProcessTokResponse(BaseModel):
    errcode: int = Field(
        default=0,
        description="错误码，0 表示成功",
        example=0
    )
    errmsg: str = Field(
        default="ok",
        description="错误信息，成功时为 'ok'",
        example="ok"
    )
    tokens: List[str] = Field(
        default=[],
        description="分词后的结果列表",
        example=["我趣玩AI", "是", "数字人", "平台"]
    )
