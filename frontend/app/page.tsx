"use client";

import { useEffect, useState } from "react";
import styles from "./wine-recommend.module.css";
import { fetchRecommendation, imageUrl, type WineCard, type WineType } from "./api";

const COMPANION_TYPE: Record<WineType, WineType> = { Red: "White", White: "Sparkling", Sparkling: "Red" };
const TIER_CAP_COLORS = [
  "#D8CDBB", "#D8CDBB", "#C9A24B", "#C9A24B", "#C9A24B",
  "#C9A24B", "#7A1F2B", "#7A1F2B", "#7A1F2B", "#7A1F2B",
];
const GLASS_COLOR: Record<WineType, string> = { Red: "#5C1F2E", White: "#C9BC79", Sparkling: "#D8C687" };

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

export default function Home() {
  const [isIntro, setIsIntro] = useState(true);
  const [introStep, setIntroStep] = useState(0);
  const [typeAnswer, setTypeAnswer] = useState<WineType>("Red");
  const [regionIndex, setRegionIndex] = useState(0);
  const [countryIndex, setCountryIndex] = useState(0);
  const [tierIndex, setTierIndex] = useState(0);
  const [pairingText, setPairingText] = useState("");
  const [pairingInput, setPairingInput] = useState("");
  const [cards, setCards] = useState<Record<"a" | "b", CardState>>({
    a: { visible: true, saved: false, swap: 0 },
    b: { visible: true, saved: false, swap: 0 },
  });
  const [cardData, setCardData] = useState<Record<"a" | "b", WineCard | null>>({ a: null, b: null });
  const [loading, setLoading] = useState(false);

  function selectIntro(stepIdx: number, value: string | number) {
    if (stepIdx === 1) setTierIndex(Number(value));
    if (stepIdx === 2) setTypeAnswer(value as WineType);
    if (stepIdx < 2) {
      setIntroStep(stepIdx + 1);
    } else {
      setIsIntro(false);
    }
  }

  useEffect(() => {
    if (isIntro) return;
    setLoading(true);
    const typeB = COMPANION_TYPE[typeAnswer];
    Promise.all([
      fetchRecommendation({ priceTier: tierIndex, countryIndex, regionIndex, wineType: typeAnswer, pairingText }),
      fetchRecommendation({ priceTier: tierIndex, countryIndex, regionIndex, wineType: typeB, pairingText }),
    ])
      .then(([a, b]) => setCardData({ a, b }))
      .finally(() => setLoading(false));
  }, [isIntro, typeAnswer, countryIndex, regionIndex, tierIndex, pairingText]);

  function bumpAll() {
    setCards((c) => ({ a: { ...c.a, swap: c.a.swap + 1 }, b: { ...c.b, swap: c.b.swap + 1 } }));
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
  function submitPairing() {
    setPairingText(pairingInput.trim());
    bumpAll();
  }
  function toggleSave(id: "a" | "b") {
    setCards((c) => ({ ...c, [id]: { ...c[id], saved: !c[id].saved } }));
  }
  function exclude(id: "a" | "b") {
    setCards((c) => ({ ...c, [id]: { ...c[id], visible: false } }));
  }
  function resetCards() {
    setCards((c) => ({
      a: { visible: true, saved: c.a.saved, swap: c.a.swap + 1 },
      b: { visible: true, saved: c.b.saved, swap: c.b.swap + 1 },
    }));
  }

  const visibleCardIds = (["a", "b"] as const).filter((id) => cards[id].visible && cardData[id]);
  const anyHidden = !(cards.a.visible && cards.b.visible);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.brand}>SIP.</div>
        <div className={styles.tagline}>AI 소믈리에가 지금 이 순간에 맞는 와인을 골라줘요</div>
      </div>

      {isIntro ? (
        <div className={styles.introSection}>
          <div className={styles.dots}>
            {INTRO_STEPS.map((_, i) => (
              <div key={i} className={i <= introStep ? `${styles.dot} ${styles.dotActive}` : styles.dot} />
            ))}
          </div>
          <div key={introStep} className={styles.stepCard}>
            <div className={styles.stepLabel}>Step {introStep + 1} / 3</div>
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
                const type = id === "a" ? typeAnswer : COMPANION_TYPE[typeAnswer];
                return (
                  <div key={`${id}-${cards[id].swap}`} className={styles.card}>
                    <button type="button" onClick={() => toggleSave(id)} className={cards[id].saved ? `${styles.saveBtn} ${styles.saveBtnActive}` : styles.saveBtn}>
                      &#9825;
                    </button>
                    <button type="button" onClick={() => exclude(id)} className={styles.excludeBtn}>&#10005;</button>

                    <div className={styles.bottleWrap}>
                      <div className={styles.bottleAnim}>
                        <div className={styles.cap} style={{ background: TIER_CAP_COLORS[tierIndex] }} />
                        <div className={styles.neck} style={{ background: GLASS_COLOR[type] }} />
                        <div className={styles.shoulder} style={{ borderBottomColor: GLASS_COLOR[type] }} />
                        <div className={styles.bottleBody} style={{ background: GLASS_COLOR[type] }}>
                          {imageUrl(card.pdata_id) ? (
                            <img src={imageUrl(card.pdata_id)!} alt={card.wine_name} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain" }} />
                          ) : (
                            <div className={styles.labelPatch}>
                              <div className={styles.labelRegion}>{card.region}</div>
                              <div className={styles.labelGrape}>{card.grape}</div>
                            </div>
                          )}
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
              <input
                type="text"
                value={pairingInput}
                onChange={(e) => setPairingInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitPairing()}
                placeholder="같이 먹을 음식"
                className={styles.option}
                style={{ fontSize: 13, padding: "8px 12px", width: 120 }}
              />
              <button type="button" onClick={submitPairing} className={styles.joyBtn}>
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
