# -*- coding: utf-8 -*-
'''Redis操作封装，统一处理Redis交互'''
import json
import uuid
import redis
from config import REDIS_URL, RedisKey, TaskStatus

class RedisService:
    def __init__(self):
        self.client = redis.from_url(REDIS_URL)
    
    @staticmethod
    def generate_task_id() -> str:
        """生成唯一任务ID"""
        return str(uuid.uuid4())
    
    # ------------------------------ 基础任务操作 ------------------------------
    def add_base_task(self, task_id: str, bid: str, file_path: str) -> None:
        """添加基础任务到队列"""
        task_data = {
            "task_id": task_id,
            "bid": bid,
            "file_path": file_path
        }
        self.client.rpush(RedisKey.BASE_TASK_QUEUE, json.dumps(task_data))
        self.client.set(RedisKey.BASE_TASK_BID_MAPPING.format(bid=bid), task_id)
        self.set_base_task_status(task_id, TaskStatus.PENDING)
    
    def get_next_base_task(self) -> dict:
        """获取下一个基础任务"""
        _, task_data = self.client.blpop(RedisKey.BASE_TASK_QUEUE)
        return json.loads(task_data)
    
    def set_base_task_status(self, task_id: str, status: TaskStatus) -> None:
        """设置基础任务状态"""
        self.client.set(RedisKey.BASE_TASK_STATUS.format(task_id=task_id), status.value)
    
    def get_base_task_status(self, task_id: str) -> str:
        """获取基础任务状态"""
        status = self.client.get(RedisKey.BASE_TASK_STATUS.format(task_id=task_id))
        return status.decode() if status else None
    
    def set_base_task_result(self, task_id: str, result: dict) -> None:
        """设置基础任务结果"""
        self.client.set(RedisKey.BASE_TASK_RESULT.format(task_id=task_id), json.dumps(result))
    
    def get_base_task_result(self, task_id: str) -> dict:
        """获取基础任务结果"""
        result = self.client.get(RedisKey.BASE_TASK_RESULT.format(task_id=task_id))
        return json.loads(result) if result else None
    
    def get_base_task_id_by_bid(self, bid: str) -> str:
        """通过bid获取基础任务ID"""
        task_id = self.client.get(RedisKey.BASE_TASK_BID_MAPPING.format(bid=bid))
        return task_id.decode() if task_id else None
    
    # ------------------------------ 评分任务操作 ------------------------------
    def add_score_task(self, task_id: str, bid: str, file_path: str) -> None:
        """添加评分任务到队列"""
        task_data = {
            "task_id": task_id,
            "bid": bid,
            "file_path": file_path
        }
        self.client.rpush(RedisKey.SCORE_TASK_QUEUE, json.dumps(task_data))
        self.client.set(RedisKey.SCORE_TASK_BID_MAPPING.format(bid=bid), task_id)
        self.set_score_task_status(task_id, TaskStatus.PENDING)
    
    def get_next_score_task(self) -> dict:
        """获取下一个评分任务"""
        _, task_data = self.client.blpop(RedisKey.SCORE_TASK_QUEUE)
        return json.loads(task_data)
    
    def set_score_task_status(self, task_id: str, status: TaskStatus) -> None:
        """设置评分任务状态"""
        self.client.set(RedisKey.SCORE_TASK_STATUS.format(task_id=task_id), status.value)
    
    def get_score_task_status(self, task_id: str) -> str:
        """获取评分任务状态"""
        status = self.client.get(RedisKey.SCORE_TASK_STATUS.format(task_id=task_id))
        return status.decode() if status else None
    
    def set_score_task_result(self, task_id: str, result: dict) -> None:
        """设置评分任务结果"""
        self.client.set(RedisKey.SCORE_TASK_RESULT.format(task_id=task_id), json.dumps(result))
    
    def get_score_task_result(self, task_id: str) -> dict:
        """获取评分任务结果"""
        result = self.client.get(RedisKey.SCORE_TASK_RESULT.format(task_id=task_id))
        return json.loads(result) if result else None
    
    def get_score_task_id_by_bid(self, bid: str) -> str:
        """通过bid获取评分任务ID"""
        task_id = self.client.get(RedisKey.SCORE_TASK_BID_MAPPING.format(bid=bid))
        return task_id.decode() if task_id else None


    def add_catalogue_task(self, task_id, bid, file_path):
        """添加目录任务到队列"""
        task_data = {
            "task_id": task_id,
            "bid": bid,
            "file_path": file_path
        }
        # 引用RedisKey的目录任务键（替换原CATALOGUE_TASK_QUEUE_KEY）
        self.client.rpush(RedisKey.CATALOGUE_TASK_QUEUE, json.dumps(task_data))
        self.client.set(RedisKey.CATALOGUE_TASK_BID_MAPPING.format(bid=bid), task_id)
        self.set_catalogue_task_status(task_id, TaskStatus.PENDING)

    def get_next_catalogue_task(self):
        """获取下一个目录任务"""
        # 引用RedisKey的目录任务键（替换原CATALOGUE_TASK_QUEUE_KEY）
        _, task_data = self.client.blpop(RedisKey.CATALOGUE_TASK_QUEUE)
        return json.loads(task_data)

    def set_catalogue_task_status(self, task_id, status):
        """设置目录任务状态"""
        # 引用RedisKey的目录任务键（替换原CATALOGUE_TASK_STATUS_KEY）
        self.client.set(RedisKey.CATALOGUE_TASK_STATUS.format(task_id=task_id), status.value)

    def get_catalogue_task_status(self, task_id):
        """获取目录任务状态"""
        # 引用RedisKey的目录任务键（替换原CATALOGUE_TASK_STATUS_KEY）
        status = self.client.get(RedisKey.CATALOGUE_TASK_STATUS.format(task_id=task_id))
        return status.decode() if status else None

    def set_catalogue_task_result(self, task_id, result):
        """设置目录任务结果"""
        # 引用RedisKey的目录任务键（替换原CATALOGUE_TASK_RESULT_KEY）
        self.client.set(RedisKey.CATALOGUE_TASK_RESULT.format(task_id=task_id), json.dumps(result))

    def get_catalogue_task_result(self, task_id):
        """获取目录任务结果"""
        # 引用RedisKey的目录任务键（替换原CATALOGUE_TASK_RESULT_KEY）
        result = self.client.get(RedisKey.CATALOGUE_TASK_RESULT.format(task_id=task_id))
        return json.loads(result) if result else None

    def get_catalogue_task_id_by_bid(self, bid):
        """通过bid获取目录任务ID"""
        # 引用RedisKey的目录任务键（替换原CATALOGUE_TASK_BID_MAPPING）
        task_id = self.client.get(RedisKey.CATALOGUE_TASK_BID_MAPPING.format(bid=bid))
        return task_id.decode() if task_id else None

# 单例实例
redis_service = RedisService()