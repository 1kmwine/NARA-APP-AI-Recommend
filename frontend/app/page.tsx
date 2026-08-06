"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import styles from "./wine-recommend.module.css";
import { fetchBracket, imageUrl, type BracketCard, type WineType } from "./api";
import { useBracket } from "./useBracket";

const REAL_FOODS = [
  { id: "삼겹살", label: "삼겹살" },
  { id: "치킨", label: "치킨" },
  { id: "스테이크", label: "스테이크" },
  { id: "파스타", label: "파스타" },
  { id: "초밥", label: "초밥" },
  { id: "치즈", label: "치즈 플래터" },
  { id: "매운탕", label: "매운탕" },
  { id: "피자", label: "피자" },
  { id: "디저트", label: "디저트" },
];
const FOODS = [...REAL_FOODS, { id: "custom", label: "직접 입력하기" }];
const WINE_DETAIL_BASE = "http://192.168.47.105/NID/wine-info/view.php";

const INTRO_STEPS: { question: string; options: { id: string | number; label: string }[] }[] = [
  {
    question: "오늘은 어떤 자리야?",
    options: [
      { id: "gift", label: "선물할 와인" },
      { id: "party", label: "파티, 다 같이" },
      { id: "solo", label: "혼자, 편하게" },
      { id: "anniversary", label: "기념일, 특별하게" },
    ],
  },
  {
    question: "가격대는 얼마쯤 생각해?",
    options: [
      { id: 0, label: "1만원 이하" }, { id: 1, label: "2만원대" }, { id: 2, label: "3만원대" },
      { id: 3, label: "5만원대" }, { id: 4, label: "7만원대" }, { id: 5, label: "10만원대" },
      { id: 6, label: "30만원대" }, { id: 7, label: "100만원대" }, { id: 8, label: "1000만원대" },
      { id: 9, label: "1000만원 이상" },
    ],
  },
  {
    question: "어떤 스타일이 끌려?",
    options: [
      { id: "Red", label: "레드" },
      { id: "White", label: "화이트" },
      { id: "Sparkling", label: "스파클링" },
    ],
  },
];

const AXIS_TITLE: Record<string, string> = {
  acidity: "산도가 다른 두 와인 — 뭐가 더 끌려?",
  aroma: "향이 다른 두 와인 — 뭐가 더 끌려?",
  story: "이야기가 있는 두 와인 — 뭐가 더 끌려?",
  philosophy: "철학이 다른 두 와인 — 뭐가 더 끌려?",
  semifinal: "준결승 — 뭐가 더 끌려?",
  final: "결승 — 최종 선택은?",
};

function wineDetailUrl(itemCd: string): string {
  return `${WINE_DETAIL_BASE}?itemCd=${encodeURIComponent(itemCd)}&cat=wine`;
}

