import requests

url = "http://10.218.11.219:9000/audit/2025-08-14/20250814/test0506.doc_1755142086365.doc"

try:
    # 发送GET请求，设置超时时间为10秒
    response = requests.get(url, timeout=10)
    # 打印响应状态码，200表示请求成功
    print(f"请求状态码：{response.status_code}")
    if response.status_code == 200:
        print("URL可成功调用")
    else:
        print(f"URL调用失败，状态码：{response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"调用URL时发生错误：{e}")