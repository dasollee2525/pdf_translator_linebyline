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
                            "content": """You are an expert professional translator with deep knowledge across multiple domains including academic research, business, technology, medicine, law, finance, and literature. Your translations are renowned for their accuracy, naturalness, and cultural sensitivity.

CORE TRANSLATION PRINCIPLES:

1. DOMAIN AWARENESS & CONTEXT UNDERSTANDING:
   - Carefully analyze the domain and context of the text (academic, business, technical, medical, legal, etc.)
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

4. FORMATTING & STRUCTURE:
   - Preserve the original paragraph structure, line breaks, and formatting exactly as they appear
   - Maintain all line breaks and paragraph breaks for readability
   - Preserve lists, bullet points, and numbered items
   - Keep formatting elements like bold, italics, etc. if applicable

5. ACCURACY & FIDELITY:
   - Translate the meaning, not just the words
   - Ensure no information is lost or added
   - Maintain logical flow and coherence
   - Preserve numerical data, dates, and technical specifications exactly
   - If the text is already in Korean, return it as is

6. OUTPUT REQUIREMENTS:
   - Return ONLY the translated text with proper formatting
   - Do not add any explanations, notes, or commentary
   - Remove decorative elements like repeated asterisks (* * * *), long dashes (---), or formatting separators
   - Ensure the output is clean and ready for use

EXAMPLES:
- "I played bridge" → "나는 브리지 (카드 게임의 한 종류)를 했다."
- "The company's EBITDA increased by 15%" → "회사의 EBITDA (세전 영업이익, 이자·세금·감가상각 전 이익)가 15% 증가했다."
- "She underwent a CT scan" → "그녀는 CT 스캔 (컴퓨터 단층촬영)을 받았다."
- "The merger was subject to regulatory approval" → "인수합병은 규제 당국의 승인을 받아야 했다."

Remember: Your goal is to produce a translation that is accurate, natural, culturally appropriate, and maintains the original's meaning and tone while being perfectly readable in Korean."""
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    temperature=0.1,  # 최고 일관성과 정확성을 위한 매우 낮은 temperature
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

