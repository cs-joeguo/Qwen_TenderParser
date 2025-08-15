'''
Descripttion: 
Author: Joe Guo
version: 
Date: 2025-08-15 16:25:28
LastEditors: Joe Guo
LastEditTime: 2025-08-15 16:25:31
'''
'''全局配置参数'''
import os
import logging
from enum import Enum
from tempfile import TemporaryDirectory

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/tender_service.log"),  # 日志输出到logs目录
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tender_service")

# Redis配置
REDIS_HOST = "localhost"
REDIS_PORT = 16379
REDIS_DB = 0
REDIS_PASSWORD = "Zjtx@2024CgAi"
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# 业务配置
SUPPORTED_EXTENSIONS = ['.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.pdf']
EXTRACT_API_URL = "http://192.168.230.29:8000/v1/chat/completions"
DB_STRUCT_PATH = "doc/tendering-struct.txt"  # 数据库结构文件路径

# 临时目录
TEMP_DIR = TemporaryDirectory(prefix="tender_")

# 任务状态枚举
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"

# Redis键前缀（按任务类型分离）
class RedisKey:
    # 基础任务键
    BASE_TASK_QUEUE = "task:queue"
    BASE_TASK_STATUS = "task:status:{task_id}"
    BASE_TASK_RESULT = "task:result:{task_id}"
    BASE_TASK_BID_MAPPING = "task:bid:mapping:{bid}"
    
    # 评分任务键
    SCORE_TASK_QUEUE = "score_task:queue"
    SCORE_TASK_STATUS = "score_task:status:{task_id}"
    SCORE_TASK_RESULT = "score_task:result:{task_id}"
    SCORE_TASK_BID_MAPPING = "score_task:bid:mapping:{bid}"