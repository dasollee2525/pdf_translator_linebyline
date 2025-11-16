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
- **번역**: OpenAI GPT-4o-mini
- **언어**: Python 3.9+

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
