import requests
import os
import time
import json

# API基础地址（根据实际部署情况修改）
BASE_URL = "http://localhost:8000"

def submit_base_task(bid: str, file_path: str) -> dict:
    """提交基础招标信息处理任务（POST接口）"""
    url = f"{BASE_URL}/api/base_tasks"
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return {"success": False, "message": f"文件不存在: {file_path}"}
    
    # 构造表单数据
    files = {"file": open(file_path, "rb")}
    data = {"bid": bid}
    
    try:
        response = requests.post(url, data=data, files=files, timeout=30)
        response.raise_for_status()  # 抛出HTTP错误
        result = response.json()
        return {"success": True, "data": result}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"提交任务失败: {str(e)}"}
    finally:
        files["file"].close()

def get_base_result(bid: str) -> dict:
    """查询基础招标信息任务结果（GET接口）"""
    url = f"{BASE_URL}/api/base_results"
    params = {"bid": bid}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"查询结果失败: {str(e)}"}

def submit_score_task(bid: str, file_path: str) -> dict:
    """提交商务评分标准处理任务（POST接口）"""
    url = f"{BASE_URL}/api/business_score_tasks"
    
    if not os.path.exists(file_path):
        return {"success": False, "message": f"文件不存在: {file_path}"}
    
    files = {"file": open(file_path, "rb")}
    data = {"bid": bid}
    
    try:
        response = requests.post(url, data=data, files=files, timeout=30)
        response.raise_for_status()
        result = response.json()
        return {"success": True, "data": result}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"提交任务失败: {str(e)}"}
    finally:
        files["file"].close()

def get_score_result(bid: str) -> dict:
    """查询商务评分标准任务结果（GET接口）"""
    url = f"{BASE_URL}/api/business_score_results"
    params = {"bid": bid}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"查询结果失败: {str(e)}"}

def main():
    # 示例：处理基础招标信息任务
    base_bid = "BID20250815001"
    base_file = "demo/招标文件.docx"  # 替换为实际文件路径
    
    print("=== 提交基础招标信息任务 ===")
    submit_result = submit_base_task(base_bid, base_file)
    if not submit_result["success"]:
        print(submit_result["message"])
        return
    
    print(f"任务提交成功: {json.dumps(submit_result['data'], indent=2)}")
    task_id = submit_result["data"]["task_id"]
    
    # 轮询查询结果（实际使用时可调整间隔）
    print("\n=== 等待基础任务处理完成 ===")
    while True:
        result = get_base_result(base_bid)
        if not result["success"]:
            print(result["message"])
            break
        
        data = result["data"]
        print(f"当前状态: {data.get('retCode')} - {data.get('retMessage')}")
        
        if data.get("retCode") == "0000":  # 成功状态
            print("处理结果:")
            print(json.dumps(data, indent=2))
            break
        elif data.get("retCode") == "9999":  # 失败状态
            print("处理失败:", data.get("retMessage"))
            break
        
        time.sleep(5)  # 5秒查询一次
    
    # 示例：处理商务评分标准任务
    score_bid = "BID20250815002"
    score_file = "demo/招标文件.docx"  # 替换为实际文件路径
    
    print("\n=== 提交商务评分标准任务 ===")
    submit_result = submit_score_task(score_bid, score_file)
    if not submit_result["success"]:
        print(submit_result["message"])
        return
    
    print(f"任务提交成功: {json.dumps(submit_result['data'], indent=2)}")
    
    # 轮询查询结果
    print("\n=== 等待评分任务处理完成 ===")
    while True:
        result = get_score_result(score_bid)
        if not result["success"]:
            print(result["message"])
            break
        
        data = result["data"]
        print(f"当前状态: {data.get('retCode')} - {data.get('retMessage')}")
        
        if data.get("retCode") == "0000":  # 成功状态
            print("处理结果:")
            print(json.dumps(data, indent=2))
            break
        elif data.get("retCode") == "9999":  # 失败状态
            print("处理失败:", data.get("retMessage"))
            break
        
        time.sleep(5)

if __name__ == "__main__":
    main()