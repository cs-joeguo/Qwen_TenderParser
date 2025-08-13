'''
Descripttion: qwen提取标书中的招标信息
Author: Joe Guo
version: 
Date: 2025-08-12 14:09:48
LastEditors: Joe Guo
LastEditTime: 2025-08-13 14:17:00
'''

import os
import json
import uuid
import time
import logging
import requests
import pdfplumber
import subprocess
from enum import Enum
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import redis
import tempfile
from multiprocessing import Process

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tender_service")

# 配置参数
REDIS_HOST = "localhost"
REDIS_PORT = 16379
REDIS_DB = 0
REDIS_PASSWORD = "Zjtx@2024CgAi"
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
SUPPORTED_EXTENSIONS = ['.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.pdf']
EXTRACT_API_URL = "http://192.168.230.29:8000/v1/chat/completions"

# 任务状态枚举
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"

# Redis键前缀
TASK_QUEUE_KEY = "task:queue"
TASK_STATUS_KEY = "task:status:{task_id}"
TASK_RESULT_KEY = "task:result:{task_id}"
TASK_BID_MAPPING = "task:bid:mapping"

# 初始化Redis连接
redis_client = redis.from_url(REDIS_URL)

# 临时文件目录
TEMP_DIR = tempfile.TemporaryDirectory(prefix="tender_")

# Redis操作工具函数
def generate_task_id():
    return str(uuid.uuid4())

def add_task_to_queue(task_id, bid, file_path):
    task_data = {
        "task_id": task_id,
        "bid": bid,
        "file_path": file_path
    }
    redis_client.rpush(TASK_QUEUE_KEY, json.dumps(task_data))
    redis_client.set(f"{TASK_BID_MAPPING}:{bid}", task_id)
    set_task_status(task_id, TaskStatus.PENDING)

def get_next_task():
    _, task_data = redis_client.blpop(TASK_QUEUE_KEY)
    return json.loads(task_data)

def set_task_status(task_id, status):
    redis_client.set(TASK_STATUS_KEY.format(task_id=task_id), status.value)

def get_task_status(task_id):
    status = redis_client.get(TASK_STATUS_KEY.format(task_id=task_id))
    return status.decode() if status else None

def set_task_result(task_id, result):
    redis_client.set(TASK_RESULT_KEY.format(task_id=task_id), json.dumps(result))

def get_task_result(task_id):
    result = redis_client.get(TASK_RESULT_KEY.format(task_id=task_id))
    return json.loads(result) if result else None

def get_task_id_by_bid(bid):
    task_id = redis_client.get(f"{TASK_BID_MAPPING}:{bid}")
    return task_id.decode() if task_id else None

# 文件处理工具函数
def convert_to_pdf(file_path, libreoffice_path=None):
    try:
        file_dir = os.path.dirname(file_path)
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        pdf_path = os.path.join(file_dir, f"{file_name}.pdf")
        
        cmd = [
            libreoffice_path or "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", file_dir,
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"转换失败，错误信息: {result.stderr}")
            return None
            
        if os.path.exists(pdf_path):
            return pdf_path
        logger.error("转换成功但未找到生成的PDF文件")
        return None
        
    except Exception as e:
        logger.error(f"转换过程出错: {str(e)}")
        return None

def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text if text else None
    except Exception as e:
        logger.error(f"提取PDF文本失败: {str(e)}")
        return None

