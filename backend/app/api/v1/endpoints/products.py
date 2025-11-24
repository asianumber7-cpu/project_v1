# backend/app/api/v1/endpoints/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from transformers import AutoProcessor, AutoModel
import torch
import torch.nn.functional as F

from app.db.database import get_db
from app.schemas.product import Product, ProductCreate
from app.crud import crud_product

router = APIRouter()

# --- AI 모델 로드 ---
# MODEL_NAME = 'koclip/koclip-base-pt'
MODEL_NAME = 'Bingsu/clip-vit-large-patch14-ko'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print("🔄 AI 모델 로딩 중...")
try:
    model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    print("✅ AI 모델 로딩 완료!")
except Exception as e:
    print(f"❌ AI 모델 로딩 실패: {e}")
    model = None
    processor = None

class SearchRequest(BaseModel):
    query: str

# ---------------------------------------------------------

def extract_filters(query: str) -> dict:
    """쿼리에서 성별, 계절 추출 (최종 수정)"""
    query_lower = query.lower()
    gender = None
    
    # 1. 문맥(Context) 파악: "선물" 여부 확인
    is_gift = any(word in query_lower for word in ["선물", "사주고", "줄"])
    
    # 남성 대상 키워드
    male_targets = ["남자친구", "남친", "남편", "신랑", "아빠", "오빠", "형", "할아버지", "싸나이", "사나이", "남자", "남성"]
    # 여성 대상 키워드
    female_targets = ["여자친구", "여친", "아내", "와이프", "엄마", "누나", "언니", "여동생", "할머니", "여자", "여성", "숙녀"]

    # 2. 성별 결정 로직
    if is_gift:
        # 선물인 경우: 대상의 성별을 따름
        if any(t in query_lower for t in male_targets):
            gender = "남성"
        elif any(t in query_lower for t in female_targets):
            gender = "여성"
    else:
        # 선물이 아닌 경우 (내가 입을 옷 or 데이트)
        # "남자친구랑..." -> 나는 여자
        if any(t in query_lower for t in ["남자친구", "남친", "남편", "신랑"]):
            gender = "여성"
        # "여자친구랑..." -> 나는 남자
        elif any(t in query_lower for t in ["여자친구", "여친", "아내", "와이프"]):
            gender = "남성"
        # "싸나이", "남자" 등 직접 언급 -> 남자
        elif any(t in query_lower for t in male_targets):
            gender = "남성"
        # "숙녀", "여자" 등 직접 언급 -> 여자
        elif any(t in query_lower for t in female_targets):
            gender = "여성"

    # 연예인 및 일반 명사 감지
    if gender is None:
        # --- 여자 연예인 리스트 ---
        female_celebs = [
            "여성", "여자", "우먼", "숙녀", "아가씨", "딸", 
            "제니", "장원영", "원영", "카리나", "윈터", "아이유", "수지", 
            "김고은", "한소희", "뉴진스", "안유진", "로제", "지수", "리사", "태연"
        ]
        # --- 남자 연예인 리스트 ---
        male_celebs = [
            "남성", "남자", "맨즈", "신사", "아들", 
            "차은우", "은우", "송강", "변우석", "뷔", "정국", "지민", 
            "지디", "지드래곤", "공유", "박서준", "손흥민", "이동욱", "남주혁"
        ]

        if any(word in query_lower for word in female_celebs):
            gender = "여성"
        elif any(word in query_lower for word in male_celebs):
            gender = "남성"

    #  헤어스타일/특징 추가 
    if gender is None:
        # 여자 관련 단어 (헤어스타일 추가)
        female_keywords = [
            "여성", "여자", "우먼", "숙녀", "아가씨", "딸", 
            "긴생머리", "생머리", "단발", "웨이브", "여신", "똥머리"
        ]
        # 남자 관련 단어
        male_keywords = [
            "남성", "남자", "맨즈", "신사", "아들", 
            "포마드", "쉼표머리", "투블럭"
        ]

        if any(word in query_lower for word in female_keywords):
            gender = "여성"
        elif any(word in query_lower for word in male_keywords):
            gender = "남성"        

    # 3. 계절 감지 (기존 유지)
    season = None
    winter_words = ["겨울", "한파", "추운", "두꺼운", "기모", "패딩", "코트", "크리스마스", "연말", "목도리", "수능", "설날", "새해"]
    summer_words = ["여름", "더운", "시원한", "얇은", "린넨", "반팔", "휴가", "바캉스", "장마", "수영"]
    spring_fall_words = ["봄", "가을", "간절기", "바람막이", "가디건", "트렌치", "자켓", "벚꽃", "소풍", "추석"]

    if any(word in query_lower for word in winter_words):
        season = "겨울"
    elif any(word in query_lower for word in summer_words):
        season = "여름"
    elif any(word in query_lower for word in spring_fall_words):
        season = "가을"
    elif "사계절" in query_lower:
        season = "사계절"
    
    return {
        "gender": gender,
        "season": season
    }


