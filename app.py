"""
PDF Translator - Streamlit 앱
LangChain PDF loader를 사용한 문서 자동 번역 서비스
"""
import streamlit as st
import uuid
import os
import traceback
import re
import threading
import time
import html
import json
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from lib.pdf_loader import extract_paragraphs_from_pdf
from lib.translator import translate_paragraphs
from lib.storage import save_document, get_document, get_translations, save_translation, save_sentence_translation, get_sentence_translations, is_translation_completed, update_document_name, delete_document, get_all_documents, load_document_from_paper_folder, save_document_to_paper_folder
from lib.pdf_renderer import render_pdf_page

import html


def _split_sentences_improved(text: str) -> List[str]:
    """개선된 문장 분리 함수 (약어 고려)"""
    if not text or not text.strip():
        return []
    
    # 일반적인 약어 목록
    abbreviations = [
        'Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Sr.', 'Jr.',
        'vs.', 'etc.', 'e.g.', 'i.e.', 'a.m.', 'p.m.',
        'U.S.', 'U.K.', 'Ph.D.', 'M.D.', 'B.A.', 'M.A.',
        'Inc.', 'Ltd.', 'Corp.', 'St.', 'Ave.', 'Blvd.',
        'No.', 'Vol.', 'pp.', 'cf.', 'ed.', 'eds.'
    ]
    
    # 간단한 접근: 마침표 + 공백 + 대문자 패턴으로 문장 분리
    # 단, 약어 다음에는 예외 처리
    sentences = []
    i = 0
    start = 0
    
    while i < len(text):
        if text[i] in '.!?':
            # 다음 문자 확인
            j = i + 1
            while j < len(text) and text[j].isspace():
                j += 1
            
            if j >= len(text):
                # 텍스트 끝
                sentence = text[start:].strip()
                if sentence:
                    sentences.append(sentence)
                break
            
            # 구두점 앞 부분
            before = text[start:i]
            
            # 약어 체크
            is_abbrev = False
            words = before.split()
            if words:
                last_word = words[-1].rstrip('.,!?')
                # 약어 목록 체크
                for abbr in abbreviations:
                    if last_word.endswith(abbr.rstrip('.')) or last_word == abbr.rstrip('.'):
                        is_abbrev = True
                        break
                
                # 짧은 대문자 단어 체크
                if not is_abbrev and len(last_word) <= 4 and last_word.replace("'", '').isupper():
                    is_abbrev = True
            
            # 약어가 아니고 다음이 대문자면 문장 끝
            if not is_abbrev and text[j].isupper():
                sentence = text[start:j].strip()
                if sentence:
                    sentences.append(sentence)
                start = j
                i = j - 1  # 다음 루프에서 j부터 시작하도록
        
        i += 1
    
    # 마지막 문장 (아직 추가되지 않은 경우만)
    if start < len(text):
        remaining = text[start:].strip()
        if remaining and (not sentences or sentences[-1] != remaining):
            sentences.append(remaining)
    
    return sentences if sentences else [text]

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="PDF Translator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if 'document_id' not in st.session_state:
    st.session_state.document_id = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'hovered_paragraph_id' not in st.session_state:
    st.session_state.hovered_paragraph_id = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    """비밀번호 확인 (간단한 인증)"""
    # 환경 변수에서 비밀번호 가져오기 (없으면 기본값 사용)
    # 실제 사용 시 .env 파일에 APP_PASSWORD=your_password 설정
    correct_password = os.getenv("APP_PASSWORD", "changeme")
    
    if st.session_state.authenticated:
        return True
    
    # 비밀번호 입력 폼
    with st.form("password_form"):
        st.info("🔒 이 앱은 비밀번호로 보호되어 있습니다.")
        password = st.text_input("암호를 대라!", type="password")
        submitted = st.form_submit_button("로그인")
        
        if submitted:
            if password == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다.")
    
    return False

