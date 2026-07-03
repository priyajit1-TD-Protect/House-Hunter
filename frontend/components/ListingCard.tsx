"use client";

import { useState } from "react";
import Image from "next/image";
import { Listing } from "@/lib/types";
import {
  formatFullPrice,
  formatIncome,
  formatDate,
  getScore,
  getScoreTier,
  getScoreColor,
  extractTags,
} from "@/lib/utils";
import { ScoreBreakdown } from "./ScoreBreakdown";

interface ListingCardProps {
  listing: Listing;
}

export function ListingCard({ listing }: ListingCardProps) {
  const [expanded, setExpanded] = useState(false);

  const score = getScore(listing);
  const tier = getScoreTier(score);
  const scoreData = listing.listing_scores?.[0];
  const tags = extractTags(listing);

  return (
    <article className="bg-white rounded-xl border border-td-grey overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200 flex flex-col">
      {/* Image + badges */}
      <div className="relative aspect-[16/9] bg-td-grey overflow-hidden">
        {listing.img_url ? (
          <Image
            src={listing.img_url}
            alt={listing.address}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-td-grey">
            <span className="text-4xl opacity-20">🏠</span>
          </div>
        )}

        {/* Score badge — top left */}
        <div className="absolute top-3 left-3">
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg backdrop-blur-sm
              ${score >= 80 ? "bg-td-premiumGreen/90" : score >= 65 ? "bg-td-darkGrey/90" : "bg-gray-700/90"}`}
          >
            <div className={`w-1.5 h-1.5 rounded-full ${getScoreColor(score)}`} />
            <span className="text-white text-sm font-black tabular-nums">{score}</span>
            <span className="text-white/60 text-xs">/100</span>
          </div>
        </div>

        {/* Tier pill — top right */}
        <div className="absolute top-3 right-3">
          <span
            className={`text-xs font-bold px-2.5 py-1.5 rounded-lg border
              ${tier.bg} ${tier.color} ${tier.border}`}
          >
            {tier.label}
          </span>
        </div>

        {/* Type chip — bottom left */}
        {listing.listing_type && (
          <div className="absolute bottom-3 left-3">
            <span className="text-xs text-white bg-black/50 backdrop-blur-sm px-2 py-1 rounded-md">
              {listing.listing_type}
            </span>
          </div>
        )}
      </div>

      {/* Card body */}
      <div className="flex-1 flex flex-col p-4 gap-3">
        {/* Address + price */}
        <div>
          <p className="text-xs text-td-greenGrey font-medium uppercase tracking-wide mb-0.5">
            {listing.neighbourhood ?? listing.city}
          </p>
          <h3 className="font-display font-black text-td-nearBlack text-base leading-tight mb-2">
            {listing.address}
          </h3>
          <p className="text-2xl font-black text-td-premiumGreen tabular-nums">
            {formatFullPrice(listing.price)}
          </p>
        </div>

        {/* Bed/bath/sqft chips */}
        <div className="flex flex-wrap gap-1.5">
          {listing.beds && (
            <span className="text-xs bg-td-grey text-td-darkGrey px-2.5 py-1 rounded-full font-medium">
              🛏 {listing.beds} bed{listing.beds !== 1 ? "s" : ""}
            </span>
          )}
          {listing.baths && (
            <span className="text-xs bg-td-grey text-td-darkGrey px-2.5 py-1 rounded-full font-medium">
              🚿 {listing.baths} bath{listing.baths !== 1 ? "s" : ""}
            </span>
          )}
          {listing.sqft && (
            <span className="text-xs bg-td-grey text-td-darkGrey px-2.5 py-1 rounded-full font-medium">
              📐 {listing.sqft.toLocaleString()} sqft
            </span>
          )}
        </div>

        {/* Neighbourhood signals */}
        {scoreData && (
          <div className="flex items-center gap-3 py-2.5 border-y border-td-grey text-xs text-td-darkGrey">
            <span className="flex items-center gap-1">
              🏫 <strong>{scoreData.school_rating ?? "—"}</strong>/10
            </span>
            <span className="text-td-grey">|</span>
            <span className="flex items-center gap-1">
              🚇 <strong>{scoreData.transit_min < 99 ? scoreData.transit_min : "—"}</strong>
              {scoreData.transit_min < 99 ? " min" : ""}
            </span>
            <span className="text-td-grey">|</span>
            <span className="flex items-center gap-1">
              💰 <strong>{scoreData.neighbourhood_income ? formatIncome(scoreData.neighbourhood_income) : "—"}</strong>
            </span>
          </div>
        )}

        {/* Tags */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <span
                key={tag}
                className="text-xs text-td-digitalGreen bg-td-insightBg border border-td-lightGreen px-2 py-0.5 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Score breakdown — expandable */}
        {scoreData && (
          <div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center justify-between w-full text-left py-1 text-xs font-semibold text-td-greenGrey hover:text-td-darkGrey transition-colors"
              aria-expanded={expanded}
            >
              <span>Score breakdown</span>
              <span className="text-base leading-none">{expanded ? "▲" : "▼"}</span>
            </button>
            {expanded && <ScoreBreakdown score={scoreData} />}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-1 mt-auto">
          <span className="text-xs text-td-greenGrey">
            Listed {formatDate(listing.listed_date)}
          </span>
          <a
            href={listing.realtor_url ?? "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-bold text-td-digitalGreen
              bg-td-insightBg border border-td-lightGreen px-3 py-1.5 rounded-lg
              hover:bg-td-lightGreen transition-colors"
          >
            View on Realtor.ca
            <span>↗</span>
          </a>
        </div>
      </div>
    </article>
  );
}
