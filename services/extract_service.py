# -*- coding: utf-8 -*-
'''信息提取服务：调用API解析文本内容'''
import os
import json
import requests
import re
from json import JSONDecodeError
from config import EXTRACT_API_URL, DB_STRUCT_PATH, EXTRACT_API_URL
# 在文件顶部导入logging模块（如果已有则忽略）
import logging
from logging.handlers import RotatingFileHandler

# 在类定义之前添加日志配置
# 确保日志目录存在
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志格式
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 设置日志文件（按大小切割，最多保留5个备份）
log_file = os.path.join(log_dir, "extract_service.log")
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=1024 * 1024 * 5,  # 5MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(log_format)
file_handler.setLevel(logging.INFO)

# 获取logger并添加处理器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# 如果需要同时在控制台输出日志，可以添加StreamHandler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)

class ExtractService:
    @staticmethod
    def extract_base_info(pdf_content: str) -> dict:
        """提取基础招标信息（优化版：先经Qwen处理PDF内容）"""
        logger.info("=== 开始执行基础招标信息提取流程 ===")
        try:
            # 1. 调用Qwen预处理PDF内容
            logger.info("准备调用Qwen API进行PDF内容预处理")
            qwen_payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""请帮我从提供的文件中提取指定信息，并按照以下结构化格式返回结果。具体要求如下：

                        1. 整体结构：返回内容需包含1个状态信息和3个字典（Dict），分别为"返回状态"、"projectInfo"、"bidContactInfo"、"bidBond"，每个部分包含对应的字段。

                        2. 各字段详细要求：
                        - 返回状态：
                            - retCode：字符串类型，取值范围为"0000"（返回成功）、"0001"（解析中）、"9999"（解释失败），示例："0000"
                            - retMessage：字符串类型，用于说明错误原因，若返回成功则留空，示例：""

                        - projectInfo（项目信息）：
                            - projectCode：字符串类型，必填项，示例："2024-JL05-W1813"
                            - projectName：字符串类型，必填项，示例："智能化管控及信息化设备"
                            - customerName：字符串类型，非必填项，示例："中国解放军陆军工程大学"
                            - bidOpenTime：字符串类型，格式为"YYYY-MM-DD HH24:MM:SS"，示例："2025-02-09 09:00:00"
                            - bidDeadlineTime：字符串类型，格式同上，示例："2025-02-09 09:00:00"
                            - bidAddress：字符串类型，示例："江苏徐州"
                            - budgetAmount：十进制数类型，保留两位小数（去除千位分隔符），示例："3970000.00"

                        - bidContactInfo（招标联系方式）：
                            - bidAgentOrg：字符串类型
                            - agentContactPerson：字符串类型
                            - agentContactPhone：字符串类型

                        - bidBond（投标保证金）：
                            - bondAccountNumber：字符串类型
                            - bondAccountName：字符串类型
                            - bondAccountBranch：字符串类型
                            - bondAmount：十进制数类型，保留两位小数（去除千位分隔符），示例："450000.00"
                            - bondDeadlineTime：字符串类型，格式为"YYYY-MM-DD HH24:MM:SS"

                        3. 补充说明：
                        - 若文件中无对应信息，该字段留空即可
                        - 请严格按照上述格式（包括字段名称、类型、格式要求）返回，避免遗漏或格式错误

                        请处理以下PDF文件内容,返回符合要求的结构化数据，不要多余的内容：
                        {pdf_content}"""
                    }
                ],
                "stream": False
            }
            
            qwen_headers = {"Content-Type": "application/json"}
            logger.info(f"向Qwen API发送请求，URL: {EXTRACT_API_URL}")
            qwen_response = requests.post(EXTRACT_API_URL, headers=qwen_headers, data=json.dumps(qwen_payload))
            qwen_response.raise_for_status()
            logger.info("Qwen API请求成功，状态码: %d", qwen_response.status_code)
            
            # 解析Qwen返回结果
            logger.info("开始解析Qwen返回结果")
            qwen_result = qwen_response.json()["choices"][0]["message"]["content"].strip()
            qwen_result = qwen_result.replace("```json", "").replace("```", "").strip()
            # processed_content = json.loads(qwen_result)
            # 新增：用正则提取首个完整JSON对象（处理多余内容）
            json_pattern = r'\{.*\}'  # 匹配最外层的{}包裹的内容
            match = re.search(json_pattern, qwen_result, re.DOTALL)  # re.DOTALL让.匹配换行符
            if not match:
                raise Exception("Qwen返回结果中未找到有效的JSON内容")
            cleaned_json_str = match.group(0)

            # 新增：尝试解析并捕获错误
            try:
                processed_content = json.loads(cleaned_json_str)
            except JSONDecodeError as e:
                # 输出错误详情和原始内容，方便调试
                logger.error(f"Qwen返回JSON解析失败：{str(e)}，原始内容：{cleaned_json_str[:500]}...")
                raise Exception(f"Qwen返回结果格式错误：{str(e)}")
            logger.info("Qwen返回结果解析完成，获取预处理数据")

            # 检查Qwen处理状态
            ret_code = processed_content.get("返回状态", {}).get("retCode")
            logger.info(f"Qwen处理状态码: {ret_code}")
            if ret_code != "0000":
                error_msg = processed_content.get("retMessage", "未知错误")
                logger.error(f"Qwen处理失败，错误信息: {error_msg}")
                raise Exception(f"Qwen处理失败：{error_msg}")
            
            # 2. 使用处理后的内容调用提取API
            logger.info("准备调用提取API进行二次处理")
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""请帮我从提供的内容中提取指定信息，并按照以下结构化格式返回结果：
                        【提取要求】
                        1. 整体结构：包含"返回状态"、"projectInfo"、"bidContactInfo"、"bidBond"
                        2. 各字段详细要求：
                        - 返回状态：retCode（"0000"/"0001"/"9999"）、retMessage
                        - projectInfo：projectCode、projectName、customerName、bidOpenTime（YYYY-MM-DD HH24:MM:SS）、bidDeadlineTime、bidAddress、budgetAmount（两位小数）
                        - bidContactInfo：bidAgentOrg、agentContactPerson、agentContactPhone
                        - bidBond：bondAccountNumber、bondAccountName、bondAccountBranch、bondAmount（两位小数）、bondDeadlineTime
                        3. 补充说明：无信息则字段留空，严格按格式返回

                        【处理后的内容】
                        {json.dumps(processed_content)}"""
                    }
                ],
                "stream": False
            }
            
            headers = {"Content-Type": "application/json"}
            logger.info(f"向提取API发送请求，URL: {EXTRACT_API_URL}")
            response = requests.post(EXTRACT_API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            logger.info("提取API请求成功，状态码: %d", response.status_code)
            
            # 解析最终响应
            logger.info("开始解析提取API返回结果")
            core_content = response.json()["choices"][0]["message"]["content"].strip()
            core_content = core_content.replace("```json", "").replace("```", "").strip()
            extracted_data = json.loads(core_content)
            logger.info("提取API返回结果解析完成")
            
            result = {
                "retCode": extracted_data.get("retCode", "0000"),
                "retMessage": extracted_data.get("retMessage", "解析成功"),
                "projectInfo": extracted_data.get("projectInfo", {}),
                "bidContactInfo": extracted_data.get("bidContactInfo", {}),
                "bidBond": extracted_data.get("bidBond", {})
            }
            logger.info(f"基础招标信息提取完成，返回状态: {result['retCode']}")
            return result
            
        except Exception as e:
            logger.error(f"基础信息提取失败：{str(e)}", exc_info=True)
            raise Exception(f"基础信息提取出错：{e}")
        finally:
            logger.info("=== 基础招标信息提取流程结束 ===")
    
    @staticmethod
    def extract_business_score(pdf_content: str) -> dict:
        """提取商务评分标准（优化版：先经Qwen处理PDF内容）"""
        logger.info("=== 开始执行商务评分标准提取流程 ===")
        try:
            # 1. 调用Qwen预处理PDF内容
            logger.info("准备调用Qwen API进行商务评分内容预处理")
            qwen_payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""请帮我从提供的PDF文件中提取商务评分标准相关信息，具体包括但不限于以下可能涉及的方面：
                        - 价格部分的评分规则（如基准价设定、价格偏差对应的分值计算方式等）
                        - 财务状况的评分标准（如注册资本、净资产、盈利能力等指标的评分依据）
                        - 商业信誉的评分细则（如是否有不良记录、获得的荣誉资质等对应的分值）
                        - 履约能力相关的评分标准（如类似项目业绩的数量、规模及对应分值等）

                        请按照以下结构化格式返回结果，不要多余的内容：

                        1. 整体结构：返回内容需包含状态信息和商务评分标准文段，分别为"返回状态"和"scoreCriteria"。

                        2. 各字段详细要求：
                        - 返回状态：
                            - retCode：字符串类型，取值范围为"0000"（返回成功）、"0001"（解析中）、"9999"（解析失败），示例："0000"
                            - retMessage：字符串类型，用于说明错误原因，若返回成功则留空，示例：""

                        - scoreCriteria（商务评分标准文段）：
                            字符串类型，**必须是整合所有维度信息的连贯自然段落**，需包含价格、财务状况、商业信誉、履约能力等各维度的具体评分规则、补充说明、最高分值及评分方法等内容。  
                            ▶ 禁止使用任何结构化格式（如字典、数组、分点、标题、层级划分等），仅以连贯的文字串联所有信息；  
                            ▶ 语言需流畅，逻辑清晰，按维度自然过渡（如“价格部分的评分规则为...；财务状况方面...；商业信誉评分则依据...；履约能力评分主要考察...”）。

                        3. 补充说明：
                        - 若文件中无对应信息，scoreCriteria字段留空即可
                        - 请严格按照上述格式（包括字段名称、类型要求）返回，**尤其确保scoreCriteria为单一连贯段落，无任何结构化元素**

                        请处理以下PDF文件内容，返回符合要求的结构化数据：
                        {pdf_content}"""
                    }
                ],
                "stream": False
            }
            
            qwen_headers = {"Content-Type": "application/json"}
            logger.info(f"向Qwen API发送请求，URL: {EXTRACT_API_URL}")
            qwen_response = requests.post(EXTRACT_API_URL, headers=qwen_headers, data=json.dumps(qwen_payload))
            qwen_response.raise_for_status()
            logger.info("Qwen API请求成功，状态码: %d", qwen_response.status_code)
            
            # 解析Qwen返回结果
            logger.info("开始解析Qwen返回结果")
            qwen_result = qwen_response.json()["choices"][0]["message"]["content"].strip()
            qwen_result = qwen_result.replace("```json", "").replace("```", "").strip()
            # processed_content = json.loads(qwen_result)
            # 新增：用正则提取首个完整JSON对象（处理多余内容）
            json_pattern = r'\{.*\}'  # 匹配最外层的{}包裹的内容
            match = re.search(json_pattern, qwen_result, re.DOTALL)  # re.DOTALL让.匹配换行符
            if not match:
                raise Exception("Qwen返回结果中未找到有效的JSON内容")
            cleaned_json_str = match.group(0)

            # 新增：尝试解析并捕获错误
            try:
                processed_content = json.loads(cleaned_json_str)
            except JSONDecodeError as e:
                # 输出错误详情和原始内容，方便调试
                logger.error(f"Qwen返回JSON解析失败：{str(e)}，原始内容：{cleaned_json_str[:500]}...")
                raise Exception(f"Qwen返回结果格式错误：{str(e)}")
            
            # 检查Qwen处理状态
            ret_code = processed_content.get("返回状态", {}).get("retCode")
            logger.info(f"Qwen处理状态码: {ret_code}")
            if ret_code != "0000":
                error_msg = processed_content.get("retMessage", "未知错误")
                logger.error(f"Qwen处理失败，错误信息: {error_msg}")
                raise Exception(f"Qwen处理失败：{error_msg}")
            
            refined_pdf_content = processed_content.get("scoreCriteria", "")
            logger.info(f"获取预处理后的评分标准内容，长度: {len(refined_pdf_content)}字符")


            # 2. 使用处理后的内容调用提取API
            logger.info("准备调用提取API进行商务评分标准提取")
            example_json = '''{
                                "retCode": "0000",
                                "retMessage": "解析成功",
                                "criteria": [
                                    {
                                    "itemName": "比较合同签订时间在投标（报价）截止时间前三年以内（截止时间前三个月内不计）的主要产品（智能交互屏、录播设备、虚拟化服务器集群）的销售业绩，按销售金额计算。项目合同金额大于400万 ",
                                    "score": 15,
                                    "itemName": "项目业绩",
                                    "quantity": 8,
                                    "TagCondition": [
                                        {
                                        "fieldName": "projectDate",
                                        "judge": "BETWEEN",
                                        "condition": ["2022-07", "2025-7"]
                                        },
                                        {
                                        "fieldName": "projectName",
                                        "judge": "LIKE",
                                        "condition": ["智能交互屏", "录播设备", "虚拟化集群"]
                                        },
                                        {
                                        "fieldName": "projectAmount",
                                        "judge": "GEQ",
                                        "condition": [4000000.00]
                                        }
                                    ]
                                    },
                                    {
                                    "itemName": "涉及国家秘密的计算机信息系统集成资质乙级（含乙级）以上资质、ISO9001、ISO270001",
                                    "score": 10,
                                    "itemName": "公司资质",
                                    "TagCondition": [
                                        {
                                        "fieldName": "projectName",
                                        "judge": "like",
                                        "condition": ["涉及国家秘密的计算机信息系统集成资质乙级", "ISO9001", "ISO270001"]
                                        }
                                    ]
                                    },
                                    {
                                    "itemName": "团队人员要求5人，研究生、具备高级工程师、网络工程师证书、PMP证书",
                                    "score": 10,
                                    "itemName": "人员要求",
                                    "quantity": 5,
                                    "TagCondition": [
                                        {
                                        "fieldName": "certificateName",
                                        "judge": "like",
                                        "condition": ["高级工程师", "网络工程师", "PMP证书"]
                                        }
                                    ]
                                    }
                                ]
                                }'''
            
            # 检查数据库结构文件
            logger.info(f"检查数据库结构文件是否存在: {DB_STRUCT_PATH}")
            if not os.path.exists(DB_STRUCT_PATH):
                logger.error(f"数据库结构文件不存在: {DB_STRUCT_PATH}")
                raise Exception(f"数据库结构文件不存在：{DB_STRUCT_PATH}")
            
            # 读取数据库结构文件
            logger.info("读取数据库结构文件内容")
            with open(DB_STRUCT_PATH, "r", encoding="utf-8") as f:
                db_struct = f.read()
            logger.info(f"数据库结构文件读取完成，内容长度: {len(db_struct)}字符")
            
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""请结合以下数据库表结构信息和PDF文件内容，提取商务评分标准并生成结构化数据：
                        
                        【数据库表结构参考】
                        {db_struct}
                        
                        【提取要求】
                        1. 从PDF中识别所有评分项，每个评分项需包含：
                        - itemName：评分项完整描述（字符串类型）
                        - score：该项分值（数字类型，保留两位小数）
                        - itemTag：业务标签（如"项目业绩"、"公司资质"、"人员要求"等）
                        - quantity：数量要求（无则留空，数字类型）
                        - TagCondition：条件数组，每个条件包含：
                            - fieldName：对应数据库表字段名（需从表结构中匹配，字符串类型）
                            - judge：判断方式（如BETWEEN、LIKE、GEQ、LEQ、EQ等）
                            - condition：条件值数组（根据判断方式填写对应格式值）
                        
                        2. 返回格式示例：
                        {example_json}
                        
                        3. 补充说明：无法匹配字段则fieldName留空，无信息则criteria为空数组
                        
                        【处理后的内容】
                        {refined_pdf_content}"""
                    }
                ],
                "stream": False
            }
            
            headers = {"Content-Type": "application/json"}
            logger.info(f"向提取API发送请求，URL: {EXTRACT_API_URL}")
            response = requests.post(EXTRACT_API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            logger.info("提取API请求成功，状态码: %d", response.status_code)
            
            # 解析最终响应
            logger.info("开始解析提取API返回结果")
            core_content = response.json()["choices"][0]["message"]["content"].strip()
            core_content = core_content.replace("```json", "").replace("```", "").strip()
            extracted_data = json.loads(core_content)
            logger.info("提取API返回结果解析完成")
            
            # 结构校验
            logger.info("对提取结果进行结构校验和修正")
            if "criteria" not in extracted_data:
                extracted_data["criteria"] = []
                logger.info("提取结果中未包含criteria字段，已自动补充为空数组")
            
            for i, item in enumerate(extracted_data["criteria"]):
                for key in ["itemName", "score", "itemTag", "TagCondition"]:
                    if key not in item:
                        item[key] = "" if key != "score" else 0
                        logger.info(f"评分项[{i}]缺少{key}字段，已自动补充默认值")
            
            result = {
                "retCode": extracted_data.get("retCode", "0000"),
                "retMessage": extracted_data.get("retMessage", "解析成功"),
                "criteria": extracted_data.get("criteria", [])
            }
            logger.info(f"商务评分标准提取完成，返回状态: {result['retCode']}，共提取{len(result['criteria'])}项评分标准")
            return result
            
        except Exception as e:
            logger.error(f"商务评分提取失败：{str(e)}", exc_info=True)
            raise Exception(f"商务评分提取出错：{e}")
        finally:
            logger.info("=== 商务评分标准提取流程结束 ===")

    @staticmethod
    def extract_catalogue(pdf_content: str, bid: str) -> dict:
        """提取并结构化目录信息"""
        logger.info("=== 开始执行目录信息提取流程 ===")
        try:
            # 定义目录结构-业务标签对照表
            logger.info("加载目录结构-业务标签对照表")
            official_catalogue_mapping = {
                "附件一：投标函": [],
                "附件二：法定代表人授权书": [],
                "附件三：报价一览表": [],
                "附件四：商务条款偏离表": [],
                "附件五：服务条款偏离表": [],
                "附件六：合同条款偏离表": [],
                "附件七：营业执照": [],
                "附件八：江苏银行开户证明": [],
                "附件九：承诺函": [],
                "附件十：综合实力": ["企业规模", "财务状况", "资质证书", "荣誉奖项"],
                "附件十一：业绩经验": ["项目业绩"],
                "附件十二：项目组成员": ["人员信息"],
                "附件十三：招标业务能力": [],
                "附件十四：自有专家库": [],
                "附件十五：服务方案": ["服务方案"],
                "附件十六：沟通、协调方案": [],
                "附件十七：内部管理制度": [],
                "附件十八：增值服务": [],
                "附件十九：其他材料": [],
                "附件二十：反商业贿赂承诺书": []
            }
            logger.info(f"目录结构-业务标签对照表加载完成，共包含{len(official_catalogue_mapping)}项对照关系")
            
            # 调用Qwen提取并筛选目录
            logger.info("准备调用Qwen API进行目录信息提取")
            qwen_payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""
                        # 任务指令（必须严格执行）
                        基于用户提供的「文件内容」和「标签对应规则」，完成以下操作：
                        1. 筛选：仅提取文件中真实存在的应答/投标相关文件，不虚构、不遗漏；
                        2. 打标：按「标签对应规则」为提取的文件添加业务标签，无匹配标签则填空数组[]；
                        3. 输出：严格按指定JSON格式返回结果，不可添加任何多余文本（如解释、注释）。

                        # 核心参考信息
                        ## 1. 输出格式（固定不可修改）
                        ```json
                        {{
                            "retCode": "0000",
                            "retMessage": "解析成功",
                            "catalogue": [
                                {{
                                    "itemName": "________", // 文件中真实存在的应答文件格式/投标文件格式，不虚构、不遗漏（如“法定代表人/负责人授权委托书”“业绩情况表”）
                                    "itemTag": ["________"] // 仅从“2. 标签对应规则”提取匹配标签，无匹配则填[]
                                }}
                            ]
                        }}
                        ```

                        ## 2. 标签对应规则（唯一依据，不可新增/修改）
                        | 目录结构                | 唯一业务标签                          |
                        |-------------------------|---------------------------------------|
                        | 附件一：投标函          | []                                    |
                        | 附件二：法定代表人授权书| []                                    |
                        | 附件三：报价一览表      | []                                    |
                        | 附件四：商务条款偏离表  | []                                    |
                        | 附件五：服务条款偏离表  | []                                    |
                        | 附件六：合同条款偏离表  | []                                    |
                        | 附件七：营业执照        | []                                    |
                        | 附件八：江苏银行开户证明| []                                    |
                        | 附件九：承诺函          | []                                    |
                        | 附件十：综合实力        | ["企业规模", "财务状况", "资质证书", "荣誉奖项"] |
                        | 附件十一：业绩经验      | ["项目业绩"]                          |
                        | 附件十二：项目组成员    | ["人员信息"]                          |
                        | 附件十三：招标业务能力  | []                                    |
                        | 附件十四：自有专家库    | []                                    |
                        | 附件十五：服务方案      | ["服务方案"]                          |
                        | 附件十六：沟通、协调方案| []                                    |
                        | 附件十七：内部管理制度  | []                                    |
                        | 附件十八：增值服务      | []                                    |
                        | 附件十九：其他材料      | []                                    |
                        | 附件二十：反商业贿赂承诺书| []                                  |

                        ## 3. 提取规则（必须遵守）
                        1. 仅保留文件中真实存在的应答文件格式/投标文件格式目录下的所有内容，不虚构、不遗漏；
                        2. 基于上传文件中「应答文件格式 / 投标文件格式目录下真实存在的全部内容」，完成 “提取文件名称 + 按规则打标”，确保不遗漏任何一个真实存在的 itemName，不虚构未提及的内容；
                        3. “itemName”需完整依据文件内容填写，不得捏造、篡改；
                        4. “itemTag”需准确依据标签对应规则获取，反映文件内容所对应的业务标签，不得遗漏；
                        5. 若单个文件对应多个标签（如“资质证书”属于“附件十：综合实力”），需将所有标签列入“itemTag”；
                        6. 文件中无对应“目录结构”的内容（如“社保缴纳证明”），“itemTag”填[]。

                        ## 4. 错误案例（禁止出现以下情况）
                        - 错误1：将“法定代表人/负责人授权委托书”简写为“法人授权书”；
                        - 错误2：“附件十：综合实力”的itemTag遗漏“荣誉奖项”标签；
                        - 错误3：输出结果中包含“已完成解析”“结果如下”等JSON外多余文字。


                        # 处理文件内容：
                        {pdf_content}"""
                    }
                ],
                "stream": False
            }
            # qwen_payload = {
            #     "messages": [
            #         {
            #             "role": "user",
            #             "content": f"""
            #             # 任务指令（必须严格执行）
            #             基于用户提供的「文件内容」和「目录结构-业务标签对照表」，完成以下操作：
            #             1. 筛选：保留与“附件一至附件二十”名称匹配的目录（允许轻微格式差异，如“附件 1：投标函”→“附件一：投标函”）。必须返回文件内容实际存在的内容；
            #             2. 打标：按对照表为目录添加业务标签（无标签则不包含itemTag字段）；
            #             3. 输出：按指定JSON格式返回，不可添加任何多余文本（如解释、注释）。

            #             # 核心参考信息
            #             ## 1. 目录结构-业务标签对照表
            #             {official_catalogue_mapping}

            #             ## 2. 输出JSON格式规则（字段不可缺失/篡改）
            #             - bidId：固定为 "{bid}"（不可修改）；
            #             - retCode："0000"表示成功，0001表示解析中，9999表示解析失败；
            #             - retMessage：目录有匹配时为"解析成功"，无匹配时为"解析成功（无匹配目录）"；
            #             - catalogue：筛选后的目录数组，每个元素必须包含"itemName"，有标签时添加"itemTag"（完整填写所有标签），无标签时也添加"itemTag"[]。

            #             ## 3. 错误案例（禁止出现以下情况）
            #             - 错误1：将“附件十：综合实力”简写为“综合实力（附件十）”；
            #             - 错误2：“附件十：综合实力”的itemTag遗漏“荣誉奖项”；
            #             - 错误3：输出JSON外包含“已完成”“结果如下”等多余文字。


            #             # 必须返回的JSON示例（仅作格式参考，需替换为实际结果）
            #             {{
            #             "bidId": "{bid}",
            #             "retCode": "0000",
            #             "retMessage": "解析成功",
            #             "catalogue": [
            #                 {{
            #                 "itemName": "附件一：投标函",
            #                 "itemTag": []
            #                 }},
            #                 {{
            #                 "itemName": "附件十：综合实力",
            #                 "itemTag": ["企业规模", "财务状况", "资质证书", "荣誉奖项"]
            #                 }}
            #             ]
            #             }}                      
            #             处理文件内容：
            #             {pdf_content}"""
            #         }
            #     ],
            #     "stream": False
            # }
            
            qwen_headers = {"Content-Type": "application/json"}
            qwen_response = requests.post(EXTRACT_API_URL, headers=qwen_headers, data=json.dumps(qwen_payload))
            qwen_response.raise_for_status()
            
            # 解析Qwen返回结果
            qwen_result = qwen_response.json()["choices"][0]["message"]["content"].strip()
            qwen_result = qwen_result.replace("```json", "").replace("```", "").strip()
            # processed_content = json.loads(qwen_result)
            # 新增：用正则提取首个完整JSON对象（处理多余内容）
            json_pattern = r'\{.*\}'  # 匹配最外层的{}包裹的内容
            match = re.search(json_pattern, qwen_result, re.DOTALL)  # re.DOTALL让.匹配换行符
            if not match:
                raise Exception("Qwen返回结果中未找到有效的JSON内容")
            cleaned_json_str = match.group(0)

            # 新增：尝试解析并捕获错误
            try:
                processed_content = json.loads(cleaned_json_str)
            except JSONDecodeError as e:
                # 输出错误详情和原始内容，方便调试
                logger.error(f"Qwen返回JSON解析失败：{str(e)}，原始内容：{cleaned_json_str[:500]}...")
                raise Exception(f"Qwen返回结果格式错误：{str(e)}")
            
            # 结构校验与修正
            if "catalogue" not in processed_content:
                processed_content["catalogue"] = []
            
            return processed_content
            
        except Exception as e:
            logger.error(f"目录提取失败：{str(e)}")
            raise Exception(f"目录提取出错：{str(e)}")

# 单例实例
extract_service = ExtractService()