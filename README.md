# PDF Translator - Python (Streamlit) 버전

LangChain PDF Loader를 사용한 문서 자동 번역 서비스

**Firebase Storage + Firestore 기반 영구 저장** - Streamlit Cloud 배포 시에도 데이터가 영구 보존됩니다.

## 실행 방법

### 1. 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성:

```bash
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Firebase 설정
# 방법 1: JSON 파일 경로
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
# 방법 2: JSON 문자열 (환경 변수)
# FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com

# 앱 비밀번호 (선택사항)
APP_PASSWORD=your_app_password_here
```

### 2. Firebase 설정

1. [Firebase Console](https://console.firebase.google.com/)에서 프로젝트 생성
2. **Storage** 활성화
3. **Firestore Database** 활성화 (NoSQL 데이터베이스)
   - 프로젝트 설정 → Firestore Database → 데이터베이스 만들기
   - 프로덕션 모드로 시작 (나중에 보안 규칙 설정 가능)
4. **서비스 계정** 생성:
   - 프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성
   - 다운로드한 JSON 파일을 **프로젝트 루트 디렉토리**에 `firebase-credentials.json`으로 저장
     ```
     PDF_Translator/
     ├── firebase-credentials.json  ← 여기에 저장
     ├── app.py
     ├── requirements.txt
     └── ...
     ```
   - 또는 JSON 내용을 `FIREBASE_CREDENTIALS_JSON` 환경 변수로 설정 (Streamlit Cloud 배포 시 권장)

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. Streamlit 앱 실행

```bash
streamlit run app.py
```

브라우저에서 자동으로 열립니다 (보통 `http://localhost:8501`)

## 프로젝트 구조

```
PDF_Translator/
├── app.py                    # Streamlit 메인 앱
├── requirements.txt          # Python 의존성
├── .env                      # 환경 변수
├── firebase-credentials.json # Firebase 인증 정보 (Git에 포함하지 말 것!)
├── .streamlit/
│   └── config.toml          # Streamlit 설정
└── lib/
    ├── __init__.py
    ├── pdf_loader.py         # LangChain PDF Loader (PDFPlumberLoader)
    ├── translator.py         # OpenAI 번역
    ├── storage.py            # Firebase Storage + Firestore 스토리지
    ├── firebase_storage.py   # Firebase Storage 업로드/다운로드
    ├── firestore.py          # Firestore 데이터베이스 연결
    └── pdf_renderer.py       # PDF 페이지 이미지 렌더링
```

## 주요 기능

- **PDF 업로드**: 드래그 앤 드롭 또는 파일 선택
- **문단 추출**: LangChain PDFPlumberLoader 사용
- **자동 번역**: OpenAI GPT-4o (고성능 모델)
- **좌우 뷰어**: 원문과 번역문 동시 표시
- **페이지 네비게이션**: 페이지별 이동
- **영구 저장**: Firebase Storage (PDF) + Postgres (메타데이터/번역)

## 기술 스택

- **Frontend**: Streamlit
- **PDF 파싱**: LangChain PDFPlumberLoader
- **번역**: OpenAI GPT-4o
- **PDF 저장**: Firebase Storage
- **데이터베이스**: Firestore (Firebase NoSQL)
- **언어**: Python 3.9+

## 데이터 저장 구조

### Firebase Storage
- **저장 위치**: `pdfs/{document_id}.pdf`
- **용도**: PDF 파일 영구 저장
- **장점**: Streamlit Cloud 배포 시에도 영구 보존

### Firestore 데이터베이스

#### `documents` 컬렉션
- `document_id`: 문서 고유 ID (문서 ID)
- `document_name`: 문서 이름
- `total_pages`: 전체 페이지 수
- `firebase_storage_url`: Firebase Storage URL
- `paragraphs`: 문단 정보 (배열)
- `created_at`: 생성 시간

#### `documents/{document_id}/translations` 서브컬렉션
- `sentence_id`: 문장 ID (문서 ID)
- `translated_text`: 번역된 텍스트
- `is_completed`: 번역 완료 여부
- `updated_at`: 업데이트 시간

## 배포 방법

### Streamlit Cloud 배포

1. **GitHub에 코드 업로드**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-username/pdf-translator.git
   git push -u origin main
   ```

2. **Streamlit Cloud 설정**
   - [share.streamlit.io](https://share.streamlit.io) 접속
   - "Sign in with GitHub" 클릭
   - "New app" 클릭
   - Repository 선택
   - Main file path: `app.py`

3. **Secrets 설정** (Advanced settings → Secrets)
   ```toml
   OPENAI_API_KEY = "your_openai_api_key_here"
   FIREBASE_CREDENTIALS_JSON = '{"type":"service_account","project_id":"..."}'
   FIREBASE_STORAGE_BUCKET = "your-project-id.appspot.com"
   APP_PASSWORD = "your_secure_password_here"
   ```

4. **Deploy** 클릭

**장점**: 
- 무료
- 24시간 접근 가능
- 자동 업데이트
- **데이터 영구 보존** (Firebase Storage + Firestore)

### Railway / Render 배포

Private GitHub repo를 사용할 수 있어서 더 안전합니다!

#### Railway 배포
1. [railway.app](https://railway.app) 가입
2. "New Project" → "Deploy from GitHub repo"
3. 환경 변수 설정 (`.env` 파일 내용)
4. Build command: `pip install -r requirements.txt`
5. Start command: `streamlit run app.py --server.port $PORT`

#### Render 배포
1. [render.com](https://render.com) 가입
2. "New Web Service" → GitHub repo 연결
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. 환경 변수 설정

## 비용 예상

### 무료 티어로 시작 가능

- **Firebase Storage**: 
  - 무료: 5GB 저장, 1GB/일 다운로드
  - 충분한 용량 제공
- **Firestore**:
  - 무료: 1GB 저장, 50K 읽기/일, 20K 쓰기/일, 20K 삭제/일
  - 충분한 용량 제공
- **Streamlit Cloud**: 무료
- **OpenAI API**: 사용량에 따라 과금 (GPT-4o)

## 주의사항

1. **Firebase 인증 정보 보안** ⚠️
   - `firebase-credentials.json` 파일은 **절대 Git에 커밋하지 마세요**
   - `.gitignore`에 이미 포함되어 있습니다
   - 파일 위치: 프로젝트 루트 디렉토리 (`PDF_Translator/firebase-credentials.json`)
   - Streamlit Cloud 배포 시:
     - Secrets에 `FIREBASE_CREDENTIALS_JSON` 환경 변수로 JSON 문자열 설정 (권장)
     - 또는 파일을 업로드하고 `FIREBASE_CREDENTIALS_PATH` 설정

2. **Firestore 설정**
   - Firebase Console에서 Firestore Database를 활성화하면 자동으로 사용 가능
   - 별도의 데이터베이스 서버 설정 불필요

3. **기존 paper 폴더 데이터**
   - 앱 시작 시 `paper/` 폴더의 JSON 파일을 자동으로 Firebase Storage + Firestore로 마이그레이션합니다
   - 마이그레이션 후에도 `paper/` 폴더는 백업용으로 유지됩니다

## 문제 해결

### Firebase Storage 연결 오류
- `FIREBASE_CREDENTIALS_PATH` 또는 `FIREBASE_CREDENTIALS_JSON`이 올바르게 설정되었는지 확인
- Firebase Console에서 Storage가 활성화되었는지 확인

### Firestore 연결 오류
- Firebase 인증 정보가 올바르게 설정되었는지 확인
- Firebase Console에서 Firestore Database가 활성화되었는지 확인

### PDF 다운로드 오류
- Firebase Storage 버킷 권한이 올바르게 설정되었는지 확인
- Storage 규칙에서 읽기 권한이 허용되었는지 확인
