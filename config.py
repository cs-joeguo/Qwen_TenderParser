# -*- coding: utf-8 -*-
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
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = ""  # 可能为None或空字符串

# 根据密码是否存在生成不同格式的URL
if REDIS_PASSWORD:
    # 有密码时：redis://:密码@主机:端口/数据库
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    # 无密码时：redis://主机:端口/数据库（省略密码部分）
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    

# 业务配置
SUPPORTED_EXTENSIONS = ['.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.pdf']
EXTRACT_API_URL = "http://192.168.230.29:8000/v1/chat/completions"
DB_STRUCT_PATH = "/home/zjtx/Qwen_TenderParser/doc/tendering-struct.txt"  # 数据库结构文件路径

# 临时目录
TEMP_DIR = TemporaryDirectory(prefix="tender_")

# 任务状态枚举
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


# 目录-标签映射表（供Qwen参考）
CATALOG_TAG_MAPPING = {
    "综合实力": ["企业规模", "财务状况", "人员配置"],
    "资质证明": ["资质认证", "行业许可"],
    "项目业绩": ["过往业绩", "案例规模"],
    "技术方案": ["技术架构", "实施计划"],
    "服务承诺": ["售后服务", "响应时间"],
    "投标函": ["核心文件", "法律文件"],
    "反商业贿赂承诺书": ["合规文件", "法律文件"]
}


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

    # ------------------------------ 新增：目录任务键 ------------------------------
    CATALOGUE_TASK_QUEUE = "catalogue_task:queue"  # 对应原CATALOGUE_TASK_QUEUE_KEY
    CATALOGUE_TASK_STATUS = "catalogue_task:status:{task_id}"  # 对应原CATALOGUE_TASK_STATUS_KEY
    CATALOGUE_TASK_RESULT = "catalogue_task:result:{task_id}"  # 对应原CATALOGUE_TASK_RESULT_KEY
    CATALOGUE_TASK_BID_MAPPING = "catalogue_task:bid:mapping:{bid}"  # 对应原CATALOGUE_TASK_BID_MAPPING
