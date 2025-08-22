'''
Descripttion: 
Author: Joe Guo
version: 
Date: 2025-08-20 09:51:35
LastEditors: Joe Guo
LastEditTime: 2025-08-21 15:07:56
'''
# -*- coding: utf-8 -*-
'''目录筛选与结构化任务API路由'''
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from config import SUPPORTED_EXTENSIONS, TEMP_DIR, TaskStatus
from services.redis_service import redis_service

catalogue_router = APIRouter(tags=["目录筛选与结构化任务"])

@catalogue_router.post("/bidAnalysis/bidCatalogue", summary="提交目录筛选与结构化处理任务")
async def create_catalogue_task(
    bid: str = Form(..., description="投标编号"),
    file: UploadFile = File(..., description="待处理文件")
):
    existing_task_id = redis_service.get_score_task_id_by_bid(bid)
    if existing_task_id:
        existing_status = redis_service.get_score_task_status(existing_task_id)
        if existing_status in [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]:
            raise HTTPException(
                status_code=400,
                detail=f"该投标编号（{bid}）已有任务在处理中（任务ID: {existing_task_id}），请稍后再试"
            )
    
    # 校验文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，支持：{SUPPORTED_EXTENSIONS}"
        )
    
    try:
        # 保存临时文件
        task_id = redis_service.generate_task_id()
        file_path = os.path.join(TEMP_DIR.name, f"{bid}_{task_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 创建任务
        redis_service.add_catalogue_task(task_id, bid, file_path)
        
        return JSONResponse({
            "task_id": task_id,
            "bidId": bid,
            "status": TaskStatus.PENDING.value,
            "message": "目录筛选任务已提交"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"创建目录任务失败：{str(e)}"}
        )

@catalogue_router.get("/bidAnalysis/bidCatalogue/result", summary="查询目录筛选任务结果")
async def get_catalogue_result(bid: str):
    task_id = redis_service.get_catalogue_task_id_by_bid(bid)
    if not task_id:
        raise HTTPException(status_code=404, detail="未找到该bid的目录任务")
    
    status = redis_service.get_catalogue_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="目录任务状态不存在")
    
    if status == TaskStatus.SUCCESS.value:
        result = redis_service.get_catalogue_task_result(task_id)
        if result:
            return JSONResponse(result)
    
    # 处理中或失败状态
    result = redis_service.get_catalogue_task_result(task_id) or {}
    return JSONResponse({
        "bidId": bid,
        "retCode": "0001" if status == TaskStatus.PROCESSING.value else "9999",
        "retMessage": "解析中" if status == TaskStatus.PROCESSING.value else result.get("retMessage", "解析失败"),
        "catalogue": []
    })