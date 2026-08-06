import type { WineCard, WineTaste } from "./api";

// 로그인 시스템이 없어서 브라우저 localStorage에만 저장한다(기기별로 따로 쌓임).
const LIKED_KEY = "sip.likedWines.v1";
const EXCLUDED_KEY = "sip.excludedWines.v1";
const MAX_EXCLUDED = 200;

interface ExcludedEntry {
  itemCd: string;
  taste: WineTaste;
}

function readJSON<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJSON(key: string, value: unknown) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(key, JSON.stringify(value));
}

export function getLikedWines(): WineCard[] {
  return readJSON<WineCard[]>(LIKED_KEY, []);
}

export function isLiked(itemCd: string): boolean {
  return getLikedWines().some((w) => w.item_cd === itemCd);
}

export function addLikedWine(card: WineCard) {
  const current = getLikedWines();
  if (current.some((w) => w.item_cd === card.item_cd)) return;
  writeJSON(LIKED_KEY, [card, ...current]);
}

export function removeLikedWine(itemCd: string) {
  writeJSON(
    LIKED_KEY,
    getLikedWines().filter((w) => w.item_cd !== itemCd)
  );
}

function getExcludedEntries(): ExcludedEntry[] {
  return readJSON<ExcludedEntry[]>(EXCLUDED_KEY, []);
}

export function addExcludedWine(itemCd: string, taste: WineTaste) {
  const withoutDuplicate = getExcludedEntries().filter((e) => e.itemCd !== itemCd);
  const next = [{ itemCd, taste }, ...withoutDuplicate].slice(0, MAX_EXCLUDED);
  writeJSON(EXCLUDED_KEY, next);
}

export function getExcludedItemCds(): string[] {
  return getExcludedEntries().map((e) => e.itemCd);
}

function averageTaste(vectors: WineTaste[]): WineTaste | null {
  if (vectors.length === 0) return null;
  const sum = vectors.reduce(
    (acc, v) => ({
      sweetness: acc.sweetness + v.sweetness,
      acidity: acc.acidity + v.acidity,
      body: acc.body + v.body,
      tannin: acc.tannin + v.tannin,
    }),
    { sweetness: 0, acidity: 0, body: 0, tannin: 0 }
  );
  const n = vectors.length;
  return {
    sweetness: Math.round(sum.sweetness / n),
    acidity: Math.round(sum.acidity / n),
    body: Math.round(sum.body / n),
    tannin: Math.round(sum.tannin / n),
  };
}

export function getLikedTasteAverage(): WineTaste | null {
  return averageTaste(getLikedWines().map((w) => w.taste));
}

export function getDislikedTasteAverage(): WineTaste | null {
  return averageTaste(getExcludedEntries().map((e) => e.taste));
}
