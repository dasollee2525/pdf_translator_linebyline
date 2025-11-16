"""
Firebase Storage + Firestore 기반 영구 스토리지
Streamlit Cloud 배포 시에도 데이터가 영구 보존됨

- PDF 파일: Firebase Storage
- 문서/문장/번역 메타데이터: Firestore
"""
from typing import Dict, List, Optional
from pathlib import Path
import shutil

# Firebase Storage 모듈
from lib.firebase_storage import upload_pdf, download_pdf, delete_pdf, get_pdf_url

# Firestore 모듈
from lib.firestore import (
    save_document as db_save_document,
    get_document as db_get_document,
    get_all_documents as db_get_all_documents,
    update_document_name as db_update_document_name,
    delete_document as db_delete_document,
    save_sentence_translation as db_save_sentence_translation,
    get_sentence_translations as db_get_sentence_translations,
    is_translation_completed as db_is_translation_completed,
)


def save_document(document_id: str, paragraphs: List[Dict], total_pages: int, 
                  file_path: str, document_name: Optional[str] = None):
    """
    문서 저장
    - PDF 파일을 Firebase Storage에 업로드
    - 문서 메타데이터를 Postgres에 저장
    
    Args:
        document_id: 문서 ID
        paragraphs: 문단 리스트
        total_pages: 전체 페이지 수
        file_path: 로컬 PDF 파일 경로 (Firebase Storage에 업로드됨)
        document_name: 문서 이름 (None이면 파일명에서 추출)
    """
    # 파일명에서 기본 이름 추출
    if document_name is None:
        document_name = Path(file_path).stem
    
    # 1. PDF 파일을 Firebase Storage에 업로드
    try:
        firebase_url = upload_pdf(file_path, document_id)
    except Exception as e:
        print(f"Error uploading PDF to Firebase Storage: {e}")
        raise
    
    # 2. 문서 메타데이터를 Firestore에 저장
    success = db_save_document(
        document_id=document_id,
        document_name=document_name,
        total_pages=total_pages,
        firebase_storage_url=firebase_url,
        paragraphs=paragraphs
    )
    
    if not success:
        raise Exception("Failed to save document to database")


def get_document(document_id: str) -> Optional[Dict]:
    """문서 조회 (Firestore에서 메타데이터 조회)"""
    return db_get_document(document_id)


def get_all_documents() -> List[Dict]:
    """모든 문서 조회"""
    return db_get_all_documents()


def update_document_name(document_id: str, new_name: str) -> bool:
    """문서 이름 업데이트"""
    return db_update_document_name(document_id, new_name)


def delete_document(document_id: str) -> bool:
    """
    문서 삭제
    - Firebase Storage에서 PDF 파일 삭제
    - Postgres에서 문서 및 번역 데이터 삭제 (CASCADE)
    """
    # 1. Firebase Storage에서 PDF 삭제
    delete_pdf(document_id)
    
    # 2. Firestore에서 문서 삭제 (translations 서브컬렉션도 함께 삭제)
    return db_delete_document(document_id)


def save_translation(document_id: str, paragraph_id: str, translated_text: str):
    """번역 저장 (문단 단위) - 하위 호환성 유지"""
    # 문단 단위 번역도 sentence_id로 저장
    save_sentence_translation(document_id, paragraph_id, translated_text, is_final=True)


def save_sentence_translation(document_id: str, sentence_id: str, 
                              translated_text: str, is_final: bool = False):
    """문장 단위 번역 저장 (Firestore)"""
    db_save_sentence_translation(document_id, sentence_id, translated_text, is_final)


def get_translations(document_id: str, paragraph_ids: List[str]) -> Dict[str, str]:
    """번역 조회 (문단 단위) - 하위 호환성 유지"""
    return get_sentence_translations(document_id, paragraph_ids)


def get_sentence_translations(document_id: str, sentence_ids: List[str]) -> Dict[str, str]:
    """문장 단위 번역 조회 (Firestore)"""
    return db_get_sentence_translations(document_id, sentence_ids)


def is_translation_completed(document_id: str, sentence_id: str) -> bool:
    """번역 완료 여부 확인 (Firestore)"""
    return db_is_translation_completed(document_id, sentence_id)


# ============================================================
# PDF 파일 다운로드 헬퍼 (로컬에서 사용할 때)
# ============================================================

def get_local_pdf_path(document_id: str) -> Optional[str]:
    """
    Firebase Storage에서 PDF를 다운로드하여 로컬 임시 파일로 저장
    (PDF 렌더링 등 로컬 작업에 필요)
    
    Returns:
        로컬 파일 경로 (다운로드 실패 시 None)
    """
    return download_pdf(document_id)


