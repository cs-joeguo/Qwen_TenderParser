# -*- coding: utf-8 -*-
'''
Descripttion: 
Author: Joe Guo
version: 
Date: 2025-08-20 09:52:18
LastEditors: Joe Guo
LastEditTime: 2025-08-21 14:49:23
'''

'''商务评分标准任务处理逻辑'''
import time
import os  # 新增
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
        logger.debug(f"进入评分任务处理函数，参数: task_id={task_id}, bid={bid}, file_path={file_path}")
        
        redis_service.set_score_task_status(task_id, TaskStatus.PROCESSING)
        logger.info(f"评分任务 {task_id} 状态更新为: {TaskStatus.PROCESSING}")
        
        # 转换为PDF
        logger.debug(f"开始转换文件为PDF: {file_path} (大小: {os.path.getsize(file_path)/1024:.2f}KB)")
        pdf_path = file_service.convert_to_pdf(file_path)
        if not pdf_path:
            raise Exception("文件转换为PDF失败")
        logger.debug(f"PDF转换成功，保存路径: {pdf_path}")
        
        # 提取文本
        logger.debug(f"开始从PDF提取文本: {pdf_path}")
        pdf_content = file_service.extract_text_from_pdf(pdf_path)
        if not pdf_content:
            logger.error(f"PDF文本提取失败，PDF路径: {pdf_path}，文件大小: {os.path.getsize(pdf_path)/1024:.2f}KB")
            raise Exception("PDF文本提取失败")
        
        # 提取评分标准
        logger.debug(f"开始调用评分标准提取服务，task_id={task_id}")
        result = extract_service.extract_business_score(pdf_content)
        logger.debug(f"评分标准提取完成，结果预览: {str(result)[:200]}...")
        
        # 更新状态和结果
        redis_service.set_score_task_status(task_id, TaskStatus.SUCCESS)
        redis_service.set_score_task_result(task_id, result)
        logger.info(f"评分任务 {task_id} 处理成功")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"评分任务 {task_id} 处理失败：{error_msg}", exc_info=True)
        redis_service.set_score_task_status(task_id, TaskStatus.FAILED)
        redis_service.set_score_task_result(task_id, {
            "retCode": "9999",
            "retMessage": error_msg,
            "criteria": []
        })
    finally:
        logger.debug(f"清理临时文件: {file_path}")
        file_service.clean_temp_files(file_path)

def run_score_consumer() -> None:
    """评分任务消费者进程"""
    logger.info("评分任务消费者启动，等待任务...")
    while True:
        try:
            logger.debug("尝试从Redis队列获取评分任务")
            task = redis_service.get_next_score_task()
            if not task:
                logger.debug("未获取到评分任务，等待1秒重试")
                time.sleep(1)
                continue
            
            logger.info(f"接收到评分任务：{task['task_id']} (bid: {task['bid']})")
            process_score_task(task)
        except Exception as e:
            logger.error(f"评分任务消费者异常：{str(e)}", exc_info=True)
            time.sleep(5)