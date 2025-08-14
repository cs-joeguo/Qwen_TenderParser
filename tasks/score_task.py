'''商务评分标准任务处理逻辑'''
import time
from config import logger, TaskStatus
from services.redis_service import redis_service
from services.file_service import file_service
from services.extract_service import extract_service

def process_score_task(task: dict) -> None:
    """处理单个评分任务"""
    task_id = task["task_id"]
    bid = task["bid"]
    file_path = task["file_path"]
    
    try:
        redis_service.set_score_task_status(task_id, TaskStatus.PROCESSING)
        logger.info(f"开始处理评分任务 {task_id}（bid: {bid}）")
        
        # 转换为PDF
        pdf_path = file_service.convert_to_pdf(file_path)
        if not pdf_path:
            raise Exception("文件转换为PDF失败")
        
        # 提取文本
        pdf_content = file_service.extract_text_from_pdf(pdf_path)
        if not pdf_content:
            raise Exception("PDF文本提取失败")
        
        # 提取评分标准并保存结果
        result = extract_service.extract_business_score(pdf_content)
        redis_service.set_score_task_status(task_id, TaskStatus.SUCCESS)
        redis_service.set_score_task_result(task_id, result)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"评分任务 {task_id} 处理失败：{error_msg}")
        redis_service.set_score_task_status(task_id, TaskStatus.FAILED)
        redis_service.set_score_task_result(task_id, {
            "retCode": "9999",
            "retMessage": error_msg,
            "criteria": []
        })
    finally:
        # 清理临时文件
        file_service.clean_temp_files(file_path)

def run_score_consumer() -> None:
    """评分任务消费者进程"""
    logger.info("评分任务消费者启动，等待任务...")
    while True:
        try:
            task = redis_service.get_next_score_task()
            logger.info(f"接收到评分任务：{task['task_id']}")
            process_score_task(task)
        except Exception as e:
            logger.error(f"评分任务消费者异常：{str(e)}")
            time.sleep(5)