"""
OpenAI를 사용한 번역 기능
"""
import os
from typing import List, Dict, Optional
from openai import OpenAI

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """OpenAI 클라이언트를 가져오거나 생성"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        _client = OpenAI(api_key=api_key)
    return _client


def _clean_translation(text: str) -> str:
    """번역 결과에서 불필요한 문자 제거"""
    import re
    
    if not text:
        return text
    
    # 반복되는 구분선 제거 (* * * * * 같은 패턴)
    text = re.sub(r'\*[\s*]*\*[\s*]*\*[\s*]*\*[\s*]*\*+', '', text)
    text = re.sub(r'[-]{3,}', '', text)  # --- 같은 긴 대시
    text = re.sub(r'[=]{3,}', '', text)  # === 같은 긴 등호
    text = re.sub(r'[_]{3,}', '', text)  # ___ 같은 긴 언더스코어
    
    # 연속된 공백 정리
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 빈 줄이 3개 이상이면 2개로 제한
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text


def translate_paragraphs(paragraphs: List[Dict]) -> Dict[str, str]:
    """
    문단들을 번역
    
    Args:
        paragraphs: [{'paragraph_id': 'p1_01', 'text': '...'}, ...]
        
    Returns:
        {paragraph_id: translated_text, ...}
    """
    if not paragraphs:
        return {}
    
    # 문단별로 개별 번역 (더 정확한 번역을 위해)
    translations = {}
    client = _get_client()
    
    try:
        # 각 문단을 개별적으로 번역
        for paragraph in paragraphs:
            paragraph_id = paragraph['paragraph_id']
            text = paragraph['text']
            
            # 빈 텍스트는 건너뛰기
            if not text.strip():
                translations[paragraph_id] = text
                continue
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",  # 더 나은 번역 품질을 위해 gpt-4o 사용
                    messages=[
                        {
                            "role": "system",
                            "content": """You are a professional translator specializing in academic and technical documents. Translate the following text to Korean with high accuracy.

IMPORTANT TRANSLATION RULES:
1. Preserve the original paragraph structure, line breaks, and formatting exactly as they appear in the source text.
2. For proper nouns (place names, company names, product names, etc.) and unique technical terms that may be unfamiliar to Korean readers, add a brief explanatory note in parentheses after the Korean translation. The note should explain what the term means, not just repeat the original English term. Format: "한국어 번역 (의미 설명)"
3. Only add explanatory notes for terms that are genuinely unfamiliar or technical. Common terms that are well-known in Korean do not need explanations.
4. Maintain natural Korean sentence flow while preserving the original meaning.
5. Preserve all line breaks and paragraph breaks to maintain readability.
6. If the text is already in Korean, return it as is.
7. Do not add any explanations or notes, only return the translated text with proper formatting.

Example: "I played bridge" → "나는 브리지 (카드 게임의 한 종류)를 했다."
Example: "The Golden Gate Bridge" → "금문교 (샌프란시스코의 유명한 다리)" (if the bridge is not well-known, otherwise just "금문교")
Example: "I used a VPN" → "나는 VPN (가상 사설망, 인터넷 보안을 위한 기술)을 사용했다."

IMPORTANT: Remove any decorative elements like repeated asterisks (* * * *), long dashes (---), or other formatting separators that are not part of the actual content. Only return the translated text content."""
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    temperature=0.2,  # 더 일관된 번역을 위해 낮춤
                )
                
                translated_text = response.choices[0].message.content or ''
                # 불필요한 문자 정리
                translated_text = _clean_translation(translated_text)
                translations[paragraph_id] = translated_text.strip() if translated_text.strip() else text
                
            except Exception as e:
                print(f"Translation error for {paragraph_id}: {e}")
                # 에러 발생 시 원문 반환
                translations[paragraph_id] = text
        
        return translations
        
    except Exception as e:
        print(f"Translation error: {e}")
        # 에러 발생 시 원문 반환
        return {p['paragraph_id']: p['text'] for p in paragraphs}

