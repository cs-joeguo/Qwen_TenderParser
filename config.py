'''
Descripttion: 
Author: Joe Guo
version: 
Date: 2025-08-12 16:18:25
LastEditors: Joe Guo
LastEditTime: 2025-08-13 17:15:56
'''
import os
from pathlib import Path


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# Redis配置
REDIS_HOST = "localhost"
REDIS_PORT = 16379
REDIS_DB = 0
REDIS_PASSWORD = "Zjtx@2024CgAi"
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# 上传文件配置
UPLOAD_DIR = BASE_DIR / "uploads"  # 使用Path对象
UPLOAD_DIR.mkdir(exist_ok=True)    # 确保目录存在

# 支持的文件类型
SUPPORTED_EXTENSIONS = ['.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.pdf']

# 日志配置
LOG_DIR = BASE_DIR / "logs"  # 使用Path对象
LOG_DIR.mkdir(exist_ok=True)  # 确保目录存在

# 信息提取API配置
EXTRACT_API_URL = "http://192.168.230.29:8000/v1/chat/completions"
