"""
인메모리 스토리지 (실제 프로덕션에서는 DB 사용)
"""
from typing import Dict, List, Optional
from datetime import datetime


# 인메모리 저장소
documents: Dict[str, Dict] = {}
translation_cache: Dict[str, Dict[str, str]] = {}
# 번역 완료 플래그 (문장 단위)
translation_completed: Dict[str, set] = {}  # {document_id: {sentence_id, ...}}


def save_document(document_id: str, paragraphs: List[Dict], total_pages: int, file_path: str):
    """문서 저장"""
    documents[document_id] = {
        'document_id': document_id,
        'paragraphs': paragraphs,
        'total_pages': total_pages,
        'file_path': file_path,
        'created_at': datetime.now().isoformat(),
    }


def get_document(document_id: str) -> Optional[Dict]:
    """문서 조회"""
    return documents.get(document_id)


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

