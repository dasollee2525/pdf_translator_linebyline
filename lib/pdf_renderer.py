"""
PDF 페이지를 이미지로 렌더링
"""
import fitz  # pymupdf
from PIL import Image
import io
from pathlib import Path
from typing import Optional


def render_pdf_page(file_path: str, page_number: int, zoom: float = 2.0) -> Optional[Image.Image]:
    """
    PDF 페이지를 이미지로 렌더링
    
    Args:
        file_path: PDF 파일 경로
        page_number: 페이지 번호 (1부터 시작)
        zoom: 확대 배율 (기본값 2.0)
        
    Returns:
        PIL Image 객체 또는 None
    """
    try:
        doc = fitz.open(file_path)
        
        if page_number < 1 or page_number > len(doc):
            doc.close()
            return None
        
        # 페이지 인덱스는 0부터 시작
        page = doc[page_number - 1]
        
        # 매트릭스 생성 (zoom 배율)
        mat = fitz.Matrix(zoom, zoom)
        
        # 페이지를 이미지로 렌더링
        pix = page.get_pixmap(matrix=mat)
        
        # PIL Image로 변환
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        doc.close()
        return img
        
    except Exception as e:
        print(f"PDF 렌더링 오류: {e}")
        return None

