import { useState } from "react";
import type { BracketCard, BracketMatch, BracketResponse } from "./api";

export type BracketPhase = "quarterfinal" | "semifinal" | "final" | "done";

export interface CurrentMatch {
  phase: BracketPhase;
  axis: string;
  cards: BracketCard[];
}

export interface UseBracketResult {
  currentMatch: CurrentMatch | null;
  winner: BracketCard | null;
  pickWinner: (card: BracketCard) => void;
  reset: (data: BracketResponse) => void;
}

function pairUp(cards: BracketCard[]): BracketCard[][] {
  const pairs: BracketCard[][] = [];
  for (let i = 0; i < cards.length; i += 2) {
    if (i + 1 < cards.length) pairs.push([cards[i], cards[i + 1]]);
    else pairs.push([cards[i]]); // 홀수면 마지막 하나는 부전승
  }
  return pairs;
}

/** 8강(quarterfinal, 최대 4경기) → 준결승(semifinal) → 결승(final) 순서로 진행한다.
 * 8강 경기 수가 4보다 적으면(후보 부족으로 일부 경기가 빠진 경우) 그 수에 맞춰
 * 준결승/결승 규모도 자동으로 줄어든다:
 * - 승자가 1명뿐이면(8강 1경기만 있었던 경우) 그 자리에서 바로 최종 승자.
 * - 승자가 정확히 2명이면 준결승 없이 바로 결승.
 * - 승자가 홀수(예: 3명)면 마지막 한 명은 부전승으로 다음 라운드에 자동 진출한다
 *   (화면에 부전승 매치는 안 보여주고, 실제 대결이 있는 페어만 그 라운드에 보여준다). */
export function useBracket(): UseBracketResult {
  const [quarterfinals, setQuarterfinals] = useState<BracketMatch[]>([]);
  const [quarterfinalIndex, setQuarterfinalIndex] = useState(0);
  const [quarterfinalWinners, setQuarterfinalWinners] = useState<BracketCard[]>([]);
  const [semifinals, setSemifinals] = useState<BracketCard[][]>([]);
  const [semifinalIndex, setSemifinalIndex] = useState(0);
  const [semifinalWinners, setSemifinalWinners] = useState<BracketCard[]>([]);
  const [byeWinners, setByeWinners] = useState<BracketCard[]>([]);
  const [phase, setPhase] = useState<BracketPhase>("quarterfinal");
  const [winner, setWinner] = useState<BracketCard | null>(null);

  function reset(data: BracketResponse) {
    setQuarterfinals(data.matches);
    setQuarterfinalIndex(0);
    setQuarterfinalWinners([]);
    setSemifinals([]);
    setSemifinalIndex(0);
    setSemifinalWinners([]);
    setByeWinners([]);
    setWinner(null);
    setPhase(data.matches.length > 0 ? "quarterfinal" : "done");
  }

  /** winners 목록으로 다음 라운드를 계산해서 state를 세팅한다. */
  function advance(winners: BracketCard[]) {
    if (winners.length <= 1) {
      setWinner(winners[0] ?? null);
      setPhase("done");
      return;
    }
    const pairs = pairUp(winners);
    const realPairs = pairs.filter((p) => p.length === 2);
    const byes = pairs.filter((p) => p.length === 1).map((p) => p[0]);

    if (realPairs.length === 0) {
      // winners.length>=2면 최소 한 쌍은 생기므로 이론상 안 오지만, 방어적으로 처리.
      advance(byes);
      return;
    }
    if (realPairs.length === 1 && byes.length === 0) {
      // 진짜 대결 한 쌍만 있고 부전승도 없으면 준결승 없이 바로 결승.
      setPhase("final");
      setSemifinalWinners(realPairs[0]);
      setByeWinners([]);
      return;
    }
    setSemifinals(realPairs);
    setSemifinalIndex(0);
    setSemifinalWinners([]);
    setByeWinners(byes);
    setPhase("semifinal");
  }

  function pickWinner(card: BracketCard) {
    if (phase === "quarterfinal") {
      const nextWinners = [...quarterfinalWinners, card];
      if (quarterfinalIndex + 1 < quarterfinals.length) {
        setQuarterfinalWinners(nextWinners);
        setQuarterfinalIndex((i) => i + 1);
        return;
      }
      advance(nextWinners);
      return;
    }

    if (phase === "semifinal") {
      const nextWinners = [...semifinalWinners, card];
      if (semifinalIndex + 1 < semifinals.length) {
        setSemifinalWinners(nextWinners);
        setSemifinalIndex((i) => i + 1);
        return;
      }
      // 이번 라운드 승자들 + 부전승으로 대기 중이던 승자들을 합쳐 다음 라운드 계산.
      advance([...nextWinners, ...byeWinners]);
      return;
    }

    if (phase === "final") {
      setWinner(card);
      setPhase("done");
    }
  }

  let currentMatch: CurrentMatch | null = null;
  if (phase === "quarterfinal" && quarterfinals[quarterfinalIndex]) {
    const m = quarterfinals[quarterfinalIndex];
    currentMatch = { phase, axis: m.axis, cards: m.cards };
  } else if (phase === "semifinal" && semifinals[semifinalIndex]) {
    currentMatch = { phase, axis: "semifinal", cards: semifinals[semifinalIndex] };
  } else if (phase === "final") {
    currentMatch = { phase, axis: "final", cards: semifinalWinners };
  }

  return { currentMatch, winner, pickWinner, reset };
}