def extract_core_keywords(query: str, gender: str = None) -> list:
    """핵심 카테고리, 상황, 그리고 연예인 스타일 매핑"""
    
    # 불용어 (기존 유지)
    stopwords = {
        '을', '를', '이', '가', '은', '는', '의', '에', '와', '과',
        '입을', '할때', '때', '할', '추천', '추천해줘', '해줘', '좀',
        '에서', '입을만한', '입기', '좋은', '적합한', '어울리는',
        '입을옷', '옷', '꺼로', '것', '거', '같은', '같이', '위한', '위해',
    }
    
    keyword_patterns = {
        # --- 1. 기본 카테고리 ---
        "상의": ["티셔츠", "셔츠", "맨투맨", "후드", "블라우스", "니트"],
        "반팔": ["티셔츠", "셔츠", "블라우스"],
        "티셔츠": ["티셔츠"],
        "셔츠": ["셔츠"],
        "맨투맨": ["맨투맨"],
        "후드": ["후드"],
        "커플": ["맨투맨", "후드", "니트", "가디건", "유니섹스", "공용", "오버핏", "시밀러룩"],
        "시밀러룩": ["맨투맨", "후드", "셔츠", "니트", "체크", "색감"],
        "트윈룩": ["맨투맨", "후드", "원피스", "스커트"],

        # ★★★ [추가] 체형 고민 & 해결 솔루션 (여기가 핵심!) ★★★
        
        # 머리숱/탈모 고민 -> 모자, 시선 분산 아이템 추천
        "머리": ["모자", "볼캡", "비니", "버킷햇", "캡", "후드"],
        "머리카락": ["모자", "볼캡", "비니", "버킷햇"],
        "숱": ["모자", "볼캡", "비니", "펌", "버킷햇", "셔츠", "니트"],
        "탈모": ["모자", "볼캡", "비니", "버킷햇", "캡", "안경", "선글라스"],
        "대머리": ["모자", "볼캡", "비니", "버킷햇"],
        "민머리": ["모자", "볼캡", "비니", "버킷햇"],
        "이마": ["모자", "볼캡", "비니", "버킷햇", "앞머리"],
        "M자": ["모자", "볼캡", "비니"],

        "탈모": [
            "모자", "볼캡", "비니", "버킷햇",  # 가리기용
            "셔츠", "카라", "자켓", "블레이저", # 시선 분산 (카라가 중요)
            "안경", "선글라스", "뿔테",         # 얼굴 중앙 포인트
            "터틀넥", "목폴라", "하이넥",       # 경계선 강조
            "니트", "가디건"                   # 포근한 느낌으로 시선 유도
        ],
        
        # (참고) 다른 체형 고민도 미리 넣어두면 좋습니다
        "뱃살": ["오버핏", "맨투맨", "후드", "박시", "루즈핏", "자켓"],
        "배": ["오버핏", "맨투맨", "후드", "박시", "자켓"],
        "키작남": ["크롭", "숏자켓", "슬림핏", "키높이", "세로줄", "스트라이프"],
        "키작은": ["크롭", "숏자켓", "슬림핏", "키높이", "세로줄", "스트라이프"],
        "뚱뚱한": ["오버핏", "블랙", "스트라이프", "와이드팬츠", "자켓"],
        "마른": ["레이어드", "니트", "가디건", "셔츠", "밝은색", "화이트"],

        # 긴생머리 -> 청순하고 여성스러운 룩 (뉴진스/수지 스타일)
        "긴생머리": ["원피스", "블라우스", "스커트", "가디건", "청순", "여리여리", "니트", "코트"],
        "생머리": ["원피스", "셔츠", "청바지", "청순", "화이트"],
        
        # 단발 -> 시크하거나 귀여운 룩
        "단발": ["자켓", "셔츠", "크롭", "귀여운", "시크", "맨투맨"],
        "태슬컷": ["자켓", "슬랙스", "셔츠", "모던", "시크"],
        
        # 웨이브 -> 러블리하고 우아한 룩
        "웨이브": ["원피스", "블라우스", "러블리", "우아한", "롱스커트"],
        
        # 똥머리/포니테일 -> 편안하고 스포티한 룩
        "똥머리": ["후드", "맨투맨", "트레이닝", "오버핏", "편한"],
        "포니테일": ["트레이닝", "크롭", "스포티", "조거팬츠"],

        # 게임/PC방 -> 장시간 앉아있어도 편한 옷
        "게임": ["트레이닝", "조거팬츠", "후드", "맨투맨", "반바지", "오버핏", "편한", "스웨트"],
        "피시방": ["후드", "맨투맨", "조거팬츠", "슬리퍼", "편한"],
        "PC방": ["후드", "맨투맨", "조거팬츠", "편한"],
        "롤": ["후드", "맨투맨", "트레이닝"], # 게임 이름 예시
        
        # 집/휴식 -> 홈웨어
        "집": ["파자마", "잠옷", "반바지", "트레이닝", "맨투맨", "홈웨어", "박시"],
        "방구석": ["파자마", "잠옷", "트레이닝", "반바지", "후드"],
        "동네": ["마실룩", "트레이닝", "후드", "맨투맨", "조거팬츠", "슬리퍼"],
        "편의점": ["트레이닝", "후드", "맨투맨", "반바지"],
        
        # 편안함 관련 형용사 -> 소재나 핏으로 연결
        "편한": ["밴딩", "와이드", "스웨트", "면", "오버핏", "트레이닝"],
        "편하게": ["밴딩", "와이드", "스웨트", "면", "오버핏"],
        "안불편한": ["스판", "밴딩", "와이드"],
        
        "하의": ["바지", "팬츠", "슬랙스", "청바지", "쇼츠", "스커트"],
        "바지": ["바지", "팬츠", "슬랙스", "청바지"],
        "반바지": ["쇼츠"],
        
        "운동": ["트레이닝", "레깅스", "쇼츠", "타이즈"],
        "트레이닝": ["트레이닝", "레깅스", "쇼츠"],
        "헬스": ["트레이닝", "쇼츠", "컴프레션"],
        "요가": ["레깅스", "브라탑"],
        "필라테스": ["레깅스", "브라탑"],
        "러닝": ["쇼츠", "레깅스", "바람막이"],

        # ★★★ [추가] 수면/취침 관련 키워드 (이걸 추가해야 '잠잘때'를 알아듣습니다) ★★★
        "잠": ["파자마", "잠옷", "수면", "홈웨어", "세트"],
        "잘때": ["파자마", "잠옷", "수면", "편한"],
        "수면": ["파자마", "잠옷", "수면", "극세사", "홈웨어"],
        "자려": ["파자마", "잠옷"],
        "꿀잠": ["파자마", "잠옷", "수면"],
        
        "패딩": ["패딩"],
        "코트": ["코트"],
        "자켓": ["자켓"],
        "누나": ["가디건", "니트", "블라우스", "자켓", "원피스", "코트"],
        "언니": ["가디건", "니트", "블라우스", "자켓", "원피스"],
        "여친": ["원피스", "스커트", "니트", "가디건", "커플"],
        "여자친구": ["원피스", "스커트", "니트", "가디건"],
        "엄마": ["코트", "자켓", "블라우스", "니트", "스카프"],
        
        # 형/남친 선물 -> 인기 남성 아이템 자동 매칭
        "형": ["셔츠", "니트", "맨투맨", "자켓", "후드"],
        "오빠": ["셔츠", "니트", "맨투맨", "자켓", "코트"],
        "남친": ["셔츠", "니트", "맨투맨", "자켓", "커플"],
        "남자친구": ["셔츠", "니트", "맨투맨", "자켓"],
        
        # 싸나이 -> 남성미 넘치는 옷
        "싸나이": ["자켓", "가죽", "셔츠", "코트", "수트", "블랙"],
        "사나이": ["자켓", "가죽", "셔츠", "코트", "수트"],
        
        # 선물 -> 무난하고 인기 많은 카테고리
        "선물": ["니트", "가디건", "파자마", "목도리", "장갑"],
        "생일": ["니트", "가디건", "원피스", "자켓"],

        # --- 2. 상황별 키워드 (여기가 핵심입니다!) ---
        # 사용자가 "설날"이라고 하면 -> 코트, 정장, 슬랙스를 자동으로 검색어에 추가
        "설날": ["코트", "자켓", "슬랙스", "셔츠", "블라우스", "정장", "단정한"],
        "명절": ["코트", "자켓", "셔츠", "블라우스", "니트", "단정한"],
        "추석": ["코트", "자켓", "셔츠", "블라우스", "니트"],
        
        "100일": ["원피스", "스커트", "블라우스", "코트", "자켓", "데이트", "러블리"],
        "기념일": ["원피스", "자켓", "코트", "셔츠", "데이트"],
        "데이트": ["원피스", "스커트", "코트", "자켓", "셔츠", "니트"],
        
        "크리스마스": ["레드", "초록", "체크", "니트", "코트", "벨벳", "목도리", "무스탕"],
        "성탄절": ["레드", "초록", "니트", "코트"],
        "연말": ["코트", "자켓", "무스탕", "원피스", "블랙", "파티"],
        "파티": ["원피스", "드레스", "자켓", "벨벳", "화려한"],
        
        "인생사진": ["원피스", "코트", "자켓", "블라우스", "색감", "화사한"],
        "여행": ["원피스", "바람막이", "편한", "모자", "선글라스"],
        
        "하객": ["원피스", "블라우스", "슬랙스", "자켓", "정장", "수트"],
        "결혼식": ["원피스", "블라우스", "슬랙스", "자켓", "정장", "수트"],

        # --- ★★★ 남자 연예인 스타일 (Namchin-Look) ★★★ ---
        # 댄디/깔끔파
        "차은우": ["코트", "자켓", "슬랙스", "니트", "가디건", "댄디", "남친룩", "화이트", "셔츠"],
        "은우": ["코트", "자켓", "니트", "댄디"],
        "송강": ["니트", "가디건", "셔츠", "슬랙스", "캐주얼", "남친룩"],
        "변우석": ["셔츠", "슬랙스", "자켓", "청바지", "깔끔한", "모델핏"],
        "공유": ["롱코트", "터틀넥", "니트", "가디건", "클래식", "분위기"],
        "박서준": ["자켓", "수트", "포멀", "슬랙스", "가죽자켓", "맨투맨"],
        
        # 힙/유니크파
        "지디": ["유니크", "스트릿", "자켓", "악세사리", "오버핏", "화려한", "트위드"],
        "지드래곤": ["유니크", "스트릿", "자켓", "빈티지"],
        "뷔": ["오버핏", "셔츠", "베스트", "와이드팬츠", "클래식", "패턴"],
        "정국": ["오버핏", "후드", "조거팬츠", "블랙", "스트릿", "편한"],
        
        # 스포티파
        "손흥민": ["트레이닝", "맨투맨", "후드", "바람막이", "운동복", "스포츠", "패딩"],

        # --- ★★★ 여자 연예인 스타일 (Wannabe-Look) ★★★ ---
        # 러블리/공주님파
        "장원영": ["블라우스", "스커트", "트위드", "원피스", "러블리", "핑크", "화이트", "리본"],
        "원영": ["블라우스", "스커트", "트위드", "미니"],
        "아이유": ["가디건", "원피스", "니트", "청순", "블라우스", "롱스커트"],
        "수지": ["청순", "원피스", "블라우스", "자켓", "코트", "긴생머리"],
        
        # 힙/트렌디파
        "제니": ["크롭", "자켓", "와이드팬츠", "힙한", "샤넬", "가디건", "선글라스"],
        "카리나": ["시크", "블랙", "레더", "부츠", "크롭", "스트릿", "무대의상"],
        "윈터": ["후드", "체크", "귀여운", "캐주얼", "니트"],
        "뉴진스": ["와이드", "오버핏", "후드", "스포티", "Y2K", "레트로", "청바지", "크롭"],
        
        # 시크/분위기파
        "한소희": ["블랙", "원피스", "자켓", "부츠", "시크", "고혹적인", "레더"],
        "김고은": ["자켓", "셔츠", "슬랙스", "심플", "모던", "코트", "내추럴"],

        # --- 상황별 키워드 ---
        "남친룩": ["코트", "니트", "가디건", "슬랙스", "셔츠", "깔끔한"],
        "여친룩": ["원피스", "스커트", "블라우스", "가디건", "러블리", "청순"],
        "하객": ["원피스", "블라우스", "슬랙스", "자켓", "정장"],
        "소개팅": ["원피스", "블라우스", "셔츠", "슬랙스", "자켓", "코트"],
        "크리스마스": ["레드", "초록", "체크", "니트", "코트", "벨벳"],
        "여행": ["원피스", "바람막이", "편한", "모자", "선글라스"],

        # --- 3. 색상 ---
        "빨간": ["레드", "빨강", "버건디"],
        "빨강": ["레드", "빨강", "버건디"],
        "레드": ["레드", "빨강", "버건디"],
        "검정": ["블랙", "검정"],
        "블랙": ["블랙", "검정"],
        "까만": ["블랙", "검정"],
        "흰색": ["화이트", "아이보리", "크림"],
        "화이트": ["화이트", "아이보리", "크림"],
        "하얀": ["화이트", "아이보리"],
        "파란": ["블루", "네이비"],
        "블루": ["블루", "네이비"],
        "초록": ["그린", "카키"],
        "그린": ["그린", "카키"],
        "노란": ["옐로우", "베이지"],
        
        # --- 4. 스타일 ---
        "편한": ["맨투맨", "후드", "조거팬츠", "트레이닝"],
        "정장": ["셔츠", "블라우스", "슬랙스", "자켓", "수트"],
    }
    
    # 성별에 따른 추가 로직 (기존 유지)
    if gender == "남성":
        keyword_patterns.update({
            "출근": ["셔츠", "슬랙스", "자켓"],
            "면접": ["정장", "수트", "셔츠", "넥타이"]
        })
    elif gender == "여성":
        keyword_patterns.update({
            "출근": ["블라우스", "스커트", "자켓", "슬랙스"],
            "면접": ["블라우스", "자켓", "스커트", "슬랙스"]
        })

    words = query.split()
    keywords = []
    
    for word in words:
        if word in stopwords or len(word) <= 1:
            continue
            
        matched = False
        for pattern, expanded in keyword_patterns.items():
            if pattern in word:
                keywords.extend(expanded)
                matched = True
                # break를 빼면 하나의 단어가 여러 카테고리에 걸릴 수 있음 (더 풍부한 검색)
                # break 
        
        # 매칭 안 된 단어도 검색에 포함시킬지 여부 (여기선 매칭된 것 위주로)
        # if not matched:
        #    keywords.append(word)
    
    return list(set(keywords))


