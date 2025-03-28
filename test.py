from zhconv import convert

from custom.SrtProcessor import SrtProcessor
from custom.TextProcessor import TextProcessor

text = """"Ancient Architecture Lovers Must Visit Kaiyuan Temple in Quanzhou  
This thousand-year-old temple houses twin pagodas from the Song Dynastyexquisite stone carvings. The red wallsdark tiles showcase the charm of southern Fujian.  
Strolling through the temple, you can immerse yourself in Buddhist culture while discovering perfect photo spots. Located just 5 minutes from West Street's food alley, it's the ideal blend of sightseeingdining!"""
# 查看文本的原始表示
print(repr(text))
dir = "8910cosyvoice"
textgrid_file = f"D:/AI/Montreal-Forced-Aligner/results/{dir}/{dir}.TextGrid"
srt_file = f"D:/AI/Montreal-Forced-Aligner/results/{dir}/{dir}.srt"
json_file = f"D:/AI/Montreal-Forced-Aligner/results/{dir}/{dir}.json"

text = TextProcessor.clear_text(text)
text = convert(text, 'zh-cn')
print(text)
SrtProcessor.textgrid_to_srt_for_punctuation(
    text=text,
    textgrid_path=textgrid_file,
    output_srt_path=srt_file,
    output_json_path=json_file,
    language="en"
)
