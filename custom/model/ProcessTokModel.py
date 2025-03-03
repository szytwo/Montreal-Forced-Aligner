from typing import List

from pydantic import BaseModel, Field

from custom.model.APIBaseModel import ResponseBaseModel


# 定义请求体模型
class ProcessTokRequest(BaseModel):
    text: str = Field(
        ...,
        description="需要分词的文本，必填",
    )
    dict_force: List[str] = Field(
        default=[],
        description="强制自定义词条列表，例如：['我趣玩', '我趣玩AI', '数字人']",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "欢迎使用我趣玩AI的数字人服务",
                "dict_force": ["我趣玩", "我趣玩AI", "数字人"]
            }
        }


# 定义响应体模型
class ProcessTokResponse(ResponseBaseModel):
    tokens: List[str] = Field(
        default=[],
        description="分词后的结果列表",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "errcode": 0,
                "errmsg": "ok",
                "tokens": ["我趣玩AI", "是", "数字人"]
            }
        }
