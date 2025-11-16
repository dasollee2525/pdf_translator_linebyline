"""
LangChain PDF Loader를 사용한 PDF 파싱
PDFPlumberLoader 스타일로 문단 추출
"""
from typing import List, Dict, Tuple
from langchain_community.document_loaders import PDFPlumberLoader


def extract_paragraphs_from_pdf(file_path: str) -> Tuple[List[Dict], int]:
    """
    PDF 파일에서 문단 추출
    LangChain PDFPlumberLoader 사용 (더 정확한 문단 분리)
    
    Args:
        file_path: PDF 파일 경로
        
    Returns:
        (paragraphs, total_pages) 튜플
        paragraphs: [{
            'paragraph_id': 'p1_01',
            'page_number': 1,
            'text': '문단 텍스트'
        }, ...]
    """
    # PDFPlumberLoader 사용 (더 정확한 문단 분리)
    loader = PDFPlumberLoader(file_path)
    documents = loader.load()
    
    paragraphs: List[Dict] = []
    
    # 페이지별로 문단 추출
    for doc in documents:
        # LangChain Document에서 페이지 번호 추출 (0-based → 1-based로 변환)
        page_number_0based = doc.metadata.get('page', 0)
        page_number = page_number_0based + 1  # 1-based로 변환
        text = doc.page_content.strip()
        
        if not text:
            continue
        
        # 빈 줄 기준으로 문단 분리
        text_blocks = text.split('\n\n')
        
        paragraph_index = 1
        for block in text_blocks:
            block = block.strip()
            if not block:
                continue
            
            # 줄바꿈을 보존하되, 불필요한 공백은 정리
            # 각 줄의 앞뒤 공백 제거 후 줄바꿈 유지
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            paragraph_text = '\n'.join(lines)
            
            if paragraph_text:
                paragraphs.append({
                    'paragraph_id': f"p{page_number}_{str(paragraph_index).zfill(2)}",
                    'page_number': page_number,  # 1-based
                    'text': paragraph_text,
                })
                paragraph_index += 1
    
    total_pages = max([p['page_number'] for p in paragraphs], default=1) if paragraphs else 1
    
    return paragraphs, total_pages

