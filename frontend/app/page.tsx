"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import styles from "./wine-recommend.module.css";
import { fetchRecommendation, imageUrl, type WineCard, type WineType } from "./api";
import {
  addExcludedWine,
  addLikedWine,
  getDislikedTasteAverage,
  getExcludedItemCds,
  getLikedTasteAverage,
  isLiked,
  removeLikedWine,
} from "./preferences";

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

type CardId = "a" | "b";
const CARD_IDS: CardId[] = ["a", "b"];

interface CardState {
  visible: boolean;
  saved: boolean;
  swap: number;
}

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

function slotForCard(id: CardId): number {
  return id === "a" ? 0 : 1;
}

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
  const [cards, setCards] = useState<Record<CardId, CardState>>({
    a: { visible: true, saved: false, swap: 0 },
    b: { visible: true, saved: false, swap: 0 },
  });
  const [cardData, setCardData] = useState<Record<CardId, WineCard | null>>({ a: null, b: null });
  const [loading, setLoading] = useState(false);

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
    setCards({
      a: { visible: true, saved: false, swap: 0 },
      b: { visible: true, saved: false, swap: 0 },
    });
  }

  useEffect(() => {
    if (isIntro) return;
    let ignore = false;
    setLoading(true);
    const excludeItemCds = getExcludedItemCds();
    const likedTaste = getLikedTasteAverage();
    const dislikedTaste = getDislikedTasteAverage();
    Promise.all(
      CARD_IDS.map((id) =>
        fetchRecommendation({
          priceTier: tierIndex,
          countryIndex,
          regionIndex,
          wineType: typeAnswer,
          pairingText,
          slot: slotForCard(id),
          excludeItemCds,
          likedTaste,
          dislikedTaste,
        })
      )
    )
      .then(([a, b]) => {
        if (!ignore) {
          setCardData({ a, b });
          // 이 와인 예전에 찜한 적 있으면 하트가 눌린 상태로 보여야 함
          setCards((c) => ({
            a: { ...c.a, saved: a ? isLiked(a.item_cd) : false },
            b: { ...c.b, saved: b ? isLiked(b.item_cd) : false },
          }));
        }
      })
      .catch(() => {
        if (!ignore) setCardData({ a: null, b: null });
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [isIntro, typeAnswer, countryIndex, regionIndex, tierIndex, pairingText]);

  function bumpAll() {
    // 방향키(가격/지역/국가/페어링)를 누르면 새로 추천을 받는 거니까, 이전에 배제(X)
    // 했던 자리도 다시 채워서 2개로 보여준다 — 배제는 "이번 조합에서 이 와인만 빼줘"
    // 정도의 일시적 액션이지, 자리 자체를 계속 비워두라는 뜻은 아니다.
    setCards((c) => ({
      a: { ...c.a, visible: true, swap: c.a.swap + 1 },
      b: { ...c.b, visible: true, swap: c.b.swap + 1 },
    }));
  }
  function priceUp() {
    if (tierIndex >= 9) return;
    setTierIndex((t) => t + 1);
    bumpAll();
  }
  function priceDown() {
    if (tierIndex <= 0) return;
    setTierIndex((t) => t - 1);
    bumpAll();
  }
  function regionNext() {
    setRegionIndex((r) => r + 1);
    bumpAll();
  }
  function countryNext() {
    setCountryIndex((c) => c + 1);
    setRegionIndex(0);
    bumpAll();
  }
  function submitCustom() {
    setPairingText(pairingCustom.trim());
    bumpAll();
  }
  function selectPairing(value: string) {
    setPairingChoice(value);
    if (value !== "custom") {
      setPairingText(value);
      bumpAll();
    }
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
    bumpAll();
  }
  function toggleSave(id: CardId) {
    const card = cardData[id];
    const willSave = !cards[id].saved;
    if (card) {
      // AI가 "좋아하는 취향" 학습하는 신호 — 하트한 와인 목록 + 취향 평균에 반영됨
      if (willSave) addLikedWine(card);
      else removeLikedWine(card.item_cd);
    }
    setCards((c) => ({ ...c, [id]: { ...c[id], saved: willSave } }));
  }
  function exclude(id: CardId) {
    const card = cardData[id];
    // AI가 "싫어하는 취향" 학습하는 신호 — 이 와인은 다음부터 아예 후보에서 빠지고,
    // 취향 평균에도 반영돼서 비슷한 와인의 순위가 낮아진다
    if (card) addExcludedWine(card.item_cd, card.taste);
    setCards((c) => ({ ...c, [id]: { ...c[id], visible: false } }));
  }
  function resetCards() {
    setCards((c) => ({
      a: { visible: true, saved: c.a.saved, swap: c.a.swap + 1 },
      b: { visible: true, saved: c.b.saved, swap: c.b.swap + 1 },
    }));
  }

  const visibleCardIds = CARD_IDS.filter((id) => cards[id].visible && cardData[id]);
  const anyHidden = !(cards.a.visible && cards.b.visible);

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
        <>
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
              {!loading && visibleCardIds.map((id) => {
                const card = cardData[id]!;
                return (
                  <div
                    key={`${id}-${cards[id].swap}`}
                    className={styles.card}
                    onClick={() => window.open(wineDetailUrl(card.item_cd), "_blank", "noopener,noreferrer")}
                  >
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); toggleSave(id); }}
                      className={cards[id].saved ? `${styles.saveBtn} ${styles.saveBtnActive}` : styles.saveBtn}
                    >
                      &#9825;
                    </button>
                    <button type="button" onClick={(e) => { e.stopPropagation(); exclude(id); }} className={styles.excludeBtn}>&#10005;</button>

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

                    <div className={styles.note}>{card.note}</div>

                    <div className={styles.personaBox}>
                      <div className={styles.personaLine}>&ldquo;{card.persona_line}&rdquo;</div>
                    </div>
                  </div>
                );
              })}
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

          {anyHidden && (
            <div className={styles.resetWrap}>
              <button type="button" onClick={resetCards} className={styles.resetLink}>추천 다시 두 개 보기</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
