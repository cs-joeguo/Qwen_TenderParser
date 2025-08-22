# -*- coding: utf-8 -*-
'''
Descripttion: 
Author: Joe Guo
version: 
Date: 2025-08-20 09:51:48
LastEditors: Joe Guo
LastEditTime: 2025-08-20 17:45:57
'''

"""目录筛选与结构化服务（基于Qwen预处理）"""
import json
import uuid
import requests
from config import logger, CATALOG_TAG_MAPPING, EXTRACT_API_URL

class CatalogueService:
    @staticmethod
    def process_catalogue(pdf_content: str) -> list:
        """
        使用Qwen预处理PDF内容，实现目录筛选与标签映射
        """
        try:
            # 构造标签映射说明文本
            tag_mapping_desc = "目录结构-业务标签对照表：\n"
            for pattern, tags in CATALOG_TAG_MAPPING.items():
                tag_mapping_desc += f"- 包含'{pattern}'的目录：映射标签{tags}\n"
            
            # 构造Qwen提示词
            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""请帮我从以下PDF内容中处理目录信息，具体要求如下：

                        1. 目录筛选范围：仅保留从"投标函"开始到"反商业贿赂承诺书"结束的所有目录（包括这两个目录），排除此范围外的其他目录。

                        2. 标签映射规则：
                        - 参照提供的标签对照表，为筛选出的目录添加对应的业务标签
                        - 若目录名称与对照表中的模式匹配，则添加对应标签；无匹配则不添加标签
                        - {tag_mapping_desc}

                        3. 输出格式要求：
                        - 返回多层级JSON结构，包含"catalogue"数组，每个目录项需包含：
                            - "id"：唯一标识（字符串，可使用UUID）
                            - "name"：目录名称（字符串）
                            - "parentId"：父目录ID（顶级目录为null）
                            - "tags"：标签数组（无标签则为空数组）
                            - "children"：子目录数组（无则为空数组）
                        - 确保目录层级关系正确，严格遵循原文件的目录结构
                        - 仅返回JSON数据，不要多余解释，不要用代码块包裹

                        请处理以下PDF内容：
                        {pdf_content}"""
                    }
                ],
                "stream": False
            }
            
            # 调用Qwen API
            headers = {"Content-Type": "application/json"}
            response = requests.post(EXTRACT_API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            # 解析结果
            qwen_result = response.json()["choices"][0]["message"]["content"].strip()
            result_data = json.loads(qwen_result)
            
            # 结构校验与修正
            if "catalogue" not in result_data:
                result_data["catalogue"] = []
            
            # 确保所有目录项包含必要字段
            def validate_catalogue_items(items, parent_id=None):
                validated = []
                for item in items:
                    # 生成UUID（若Qwen未提供）
                    item_id = item.get("id") or str(uuid.uuid4())
                    # 补全必要字段
                    validated_item = {
                        "id": item_id,
                        "name": item.get("name", ""),
                        "parentId": parent_id,
                        "tags": item.get("tags", []),
                        "children": validate_catalogue_items(item.get("children", []), item_id)
                    }
                    validated.append(validated_item)
                return validated
            
            return validate_catalogue_items(result_data["catalogue"])
            
        except Exception as e:
            logger.error(f"Qwen目录处理失败：{str(e)}")
            raise Exception(f"目录结构化处理失败：{str(e)}")

catalogue_service = CatalogueService()