def extract_info(pdf_content):
    try:
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": f"""请帮我从提供的文件中提取指定信息，并按照以下结构化格式返回结果。具体要求如下：

                    1. 整体结构：返回内容需包含1个状态信息和3个字典（Dict），分别为"返回状态"、"projectInfo"、"bidContactInfo"、"bidBond"，每个部分包含对应的字段。

                    2. 各字段详细要求：
                    - 返回状态：
                        - retCode：字符串类型，取值范围为"0000"（返回成功）、"0001"（解析中）、"9999"（解释失败），示例："0000"
                        - retMessage：字符串类型，用于说明错误原因，若返回成功则留空，示例：""

                    - projectInfo（项目信息）：
                        - projectCode：字符串类型，必填项，示例："2024-JL05-W1813"
                        - projectName：字符串类型，必填项，示例："智能化管控及信息化设备"
                        - customerName：字符串类型，非必填项，示例："中国解放军陆军工程大学"
                        - bidOpenTime：字符串类型，格式为"YYYY-MM-DD HH24:MM:SS"，示例："2025-02-09 09:00:00"
                        - bidDeadlineTime：字符串类型，格式同上，示例："2025-02-09 09:00:00"
                        - bidAddress：字符串类型，示例："江苏徐州"
                        - budgetAmount：十进制数类型，保留两位小数（去除千位分隔符），示例："3970000.00"

                    - bidContactInfo（招标联系方式）：
                        - bidAgentOrg：字符串类型
                        - agentContactPerson：字符串类型
                        - agentContactPhone：字符串类型

                    - bidBond（投标保证金）：
                        - bondAccountNumber：字符串类型
                        - bondAccountName：字符串类型
                        - bondAccountBranch：字符串类型
                        - bondAmount：十进制数类型，保留两位小数（去除千位分隔符），示例："450000.00"
                        - bondDeadlineTime：字符串类型，格式为"YYYY-MM-DD HH24:MM:SS"

                    3. 补充说明：
                    - 若文件中无对应信息，该字段留空即可
                    - 请严格按照上述格式（包括字段名称、类型、格式要求）返回，避免遗漏或格式错误

                    请处理以下PDF文件内容,返回符合要求的结构化数据，不要多余的内容：
                    {pdf_content}"""
                }
            ],
            "stream": False
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(
            EXTRACT_API_URL,
            headers=headers,
            data=json.dumps(payload)
        )


        response.raise_for_status()
        
        response_data = response.json()
        core_content = response_data["choices"][0]["message"]["content"]
        # 去除Markdown代码块标记
        core_content = core_content.strip()
        if core_content.startswith("```json"):
            core_content = core_content[len("```json"):]
        if core_content.endswith("```"):
            core_content = core_content[:-len("```")]
        core_content = core_content.strip()
        
        # 解析结果并构建包含状态信息的完整结构
        extracted_data = json.loads(core_content)
        
        # 构建包含状态信息的返回结构
        return {
            "retCode": extracted_data.get("retCode", "0000"),
            "retMessage": extracted_data.get("retMessage", "解析成功"),
            "projectInfo": extracted_data.get("projectInfo", {}),
            "bidContactInfo": extracted_data.get("bidContactInfo", {}),
            "bidBond": extracted_data.get("bidBond", {})
        }

        
    except requests.exceptions.HTTPError as e:
        logger.error(f"API请求错误: {e}")
        raise Exception(f"API请求错误: {e}")
    except KeyError as e:
        logger.error(f"API响应结构错误，缺少字段: {e}")
        raise Exception(f"API响应结构错误: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"解析API返回结果失败: {e}")
        raise Exception(f"解析结果失败: {e}")
    except Exception as e:
        logger.error(f"信息提取过程出错: {e}")
        raise Exception(f"信息提取出错: {e}")

# 任务处理函数
def process_task(task):
    task_id = task["task_id"]
    bid = task["bid"]
    file_path = task["file_path"]
    
    try:
        set_task_status(task_id, TaskStatus.PROCESSING)
        logger.info(f"开始处理任务 {task_id}, bid: {bid}")
        
        # 转换为PDF
        pdf_path = convert_to_pdf(file_path)
        if not pdf_path:
            raise Exception("文件转换为PDF失败")
        
        # 提取PDF内容
        pdf_content = extract_text_from_pdf(pdf_path)
        if not pdf_content:
            raise Exception("提取PDF内容失败")
        
        # 提取信息（包含状态信息的完整结构）
        result = extract_info(pdf_content)
        
        # 存储包含状态信息的结果
        set_task_status(task_id, TaskStatus.SUCCESS)
        set_task_result(task_id, result)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"任务 {task_id} 处理失败: {error_msg}")
        set_task_status(task_id, TaskStatus.FAILED)
        set_task_result(task_id, {
            "retCode": "9999",
            "retMessage": error_msg,
            "projectInfo": {},
            "bidContactInfo": {},
            "bidBond": {}
        })
    finally:
        # 清理临时文件
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {str(e)}")
        
        # 清理PDF文件
        pdf_path = os.path.splitext(file_path)[0] + ".pdf"
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                logger.info(f"已删除临时PDF文件: {pdf_path}")
            except Exception as e:
                logger.warning(f"删除临时PDF文件失败: {str(e)}")

# 消费者进程
def run_consumer():
    logger.info("任务消费者已启动，等待任务...")
    while True:
        try:
            task = get_next_task()
            logger.info(f"接收到新任务: {task['task_id']}")
            process_task(task)
        except Exception as e:
            logger.error(f"消费者处理出错: {str(e)}")
            time.sleep(5)

# FastAPI应用
app = FastAPI(title="招标信息提取服务")

@app.post("/api/base_tasks", summary="提交文件处理任务")
async def create_task(
    bid: str = Form(..., description="投标编号"),
    file: UploadFile = File(..., description="待处理的文件")
):
    # 验证文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，支持的类型: {SUPPORTED_EXTENSIONS}"
        )
    
    # 保存文件到临时目录
    try:
        file_path = os.path.join(TEMP_DIR.name, f"{bid}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 创建任务
        task_id = generate_task_id()
        add_task_to_queue(task_id, bid, file_path)
        
        return JSONResponse({
            "task_id": task_id,
            "bid": bid,
            "status": TaskStatus.PENDING.value,
            "message": "任务已提交，正在等待处理"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"创建任务失败: {str(e)}"}
        )

@app.get("/api/base_results", summary="查询任务结果")
async def get_result(bid: str):
    """通过bid查询任务结果"""
    task_id = get_task_id_by_bid(bid)
    if not task_id:
        raise HTTPException(status_code=404, detail="未找到该bid对应的任务")
    
    status = get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务状态不存在")
    
    # 任务成功时返回包含状态信息的完整结果
    if status == TaskStatus.SUCCESS.value:
        task_result = get_task_result(task_id)
        if task_result:
            return JSONResponse(task_result)
    
    # 任务未完成或失败时返回统一格式的状态信息
    # 修复：确保task_result不为None，使用空字典作为默认值
    task_result = get_task_result(task_id) or {}
    return JSONResponse({
        "retCode": "0001" if status == TaskStatus.PROCESSING.value else "9999",
        "retMessage": "解析中" if status == TaskStatus.PROCESSING.value else task_result.get("retMessage", "解析失败"),
        "projectInfo": {},
        "bidContactInfo": {},
        "bidBond": {}
    })

if __name__ == "__main__":
    # 启动消费者进程
    consumer_process = Process(target=run_consumer, daemon=True)
    consumer_process.start()
    
    # 启动FastAPI服务
    uvicorn.run(app, host="0.0.0.0", port=8001)
