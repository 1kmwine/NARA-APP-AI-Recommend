import json
from collections import Counter

# NARA-DATA-Wine-Info의 quicklook/wine-info/helpers.php REGION_COUNTRY_OVERRIDE를
# 그대로 이식(2026-07-13 기준 실데이터). place.ko(지역명, 자유텍스트)로 국가를
# 역산하기 위한 표 — integrated_item_info.countryName은 ERP 매핑 누락으로 상당수가
# "Korea"로 잘못 들어있어 신뢰할 수 없다.
REGION_COUNTRY_OVERRIDE: dict[str, str] = {
    "가스꼬뉴": "France", "가스코뉴": "France", "갈라시아": "Spain", "까딸루냐": "Spain",
    "까리레나": "Spain", "까스띨랴 이 레온": "Spain", "까오르": "France", "까탈루냐": "Spain",
    "꼬뜨 뒤 론": "France", "꼬뜨 드 가스꼬뉴": "France", "꼬뜨 드 본": "France",
    "끼안티": "Italy", "나바라": "Spain", "나이아가라 페닌슐라": "Canada", "나파밸리": "USA",
    "나헤": "Germany", "남 프랑스": "France", "네메아": "Greece", "노스 아일랜드": "New Zealand",
    "뉘른베르크": "Germany", "뉴 사우스 웨일즈": "Australia", "니더외스터라이히": "Austria",
    "니바라": "Spain", "도우로": "Portugal", "도우루": "Portugal", "라 만차": "Spain",
    "라인가우": "Germany", "라인하센": "Germany", "라치오": "Italy", "라펠": "Chile",
    "라펠 밸리": "Chile", "라펠밸리": "Chile", "랑그독": "France", "랑그독 루시옹": "France",
    "랑그독 루씨용": "France", "론": "France", "론 밸리": "France", "롬바르디아": "Italy",
    "루시용": "France", "루씨옹": "France", "루씨용": "France", "루아르": "France",
    "루아르 밸리": "France", "루에다": "Spain", "리베라 델 두에로": "Spain", "리스본": "Portugal",
    "리아스 바이사스": "Spain", "리오하": "Spain", "마가렛 리버": "Australia", "마데이라": "Portugal",
    "마드라드": "Spain", "마드리드": "Spain", "마르께": "Italy", "마르케": "Italy",
    "마울레 밸리": "Chile", "마이포 밸리": "Chile", "마틴로보": "New Zealand", "마틴보로": "New Zealand",
    "말보로": "New Zealand", "말보르": "New Zealand", "맥라렌 베일": "Australia", "멘도사": "Argentina",
    "멘도자": "Argentina", "모젤": "Germany", "모젤-자르-루버": "Germany", "몬탈치노": "Italy",
    "몰도바": "Moldova", "무르시아": "Spain", "미뉴": "Portugal", "바로사 밸리": "Australia",
    "바실리카타": "Italy", "바이에른": "Germany", "발데오라스": "Spain", "발렌시아": "Spain",
    "베네토": "Italy", "베어 리버": "USA", "베카 밸리": "Lebanon", "보드로": "France",
    "보르도": "France", "보졸레": "France", "부르게란트": "Austria", "부르겐란트": "Austria",
    "부르고뉴": "France", "비뉴 베르데": "Portugal", "비에조": "Spain", "비파바 밸리": "Slovenia",
    "빅토리아": "Australia", "뿔리아": "Italy", "사르데냐": "Italy", "사우스 아일랜드": "New Zealand",
    "사우스 오스트레일리아": "Australia", "사우스 웨스트 프랑스": "France",
    "사우스 이스턴 오스트레일리아": "Australia", "사우스웨스트 프랑스": "France",
    "산 후안": "Argentina", "살렌토": "Italy", "살타": "Argentina", "상파뉴": "France",
    "샴페인": "France", "샹파뉴": "France", "서던 프랑스": "France", "센터럴 밸리": "Chile",
    "센트럴 밸리": "Chile", "슈타이어마르크": "Austria", "스테판 보다": "Moldova",
    "스텔렌보쉬": "South Africa", "시칠리아": "Italy", "아라곤": "Spain", "아르곤": "Spain",
    "아부르쪼": "Italy", "아브루쪼": "Italy", "아콩카구아": "Chile", "알리칸테": "Spain",
    "알베르뉴": "France", "알자스": "France", "알토 아디제": "Italy", "애들레이드 힐즈": "Australia",
    "에밀리아 로마냐": "Italy", "예클라": "Spain", "오레곤": "USA", "오리건": "USA",
    "오리건주": "USA", "온타리오": "Canada", "움브리아": "Italy", "워싱턴": "USA",
    "워싱턴주": "USA", "웨스턴  오스트레일리아": "Australia", "웨스턴 오스트레일리아": "Australia",
    "웨스턴 케이프": "South Africa", "쥐라": "France", "지공다스": "France",
    "카사블랑카 밸리": "Chile", "카스티야": "Spain", "카스티야 이 레이온": "Spain",
    "카탈루냐": "Spain", "칼라타유드": "Spain", "캄파니아": "Italy", "캄프탈": "Austria",
    "캘리포니아": "USA", "캘리포니이": "USA", "켄터키": "USA", "코드루": "Moldova",
    "코르시": "France", "코르시카": "France", "코스탈 리전": "South Africa",
    "코스탈 리젼": "South Africa", "콜롬비아 밸리": "USA", "콜차구아 밸리": "Chile",
    "콜차구아밸리": "Chile", "쿠리코 밸리": "Chile", "타즈마니아": "Australia", "토로": "Spain",
    "토스카나": "Italy", "토카이": "Hungary", "트렌티노": "Italy", "팔츠": "Germany",
    "페네데스": "Spain", "페이독": "France", "펠로폰네소스": "Greece", "포르토": "Portugal",
    "포트": "Portugal", "풀리아": "Italy", "프로방스": "France", "프리모르예": "Slovenia",
    "프리오랏": "Spain", "프리울리 베네찌아 줄리아": "Italy", "플라 데 바제스": "Spain",
    "피에": "Italy", "피에몬테": "Italy", "헤레즈-헤레스-셰리": "Spain",
    "헤레즈헤레스셰리": "Spain",
}

