"use client";

import { Listing } from "@/lib/types";
import { formatFullPrice, formatIncome, getScore } from "@/lib/utils";

interface InsightBannerProps {
  listing: Listing | null;
}

export function InsightBanner({ listing }: InsightBannerProps) {
  if (!listing) return null;

  const score = getScore(listing);
  const scoreData = listing.listing_scores?.[0];

  return (
    <div className="bg-td-insightBg border border-td-lightGreen rounded-xl p-4 flex flex-col sm:flex-row sm:items-center gap-4">
      <div className="flex items-center gap-3">
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-td-premiumGreen flex items-center justify-center">
          <span className="text-td-gold font-black text-sm tabular-nums">{score}</span>
        </div>
        <div>
          <p className="text-xs text-td-digitalGreen font-bold uppercase tracking-wide">
            ✦ Top Match Today
          </p>
          <p className="text-td-nearBlack font-bold text-sm leading-tight">
            {listing.address}
          </p>
          <p className="text-td-greenGrey text-xs">{listing.neighbourhood}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 sm:ml-auto text-xs text-td-darkGrey">
        <span className="font-bold text-td-premiumGreen">
          {formatFullPrice(listing.price)}
        </span>
        {scoreData && (
          <>
            <span>🏫 {scoreData.school_rating ?? "—"}/10</span>
            <span>🚇 {scoreData.transit_min < 99 ? `${scoreData.transit_min} min` : "—"}</span>
            <span>💰 {scoreData.neighbourhood_income ? formatIncome(scoreData.neighbourhood_income) : "—"}</span>
          </>
        )}
        <a
          href={listing.realtor_url ?? "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="font-bold text-td-digitalGreen hover:underline"
        >
          View →
        </a>
      </div>
    </div>
  );
}
