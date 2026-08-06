export type WineType = "Red" | "White" | "Sparkling";

export interface WineTaste {
  sweetness: number;
  acidity: number;
  body: number;
  tannin: number;
}

export interface WineCard {
  item_cd: string;
  wine_name: string;
  region: string;
  country: string;
  grape: string;
  type_label_kr: string;
  price_krw: number;
  price_desc: string;
  note: string;
  persona_line: string;
  pdata_id: string | null;
  taste: WineTaste;
}

export interface RecommendParams {
  priceTier: number;
  countryIndex: number;
  regionIndex: number;
  wineType: WineType;
  pairingText?: string;
  slot?: number;
  excludeItemCds?: string[];
  likedTaste?: WineTaste | null;
  dislikedTaste?: WineTaste | null;
}

function tasteParam(t: WineTaste): string {
  return `${t.sweetness},${t.acidity},${t.body},${t.tannin}`;
}

export async function fetchRecommendation(params: RecommendParams): Promise<WineCard | null> {
  const search = new URLSearchParams({
    price_tier: String(params.priceTier),
    country_index: String(params.countryIndex),
    region_index: String(params.regionIndex),
    wine_type: params.wineType,
    slot: String(params.slot ?? 0),
  });
  if (params.pairingText) search.set("pairing_text", params.pairingText);
  if (params.excludeItemCds && params.excludeItemCds.length > 0) {
    search.set("exclude", params.excludeItemCds.join(","));
  }
  if (params.likedTaste) search.set("liked_taste", tasteParam(params.likedTaste));
  if (params.dislikedTaste) search.set("disliked_taste", tasteParam(params.dislikedTaste));

  const response = await fetch(`/api/recommend?${search.toString()}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`recommend 요청 실패: ${response.status}`);
  return response.json();
}

export function imageUrl(pdataId: string | null, variant: "thumb" | "removebg" = "removebg"): string | null {
  if (!pdataId) return null;
  return `/api/images/${pdataId}?variant=${variant}`;
}

export interface BracketCard extends WineCard {
  axis_label: string;
}

export interface BracketMatch {
  round: "quarterfinal" | "semifinal" | "final";
  axis: string;
  cards: BracketCard[];
}

export interface BracketResponse {
  matches: BracketMatch[];
}

export interface BracketParams {
  priceTier: number;
  countryIndex: number;
  regionIndex: number;
  wineType: WineType;
  pairingText?: string;
}

export async function fetchBracket(params: BracketParams): Promise<BracketResponse> {
  const search = new URLSearchParams({
    price_tier: String(params.priceTier),
    country_index: String(params.countryIndex),
    region_index: String(params.regionIndex),
    wine_type: params.wineType,
  });
  if (params.pairingText) search.set("pairing_text", params.pairingText);

  const response = await fetch(`/api/bracket?${search.toString()}`);
  if (!response.ok) throw new Error(`bracket 요청 실패: ${response.status}`);
  return response.json();
}