# 표기 통일(오탈자/띄어쓰기) + 의도적 병합(나파밸리→캘리포니아 지역 그룹으로 표시).
REGION_ALIAS: dict[str, str] = {
    "가스꼬뉴": "가스코뉴", "까딸루냐": "카탈루냐", "까스띨랴 이 레온": "카스티야 이 레이온",
    "까탈루냐": "카탈루냐", "나파밸리": "캘리포니아", "니바라": "나바라", "도우로": "도우루",
    "라펠밸리": "라펠 밸리", "랑그독 루씨용": "랑그독 루시옹", "루씨옹": "루시용",
    "루씨용": "루시용", "마드라드": "마드리드", "마르께": "마르케", "마틴로보": "마틴보로",
    "말보르": "말보로", "뿔리아": "풀리아", "사우스웨스트 프랑스": "사우스 웨스트 프랑스",
    "상파뉴": "샴페인", "샹파뉴": "샴페인", "센터럴 밸리": "센트럴 밸리",
    "소노마 카운티": "소노마", "소노마 코스트": "소노마", "소노마 코스트ㅜ": "소노마",
    "소노마카운티": "소노마", "아르곤": "아라곤", "아부르쪼": "아브루쪼", "오레곤": "오리건",
    "오리건주": "오리건", "워싱턴주": "워싱턴", "웨스턴  오스트레일리아": "웨스턴 오스트레일리아",
    "캘리포니이": "캘리포니아", "코르시": "코르시카", "코스탈 리전": "코스탈 리젼",
    "콜차구아밸리": "콜차구아 밸리", "피에": "피에몬테", "헤레즈헤레스셰리": "헤레즈-헤레스-셰리",
}

# 칠레 AVA를 상위 지역으로 병합.
REGION_EXPAND: dict[str, str] = {
    "라펠 밸리": "센트럴 밸리", "라펠밸리": "센트럴 밸리", "콜차구아 밸리": "센트럴 밸리",
    "콜차구아밸리": "센트럴 밸리", "아콩카구아 밸리": "센트럴 밸리", "아콩카구아": "센트럴 밸리",
    "마이포 밸리": "센트럴 밸리", "카사블랑카 밸리": "센트럴 밸리", "쿠리코 밸리": "센트럴 밸리",
    "마울레 밸리": "센트럴 밸리",
}


def extract_raw_region(place_json: str | None) -> str:
    if not place_json:
        return ""
    try:
        data = json.loads(place_json)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("ko") or "").strip()


def region_to_country(raw_region: str) -> str | None:
    return REGION_COUNTRY_OVERRIDE.get(raw_region)


def normalize_region_label(raw_region: str) -> str:
    label = REGION_ALIAS.get(raw_region, raw_region)
    return REGION_EXPAND.get(label, REGION_EXPAND.get(raw_region, label))


def canonical_country_from_votes(
    row_countries: list[str | None], fallback_raw_country: str | None
) -> str:
    votes = Counter(c for c in row_countries if c is not None)
    if votes:
        return votes.most_common(1)[0][0]
    return fallback_raw_country if fallback_raw_country else "기타"
