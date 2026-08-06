"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import styles from "../wine-recommend.module.css";
import { imageUrl, type WineCard } from "../api";
import { getLikedWines, removeLikedWine } from "../preferences";

export default function LikedWinesPage() {
  const [wines, setWines] = useState<WineCard[]>([]);

  useEffect(() => {
    // localStorage는 브라우저에만 있어서(서버 렌더링 시점엔 접근 불가) 마운트 후에 읽는다
    setWines(getLikedWines());
  }, []);

  function unlike(itemCd: string) {
    removeLikedWine(itemCd);
    setWines((current) => current.filter((wine) => wine.item_cd !== itemCd));
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div />
        <div className={styles.brand}>찜한 와인</div>
        <div className={styles.headerRight}>
          <Link href="/" className={styles.backToStart}>
            추천으로 돌아가기
          </Link>
        </div>
      </div>

      <div className={styles.introSection}>
        {wines.length === 0 ? (
          <div className={styles.note}>
            아직 찜한 와인이 없어요. 추천 카드에서 ♡ 눌러서 모아보세요.
          </div>
        ) : (
          <div className={styles.cardsRow}>
            {wines.map((card) => (
              <div key={card.item_cd} className={styles.card}>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    unlike(card.item_cd);
                  }}
                  className={styles.excludeBtn}
                >
                  &#10005;
                </button>

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
                <div className={styles.wineMeta}>
                  {card.region}, {card.country} · {card.type_label_kr}
                </div>

                <div className={styles.priceRow}>
                  <span className={styles.price}>₩{card.price_krw.toLocaleString()}</span>
                  <span className={styles.priceDesc}>{card.price_desc}</span>
                </div>

                <div className={styles.note}>{card.note}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
