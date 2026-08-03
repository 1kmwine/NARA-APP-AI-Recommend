"use client";

import { useState } from "react";
import styles from "./wine-recommend.module.css";

type WineType = "red" | "white" | "sparkling";
type CardId = "a" | "b";

interface CardState {
  visible: boolean;
  saved: boolean;
  swap: number;
}

const REGIONS = [
  { name: "부르고뉴", country: "프랑스" },
  { name: "나파밸리", country: "미국" },
  { name: "마이포밸리", country: "칠레" },
  { name: "바로사밸리", country: "호주" },
];

const GRAPES: Record<WineType, string[]> = {
  red: ["피노누아", "카베르네 소비뇽", "까르미네르", "쉬라즈"],
  white: ["샤르도네", "소비뇽 블랑", "소비뇽 블랑", "리슬링"],
  sparkling: ["크레망", "스파클링 브뤼", "스파클링 로제", "스파클링 쉬라즈"],
};

const GLASS_COLOR: Record<WineType, string> = {
  red: "#5C1F2E",
  white: "#C9BC79",
  sparkling: "#D8C687",
};

const TIERS = [
  { price: 32000, desc: "가볍게 시작하는", cap: "#D8CDBB" },
  { price: 56000, desc: "한 단계 더 특별한", cap: "#C9A24B" },
  { price: 89000, desc: "제대로 갖춘 자리를 위한", cap: "#7A1F2B" },
];

const TYPE_LABEL: Record<WineType, string> = { red: "레드", white: "화이트", sparkling: "스파클링" };
const TIER_TAG = ["빈티지 클래식", "리저브", "그랑 셀렉션"];
const PAIRINGS = [{ name: "안심 스테이크" }, { name: "훈제 연어" }, { name: "트러플 리조또" }, { name: "다크 초콜릿" }];

const NOTE_BY_TYPE: Record<WineType, string[]> = {
  red: ["타닌이 단단하고 묵직해요.", "과일향이 진하고 스파이시해요.", "부드럽게 감기는 바디감이에요."],
  white: ["산미가 산뜻하고 청량해요.", "과실향이 화사하게 퍼져요.", "미네랄리티가 깔끔하게 남아요."],
  sparkling: ["기포가 촘촘하고 경쾌해요.", "시트러스 향이 톡 쏘고 상큼해요.", "축하 자리에 딱이에요."],
};

const PAIR_REASON: Record<WineType, string> = {
  red: "육즙이랑 타닌이 딱 물려요",
  white: "산미가 재료 감칠맛을 확 살려줘요",
  sparkling: "입안이 개운하게 리셋돼요",
};

const COMPANION_TYPE: Record<WineType, WineType> = { red: "white", white: "sparkling", sparkling: "red" };

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
      { id: 0, label: "3만원대 — 가볍게" },
      { id: 1, label: "5만원대 — 적당히" },
      { id: 2, label: "8만원대+ — 제대로" },
    ],
  },
  {
    question: "어떤 스타일이 끌려?",
    options: [
      { id: "red", label: "레드" },
      { id: "white", label: "화이트" },
      { id: "sparkling", label: "스파클링" },
    ],
  },
];

function computeWineFor(regionIndex: number, tierIndex: number, type: WineType) {
  const region = REGIONS[regionIndex];
  const tier = TIERS[tierIndex];
  const grape = GRAPES[type][regionIndex];
  const wineName = `${region.name} ${grape} ${TIER_TAG[tierIndex]}`;
  const note = NOTE_BY_TYPE[type][(regionIndex + tierIndex) % NOTE_BY_TYPE[type].length];
  return { region, tier, grape, wineName, note };
}