def main():
    # 비밀번호 확인 (환경 변수 APP_PASSWORD가 설정되어 있으면 활성화)
    if os.getenv("APP_PASSWORD"):
        if not check_password():
            return
    
    # ============================================================
    # 앱 시작 시 paper 폴더에서 저장된 문서 자동 마이그레이션
    # (기존 paper 폴더 데이터를 Firebase Storage + Firestore로 마이그레이션)
    # ============================================================
    # 한 번만 실행되도록 세션 상태 플래그 사용
    if 'papers_loaded' not in st.session_state:
        paper_dir = Path("paper")
        if paper_dir.exists():
            json_files = list(paper_dir.glob("*.json"))
            loaded_count = 0
            for json_file in json_files:
                try:
                    # 문서 불러오기 (이미 불러온 문서는 건너뛰기)
                    with open(json_file, 'r', encoding='utf-8') as f:
                        doc_data = json.load(f)
                    doc_id = doc_data.get('document_id')
                    
                    # 이미 로드된 문서인지 확인 (Firestore에서)
                    existing_docs = get_all_documents()
                    existing_doc_ids = {d['document_id'] for d in existing_docs}
                    
                    if doc_id and doc_id not in existing_doc_ids:
                        # paper 폴더에서 Firebase Storage + Firestore로 마이그레이션
                        loaded_doc = load_document_from_paper_folder(json_file)
                        if loaded_doc:
                            loaded_count += 1
                except Exception as e:
                    # 로드 실패한 파일은 무시
                    pass
            
            if loaded_count > 0:
                # 자동 로드 완료 메시지는 표시하지 않음 (사용자 경험)
                pass
        
        st.session_state['papers_loaded'] = True
    
    # 사이드바
    with st.sidebar:
        st.header("📚 문서 관리")
        
        # 새 문서 업로드
        if st.button("📄 새 문서 업로드", width='stretch', type="primary"):
            st.session_state.document_id = None
            st.session_state.current_page = 1
            st.session_state.hovered_paragraph_id = None
            st.rerun()
        
        st.divider()
        
        # 문서 리스트
        st.subheader("📋 문서 목록")
        
        document_list = get_all_documents()
        if document_list:
            document_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            for doc in document_list:
                doc_id = doc['document_id']
                doc_name = doc.get('document_name', f'문서 {doc_id[:8]}')
                created_at = doc.get('created_at', '')
                total_pages = doc.get('total_pages', 0)
                
                # 날짜 포맷팅
                try:
                    from datetime import datetime
                    if created_at:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d %H:%M')
                    else:
                        date_str = "알 수 없음"
                except:
                    date_str = created_at[:16] if created_at else "알 수 없음"
                
                # 현재 선택된 문서인지 확인
                is_selected = st.session_state.document_id == doc_id
                
                # 문서 컨테이너
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        button_label = f"📖 {doc_name}"
                        if st.button(
                            button_label,
                            key=f"doc_{doc_id}",
                            width='stretch',
                            type="primary" if is_selected else "secondary"
                        ):
                            st.session_state.document_id = doc_id
                            st.session_state.current_page = 1
                            st.session_state.hovered_paragraph_id = None
                            st.rerun()
                    
                    with col2:
                        # 편집/삭제 메뉴
                        menu_key = f"menu_{doc_id}"
                        if menu_key not in st.session_state:
                            st.session_state[menu_key] = False
                        
                        if st.button("⋮", key=f"menu_btn_{doc_id}", help="문서 관리"):
                            st.session_state[menu_key] = not st.session_state[menu_key]
                    
                    # 편집/삭제 메뉴 표시
                    if st.session_state.get(menu_key, False):
                        with st.expander(f"📝 {doc_name} 관리", expanded=True):
                            # 이름 편집
                            edit_input_key = f"edit_name_{doc_id}"
                            # 텍스트 입력 (Streamlit이 자동으로 session_state에 저장)
                            new_name = st.text_input(
                                "문서 이름",
                                value=doc_name,
                                key=edit_input_key
                            )
                            
                            col_edit1, col_edit2 = st.columns(2)
                            with col_edit1:
                                if st.button("💾 저장", key=f"save_name_{doc_id}"):
                                    # session_state에서 직접 읽기
                                    current_name = st.session_state.get(edit_input_key, doc_name)
                                    if current_name and current_name.strip():
                                        if update_document_name(doc_id, current_name.strip()):
                                            st.session_state[menu_key] = False
                                            st.success("문서 이름이 변경되었습니다.")
                                            st.rerun()
                                        else:
                                            st.error("문서 이름 변경에 실패했습니다.")
                                    else:
                                        st.error("문서 이름을 입력하세요.")
                            
                            with col_edit2:
                                if st.button("❌ 삭제", key=f"delete_{doc_id}", type="secondary"):
                                    if delete_document(doc_id):
                                        if st.session_state.document_id == doc_id:
                                            st.session_state.document_id = None
                                        st.session_state[menu_key] = False
                                        st.success("문서가 삭제되었습니다.")
                                        st.rerun()
                                    else:
                                        st.error("문서 삭제에 실패했습니다.")
                            
                            # paper 폴더에 저장 (PDF + 번역 내용)
                            st.divider()
                            save_button_label = f"{doc_name} 저장"
                            if st.button(save_button_label, key=f"save_paper_{doc_id}", width='stretch'):
                                if save_document_to_paper_folder(doc_id):
                                    st.success(f"✅ paper 폴더에 저장되었습니다!\n📁 위치: `paper/` 폴더")
                                else:
                                    st.error("저장에 실패했습니다.")
                    
                    # 문서 정보 (작게 표시)
                    st.caption(f"📅 {date_str} | 📄 {total_pages}페이지")
        else:
            st.info("업로드된 문서가 없습니다.")
    
    # 메인 컨텐츠
    st.title("📄 PDF Translator")

    # 문서가 없으면 업로드 화면, 있으면 뷰어 화면
    # 명시적으로 분리하여 번역 중일 때 업로드 화면이 표시되지 않도록 함
    if st.session_state.document_id is None:
        # 업로드 화면 표시
        show_upload_screen()
    else:
        # 뷰어 화면이 표시되는 동안에는 업로드 화면을 완전히 숨김
        # 이전에 렌더링된 업로드 컴포넌트를 명시적으로 제거
        upload_placeholder = st.empty()
        upload_placeholder.empty()
        show_viewer_screen()

