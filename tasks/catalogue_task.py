# -*- coding: utf-8 -*-
'''
Descripttion: 
Author: Joe Guo
version: 
Date: 2025-08-20 09:52:14
LastEditors: Joe Guo
LastEditTime: 2025-08-21 08:54:25
'''

'''目录筛选与结构化任务处理逻辑'''
import time
import os  # 新增
from config import logger, TaskStatus
from services.redis_service import redis_service
from services.file_service import file_service
from services.extract_service import extract_service

def process_catalogue_task(task: dict) -> None:
    """处理单个目录任务"""
    task_id = task["task_id"]
    bid = task["bid"]
    file_path = task["file_path"]
    
    try:
        logger.debug(f"进入目录任务处理函数，参数: task_id={task_id}, bid={bid}, file_path={file_path}")
        
        redis_service.set_catalogue_task_status(task_id, TaskStatus.PROCESSING)
        logger.info(f"目录任务 {task_id} 状态更新为: {TaskStatus.PROCESSING}")
        
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
            raise Exception("PDF文本提取失败")
        logger.debug(f"PDF文本提取成功，内容长度: {len(pdf_content)}字符")
        
        # 提取目录结构
        logger.debug(f"开始调用目录提取服务，task_id={task_id}")
        result = extract_service.extract_catalogue(pdf_content, bid)
        logger.debug(f"目录提取完成，目录项数量: {len(result.get('catalogue', []))}")
        
        # 更新状态和结果
        redis_service.set_catalogue_task_status(task_id, TaskStatus.SUCCESS)
        redis_service.set_catalogue_task_result(task_id, result)
        logger.info(f"目录任务 {task_id} 处理成功")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"目录任务 {task_id} 处理失败：{error_msg}", exc_info=True)
        redis_service.set_catalogue_task_status(task_id, TaskStatus.FAILED)
        redis_service.set_catalogue_task_result(task_id, {
            "bidId": bid,
            "retCode": "9999",
            "retMessage": error_msg,
            "catalogue": []
        })
    finally:
        logger.debug(f"清理临时文件: {file_path}")
        file_service.clean_temp_files(file_path)

def run_catalogue_consumer() -> None:
    """目录任务消费者进程"""
    logger.info("目录任务消费者启动，等待任务...")
    while True:
        try:
            logger.debug("尝试从Redis队列获取目录任务")
            task = redis_service.get_next_catalogue_task()
            if not task:
                logger.debug("未获取到目录任务，等待1秒重试")
                time.sleep(1)
                continue
            
            logger.info(f"接收到目录任务：{task['task_id']} (bid: {task['bid']})")
            process_catalogue_task(task)
        except Exception as e:
            logger.error(f"目录任务消费者异常：{str(e)}", exc_info=True)
            time.sleep(5)