import subprocess
import os
import argparse
from custom.MfaAlignProcessor import MfaAlignProcessor

# 参数定义
audio_path = r"./input/a.wav"  # 包含音频文件的目录
text = '《AI数字人：创业者私域IP打造新利器》，AI数字人正成为创业者塑造私域IP的强大力量。它可以全年无休地直播，持续向潜在用户传递创业者的品牌理念和产品优势，吸引流量，增加曝光度。数字人能依据创业者的个性特点和目标受众，定制独特的形象与话术，精准触达目标客户，比如时尚领域创业者就可打造时尚感十足的数字人。而且，它可以快速生成优质内容，无论是产品介绍还是知识分享，都能高效完成，保持私域内容的更新频率。在成本方面，相比真人团队，大大降低了人力、物力开支。不过，数字人也有局限。它缺乏真实情感，可能在深度互动上稍显不足。但只要创业者合理运用，AI数字人就能在私域IP打造中发挥巨大作用，开启创业新征程。'
mfa_align_processor = MfaAlignProcessor()
# 调用对齐函数
mfa_align_processor.align_audio_with_text(audio_path, text)
