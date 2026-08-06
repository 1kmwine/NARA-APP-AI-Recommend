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

/** 8강(quarterfinal, 최대 4경기) → 준결승(semifinal, 2경기) → 결승(final, 1경기) 순서로
 * 진행한다. 8강 경기 수가 4보다 적으면(후보 부족으로 일부 경기가 빠진 경우) 그 수에 맞춰
 * 준결승/결승 규모도 자동으로 줄어든다 — 예: 8강 2경기만 있으면 승자 2명이 바로 결승으로. */
export function useBracket(): UseBracketResult {
  const [quarterfinals, setQuarterfinals] = useState<BracketMatch[]>([]);
  const [quarterfinalIndex, setQuarterfinalIndex] = useState(0);
  const [quarterfinalWinners, setQuarterfinalWinners] = useState<BracketCard[]>([]);
  const [semifinals, setSemifinals] = useState<BracketCard[][]>([]);
  const [semifinalIndex, setSemifinalIndex] = useState(0);
  const [semifinalWinners, setSemifinalWinners] = useState<BracketCard[]>([]);
  const [phase, setPhase] = useState<BracketPhase>("quarterfinal");
  const [winner, setWinner] = useState<BracketCard | null>(null);

  function reset(data: BracketResponse) {
    setQuarterfinals(data.matches);
    setQuarterfinalIndex(0);
    setQuarterfinalWinners([]);
    setSemifinals([]);
    setSemifinalIndex(0);
    setSemifinalWinners([]);
    setWinner(null);
    setPhase(data.matches.length > 0 ? "quarterfinal" : "done");
  }

  function pairUp(cards: BracketCard[]): BracketCard[][] {
    const pairs: BracketCard[][] = [];
    for (let i = 0; i < cards.length; i += 2) {
      if (i + 1 < cards.length) pairs.push([cards[i], cards[i + 1]]);
      else pairs.push([cards[i]]); // 홀수면 마지막 하나는 부전승
    }
    return pairs;
  }

  function pickWinner(card: BracketCard) {
    if (phase === "quarterfinal") {
      const nextWinners = [...quarterfinalWinners, card];
      if (quarterfinalIndex + 1 < quarterfinals.length) {
        setQuarterfinalWinners(nextWinners);
        setQuarterfinalIndex((i) => i + 1);
        return;
      }
      // 8강 끝 — 준결승 구성
      if (nextWinners.length === 1) {
        setWinner(nextWinners[0]);
        setPhase("done");
        return;
      }
      const pairs = pairUp(nextWinners);
      setSemifinals(pairs);
      setSemifinalIndex(0);
      setSemifinalWinners([]);
      setPhase(pairs.length === 1 && pairs[0].length === 1 ? "final" : "semifinal");
      if (pairs.length === 1 && pairs[0].length === 1) {
        setWinner(pairs[0][0]);
        setPhase("done");
      }
      return;
    }

    if (phase === "semifinal") {
      const nextWinners = [...semifinalWinners, card];
      if (semifinalIndex + 1 < semifinals.length) {
        setSemifinalWinners(nextWinners);
        setSemifinalIndex((i) => i + 1);
        return;
      }
      if (nextWinners.length === 1) {
        setWinner(nextWinners[0]);
        setPhase("done");
        return;
      }
      setPhase("final");
      setSemifinalWinners(nextWinners);
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
