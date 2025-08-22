# -*- coding: utf-8 -*-
'''Redis操作封装，统一处理Redis交互'''
import json
import uuid
import redis
from config import REDIS_URL, RedisKey, TaskStatus, logger

class RedisService:
    def __init__(self):
        logger.info("初始化RedisService连接")
        self.client = redis.from_url(REDIS_URL)
        # 验证连接
        try:
            self.client.ping()
            logger.info(f"成功连接到Redis服务器: {REDIS_URL}")
        except Exception as e:
            logger.error(f"Redis连接失败: {str(e)}", exc_info=True)
            raise
    
    @staticmethod
    def generate_task_id() -> str:
        """生成唯一任务ID"""
        task_id = str(uuid.uuid4())
        logger.info(f"生成新任务ID: {task_id}")
        return task_id
    
    # ------------------------------ 基础任务操作 ------------------------------
    def add_base_task(self, task_id: str, bid: str, file_path: str) -> None:
        """添加基础任务到队列"""
        logger.info(f"添加基础任务，task_id: {task_id}, bid: {bid}, file_path: {file_path}")
        task_data = {
            "task_id": task_id,
            "bid": bid,
            "file_path": file_path
        }
        self.client.rpush(RedisKey.BASE_TASK_QUEUE, json.dumps(task_data))
        self.client.set(RedisKey.BASE_TASK_BID_MAPPING.format(bid=bid), task_id)
        self.set_base_task_status(task_id, TaskStatus.PENDING)
        logger.info(f"基础任务{task_id}已添加到队列: {RedisKey.BASE_TASK_QUEUE}")
    
    def get_next_base_task(self) -> dict:
        """获取下一个基础任务"""
        logger.info(f"从队列{RedisKey.BASE_TASK_QUEUE}获取下一个基础任务")
        _, task_data = self.client.blpop(RedisKey.BASE_TASK_QUEUE)
        task = json.loads(task_data)
        logger.info(f"获取到基础任务: {task['task_id']} (bid: {task['bid']})")
        return task
    
    def set_base_task_status(self, task_id: str, status: TaskStatus) -> None:
        """设置基础任务状态"""
        logger.info(f"更新基础任务状态，task_id: {task_id}, 状态: {status.value}")
        self.client.set(RedisKey.BASE_TASK_STATUS.format(task_id=task_id), status.value)
        logger.info(f"基础任务{task_id}状态已更新为{status.value}")
    
    def get_base_task_status(self, task_id: str) -> str:
        """获取基础任务状态"""
        logger.info(f"查询基础任务状态，task_id: {task_id}")
        status = self.client.get(RedisKey.BASE_TASK_STATUS.format(task_id=task_id))
        status_str = status.decode() if status else None
        logger.info(f"基础任务{task_id}当前状态: {status_str}")
        return status_str
    
    def set_base_task_result(self, task_id: str, result: dict) -> None:
        """设置基础任务结果"""
        logger.info(f"保存基础任务结果，task_id: {task_id}")
        logger.info(f"基础任务{task_id}结果摘要: {json.dumps(result)[:500]}...")  # 只显示前500字符
        self.client.set(RedisKey.BASE_TASK_RESULT.format(task_id=task_id), json.dumps(result))
        logger.info(f"基础任务{task_id}结果已保存")
    
    def get_base_task_result(self, task_id: str) -> dict:
        """获取基础任务结果"""
        logger.info(f"查询基础任务结果，task_id: {task_id}")
        result = self.client.get(RedisKey.BASE_TASK_RESULT.format(task_id=task_id))
        result_dict = json.loads(result) if result else None
        logger.info(f"基础任务{task_id}结果查询完成，是否存在: {result is not None}")
        return result_dict
    
    def get_base_task_id_by_bid(self, bid: str) -> str:
        """通过bid获取基础任务ID"""
        logger.info(f"通过bid查询基础任务ID，bid: {bid}")
        task_id = self.client.get(RedisKey.BASE_TASK_BID_MAPPING.format(bid=bid))
        task_id_str = task_id.decode() if task_id else None
        logger.info(f"bid{bid}对应的基础任务ID: {task_id_str}")
        return task_id_str
    
    # ------------------------------ 评分任务操作 ------------------------------
    def add_score_task(self, task_id: str, bid: str, file_path: str) -> None:
        """添加评分任务到队列"""
        logger.info(f"添加评分任务，task_id: {task_id}, bid: {bid}, file_path: {file_path}")
        task_data = {
            "task_id": task_id,
            "bid": bid,
            "file_path": file_path
        }
        self.client.rpush(RedisKey.SCORE_TASK_QUEUE, json.dumps(task_data))
        self.client.set(RedisKey.SCORE_TASK_BID_MAPPING.format(bid=bid), task_id)
        self.set_score_task_status(task_id, TaskStatus.PENDING)
        logger.info(f"评分任务{task_id}已添加到队列: {RedisKey.SCORE_TASK_QUEUE}")
    
    def get_next_score_task(self) -> dict:
        """获取下一个评分任务"""
        logger.info(f"从队列{RedisKey.SCORE_TASK_QUEUE}获取下一个评分任务")
        _, task_data = self.client.blpop(RedisKey.SCORE_TASK_QUEUE)
        task = json.loads(task_data)
        logger.info(f"获取到评分任务: {task['task_id']} (bid: {task['bid']})")
        return task
    
    def set_score_task_status(self, task_id: str, status: TaskStatus) -> None:
        """设置评分任务状态"""
        logger.info(f"更新评分任务状态，task_id: {task_id}, 状态: {status.value}")
        self.client.set(RedisKey.SCORE_TASK_STATUS.format(task_id=task_id), status.value)
        logger.info(f"评分任务{task_id}状态已更新为{status.value}")
    
    def get_score_task_status(self, task_id: str) -> str:
        """获取评分任务状态"""
        logger.info(f"查询评分任务状态，task_id: {task_id}")
        status = self.client.get(RedisKey.SCORE_TASK_STATUS.format(task_id=task_id))
        status_str = status.decode() if status else None
        logger.info(f"评分任务{task_id}当前状态: {status_str}")
        return status_str
    
    def set_score_task_result(self, task_id: str, result: dict) -> None:
        """设置评分任务结果"""
        logger.info(f"保存评分任务结果，task_id: {task_id}")
        logger.info(f"评分任务{task_id}结果摘要: {json.dumps(result)[:500]}...")
        self.client.set(RedisKey.SCORE_TASK_RESULT.format(task_id=task_id), json.dumps(result))
        logger.info(f"评分任务{task_id}结果已保存")
    
    def get_score_task_result(self, task_id: str) -> dict:
        """获取评分任务结果"""
        logger.info(f"查询评分任务结果，task_id: {task_id}")
        result = self.client.get(RedisKey.SCORE_TASK_RESULT.format(task_id=task_id))
        result_dict = json.loads(result) if result else None
        logger.info(f"评分任务{task_id}结果查询完成，是否存在: {result is not None}")
        return result_dict
    
    def get_score_task_id_by_bid(self, bid: str) -> str:
        """通过bid获取评分任务ID"""
        logger.info(f"通过bid查询评分任务ID，bid: {bid}")
        task_id = self.client.get(RedisKey.SCORE_TASK_BID_MAPPING.format(bid=bid))
        task_id_str = task_id.decode() if task_id else None
        logger.info(f"bid{bid}对应的评分任务ID: {task_id_str}")
        return task_id_str


    def add_catalogue_task(self, task_id, bid, file_path):
        """添加目录任务到队列"""
        logger.info(f"添加目录任务，task_id: {task_id}, bid: {bid}, file_path: {file_path}")
        task_data = {
            "task_id": task_id,
            "bid": bid,
            "file_path": file_path
        }
        self.client.rpush(RedisKey.CATALOGUE_TASK_QUEUE, json.dumps(task_data))
        self.client.set(RedisKey.CATALOGUE_TASK_BID_MAPPING.format(bid=bid), task_id)
        self.set_catalogue_task_status(task_id, TaskStatus.PENDING)
        logger.info(f"目录任务{task_id}已添加到队列: {RedisKey.CATALOGUE_TASK_QUEUE}")

    def get_next_catalogue_task(self):
        """获取下一个目录任务"""
        logger.info(f"从队列{RedisKey.CATALOGUE_TASK_QUEUE}获取下一个目录任务")
        _, task_data = self.client.blpop(RedisKey.CATALOGUE_TASK_QUEUE)
        task = json.loads(task_data)
        logger.info(f"获取到目录任务: {task['task_id']} (bid: {task['bid']})")
        return task

    def set_catalogue_task_status(self, task_id, status):
        """设置目录任务状态"""
        logger.info(f"更新目录任务状态，task_id: {task_id}, 状态: {status.value}")
        self.client.set(RedisKey.CATALOGUE_TASK_STATUS.format(task_id=task_id), status.value)
        logger.info(f"目录任务{task_id}状态已更新为{status.value}")

    def get_catalogue_task_status(self, task_id):
        """获取目录任务状态"""
        logger.info(f"查询目录任务状态，task_id: {task_id}")
        status = self.client.get(RedisKey.CATALOGUE_TASK_STATUS.format(task_id=task_id))
        status_str = status.decode() if status else None
        logger.info(f"目录任务{task_id}当前状态: {status_str}")
        return status_str

    def set_catalogue_task_result(self, task_id, result):
        """设置目录任务结果"""
        logger.info(f"保存目录任务结果，task_id: {task_id}")
        logger.info(f"目录任务{task_id}结果摘要: {json.dumps(result)[:500]}...")
        self.client.set(RedisKey.CATALOGUE_TASK_RESULT.format(task_id=task_id), json.dumps(result))
        logger.info(f"目录任务{task_id}结果已保存")

    def get_catalogue_task_result(self, task_id):
        """获取目录任务结果"""
        logger.info(f"查询目录任务结果，task_id: {task_id}")
        result = self.client.get(RedisKey.CATALOGUE_TASK_RESULT.format(task_id=task_id))
        result_dict = json.loads(result) if result else None
        logger.info(f"目录任务{task_id}结果查询完成，是否存在: {result is not None}")
        return result_dict

    def get_catalogue_task_id_by_bid(self, bid):
        """通过bid获取目录任务ID"""
        logger.info(f"通过bid查询目录任务ID，bid: {bid}")
        task_id = self.client.get(RedisKey.CATALOGUE_TASK_BID_MAPPING.format(bid=bid))
        task_id_str = task_id.decode() if task_id else None
        logger.info(f"bid{bid}对应的目录任务ID: {task_id_str}")
        return task_id_str

# 单例实例
redis_service = RedisService()