def show_upload_screen():
    """파일 업로드 화면"""
    # 문서가 이미 로드된 경우 업로드 화면을 표시하지 않음
    if st.session_state.document_id is not None:
        return
    
    st.header("PDF 파일 업로드")
    
    uploaded_file = st.file_uploader(
        "PDF 파일을 선택하거나 드래그 앤 드롭하세요",
        type=['pdf'],
        help="최대 파일 크기: 10MB",
        key="pdf_uploader"  # 고유 키 지정
    )

    if uploaded_file is not None:
        # 파일 크기 검증
        if uploaded_file.size > 10 * 1024 * 1024:
            st.error("파일 크기는 10MB 이하여야 합니다.")
            return

        with st.spinner("PDF 파일을 분석 중입니다..."):
            try:
                # 임시 파일로 저장
                temp_dir = Path("temp")
                temp_dir.mkdir(exist_ok=True)
                temp_path = temp_dir / f"{uuid.uuid4()}.pdf"
                
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # PDF 파싱 및 문단 추출 (진행 상황 표시)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("PDF 파일 로딩 중...")
                paragraphs, total_pages = extract_paragraphs_from_pdf(str(temp_path))
                
                # 문서 저장 (파일명을 기본 이름으로 사용)
                document_id = str(uuid.uuid4())
                default_name = uploaded_file.name.replace('.pdf', '').replace('.PDF', '')
                
                # Firebase Storage에 업로드하고 Postgres에 저장
                status_text.text("Firebase Storage에 업로드 중...")
                save_document(
                    document_id=document_id,
                    paragraphs=paragraphs,
                    total_pages=total_pages,
                    file_path=str(temp_path),  # 로컬 임시 파일 (Firebase Storage에 업로드됨)
                    document_name=default_name
                )
                
                # 임시 파일 삭제 (Firebase Storage에 업로드되었으므로)
                try:
                    temp_path.unlink()
                except:
                    pass

                st.session_state.document_id = document_id
                st.session_state.current_page = 1
                st.rerun()

            except Exception as e:
                st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
                with st.expander("상세 오류 정보"):
                    st.code(traceback.format_exc())
                if 'temp_path' in locals() and temp_path.exists():
                    temp_path.unlink()

