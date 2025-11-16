# PDF Translator - Python (Streamlit) 버전

LangChain PDF Loader를 사용한 문서 자동 번역 서비스

## 실행 방법

### 1. 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. Streamlit 앱 실행

```bash
streamlit run app.py
```

브라우저에서 자동으로 열립니다 (보통 `http://localhost:8501`)

## 프로젝트 구조

```
PDF_Translator/
├── app.py                    # Streamlit 메인 앱
├── requirements.txt          # Python 의존성
├── .env                      # 환경 변수 (OPENAI_API_KEY)
├── .streamlit/
│   └── config.toml          # Streamlit 설정
└── lib/
    ├── __init__.py
    ├── pdf_loader.py         # LangChain PDF Loader (PDFPlumberLoader)
    ├── translator.py         # OpenAI 번역
    └── storage.py            # 인메모리 스토리지
```

## 주요 기능

- **PDF 업로드**: 드래그 앤 드롭 또는 파일 선택
- **문단 추출**: LangChain PDFPlumberLoader 사용
- **자동 번역**: OpenAI GPT-4o-mini
- **좌우 뷰어**: 원문과 번역문 동시 표시
- **페이지 네비게이션**: 페이지별 이동

## 기술 스택

- **Frontend**: Streamlit
- **PDF 파싱**: LangChain PDFPlumberLoader
- **번역**: OpenAI GPT-4o (고성능 모델)
- **언어**: Python 3.9+

## ⚠️ 데이터 저장 및 보관 (중요)

### 현재 저장 방식

**로컬 실행 시:**
- PDF 파일: `temp/` 디렉토리에 저장 (디스크)
- 문서 메타데이터: 인메모리 딕셔너리 (메모리)
- 번역 결과: 인메모리 딕셔너리 (메모리)

**배포 환경 (Streamlit Cloud, Railway, Render 등):**
- PDF 파일: 서버의 임시 디렉토리에 저장
- 문서 메타데이터: 인메모리 딕셔너리 (메모리)
- 번역 결과: 인메모리 딕셔너리 (메모리)

### ⚠️ 중요한 제한사항

**현재 구조는 임시 저장소입니다:**

1. **서버 재시작 시 모든 데이터 사라짐**
   - Streamlit Cloud: 앱이 재시작되면 모든 데이터 삭제
   - Railway/Render: 컨테이너 재시작 시 모든 데이터 삭제
   - 업로드한 PDF 파일, 번역 결과 모두 사라짐

2. **세션 간 데이터 공유 불가**
   - 다른 브라우저나 다른 사용자가 접근하면 데이터가 보이지 않음
   - 각 세션이 독립적으로 작동

3. **파일 시스템은 임시**
   - `temp/` 디렉토리는 서버의 임시 공간
   - 서버 재시작 시 삭제됨

### 💡 영구 저장이 필요한 경우

프로덕션 환경에서는 다음 중 하나를 사용해야 합니다:

1. **데이터베이스 (추천)**
   - PostgreSQL, MongoDB, SQLite 등
   - 문서 메타데이터와 번역 결과를 DB에 저장

2. **클라우드 스토리지**
   - AWS S3, Google Cloud Storage, Azure Blob Storage
   - PDF 파일을 클라우드에 저장

3. **파일 시스템 (영구 마운트)**
   - Railway/Render: 영구 볼륨 마운트
   - VPS: 영구 디렉토리 사용

### 현재 구조의 장점

- **개인 사용**: 한 번에 하나의 문서만 작업하는 경우 적합
- **간단함**: 추가 설정 없이 바로 사용 가능
- **비용**: 추가 스토리지 비용 없음

### 개선이 필요한 경우

- 여러 문서를 오래 보관해야 하는 경우
- 여러 사용자가 동시에 사용하는 경우
- 서버 재시작 후에도 데이터를 유지해야 하는 경우

## 배포 방법 (개인 사용)

### 옵션 1: 로컬에서 계속 실행 (가장 간단)