export default function Home() {
  const [isIntro, setIsIntro] = useState(true);
  const [introStep, setIntroStep] = useState(0);
  const [typeAnswer, setTypeAnswer] = useState<WineType>("Red");
  const [regionIndex, setRegionIndex] = useState(0);
  const [countryIndex, setCountryIndex] = useState(0);
  const [tierIndex, setTierIndex] = useState(0);
  const [pairingText, setPairingText] = useState("");
  const [pairingChoice, setPairingChoice] = useState("");
  const [pairingCustom, setPairingCustom] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const bracket = useBracket();

  function selectIntro(stepIdx: number, value: string | number) {
    if (stepIdx === 1) setTierIndex(Number(value));
    if (stepIdx === 2) setTypeAnswer(value as WineType);
    if (stepIdx < 2) {
      setIntroStep(stepIdx + 1);
    } else {
      const pick = REAL_FOODS[Math.floor(Math.random() * REAL_FOODS.length)];
      setPairingChoice(pick.id);
      setPairingText(pick.id);
      setIsIntro(false);
    }
  }

  function goToStart() {
    setIsIntro(true);
    setIntroStep(0);
    setTierIndex(0);
    setRegionIndex(0);
    setCountryIndex(0);
    setPairingText("");
    setPairingChoice("");
    setPairingCustom("");
  }

  useEffect(() => {
    if (isIntro) return;
    let ignore = false;
    setLoading(true);
    setLoadError(false);
    fetchBracket({ priceTier: tierIndex, countryIndex, regionIndex, wineType: typeAnswer, pairingText })
      .then((data) => {
        if (!ignore) bracket.reset(data);
      })
      .catch(() => {
        if (!ignore) setLoadError(true);
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isIntro, typeAnswer, countryIndex, regionIndex, tierIndex, pairingText]);

  function priceUp() {
    if (tierIndex >= 9) return;
    setTierIndex((t) => t + 1);
  }
  function priceDown() {
    if (tierIndex <= 0) return;
    setTierIndex((t) => t - 1);
  }
  function regionNext() {
    setRegionIndex((r) => r + 1);
  }
  function countryNext() {
    setCountryIndex((c) => c + 1);
    setRegionIndex(0);
  }
  function submitCustom() {
    setPairingText(pairingCustom.trim());
  }
  function selectPairing(value: string) {
    setPairingChoice(value);
    if (value !== "custom") setPairingText(value);
  }
  function confirmPairing() {
    if (pairingChoice === "custom") {
      submitCustom();
      return;
    }
    const idx = REAL_FOODS.findIndex((f) => f.id === pairingChoice);
    const next = REAL_FOODS[(idx + 1 + REAL_FOODS.length) % REAL_FOODS.length];
    setPairingChoice(next.id);
    setPairingText(next.id);
  }

  function renderCard(card: BracketCard, showFullDetail: boolean) {
    return (
      <div
        key={card.item_cd}
        className={styles.card}
        onClick={() => bracket.pickWinner(card)}
      >
        <div className={styles.bottleWrap}>
          <div className={styles.bottleAnim}>
            {imageUrl(card.pdata_id) && (
              <img
                src={imageUrl(card.pdata_id)!}
                alt={card.wine_name}
                className={styles.bottleImg}
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                  e.currentTarget.nextElementSibling?.classList.remove(styles.hidden);
                }}
              />
            )}
            <div className={imageUrl(card.pdata_id) ? `${styles.labelPatch} ${styles.hidden}` : styles.labelPatch}>
              <div className={styles.labelRegion}>{card.region}</div>
              <div className={styles.labelGrape}>{card.grape}</div>
            </div>
          </div>
        </div>

        <div className={styles.wineName}>{card.wine_name}</div>
        <div className={styles.wineMeta}>{card.region}, {card.country} · {card.type_label_kr}</div>

        <div className={styles.priceRow}>
          <span className={styles.price}>₩{card.price_krw.toLocaleString()}</span>
          <span className={styles.priceDesc}>{card.price_desc}</span>
        </div>

        {!showFullDetail && <div className={styles.axisLabel}>{card.axis_label}</div>}

        {showFullDetail && (
          <>
            <div className={styles.note}>{card.note}</div>
            <div className={styles.personaBox}>
              <div className={styles.personaLine}>&ldquo;{card.persona_line}&rdquo;</div>
            </div>
            <a
              href={wineDetailUrl(card.item_cd)}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.resetLink}
              onClick={(e) => e.stopPropagation()}
            >
              상세 정보 보기 ↗
            </a>
          </>
        )}
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div />
        <div className={styles.brand}>AI 와인 추천</div>
        <div className={styles.headerRight}>
          <div className={styles.tagline}>AI 소믈리에가 지금 이 순간에 맞는 와인을 골라줘요</div>
          <Link href="/liked" className={styles.backToStart}>
            찜한 와인
          </Link>
          {!isIntro && (
            <button type="button" onClick={goToStart} className={styles.backToStart}>
              처음으로
            </button>
          )}
        </div>
      </div>

      {isIntro ? (
        <div className={styles.introSection}>
          <div className={styles.dots}>
            {INTRO_STEPS.map((_, i) => (
              <div key={i} className={i <= introStep ? `${styles.dot} ${styles.dotActive}` : styles.dot} />
            ))}
          </div>
          <div key={introStep} className={styles.stepCard}>
            <div className={styles.stepHeader}>
              {introStep > 0 && (
                <button type="button" onClick={() => setIntroStep((s) => s - 1)} className={styles.stepBack}>
                  &#8592; 이전
                </button>
              )}
              <div className={styles.stepLabel}>Step {introStep + 1} / 3</div>
            </div>
            <div className={styles.question}>{INTRO_STEPS[introStep].question}</div>
            <div className={styles.options}>
              {INTRO_STEPS[introStep].options.map((opt) => (
                <button key={opt.id} type="button" className={styles.option} onClick={() => selectIntro(introStep, opt.id)}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className={styles.stage}>
          <div className={styles.priceUpWrap}>
            <button type="button" onClick={priceUp} disabled={tierIndex >= 9} className={tierIndex >= 9 ? `${styles.joyBtn} ${styles.joyBtnDisabled}` : styles.joyBtn}>
              <span className={styles.joyAccent}>&#9650;</span>
            </button>
            <div className={`${styles.joyLabel} ${styles.joyAccent}`}>가격 UP</div>
          </div>

          <div className={styles.regionWrap}>
            <button type="button" onClick={countryNext} className={styles.joyBtn}>
              <span className={styles.joyRegion}>&#9668;&#9668;</span>
            </button>
            <button type="button" onClick={regionNext} className={styles.joyBtn}>
              <span className={styles.joyRegion}>&#9664;</span>
            </button>
            <div className={`${styles.joyLabel} ${styles.joyRegion}`}>지역<br />변경</div>
          </div>

          <div className={styles.cardsRow}>
            {loading && <div className={styles.note}>추천 찾는 중...</div>}
            {!loading && loadError && <div className={styles.note}>추천을 못 찾았어요. 가격대나 지역을 바꿔보세요.</div>}
            {!loading && !loadError && bracket.currentMatch && (
              <>
                <div className={styles.bracketTitle}>{AXIS_TITLE[bracket.currentMatch.axis] ?? "뭐가 더 끌려?"}</div>
                <div className={styles.cardsRow}>
                  {bracket.currentMatch.cards.map((card) =>
                    renderCard(card, bracket.currentMatch!.phase === "final" || bracket.currentMatch!.phase === "semifinal")
                  )}
                </div>
              </>
            )}
            {!loading && !loadError && !bracket.currentMatch && bracket.winner && (
              <div className={styles.finalWrap}>
                <div className={styles.bracketTitle}>이 와인이야!</div>
                {renderCard(bracket.winner, true)}
              </div>
            )}
          </div>

          <div className={styles.pairingWrap}>
            <select
              value={pairingChoice}
              onChange={(e) => selectPairing(e.target.value)}
              className={styles.pairingSelect}
            >
              {FOODS.map((food) => (
                <option key={food.id} value={food.id}>{food.label}</option>
              ))}
            </select>
            {pairingChoice === "custom" && (
              <input
                type="text"
                value={pairingCustom}
                onChange={(e) => setPairingCustom(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitCustom()}
                placeholder="직접 입력"
                className={styles.pairingCustomInput}
              />
            )}
            <button type="button" onClick={confirmPairing} className={styles.joyBtn}>
              <span className={styles.joyPairing}>&#9654;</span>
            </button>
            <div className={`${styles.joyLabel} ${styles.joyPairing}`}>페어링<br />검색</div>
          </div>

          <div className={styles.priceDownWrap}>
            <button type="button" onClick={priceDown} disabled={tierIndex <= 0} className={tierIndex <= 0 ? `${styles.joyBtn} ${styles.joyBtnDisabled}` : styles.joyBtn}>
              <span className={styles.joyAccent}>&#9660;</span>
            </button>
            <div className={`${styles.joyLabel} ${styles.joyAccent}`}>가격 DOWN</div>
          </div>
        </div>
      )}
    </div>
  );
}
