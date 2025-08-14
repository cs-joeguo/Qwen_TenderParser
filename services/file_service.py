'''文件处理工具：格式转换、文本提取等'''
import os
import subprocess
import pdfplumber
from config import logger

class FileService:
    @staticmethod
    def convert_to_pdf(file_path: str, libreoffice_path: str = None) -> str:
        """将文件转换为PDF"""
        try:
            file_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            pdf_path = os.path.join(file_dir, f"{file_name}.pdf")
            
            cmd = [
                libreoffice_path or "libreoffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", file_dir,
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
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