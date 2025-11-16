"""
Firebase Storage를 사용한 PDF 파일 저장/조회
Streamlit Cloud에서도 영구 저장 가능
"""
import os
from pathlib import Path
from typing import Optional
import firebase_admin
from firebase_admin import credentials, storage
import io


# Firebase 앱 초기화 (싱글톤)
_firebase_app: Optional[firebase_admin.App] = None


def _get_firebase_app():
    """Firebase 앱 초기화 (싱글톤)"""
    global _firebase_app
    
    if _firebase_app is None:
        # 환경 변수에서 Firebase 인증 정보 가져오기
        # 방법 1: JSON 파일 경로
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if cred_path and Path(cred_path).exists():
            cred = credentials.Certificate(cred_path)
        # 방법 2: JSON 문자열 (환경 변수)
        elif os.getenv("FIREBASE_CREDENTIALS_JSON"):
            import json
            cred_json = json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON"))
            cred = credentials.Certificate(cred_json)
        else:
            raise ValueError(
                "Firebase 인증 정보가 필요합니다. "
                "FIREBASE_CREDENTIALS_PATH 또는 FIREBASE_CREDENTIALS_JSON 환경 변수를 설정하세요."
            )
        
        # Firebase Storage 버킷 이름
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
        if not bucket_name:
            raise ValueError("FIREBASE_STORAGE_BUCKET 환경 변수를 설정하세요.")
        
        _firebase_app = firebase_admin.initialize_app(
            cred,
            {'storageBucket': bucket_name}
        )
    
    return _firebase_app


def upload_pdf(file_path: str, document_id: str) -> str:
    """
    PDF 파일을 Firebase Storage에 업로드
    
    Args:
        file_path: 로컬 PDF 파일 경로
        document_id: 문서 ID (파일명으로 사용)
        
    Returns:
        Firebase Storage URL (다운로드 URL)
    """
    app = _get_firebase_app()
    bucket = storage.bucket()
    
    # Firebase Storage 경로: pdfs/{document_id}.pdf
    blob_name = f"pdfs/{document_id}.pdf"
    blob = bucket.blob(blob_name)
    
    # 파일 업로드
    with open(file_path, 'rb') as f:
        blob.upload_from_file(f, content_type='application/pdf')
    
    # 공개 URL 생성 (또는 signed URL)
    # 공개 읽기 권한이 있다면 public_url 사용
    blob.make_public()
    return blob.public_url


def download_pdf(document_id: str, local_path: Optional[str] = None) -> Optional[str]:
    """
    Firebase Storage에서 PDF 파일 다운로드
    
    Args:
        document_id: 문서 ID
        local_path: 로컬 저장 경로 (None이면 임시 파일 생성)
        
    Returns:
        로컬 파일 경로 (다운로드 실패 시 None)
    """
    app = _get_firebase_app()
    bucket = storage.bucket()
    
    blob_name = f"pdfs/{document_id}.pdf"
    blob = bucket.blob(blob_name)
    
    if not blob.exists():
        return None
    
    # 로컬 경로 설정
    if local_path is None:
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        local_path = str(temp_dir / f"{document_id}.pdf")
    
    # 파일 다운로드
    blob.download_to_filename(local_path)
    return local_path


def delete_pdf(document_id: str) -> bool:
    """
    Firebase Storage에서 PDF 파일 삭제
    
    Args:
        document_id: 문서 ID
        
    Returns:
        삭제 성공 여부
    """
    try:
        app = _get_firebase_app()
        bucket = storage.bucket()
        
        blob_name = f"pdfs/{document_id}.pdf"
        blob = bucket.blob(blob_name)
        
        if blob.exists():
            blob.delete()
            return True
        return False
    except Exception as e:
        print(f"Error deleting PDF from Firebase Storage: {e}")
        return False


def get_pdf_url(document_id: str) -> Optional[str]:
    """
    Firebase Storage에서 PDF 파일의 공개 URL 가져오기
    
    Args:
        document_id: 문서 ID
        
    Returns:
        PDF 파일 URL (없으면 None)
    """
    try:
        app = _get_firebase_app()
        bucket = storage.bucket()
        
        blob_name = f"pdfs/{document_id}.pdf"
        blob = bucket.blob(blob_name)
        
        if blob.exists():
            blob.make_public()
            return blob.public_url
        return None
    except Exception as e:
        print(f"Error getting PDF URL from Firebase Storage: {e}")
        return None