# 1. 텍스트 검색 API
@router.post("/search", response_model=List[Product])
async def search_products(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    query = request.query
    clean_query = query.replace("추천해줘", "").replace("추천", "").strip()
    if not clean_query: 
        clean_query = query

    print(f"🔍 검색어: {query} -> {clean_query}")

    if not model or not processor:
        raise HTTPException(status_code=500, detail="AI Model not loaded")

    # 필터 추출
    filters = extract_filters(clean_query)
    print(f"🎯 필터: 성별={filters['gender']}, 계절={filters['season']}")

    # 텍스트 → 벡터
    inputs = processor(
        text=clean_query, 
        return_tensors="pt", 
        padding=True, 
        truncation=True,
        max_length=77
    ).to(DEVICE)
    
    text_features = model.get_text_features(**inputs)
    text_features = F.normalize(text_features, p=2, dim=1)
    query_vector = text_features[0].cpu().detach().numpy().tolist()

    # ★ gender 전달 (핵심!)
    core_keywords = extract_core_keywords(clean_query, gender=filters['gender'])
    print(f"🔑 추출된 키워드: {core_keywords}")
    
    # 쿼리 타입 분석
    if len(core_keywords) == 1 and core_keywords[0] in ["레깅스", "패딩", "자켓", "원피스", "스커트", "쇼츠"]:
        # 단일 카테고리 검색
        print(f"📌 카테고리 검색 모드")
        results = await crud_product.search_products_by_text_vector(
            db, 
            query_vector, 
            top_k=20,
            threshold=0.35,
            keywords=core_keywords,
            season_filter=filters['season'],
            gender_filter=filters['gender']
        )
    elif len(core_keywords) >= 1:
        # 복합 검색
        print(f"📌 복합 검색 모드")
        results = await crud_product.search_products_by_text_vector(
            db, 
            query_vector, 
            top_k=20,
            threshold=0.30,
            keywords=core_keywords,
            season_filter=filters['season'],
            gender_filter=filters['gender']
        )
    else:
        # 벡터 검색만
        print(f"📌 벡터 검색 모드")
        results = await crud_product.search_products_by_text_vector(
            db, 
            query_vector, 
            top_k=20,
            threshold=0.35,
            keywords=None,
            season_filter=filters['season'],
            gender_filter=filters['gender']
        )
    
    return results


# 2. 다른 색상 보기 API
@router.get("/{product_id}/colors", response_model=List[Product])
async def get_color_variations(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
    current_product = await crud_product.get_product(db, product_id)
    if not current_product:
        raise HTTPException(status_code=404, detail="Product not found")

    variations = await crud_product.get_similar_products_by_name(
        db, 
        current_product.name, 
        product_id
    )
    return variations


# 3. 상품 생성 API
@router.post("/", response_model=Product)
async def create_new_product(
    product: ProductCreate, 
    db: AsyncSession = Depends(get_db)
):
    return await crud_product.create_product(db=db, product=product)


# 4. 상품 목록 조회 API
@router.get("/", response_model=List[Product])
async def read_all_products(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    products = await crud_product.get_products(db, skip=skip, limit=limit)
    return products


# 5. 특정 상품 조회 API
@router.get("/{product_id}", response_model=Product)
async def read_single_product(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
    db_product = await crud_product.get_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product