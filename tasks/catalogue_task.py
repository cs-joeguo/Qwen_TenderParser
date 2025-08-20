# -*- coding: utf-8 -*-
'''目录筛选与结构化任务处理逻辑'''
import time
from config import logger, TaskStatus
from services.redis_service import redis_service
from services.file_service import file_service
from services.extract_service import extract_service

def process_catalogue_task(task: dict) -> None:
    """处理单个目录筛选任务"""
    task_id = task["task_id"]
    bid = task["bid"]
    file_path = task["file_path"]
    
    try:
        redis_service.set_catalogue_task_status(task_id, TaskStatus.PROCESSING)
        logger.info(f"开始处理目录任务 {task_id}（bid: {bid}）")
        
        # 转换为PDF
        pdf_path = file_service.convert_to_pdf(file_path)
        if not pdf_path:
            raise Exception("文件转换为PDF失败")
        
        # 提取文本
        pdf_content = file_service.extract_text_from_pdf(pdf_path)
        if not pdf_content:
            raise Exception("PDF文本提取失败")
        
        # 提取目录结构并保存结果
        result = extract_service.extract_catalogue(pdf_content, bid)
        redis_service.set_catalogue_task_status(task_id, TaskStatus.SUCCESS)
        redis_service.set_catalogue_task_result(task_id, result)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"目录任务 {task_id} 处理失败：{error_msg}")
        redis_service.set_catalogue_task_status(task_id, TaskStatus.FAILED)
        redis_service.set_catalogue_task_result(task_id, {
            "bidId": bid,
            "retCode": "9999",
            "retMessage": error_msg,
            "catalogue": []
        })
    finally:
        # 清理临时文件
        file_service.clean_temp_files(file_path)

def run_catalogue_consumer() -> None:
    """目录任务消费者进程"""
    logger.info("目录任务消费者启动，等待任务...")
    while True:
        try:
            task = redis_service.get_next_catalogue_task()
            logger.info(f"接收到目录任务：{task['task_id']}")
            process_catalogue_task(task)
        except Exception as e:
            logger.error(f"目录任务消费者异常：{str(e)}")
            time.sleep(5)