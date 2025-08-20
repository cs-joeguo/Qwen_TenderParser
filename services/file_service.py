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
        os_name = sys.platform
        if os_name.startswith('win'):
            # Windows系统常见安装路径
            possible_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            return "soffice.exe"  # 未找到时依赖环境变量
        
        elif os_name.startswith('darwin'):
            # macOS系统常见路径
            default_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
            return default_path if os.path.exists(default_path) else "soffice"
        
        else:
            # Linux/CentOS系统（通常通过包管理器安装）
            return "libreoffice"

    @staticmethod
    def convert_to_pdf(file_path: str, libreoffice_path: str = None) -> str:
        """将文件转换为PDF（多系统兼容版）"""
        try:
            file_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            pdf_path = os.path.join(file_dir, f"{file_name}.pdf")
            
            # 处理LibreOffice路径：优先使用用户指定路径，否则自动获取
            exec_path = libreoffice_path or FileService.get_default_libreoffice_path()
            
            # 构造命令（处理Windows路径中的空格问题）
            cmd = [
                exec_path,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", file_dir,
                file_path
            ]
            
            # 执行命令（Windows下隐藏控制台窗口）
            startupinfo = None
            if sys.platform.startswith('win'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                startupinfo=startupinfo
            )
            
            if result.returncode != 0:
                logger.error(f"文件转换PDF失败（{file_path}）：{result.stderr}")
                return None
                
            if os.path.exists(pdf_path):
                return pdf_path
            logger.error(f"PDF转换成功但未找到文件：{pdf_path}")
            return None
            
        except Exception as e:
            logger.error(f"文件转换异常（{file_path}）：{str(e)}")
            return None
    
    # 以下方法保持不变
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """从PDF中提取文本"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text if text else None
        except Exception as e:
            logger.error(f"PDF文本提取失败（{pdf_path}）：{str(e)}")
            return None
    
    @staticmethod
    def clean_temp_files(file_path: str) -> None:
        """清理临时文件（原文件和转换的PDF）"""
        # 清理原文件
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"已删除临时文件：{file_path}")
            except Exception as e:
                logger.warning(f"临时文件删除失败（{file_path}）：{str(e)}")
        
        # 清理PDF文件
        pdf_path = os.path.splitext(file_path)[0] + ".pdf"
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                logger.info(f"已删除临时PDF：{pdf_path}")
            except Exception as e:
                logger.warning(f"临时PDF删除失败（{pdf_path}）：{str(e)}")

# 单例实例
file_service = FileService()