export default function Home() {
  const [isIntro, setIsIntro] = useState(true);
  const [introStep, setIntroStep] = useState(0);
  const [occasion, setOccasion] = useState<string | null>(null);
  const [typeAnswer, setTypeAnswer] = useState<WineType>("red");
  const [regionIndex, setRegionIndex] = useState(0);
  const [tierIndex, setTierIndex] = useState(0);
  const [pairingIndex, setPairingIndex] = useState(0);
  const [cards, setCards] = useState<Record<CardId, CardState>>({
    a: { visible: true, saved: false, swap: 0 },
    b: { visible: true, saved: false, swap: 0 },
  });

  function selectIntro(stepIdx: number, value: string | number) {
    if (stepIdx === 0) setOccasion(String(value));
    if (stepIdx === 1) setTierIndex(Number(value));
    if (stepIdx === 2) setTypeAnswer(value as WineType);
    if (stepIdx < 2) {
      setIntroStep(stepIdx + 1);
    } else {
      setIsIntro(false);
      setOccasion((prev) => prev ?? "solo");
    }
  }

  function bumpAll() {
    setCards((c) => ({
      a: { ...c.a, swap: c.a.swap + 1 },
      b: { ...c.b, swap: c.b.swap + 1 },
    }));
  }

  function priceUp() {
    if (tierIndex >= 2) return;
    setTierIndex((t) => t + 1);
    bumpAll();
  }
  function priceDown() {
    if (tierIndex <= 0) return;
    setTierIndex((t) => t - 1);
    bumpAll();
  }
  function regionNext() {
    setRegionIndex((r) => (r + 1) % REGIONS.length);
    bumpAll();
  }
  function pairingNext() {
    setPairingIndex((p) => (p + 1) % PAIRINGS.length);
    bumpAll();
  }

  function toggleSave(id: CardId) {
    setCards((c) => ({ ...c, [id]: { ...c[id], saved: !c[id].saved } }));
  }
  function exclude(id: CardId) {
    setCards((c) => ({ ...c, [id]: { ...c[id], visible: false } }));
  }
  function resetCards() {
    setCards((c) => ({
      a: { visible: true, saved: c.a.saved, swap: c.a.swap + 1 },
      b: { visible: true, saved: c.b.saved, swap: c.b.swap + 1 },
    }));
  }

  function buildCard(id: CardId, type: WineType) {
    const { region, grape, wineName, note } = computeWineFor(regionIndex, tierIndex, type);
    const tier = TIERS[tierIndex];
    const pairing = PAIRINGS[pairingIndex];
    const c = cards[id];
    return {
      id,
      swap: c.swap,
      saved: c.saved,
      region: region.name,
      country: region.country,
      grape,
      typeLabelKr: TYPE_LABEL[type],
      wineName,
      price: "₩" + tier.price.toLocaleString(),
      priceDesc: tier.desc,
      note,
      personaLine: `${wineName}, ${pairing.name}이랑 같이면 ${PAIR_REASON[type]}`,
      capColor: tier.cap,
      glassColor: GLASS_COLOR[type],
    };
  }

  const cardA = buildCard("a", typeAnswer);
  const cardB = buildCard("b", COMPANION_TYPE[typeAnswer]);
  const visibleCards = [cards.a.visible ? cardA : null, cards.b.visible ? cardB : null].filter(
    (c): c is NonNullable<typeof c> => c !== null
  );
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
                <button
                  key={opt.id}
                  type="button"
                  className={styles.option}
                  onClick={() => selectIntro(introStep, opt.id)}
                >
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
              <button
                type="button"
                onClick={priceUp}
                disabled={tierIndex >= 2}
                className={
                  tierIndex >= 2 ? `${styles.joyBtn} ${styles.joyBtnDisabled}` : styles.joyBtn
                }
              >
                <span className={styles.joyAccent}>&#9650;</span>
              </button>
              <div className={`${styles.joyLabel} ${styles.joyAccent}`}>가격 UP</div>
            </div>

            <div className={styles.regionWrap}>
              <button type="button" onClick={regionNext} className={styles.joyBtn}>
                <span className={styles.joyRegion}>&#9664;</span>
              </button>
              <div className={`${styles.joyLabel} ${styles.joyRegion}`}>
                지역
                <br />
                변경
              </div>
            </div>

            <div className={styles.cardsRow}>
              {visibleCards.map((card) => (
                <div key={`${card.id}-${card.swap}`} className={styles.card}>
                  <button
                    type="button"
                    onClick={() => toggleSave(card.id)}
                    className={card.saved ? `${styles.saveBtn} ${styles.saveBtnActive}` : styles.saveBtn}
                  >
                    &#9825;
                  </button>
                  <button type="button" onClick={() => exclude(card.id)} className={styles.excludeBtn}>
                    &#10005;
                  </button>

                  <div className={styles.bottleWrap}>
                    <div className={styles.bottleAnim}>
                      <div className={styles.cap} style={{ background: card.capColor }} />
                      <div className={styles.neck} style={{ background: card.glassColor }} />
                      <div className={styles.shoulder} style={{ borderBottomColor: card.glassColor }} />
                      <div className={styles.bottleBody} style={{ background: card.glassColor }}>
                        <div className={styles.labelPatch}>
                          <div className={styles.labelRegion}>{card.region}</div>
                          <div className={styles.labelGrape}>{card.grape}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className={styles.wineName}>{card.wineName}</div>
                  <div className={styles.wineMeta}>
                    {card.region}, {card.country} · {card.typeLabelKr}
                  </div>

                  <div className={styles.priceRow}>
                    <span className={styles.price}>{card.price}</span>
                    <span className={styles.priceDesc}>{card.priceDesc}</span>
                  </div>

                  <div className={styles.note}>{card.note}</div>

                  <div className={styles.chips}>
                    {PAIRINGS.map((p, i) => (
                      <div
                        key={p.name}
                        className={i === pairingIndex ? `${styles.chip} ${styles.chipActive}` : styles.chip}
                      >
                        {p.name}
                      </div>
                    ))}
                  </div>

                  <div className={styles.personaBox}>
                    <div className={styles.personaLine}>&ldquo;{card.personaLine}&rdquo;</div>
                  </div>
                </div>
              ))}
            </div>

            <div className={styles.pairingWrap}>
              <button type="button" onClick={pairingNext} className={styles.joyBtn}>
                <span className={styles.joyPairing}>&#9654;</span>
              </button>
              <div className={`${styles.joyLabel} ${styles.joyPairing}`}>
                페어링
                <br />
                변경
              </div>
            </div>

            <div className={styles.priceDownWrap}>
              <button
                type="button"
                onClick={priceDown}
                disabled={tierIndex <= 0}
                className={
                  tierIndex <= 0 ? `${styles.joyBtn} ${styles.joyBtnDisabled}` : styles.joyBtn
                }
              >
                <span className={styles.joyAccent}>&#9660;</span>
              </button>
              <div className={`${styles.joyLabel} ${styles.joyAccent}`}>가격 DOWN</div>
            </div>
          </div>

          {anyHidden && (
            <div className={styles.resetWrap}>
              <button type="button" onClick={resetCards} className={styles.resetLink}>
                추천 다시 두 개 보기
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