def show_viewer_screen():
    """뷰어 화면"""
    document_id = st.session_state.document_id
    document = get_document(document_id)
    
    if document is None:
        st.error("문서를 찾을 수 없습니다.")
        st.session_state.document_id = None
        st.rerun()
        return

    # 좌우 분할 레이아웃
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📖 Original")
        show_original_pane(document)

    with col2:
        st.subheader("🌐 Translated")
        show_translated_pane(document)

def show_original_pane(document: Dict):
    """원문 패널"""
    total_pages = document['total_pages']
    current_page = st.session_state.current_page
    document_id = document['document_id']
    
    # Firebase Storage에서 PDF 다운로드 (로컬 임시 파일)
    from lib.storage import get_local_pdf_path
    local_pdf_path = get_local_pdf_path(document_id)
    
    if not local_pdf_path or not Path(local_pdf_path).exists():
        st.error("PDF 파일을 불러올 수 없습니다.")
        return

    # 페이지 네비게이션
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    with nav_col1:
        if st.button("◀ 이전", disabled=current_page <= 1, key="prev_page"):
            st.session_state.current_page = max(1, current_page - 1)
            st.rerun()
    
    with nav_col2:
        st.markdown(f"<div style='text-align: center; padding: 0.5rem;'>{current_page} / {total_pages}</div>", unsafe_allow_html=True)
    
    with nav_col3:
        if st.button("다음 ▶", disabled=current_page >= total_pages, key="next_page"):
            st.session_state.current_page = min(total_pages, current_page + 1)
            st.rerun()

    # PDF 페이지 이미지 표시
    pdf_image = render_pdf_page(local_pdf_path, current_page, zoom=1.5)
    if pdf_image:
        st.image(pdf_image, caption=f"Page {current_page}")
    else:
        st.warning("PDF 페이지를 불러올 수 없습니다.")

    # 현재 페이지의 문단들 표시 (선택적 - 접을 수 있게)
    current_page_paragraphs = [
        p for p in document['paragraphs'] 
        if p['page_number'] == current_page
    ]

    if current_page_paragraphs:
        with st.expander("📝 이 페이지의 문단 텍스트", expanded=False):
            for paragraph in current_page_paragraphs:
                paragraph_id = paragraph['paragraph_id']
                is_hovered = st.session_state.hovered_paragraph_id == paragraph_id
                
                # 클릭으로 하이라이트 토글
                if st.button(f"📌 {paragraph_id}", key=f"orig_{paragraph_id}", width='stretch'):
                    if st.session_state.hovered_paragraph_id == paragraph_id:
                        st.session_state.hovered_paragraph_id = None
                    else:
                        st.session_state.hovered_paragraph_id = paragraph_id
                    st.rerun()
                
                # 하이라이트 스타일
                border_color = "#3b82f6" if is_hovered else "#e5e7eb"
                bg_color = "#eff6ff" if is_hovered else "#ffffff"
                
                st.markdown(
                    f"""
                    <div style='
                        padding: 1rem;
                        margin: 0.5rem 0;
                        border: 2px solid {border_color};
                        border-radius: 0.5rem;
                        background-color: {bg_color};
                    '>
                        <small style='color: #6b7280;'>{paragraph_id}</small>
                        <p style='margin-top: 0.5rem;'>{paragraph['text']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

def show_translated_pane(document: Dict):
    """
    번역 패널 함수 (리팩토링 버전)
    - 문장 전처리 + 번역 조회를 한 번에 수행
    - 표시 + 스트리밍을 같은 루프 안에 통합
    - 한 run당 첫 번째 미번역 문장만 스트리밍하고 st.stop()으로 종료
    """
    # ============================================================
    # 1단계: 현재 페이지의 문단 필터링
    # ============================================================
    current_page = st.session_state.current_page
    
    # 현재 페이지에 속한 문단만 필터링 (page_number 기준)
    # 목적: 다른 페이지의 문단이 섞이지 않도록 보장
    current_page_paragraphs = [
        p for p in document['paragraphs'] 
        if p.get('page_number') == current_page
    ]
    
    # 현재 페이지에 문단이 없으면 안내 메시지 표시 후 종료
    if not current_page_paragraphs:
        st.info(f"페이지 {current_page}에는 문단이 없습니다.")
        return
    
    # 현재 페이지의 문단 ID를 set으로 저장 (빠른 조회를 위해)
    # 목적: 번역 데이터 필터링 시 O(1) 조회 성능 확보
    current_page_paragraph_ids = {p['paragraph_id'] for p in current_page_paragraphs}
    
    # ============================================================
    # 2단계: 문장 전처리 - 한 번에 모든 문장을 분리하고 구조화
    # ============================================================
    # sentence_map: {sentence_id: {paragraph_id, text}}
    # 목적: 문장 ID로 빠르게 원본 텍스트와 문단 ID를 조회
    sentence_map = {}
    
    # paragraph_sentences: {paragraph_id: [sentence_id, ...]}
    # 목적: 각 문단에 속한 문장 ID 목록을 관리
    paragraph_sentences = {}
    
    # current_page_paragraphs를 한 번만 순회하면서 문장 분리
    # 목적: 중복 루프 제거 및 효율적인 데이터 구조 생성
    for paragraph in current_page_paragraphs:
        # 페이지 번호 재확인 (이중 안전장치)
        if paragraph.get('page_number') != current_page:
            continue
        
        paragraph_id = paragraph['paragraph_id']
        original_text = paragraph['text']
        
        # 문단 텍스트를 문장 단위로 분리
        # 목적: 번역 단위를 문장으로 세분화
        original_sentences = _split_sentences_improved(original_text)
        
        # 현재 문단의 문장 ID 목록 초기화
        paragraph_sentences[paragraph_id] = []
        
        # 각 문장을 sentence_map에 저장
        for i, orig_sent in enumerate(original_sentences):
            # 빈 문장은 건너뛰기
            if not orig_sent.strip():
                continue
            
            sentence_id = f"{paragraph_id}_s{i}"
            
            # sentence_map에 문장 정보 저장
            sentence_map[sentence_id] = {
                'paragraph_id': paragraph_id,
                'text': orig_sent
            }
            
            # paragraph_sentences에 문장 ID 추가
            paragraph_sentences[paragraph_id].append(sentence_id)
    
    # ============================================================
    # 3단계: 번역 데이터 일괄 조회 (한 번에 모든 문장 번역 가져오기)
    # ============================================================
    # 모든 문장 ID를 리스트로 수집
    # 목적: 한 번의 DB 호출로 모든 번역 데이터를 가져오기
    all_sentence_ids = list(sentence_map.keys())
    
    # 저장소에서 모든 문장의 번역 데이터를 한 번에 조회
    # 목적: 중복 DB 호출 제거 및 성능 향상
    translations = get_sentence_translations(document['document_id'], all_sentence_ids)
    
    # ============================================================
    # 4단계: 모든 문장 표시 (1단계 - 먼저 모든 문장을 화면에 표시)
    # ============================================================
    # 이번 run에서 번역을 시작할 첫 번째 미번역 문장을 추적
    # 목적: 한 run당 하나의 문장만 스트리밍 처리
    first_untranslated_sentence_id = None
    first_untranslated_placeholder = None
    
    # 각 문단을 순회하며 모든 문장 표시
    for paragraph in current_page_paragraphs:
        # 페이지 번호 재확인
        if paragraph.get('page_number') != current_page:
            continue
        
        paragraph_id = paragraph['paragraph_id']
        
        # 현재 문단에 속한 문장 ID 목록 가져오기
        sentence_ids = paragraph_sentences.get(paragraph_id, [])
        
        # 각 문장을 순회하며 표시
        for sentence_id in sentence_ids:
            # sentence_map에서 문장 정보 가져오기
            sentence_info = sentence_map.get(sentence_id)
            if not sentence_info:
                continue
            
            orig_text = sentence_info['text']
            
            # ============================================================
            # 4-1: 원본 문장 표시 (항상 먼저 표시)
            # ============================================================
            # HTML 특수문자 이스케이프 처리
            # 목적: XSS 공격 방지 및 특수문자 안전 표시
            escaped_orig = html.escape(orig_text)
            st.markdown(f"**📄 {escaped_orig}**")
            
            # ============================================================
            # 4-2: 번역 상태 확인
            # ============================================================
            # 저장소에서 번역본 조회
            existing_trans = translations.get(sentence_id)
            
            # ============================================================
            # 4-3: 번역 상태에 따른 화면 표시
            # ============================================================
            if existing_trans:
                # 케이스 1: 번역 완료 → 최종 번역본 표시
                escaped_text = html.escape(existing_trans)
                st.markdown(f"🌐 {escaped_text}")
            else:
                # 케이스 2: 번역 없음
                # 첫 번째 미번역 문장인지 확인
                if first_untranslated_sentence_id is None:
                    # 이번 run에서 번역할 첫 번째 미번역 문장으로 설정
                    first_untranslated_sentence_id = sentence_id
                    # placeholder 생성 (스트리밍 중 실시간 업데이트용)
                    first_untranslated_placeholder = st.empty()
                    # "번역 중" 표시
                    first_untranslated_placeholder.markdown("🌐 (번역 중)")
                else:
                    # 첫 번째 미번역 문장이 아닌 경우 → "번역 대기 중" 표시
                    st.markdown("🌐 (번역 대기 중)")
            
            # 문장 간 구분을 위한 빈 줄
            st.markdown("")
    
    # ============================================================
    # 5단계: 첫 번째 미번역 문장 스트리밍 번역 실행 (2단계)
    # ============================================================
    # 첫 번째 미번역 문장이 있으면 스트리밍 번역 시작
    # 목적: 모든 문장을 표시한 후에만 번역을 시작하여 사용자가 전체 페이지를 볼 수 있도록 함
    if first_untranslated_sentence_id is not None and first_untranslated_placeholder is not None:
        try:
            from lib.translator import _get_client, _clean_translation
            
            # 첫 번째 미번역 문장 정보 가져오기
            sentence_info = sentence_map.get(first_untranslated_sentence_id)
            if sentence_info:
                orig_text = sentence_info['text']
                
                # 빈 텍스트는 번역하지 않음
                if not orig_text.strip():
                    # 빈 텍스트는 원문 그대로 저장
                    save_sentence_translation(document['document_id'], first_untranslated_sentence_id, orig_text, is_final=True)
                    first_untranslated_placeholder.markdown("🌐 (번역 대기 중)")
                else:
                    # OpenAI 클라이언트 가져오기
                    client = _get_client()
                    
                    # 스트리밍 응답으로 번역 요청
                    # 목적: 실시간으로 번역 결과를 받아 화면에 표시
                    stream = client.chat.completions.create(
                        model="gpt-4o",  # 최고 품질 번역을 위한 고성능 모델 사용
                        messages=[
                            {
                                "role": "system",
                                "content": """You are an expert professional translator with deep knowledge across multiple domains including academic research, business, technology, medicine, law, finance, and literature. Your translations are renowned for their accuracy, naturalness, and cultural sensitivity.

CORE TRANSLATION PRINCIPLES:

1. DOMAIN AWARENESS & CONTEXT UNDERSTANDING:
   - Carefully analyze the domain and context of the sentence (academic, business, technical, medical, legal, etc.)
   - Understand the subject matter deeply before translating
   - Use domain-appropriate terminology and register
   - Maintain consistency with established translations in the field
   - For academic texts: preserve formal tone and precise terminology
   - For business texts: use professional and clear language
   - For technical texts: maintain technical accuracy while ensuring readability

2. TRANSLATION QUALITY STANDARDS:
   - Produce translations that read as if originally written in Korean
   - Ensure natural Korean sentence structure and word order
   - Avoid literal word-for-word translations that sound awkward
   - Preserve the author's tone, style, and intent
   - Maintain the original's emphasis and nuance
   - Use appropriate Korean honorifics and formality levels

3. TERMINOLOGY & PROPER NOUNS:
   - For proper nouns (place names, company names, product names, etc.) and unique technical terms unfamiliar to Korean readers, add a brief explanatory note in parentheses. Format: "한국어 번역 (의미 설명)"
   - The explanatory note should explain what the term means, not just repeat the English term
   - Only add explanations for genuinely unfamiliar or technical terms
   - Well-known terms (e.g., "iPhone", "Google", "New York") do not need explanations
   - Use established Korean translations when they exist (e.g., "월스트리트" for "Wall Street")
   - For technical terms, prefer Korean translations over transliterations when appropriate

4. SENTENCE-LEVEL TRANSLATION:
   - Translate only the given SINGLE SENTENCE
   - Do not add any additional text, explanations, or commentary
   - Ensure the sentence is complete and grammatically correct in Korean
   - Maintain the sentence's original meaning and nuance

5. ACCURACY & FIDELITY:
   - Translate the meaning, not just the words
   - Ensure no information is lost or added
   - If the text is already in Korean, return it as is
   - Return ONLY the translated sentence, nothing else

EXAMPLES:
- "I played bridge" → "나는 브리지 (카드 게임의 한 종류)를 했다."
- "The company's EBITDA increased by 15%" → "회사의 EBITDA (세전 영업이익, 이자·세금·감가상각 전 이익)가 15% 증가했다."
- "She underwent a CT scan" → "그녀는 CT 스캔 (컴퓨터 단층촬영)을 받았다."
- "The merger was subject to regulatory approval" → "인수합병은 규제 당국의 승인을 받아야 했다."

Remember: Your goal is to produce a translation that is accurate, natural, culturally appropriate, and maintains the original's meaning and tone while being perfectly readable in Korean."""
                            },
                            {
                                "role": "user",
                                "content": orig_text
                            }
                        ],
                        temperature=0.1,  # 최고 일관성과 정확성을 위한 매우 낮은 temperature
                        stream=True,  # 스트리밍 모드 활성화
                    )
                    
                    # ============================================================
                    # 5-1: 스트리밍 루프 - 청크 단위로 번역 수집 및 화면 업데이트
                    # ============================================================
                    streamed = ""  # 누적된 번역 텍스트
                    
                    # 스트리밍 응답을 청크 단위로 수신
                    # 목적: 실시간으로 번역 결과를 받아 화면에 표시
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            chunk_text = chunk.choices[0].delta.content
                            streamed += chunk_text  # 로컬 변수에 누적
                            
                            # 저장소에 부분 번역 저장 (is_final=False)
                            # 목적: 스트리밍 중에도 부분 번역을 조회할 수 있도록
                            save_sentence_translation(
                                document['document_id'], 
                                first_untranslated_sentence_id, 
                                streamed, 
                                is_final=False
                            )
                            
                            # placeholder에 실시간으로 번역 표시 (rerun 없이)
                            # 목적: 사용자가 "타이핑되듯이 번역이 자라나는 것"을 보게 함
                            escaped_streamed = html.escape(streamed)
                            first_untranslated_placeholder.markdown(f"🌐 {escaped_streamed}")
                    
                    # ============================================================
                    # 5-2: 스트리밍 완료 후 최종 정리 및 저장
                    # ============================================================
                    # 번역 결과 정리 (불필요한 문자 제거)
                    final_translated_text = _clean_translation(streamed)
                    final_translated_text = final_translated_text.strip() if final_translated_text.strip() else orig_text
                    
                    # 최종 번역본 저장 (is_final=True)
                    # 목적: 번역 완료 플래그 설정 및 최종 결과 저장
                    save_sentence_translation(document['document_id'], first_untranslated_sentence_id, final_translated_text, is_final=True)
                    
                    # placeholder에 최종 번역본 표시
                    escaped_final = html.escape(final_translated_text)
                    first_untranslated_placeholder.markdown(f"🌐 {escaped_final}")
                    
                    # 다음 문장 번역을 위해 rerun
                    # 목적: 다음 run에서 다음 문장의 번역을 자동으로 시작하도록 함
                    st.rerun()
        
        except Exception as e:
            # 번역 중 오류 발생 시 처리
            st.error(f"번역 중 오류가 발생했습니다: {str(e)}")
            # 에러 발생 시 원문 저장 (최소한의 데이터 보존)
            if sentence_info:
                save_sentence_translation(document['document_id'], first_untranslated_sentence_id, sentence_info['text'], is_final=True)
            if first_untranslated_placeholder:
                first_untranslated_placeholder.markdown("🌐 (번역 대기 중)")

if __name__ == "__main__":
    main()

