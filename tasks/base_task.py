'''基础招标信息任务处理逻辑'''
import time
from config import logger, TaskStatus
from services.redis_service import redis_service
from services.file_service import file_service
from services.extract_service import extract_service

def process_base_task(task: dict) -> None:
    """处理单个基础任务"""
    task_id = task["task_id"]
    bid = task["bid"]
    file_path = task["file_path"]
    
    try:
        redis_service.set_base_task_status(task_id, TaskStatus.PROCESSING)
        logger.info(f"开始处理基础任务 {task_id}（bid: {bid}）")
        
        # 转换为PDF
        pdf_path = file_service.convert_to_pdf(file_path)
        if not pdf_path:
            raise Exception("文件转换为PDF失败")
        
        # 提取文本
        pdf_content = file_service.extract_text_from_pdf(pdf_path)
        if not pdf_content:
            raise Exception("PDF文本提取失败")
        
        # 提取信息并保存结果
        result = extract_service.extract_base_info(pdf_content)
        redis_service.set_base_task_status(task_id, TaskStatus.SUCCESS)
        redis_service.set_base_task_result(task_id, result)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"基础任务 {task_id} 处理失败：{error_msg}")
        redis_service.set_base_task_status(task_id, TaskStatus.FAILED)
        redis_service.set_base_task_result(task_id, {
            "retCode": "9999",
            "retMessage": error_msg,
            "projectInfo": {},
            "bidContactInfo": {},
            "bidBond": {}
        })
    finally:
        # 清理临时文件
        file_service.clean_temp_files(file_path)

def run_base_consumer() -> None:
    """基础任务消费者进程"""
    logger.info("基础任务消费者启动，等待任务...")
    while True:
        try:
            task = redis_service.get_next_base_task()
            logger.info(f"接收到基础任务：{task['task_id']}")
            process_base_task(task)
        except Exception as e:
            logger.error(f"基础任务消费者异常：{str(e)}")
            time.sleep(5)