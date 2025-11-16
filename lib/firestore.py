"""
Firestore를 사용한 문서/번역 메타데이터 저장
Firebase의 NoSQL 데이터베이스
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
import json
import firebase_admin
from firebase_admin import credentials, firestore


# Firestore 클라이언트 (싱글톤)
_firestore_client: Optional[firestore.Client] = None


def _get_firestore_client() -> firestore.Client:
    """Firestore 클라이언트 초기화 (싱글톤)"""
    global _firestore_client
    
    if _firestore_client is None:
        # Firebase 앱 초기화 (firebase_storage.py와 동일한 앱 사용)
        # 이미 초기화되어 있으면 재사용
        try:
            firebase_admin.get_app()
        except ValueError:
            # Firebase 앱이 없으면 초기화
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            elif os.getenv("FIREBASE_CREDENTIALS_JSON"):
                import json as json_module
                cred_json = json_module.loads(os.getenv("FIREBASE_CREDENTIALS_JSON"))
                cred = credentials.Certificate(cred_json)
            else:
                raise ValueError(
                    "Firebase 인증 정보가 필요합니다. "
                    "FIREBASE_CREDENTIALS_PATH 또는 FIREBASE_CREDENTIALS_JSON 환경 변수를 설정하세요."
                )
            
            bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
            firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
        
        _firestore_client = firestore.client()
    
    return _firestore_client


def save_document(document_id: str, document_name: str, total_pages: int,
                  firebase_storage_url: str, paragraphs: List[Dict]) -> bool:
    """문서 저장"""
    db = _get_firestore_client()
    
    try:
        doc_ref = db.collection('documents').document(document_id)
        doc_ref.set({
            'document_id': document_id,
            'document_name': document_name,
            'total_pages': total_pages,
            'firebase_storage_url': firebase_storage_url,
            'paragraphs': paragraphs,  # Firestore는 리스트/딕셔너리를 자동으로 저장
            'created_at': firestore.SERVER_TIMESTAMP,
        })
        return True
    except Exception as e:
        print(f"Error saving document: {e}")
        return False


def get_document(document_id: str) -> Optional[Dict]:
    """문서 조회"""
    db = _get_firestore_client()
    
    try:
        doc_ref = db.collection('documents').document(document_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
        
        doc_data = doc.to_dict()
        
        # created_at을 ISO 형식 문자열로 변환
        if 'created_at' in doc_data and doc_data['created_at']:
            if hasattr(doc_data['created_at'], 'isoformat'):
                doc_data['created_at'] = doc_data['created_at'].isoformat()
            elif isinstance(doc_data['created_at'], datetime):
                doc_data['created_at'] = doc_data['created_at'].isoformat()
        
        # file_path는 firebase_storage_url로 매핑 (하위 호환성)
        doc_data['file_path'] = doc_data.get('firebase_storage_url', '')
        
        return doc_data
    except Exception as e:
        print(f"Error getting document: {e}")
        return None


def get_all_documents() -> List[Dict]:
    """모든 문서 조회"""
    db = _get_firestore_client()
    
    try:
        docs = db.collection('documents').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        
        documents = []
        for doc in docs:
            doc_data = doc.to_dict()
            
            # created_at 변환
            if 'created_at' in doc_data and doc_data['created_at']:
                if hasattr(doc_data['created_at'], 'isoformat'):
                    doc_data['created_at'] = doc_data['created_at'].isoformat()
                elif isinstance(doc_data['created_at'], datetime):
                    doc_data['created_at'] = doc_data['created_at'].isoformat()
            
            # file_path 매핑
            doc_data['file_path'] = doc_data.get('firebase_storage_url', '')
            
            documents.append(doc_data)
        
        return documents
    except Exception as e:
        print(f"Error getting all documents: {e}")
        return []


def update_document_name(document_id: str, new_name: str) -> bool:
    """문서 이름 업데이트"""
    db = _get_firestore_client()
    
    try:
        doc_ref = db.collection('documents').document(document_id)
        doc_ref.update({'document_name': new_name})
        return True
    except Exception as e:
        print(f"Error updating document name: {e}")
        return False


def delete_document(document_id: str) -> bool:
    """문서 삭제 (번역 데이터도 함께 삭제)"""
    db = _get_firestore_client()
    
    try:
        # 문서 삭제
        doc_ref = db.collection('documents').document(document_id)
        doc_ref.delete()
        
        # 번역 데이터 삭제 (서브컬렉션)
        translations_ref = doc_ref.collection('translations')
        translations = translations_ref.stream()
        for trans in translations:
            trans.reference.delete()
        
        return True
    except Exception as e:
        print(f"Error deleting document: {e}")
        return False


def save_sentence_translation(document_id: str, sentence_id: str,
                             translated_text: str, is_final: bool = False) -> bool:
    """문장 단위 번역 저장"""
    db = _get_firestore_client()
    
    try:
        # 서브컬렉션으로 저장 (documents/{document_id}/translations/{sentence_id})
        doc_ref = db.collection('documents').document(document_id)
        trans_ref = doc_ref.collection('translations').document(sentence_id)
        
        trans_ref.set({
            'sentence_id': sentence_id,
            'translated_text': translated_text,
            'is_completed': is_final,
            'updated_at': firestore.SERVER_TIMESTAMP,
        }, merge=True)  # merge=True로 기존 데이터 유지
        
        return True
    except Exception as e:
        print(f"Error saving translation: {e}")
        return False


def get_sentence_translations(document_id: str, sentence_ids: List[str]) -> Dict[str, str]:
    """문장 단위 번역 조회"""
    if not sentence_ids:
        return {}
    
    db = _get_firestore_client()
    
    try:
        doc_ref = db.collection('documents').document(document_id)
        translations_ref = doc_ref.collection('translations')
        
        # Firestore는 IN 쿼리를 지원하지만, 최대 10개까지만 가능
        # 더 많은 경우 배치로 나눠서 조회
        translations = {}
        
        # 10개씩 나눠서 조회
        batch_size = 10
        for i in range(0, len(sentence_ids), batch_size):
            batch_ids = sentence_ids[i:i + batch_size]
            
            # IN 쿼리 사용
            query = translations_ref.where('sentence_id', 'in', batch_ids)
            docs = query.stream()
            
            for doc in docs:
                data = doc.to_dict()
                translations[data['sentence_id']] = data['translated_text']
        
        return translations
    except Exception as e:
        print(f"Error getting translations: {e}")
        return {}


def is_translation_completed(document_id: str, sentence_id: str) -> bool:
    """번역 완료 여부 확인"""
    db = _get_firestore_client()
    
    try:
        doc_ref = db.collection('documents').document(document_id)
        trans_ref = doc_ref.collection('translations').document(sentence_id)
        trans = trans_ref.get()
        
        if not trans.exists:
            return False
        
        data = trans.to_dict()
        return data.get('is_completed', False)
    except Exception as e:
        print(f"Error checking translation completion: {e}")
        return False

