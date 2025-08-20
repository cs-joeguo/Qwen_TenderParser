# -*- coding: utf-8 -*-
'''应用入口：启动API服务和任务消费者'''
from fastapi import FastAPI
from multiprocessing import Process
import uvicorn
from routes.base_task_routes import base_router
from routes.score_task_routes import score_router
from routes.catalogue_task_routes import catalogue_router
from tasks.base_task import run_base_consumer
from tasks.score_task import run_score_consumer
from tasks.catalogue_task import run_catalogue_consumer
from config import logger

# 初始化FastAPI应用
app = FastAPI(title="招标信息处理服务")

# 注册路由
app.include_router(base_router)
app.include_router(score_router)
app.include_router(catalogue_router)

if __name__ == "__main__":
    # 启动基础任务消费者
    base_consumer = Process(target=run_base_consumer, daemon=True)
    base_consumer.start()
    logger.info("基础任务消费者进程启动")
    
    # 启动评分任务消费者
    score_consumer = Process(target=run_score_consumer, daemon=True)
    score_consumer.start()
    logger.info("评分任务消费者进程启动")

    # 启动目录任务消费者
    catalogue_consumer = Process(target=run_catalogue_consumer, daemon=True)
    catalogue_consumer.start()
    logger.info("目录任务消费者进程启动")

    # 启动API服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