컴퓨터를 켜둘 때만 접근 가능하지만, 설정이 가장 간단합니다.

```bash
# 터미널에서 실행
streamlit run app.py

# 백그라운드로 실행하려면 (macOS/Linux)
nohup streamlit run app.py > streamlit.log 2>&1 &
```

**장점**: 무료, 설정 간단  
**단점**: 컴퓨터를 켜둬야 함, 외부에서 접근 불가

---

### 옵션 2: Streamlit Cloud (추천 ⭐)

무료로 24시간 접근 가능한 클라우드 배포

#### ⚠️ 접근 제어 방법

Streamlit Cloud는 public repo만 지원하지만, **비밀번호 보호 기능**이 내장되어 있습니다!

#### 1단계: GitHub에 코드 업로드
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/pdf-translator.git
git push -u origin main
```

#### 2단계: Streamlit Cloud 설정
1. [share.streamlit.io](https://share.streamlit.io) 접속
2. "Sign in with GitHub" 클릭
3. "New app" 클릭
4. Repository 선택: `your-username/pdf-translator`
5. Main file path: `app.py`
6. **Advanced settings** → **Secrets** 클릭
7. 다음 내용 입력:
   ```toml
   OPENAI_API_KEY = "your_openai_api_key_here"
   APP_PASSWORD = "your_secure_password_here"  # 비밀번호 보호 활성화
   ```
8. "Deploy" 클릭

**장점**: 무료, 24시간 접근 가능, 자동 업데이트, 비밀번호 보호 가능  
**단점**: GitHub에 코드 업로드 필요 (하지만 비밀번호로 보호됨)

#### 🔒 비밀번호 보호 사용법

`.env` 파일 또는 Streamlit Cloud Secrets에 `APP_PASSWORD`를 설정하면:
- 앱 접속 시 비밀번호 입력 화면이 나타남
- 비밀번호가 맞아야만 앱 사용 가능
- 코드는 public이지만, 실제 사용은 비밀번호로 보호됨

---

### 옵션 3: Railway / Render (무료 티어) ⭐ Private Repo 지원

**Private GitHub repo를 사용할 수 있어서 더 안전합니다!**

#### Railway 배포
1. [railway.app](https://railway.app) 가입
2. "New Project" → "Deploy from GitHub repo"
3. 환경 변수 설정: `OPENAI_API_KEY`
4. Build command: `pip install -r requirements.txt`
5. Start command: `streamlit run app.py --server.port $PORT`

#### Render 배포
1. [render.com](https://render.com) 가입
2. "New Web Service" → GitHub repo 연결
3. Build command: `pip install -r requirements.txt`
4. Start command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
5. 환경 변수 설정: `OPENAI_API_KEY`

**장점**: 무료 티어 제공, 더 많은 제어, **Private repo 지원** (코드 비공개 가능)  
**단점**: 설정이 조금 더 복잡

---

### 옵션 4: VPS (DigitalOcean, AWS 등)

완전한 제어가 필요한 경우

```bash
# 서버에 접속 후
git clone https://github.com/your-username/pdf-translator.git
cd pdf-translator
pip install -r requirements.txt

# systemd 서비스로 등록 (항상 실행)
sudo nano /etc/systemd/system/pdf-translator.service
```

서비스 파일 내용:
```ini
[Unit]
Description=PDF Translator Streamlit App
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/pdf-translator
Environment="OPENAI_API_KEY=your_key_here"
ExecStart=/usr/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable pdf-translator
sudo systemctl start pdf-translator
```

**장점**: 완전한 제어, 커스터마이징 가능  
**단점**: 유료, 서버 관리 필요

---

## 추천 순서

1. **개인 사용 + 간단함**: 옵션 1 (로컬 실행)
2. **24시간 접근 + 무료**: 옵션 2 (Streamlit Cloud) ⭐
3. **더 많은 제어**: 옵션 3 (Railway/Render)
4. **완전한 제어**: 옵션 4 (VPS)