# ============================================================
# Paper 폴더 마이그레이션 함수 (하위 호환성 - 제거 예정)
# ============================================================

def save_document_to_paper_folder(document_id: str):
    """
    문서를 paper/ 폴더에 저장 (하위 호환성)
    주의: 이 함수는 로컬 백업용이며, 실제 저장소는 Firebase Storage + Postgres입니다.
    """
    doc = get_document(document_id)
    if not doc:
        return False
    
    try:
        # paper 폴더 생성
        paper_dir = Path("paper")
        paper_dir.mkdir(exist_ok=True)
        
        doc_name = doc.get('document_name', f'document_{document_id[:8]}')
        
        # 안전한 파일명 생성
        safe_name = "".join(c for c in doc_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        
        # Firebase Storage에서 PDF 다운로드
        local_pdf_path = download_pdf(document_id)
        if local_pdf_path and Path(local_pdf_path).exists():
            dest_pdf = paper_dir / f"{safe_name}_{document_id[:8]}.pdf"
            shutil.copy2(local_pdf_path, dest_pdf)
        
        # 번역 결과 조회
        translations = {}
        completed_sentences = []
        
        # 모든 문장 ID 조회 (문단에서 추출)
        all_sentence_ids = []
        for paragraph in doc.get('paragraphs', []):
            # 문단을 문장으로 분리하는 로직이 필요하지만, 
            # 여기서는 간단히 paragraph_id를 sentence_id로 사용
            all_sentence_ids.append(paragraph['paragraph_id'])
        
        # 번역 조회
        translations_dict = get_sentence_translations(document_id, all_sentence_ids)
        for sentence_id, translated_text in translations_dict.items():
            translations[sentence_id] = translated_text
            if is_translation_completed(document_id, sentence_id):
                completed_sentences.append(sentence_id)
        
        # JSON으로 저장
        import json
        from datetime import datetime
        
        doc_data = {
            'document_id': document_id,
            'document_name': doc['document_name'],
            'total_pages': doc['total_pages'],
            'created_at': doc.get('created_at', datetime.now().isoformat()),
            'paragraphs': doc['paragraphs'],
            'translations': translations,
            'completed_sentences': completed_sentences,
        }
        
        json_path = paper_dir / f"{safe_name}_{document_id[:8]}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(doc_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving to paper folder: {e}")
        return False


def load_document_from_paper_folder(json_path: Path) -> Optional[Dict]:
    """
    paper 폴더에서 저장된 문서와 번역을 불러오기 (마이그레이션용)
    주의: 이 함수는 기존 paper 폴더 데이터를 Firebase Storage + Firestore로 마이그레이션합니다.
    """
    try:
        import json
        from datetime import datetime
        
        with open(json_path, 'r', encoding='utf-8') as f:
            doc_data = json.load(f)
        
        document_id = doc_data.get('document_id')
        if not document_id:
            import uuid
            document_id = str(uuid.uuid4())
        
        # PDF 파일 경로
        pdf_file = json_path.parent / json_path.name.replace('.json', '.pdf')
        
        if not pdf_file.exists():
            print(f"PDF file not found: {pdf_file}")
            return None
        
        # 1. PDF를 Firebase Storage에 업로드
        try:
            firebase_url = upload_pdf(str(pdf_file), document_id)
        except Exception as e:
            print(f"Error uploading PDF to Firebase Storage: {e}")
            return None
        
        # 2. 문서 메타데이터를 Firestore에 저장
        success = db_save_document(
            document_id=document_id,
            document_name=doc_data.get('document_name', f'document_{document_id[:8]}'),
            total_pages=doc_data.get('total_pages', 0),
            firebase_storage_url=firebase_url,
            paragraphs=doc_data.get('paragraphs', [])
        )
        
        if not success:
            return None
        
        # 3. 번역 결과 저장
        translations = doc_data.get('translations', {})
        completed_sentences = set(doc_data.get('completed_sentences', []))
        
        for sentence_id, translated_text in translations.items():
            is_completed = sentence_id in completed_sentences
            save_sentence_translation(document_id, sentence_id, translated_text, is_final=is_completed)
        
        return get_document(document_id)
    except Exception as e:
        print(f"Error loading from paper folder: {e}")
        return None


def find_saved_document_in_paper_folder(document_name: str) -> Optional[Path]:
    """paper 폴더에서 문서 이름으로 저장된 JSON 파일 찾기"""
    paper_dir = Path("paper")
    if not paper_dir.exists():
        return None
    
    for json_file in paper_dir.glob("*.json"):
        try:
            import json
            with open(json_file, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)
                if doc_data.get('document_name') == document_name:
                    return json_file
        except:
            continue
    
    return None
