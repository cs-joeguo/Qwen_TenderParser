# -*- coding: utf-8 -*-
'''文件处理工具：格式转换、文本提取等'''
import os
import subprocess
import sys
import pdfplumber
from config import logger

class FileService:
    @staticmethod
    def get_default_libreoffice_path() -> str:
        """根据操作系统获取默认的LibreOffice可执行文件路径"""
        logger.info("获取默认LibreOffice路径")
        os_name = sys.platform
        logger.debug(f"当前操作系统: {os_name}")
        
        if os_name.startswith('win'):
            logger.debug("检测到Windows系统，搜索可能的LibreOffice路径")
            possible_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    logger.info(f"找到Windows系统LibreOffice路径: {path}")
                    return path
            logger.warning("未找到Windows系统默认LibreOffice路径，将依赖环境变量")
            return "soffice.exe"
        
        elif os_name.startswith('darwin'):
            logger.debug("检测到macOS系统，检查默认路径")
            default_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
            if os.path.exists(default_path):
                logger.info(f"找到macOS系统LibreOffice路径: {default_path}")
                return default_path
            logger.warning("未找到macOS系统默认LibreOffice路径，将依赖环境变量")
            return "soffice"
        
        else:
            logger.debug("检测到Linux/CentOS系统，使用系统默认命令")
            return "libreoffice"

    @staticmethod
    def convert_to_pdf(file_path: str, libreoffice_path: str = None, max_retries: int = 2) -> str:
        """将文件转换为PDF（增强版：含重试机制和进程清理）"""
        try:
            logger.info(f"开始转换文件为PDF，源文件: {file_path}")
            file_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            pdf_path = os.path.join(file_dir, f"{file_name}.pdf")
            logger.debug(f"目标PDF路径: {pdf_path}")
            
            # 处理LibreOffice路径
            exec_path = libreoffice_path or FileService.get_default_libreoffice_path()
            logger.debug(f"使用的LibreOffice路径: {exec_path}")
            
            # 构造转换命令
            cmd = [
                exec_path,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", file_dir,
                file_path
            ]
            logger.debug(f"转换命令: {' '.join(cmd)}")
            
            # Windows下隐藏控制台窗口
            startupinfo = None
            if sys.platform.startswith('win'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                logger.debug("Windows系统：已设置隐藏控制台窗口")

            # 重试逻辑
            for retry in range(max_retries + 1):
                try:
                    # 执行转换命令（设置超时防止进程挂起）
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        startupinfo=startupinfo,
                        timeout=120  # 2分钟超时
                    )

                    # 检查返回码
                    if result.returncode != 0:
                        logger.warning(
                            f"第{retry+1}次转换失败（返回码: {result.returncode}），"
                            f"错误输出: {result.stderr[:500]}"  # 截断长错误信息
                        )
                        # 若未到最大重试次数，清理残留进程后重试
                        if retry < max_retries:
                            FileService._clean_libreoffice_processes()
                            time.sleep(3)  # 等待3秒释放资源
                            continue
                        else:
                            logger.error("已达最大重试次数，转换失败")
                            return None

                    # 验证PDF文件是否生成
                    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                        file_size = os.path.getsize(pdf_path) / 1024  # KB
                        logger.info(
                            f"PDF转换成功（第{retry+1}次尝试），"
                            f"文件路径: {pdf_path}，大小: {file_size:.2f}KB"
                        )
                        return pdf_path
                    else:
                        logger.warning(
                            f"第{retry+1}次转换未生成有效PDF文件，"
                            f"路径: {pdf_path}（{'不存在' if not os.path.exists(pdf_path) else '空文件'}）"
                        )
                        if retry < max_retries:
                            FileService._clean_libreoffice_processes()
                            time.sleep(3)
                            continue
                        else:
                            logger.error("已达最大重试次数，未生成有效PDF")
                            return None

                except subprocess.TimeoutExpired:
                    logger.warning(f"第{retry+1}次转换超时（120秒）")
                    if retry < max_retries:
                        FileService._clean_libreoffice_processes()  # 强制清理超时进程
                        time.sleep(3)
                        continue
                    else:
                        logger.error("已达最大重试次数，转换超时失败")
                        return None
                except Exception as e:
                    logger.error(
                        f"第{retry+1}次转换发生异常: {str(e)}",
                        exc_info=True
                    )
                    if retry < max_retries:
                        time.sleep(3)
                        continue
                    else:
                        return None

            # 所有重试失败
            logger.error(f"超过最大重试次数（{max_retries}次），转换失败")
            return None

        except Exception as e:
            logger.error(f"PDF转换流程异常（{file_path}）: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def _clean_libreoffice_processes():
        """清理残留的LibreOffice进程（跨平台）"""
        logger.debug("开始清理残留的LibreOffice进程")
        process_names = [
            "soffice", "soffice.bin",  # Linux/macOS
            "soffice.exe", "soffice.bin.exe"  # Windows
        ]
        
        killed = 0
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in process_names:
                    proc.terminate()  # 尝试优雅终止
                    logger.debug(f"已终止LibreOffice进程: {proc.pid} ({proc.info['name']})")
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # 强制清理未终止的进程
        if killed > 0:
            time.sleep(2)  # 等待终止
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] in process_names:
                        proc.kill()  # 强制杀死
                        logger.debug(f"已强制杀死LibreOffice进程: {proc.pid}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        logger.debug(f"LibreOffice进程清理完成，共处理{ killed }个进程")

    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """从PDF中提取文本"""
        try:
            logger.info(f"开始从PDF提取文本，文件路径: {pdf_path}")
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
                logger.debug(f"PDF文件总页数: {page_count}")
                for i, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    text += page_text
                    logger.debug(f"已提取第{i}/{page_count}页文本，长度: {len(page_text)}字符")
            
            if text:
                logger.info(f"PDF文本提取完成，总长度: {len(text)}字符")
                return text
            logger.warning(f"PDF文件{pdf_path}未提取到任何文本")
            return None
        except Exception as e:
            logger.error(f"PDF文本提取失败（{pdf_path}）: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    def clean_temp_files(file_path: str) -> None:
        """清理临时文件（原文件和转换的PDF）"""
        logger.info(f"开始清理临时文件，源文件: {file_path}")
        
        # 清理原文件
        if os.path.exists(file_path):
            try:
                file_size = os.path.getsize(file_path) / 1024
                os.remove(file_path)
                logger.info(f"已删除临时文件: {file_path}，大小: {file_size:.2f}KB")
            except Exception as e:
                logger.warning(f"临时文件删除失败（{file_path}）: {str(e)}")
        
        # 清理PDF文件
        pdf_path = os.path.splitext(file_path)[0] + ".pdf"
        if os.path.exists(pdf_path):
            try:
                pdf_size = os.path.getsize(pdf_path) / 1024
                os.remove(pdf_path)
                logger.info(f"已删除临时PDF: {pdf_path}，大小: {pdf_size:.2f}KB")
            except Exception as e:
                logger.warning(f"临时PDF删除失败（{pdf_path}）: {str(e)}")

# 单例实例
file_service = FileService()