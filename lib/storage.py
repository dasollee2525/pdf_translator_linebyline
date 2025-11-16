"""
인메모리 스토리지 (실제 프로덕션에서는 DB 사용)
"""
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json
import shutil


# 인메모리 저장소
documents: Dict[str, Dict] = {}
translation_cache: Dict[str, Dict[str, str]] = {}
# 번역 완료 플래그 (문장 단위)
translation_completed: Dict[str, set] = {}  # {document_id: {sentence_id, ...}}


def save_document(document_id: str, paragraphs: List[Dict], total_pages: int, file_path: str, document_name: Optional[str] = None):
    """문서 저장"""
    # 파일명에서 기본 이름 추출 (확장자 제거)
    if document_name is None:
        document_name = Path(file_path).stem
    
    documents[document_id] = {
        'document_id': document_id,
        'document_name': document_name,
        'paragraphs': paragraphs,
        'total_pages': total_pages,
        'file_path': file_path,
        'created_at': datetime.now().isoformat(),
    }


def update_document_name(document_id: str, new_name: str):
    """문서 이름 업데이트"""
    if document_id in documents:
        documents[document_id]['document_name'] = new_name
        return True
    return False


def delete_document(document_id: str):
    """문서 삭제"""
    if document_id in documents:
        # PDF 파일 삭제
        file_path = documents[document_id].get('file_path')
        if file_path and Path(file_path).exists():
            try:
                Path(file_path).unlink()
            except:
                pass
        
        # 문서 삭제
        del documents[document_id]
        
        # 번역 캐시 삭제
        if document_id in translation_cache:
            del translation_cache[document_id]
        
        # 번역 완료 플래그 삭제
        if document_id in translation_completed:
            del translation_completed[document_id]
        
        return True
    return False


def save_document_to_paper_folder(document_id: str):
    """문서를 paper/ 폴더에 저장 (PDF 파일과 번역 결과 JSON)"""
    if document_id not in documents:
        return False
    
    try:
        # paper 폴더 생성
        paper_dir = Path("paper")
        paper_dir.mkdir(exist_ok=True)
        
        doc = documents[document_id]
        doc_name = doc.get('document_name', f'document_{document_id[:8]}')
        
        # 안전한 파일명 생성 (특수문자 제거)
        safe_name = "".join(c for c in doc_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        
        # PDF 파일 복사
        source_pdf = Path(doc['file_path'])
        if source_pdf.exists():
            dest_pdf = paper_dir / f"{safe_name}_{document_id[:8]}.pdf"
            shutil.copy2(source_pdf, dest_pdf)
        
        # 번역 결과를 JSON으로 저장 (문장 단위 번역 포함)
        translations = translation_cache.get(document_id, {})
        completed_sentences = translation_completed.get(document_id, set())
        
        doc_data = {
            'document_id': document_id,
            'document_name': doc['document_name'],
            'total_pages': doc['total_pages'],
            'created_at': doc['created_at'],
            'paragraphs': doc['paragraphs'],
            'translations': translations,  # 문장 단위 번역 포함
            'completed_sentences': list(completed_sentences),  # 완료된 문장 ID 목록
        }
        
        json_path = paper_dir / f"{safe_name}_{document_id[:8]}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(doc_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving to paper folder: {e}")
        return False


def load_document_from_paper_folder(json_path: Path) -> Optional[Dict]:
    """paper 폴더에서 저장된 문서와 번역을 불러오기"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            doc_data = json.load(f)
        
        # JSON에서 document_id 추출 (파일명에서도 시도)
        document_id = doc_data.get('document_id')
        if not document_id:
            # 파일명에서 document_id 추출 시도 (마지막 _ 뒤의 8자리)
            file_stem = json_path.stem
            if '_' in file_stem:
                parts = file_stem.split('_')
                if len(parts) > 1 and len(parts[-1]) == 8:
                    document_id = parts[-1]
                else:
                    document_id = str(uuid.uuid4())
            else:
                document_id = str(uuid.uuid4())
        
        # 문서 정보 복원
        documents[document_id] = {
            'document_id': document_id,
            'document_name': doc_data.get('document_name', f'document_{document_id[:8]}'),
            'paragraphs': doc_data.get('paragraphs', []),
            'total_pages': doc_data.get('total_pages', 0),
            'created_at': doc_data.get('created_at', datetime.now().isoformat()),
            'file_path': str(json_path.parent / json_path.name.replace('.json', '.pdf')),
        }
        
        # 번역 결과 복원
        translations = doc_data.get('translations', {})
        if translations:
            translation_cache[document_id] = translations
        
        # 완료된 문장 플래그 복원
        completed_sentences = doc_data.get('completed_sentences', [])
        if completed_sentences:
            translation_completed[document_id] = set(completed_sentences)
        
        return documents[document_id]
    except Exception as e:
        print(f"Error loading from paper folder: {e}")
        return None


def find_saved_document_in_paper_folder(document_name: str) -> Optional[Path]:
    """paper 폴더에서 문서 이름으로 저장된 JSON 파일 찾기"""
    paper_dir = Path("paper")
    if not paper_dir.exists():
        return None
    
    # 안전한 파일명 생성
    safe_name = "".join(c for c in document_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')
    
    # JSON 파일 검색
    for json_file in paper_dir.glob(f"{safe_name}_*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)
                if doc_data.get('document_name') == document_name:
                    return json_file
        except:
            continue
    
    return None


def get_document(document_id: str) -> Optional[Dict]:
    """문서 조회"""
    return documents.get(document_id)


def get_all_documents() -> List[Dict]:
    """모든 문서 조회"""
    return list(documents.values())


def save_translation(document_id: str, paragraph_id: str, translated_text: str):
    """번역 저장 (문단 단위)"""
    if document_id not in translation_cache:
        translation_cache[document_id] = {}
    translation_cache[document_id][paragraph_id] = translated_text


def save_sentence_translation(document_id: str, sentence_id: str, translated_text: str, is_final: bool = False):
    """문장 단위 번역 저장"""
    if document_id not in translation_cache:
        translation_cache[document_id] = {}
    translation_cache[document_id][sentence_id] = translated_text
    
    # 최종 번역인 경우 완료 플래그 설정
    if is_final:
        if document_id not in translation_completed:
            translation_completed[document_id] = set()
        translation_completed[document_id].add(sentence_id)


def get_translations(document_id: str, paragraph_ids: List[str]) -> Dict[str, str]:
    """번역 조회 (문단 단위)"""
    cache = translation_cache.get(document_id, {})
    return {pid: cache[pid] for pid in paragraph_ids if pid in cache}


def get_sentence_translations(document_id: str, sentence_ids: List[str]) -> Dict[str, str]:
    """문장 단위 번역 조회"""
    cache = translation_cache.get(document_id, {})
    return {sid: cache[sid] for sid in sentence_ids if sid in cache}


def is_translation_completed(document_id: str, sentence_id: str) -> bool:
    """번역 완료 여부 확인"""
    return sentence_id in translation_completed.get(document_id, set())

