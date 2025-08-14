'''商务评分标准任务API路由'''
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from config import SUPPORTED_EXTENSIONS, TEMP_DIR, TaskStatus
from services.redis_service import redis_service

score_router = APIRouter(tags=["商务评分标准任务"])

@score_router.post("/api/business_score_tasks", summary="提交商务评分标准处理任务")
async def create_score_task(
    bid: str = Form(..., description="投标编号"),
    file: UploadFile = File(..., description="待处理文件")
):
    # 校验文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，支持：{SUPPORTED_EXTENSIONS}"
        )
    
    try:
        # 保存临时文件（加入task_id避免重名）
        task_id = redis_service.generate_task_id()
        file_path = os.path.join(TEMP_DIR.name, f"{bid}_{task_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 创建任务
        redis_service.add_score_task(task_id, bid, file_path)
        
        return JSONResponse({
            "task_id": task_id,
            "bid": bid,
            "status": TaskStatus.PENDING.value,
            "message": "商务评分任务已提交"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"创建评分任务失败：{str(e)}"}
        )

@score_router.get("/api/business_score_results", summary="查询商务评分任务结果")
async def get_score_result(bid: str):
    task_id = redis_service.get_score_task_id_by_bid(bid)
    if not task_id:
        raise HTTPException(status_code=404, detail="未找到该bid的评分任务")
    
    status = redis_service.get_score_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="评分任务状态不存在")
    
    if status == TaskStatus.SUCCESS.value:
        result = redis_service.get_score_task_result(task_id)
        if result:
            return JSONResponse(result)
    
    # 处理中或失败状态
    result = redis_service.get_score_task_result(task_id) or {}
    return JSONResponse({
        "retCode": "0001" if status == TaskStatus.PROCESSING.value else "9999",
        "retMessage": "解析中" if status == TaskStatus.PROCESSING.value else result.get("retMessage", "解析失败"),
        "criteria": []
    })