'''信息提取服务：调用API解析文本内容'''
import os
import json
import requests
from config import logger, EXTRACT_API_URL, DB_STRUCT_PATH, EXTRACT_API_URL

class ExtractService:
    @staticmethod
    def extract_base_info(pdf_content: str) -> dict:
        """提取基础招标信息（优化版：先经Qwen处理PDF内容）"""
        try:
            # 1. 调用Qwen预处理PDF内容
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
            qwen_response = requests.post(EXTRACT_API_URL, headers=qwen_headers, data=json.dumps(qwen_payload))
            qwen_response.raise_for_status()
            
            # 解析Qwen返回结果
            qwen_result = qwen_response.json()["choices"][0]["message"]["content"].strip()
            qwen_result = qwen_result.replace("```json", "").replace("```", "").strip()
            processed_content = json.loads(qwen_result)

            
            # if processed_content.get("retCode") != "0000":
            if processed_content.get("返回状态", {}).get("retCode") != "0000":
                raise Exception(f"Qwen处理失败：{processed_content.get('retMessage', '未知错误')}")
            
            # 2. 使用处理后的内容调用提取API
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
            response = requests.post(EXTRACT_API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            # 解析最终响应
            core_content = response.json()["choices"][0]["message"]["content"].strip()
            core_content = core_content.replace("```json", "").replace("```", "").strip()
            extracted_data = json.loads(core_content)
            
            return {
                "retCode": extracted_data.get("retCode", "0000"),
                "retMessage": extracted_data.get("retMessage", "解析成功"),
                "projectInfo": extracted_data.get("projectInfo", {}),
                "bidContactInfo": extracted_data.get("bidContactInfo", {}),
                "bidBond": extracted_data.get("bidBond", {})
            }
            
        except Exception as e:
            logger.error(f"基础信息提取失败：{str(e)}")
            raise Exception(f"基础信息提取出错：{e}")
    
    @staticmethod
    def extract_business_score(pdf_content: str) -> dict:
        """提取商务评分标准（优化版：先经Qwen处理PDF内容）"""
        try:
            # 1. 调用Qwen预处理PDF内容
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
            qwen_response = requests.post(EXTRACT_API_URL, headers=qwen_headers, data=json.dumps(qwen_payload))
            qwen_response.raise_for_status()
            
            # 解析Qwen返回结果
            qwen_result = qwen_response.json()["choices"][0]["message"]["content"].strip()
            qwen_result = qwen_result.replace("```json", "").replace("```", "").strip()
            processed_content = json.loads(qwen_result)
            if processed_content.get("返回状态", {}).get("retCode") != "0000":
                raise Exception(f"Qwen处理失败：{processed_content.get('retMessage', '未知错误')}")
            
            refined_pdf_content = processed_content.get("scoreCriteria", "")


            # 2. 使用处理后的内容调用提取API
            example_json = '''{
                                "retCode": "0000",
                                "retMessage": "解析成功",
                                "criteria": [
                                    {
                                    "itemName": "比较合同签订时间在投标（报价）截止时间前三年以内（截止时间前三个月内不计）的主要产品（智能交互屏、录播设备、虚拟化服务器集群）的销售业绩，按销售金额计算。项目合同金额大于400万 ",
                                    "score": 15,
                                    "itemTag": "项目业绩",
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
                                    "itemTag": "公司资质",
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
                                    "itemTag": "人员要求",
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
            
            if not os.path.exists(DB_STRUCT_PATH):
                raise Exception(f"数据库结构文件不存在：{DB_STRUCT_PATH}")
            with open(DB_STRUCT_PATH, "r", encoding="utf-8") as f:
                db_struct = f.read()
            
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
            response = requests.post(EXTRACT_API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            # 解析最终响应
            core_content = response.json()["choices"][0]["message"]["content"].strip()
            core_content = core_content.replace("```json", "").replace("```", "").strip()
            extracted_data = json.loads(core_content)
            
            # 结构校验
            if "criteria" not in extracted_data:
                extracted_data["criteria"] = []
            for item in extracted_data["criteria"]:
                for key in ["itemName", "score", "itemTag", "TagCondition"]:
                    if key not in item:
                        item[key] = "" if key != "score" else 0
            
            return {
                "retCode": extracted_data.get("retCode", "0000"),
                "retMessage": extracted_data.get("retMessage", "解析成功"),
                "criteria": extracted_data.get("criteria", [])
            }
            
        except Exception as e:
            logger.error(f"商务评分提取失败：{str(e)}")
            raise Exception(f"商务评分提取出错：{e}")

# 单例实例
extract_service = ExtractService()