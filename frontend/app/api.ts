export type WineType = "Red" | "White" | "Sparkling";

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
}

export interface RecommendParams {
  priceTier: number;
  countryIndex: number;
  regionIndex: number;
  wineType: WineType;
  pairingText?: string;
}

export async function fetchRecommendation(params: RecommendParams): Promise<WineCard | null> {
  const search = new URLSearchParams({
    price_tier: String(params.priceTier),
    country_index: String(params.countryIndex),
    region_index: String(params.regionIndex),
    wine_type: params.wineType,
  });
  if (params.pairingText) search.set("pairing_text", params.pairingText);

  const response = await fetch(`/api/recommend?${search.toString()}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`recommend 요청 실패: ${response.status}`);
  return response.json();
}

export function imageUrl(pdataId: string | null, variant: "thumb" | "removebg" = "removebg"): string | null {
  if (!pdataId) return null;
  return `/api/images/${pdataId}?variant=${variant}`;
}
