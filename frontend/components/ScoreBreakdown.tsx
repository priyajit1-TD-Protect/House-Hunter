"use client";

import { ListingScore } from "@/lib/types";
import { ScoreBar } from "./ScoreBar";

interface Dimension {
  key: keyof ListingScore;
  label: string;
  weight: string;
  valueLabel: (s: ListingScore) => string;
  icon: string;
}

const DIMENSIONS: Dimension[] = [
  {
    key: "income_score",
    label: "Neighbourhood Income",
    weight: "25%",
    icon: "💰",
    valueLabel: (s) =>
      s.neighbourhood_income
        ? `$${Math.round(s.neighbourhood_income / 1000)}K avg`
        : "No data",
  },
  {
    key: "school_score",
    label: "Elementary School",
    weight: "25%",
    icon: "🏫",
    valueLabel: (s) =>
      s.school_rating ? `Fraser ${s.school_rating}/10` : "No data",
  },
  {
    key: "transit_score",
    label: "Transit to Union",
    weight: "20%",
    icon: "🚇",
    valueLabel: (s) =>
      s.transit_min < 99 ? `${s.transit_min} min peak` : "No data",
  },
  {
    key: "price_score",
    label: "Price vs Budget",
    weight: "15%",
    icon: "🏷️",
    valueLabel: () => "vs $1.7M budget",
  },
  {
    key: "size_score",
    label: "Size",
    weight: "10%",
    icon: "📐",
    valueLabel: () => "vs 1,500 sqft target",
  },
  {
    key: "lifestyle_score",
    label: "Lifestyle & Amenities",
    weight: "5%",
    icon: "🌳",
    valueLabel: () => "parks, canopy, rec",
  },
];

interface ScoreBreakdownProps {
  score: ListingScore;
}

export function ScoreBreakdown({ score }: ScoreBreakdownProps) {
  return (
    <div className="space-y-3 pt-3">
      <p className="text-xs font-semibold text-td-greenGrey uppercase tracking-wider mb-3">
        Score Breakdown
      </p>
      {DIMENSIONS.map((dim) => {
        const val = score[dim.key] as number;
        return (
          <div key={dim.key} className="space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="text-sm">{dim.icon}</span>
                <span className="text-xs text-td-darkGrey font-medium">
                  {dim.label}
                </span>
                <span className="text-xs text-td-greenGrey">({dim.weight})</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-td-greenGrey">
                  {dim.valueLabel(score)}
                </span>
                <span className="text-xs font-bold text-td-nearBlack w-6 text-right tabular-nums">
                  {val}
                </span>
              </div>
            </div>
            <ScoreBar score={val} size="sm" />
          </div>
        );
      })}
    </div>
  );
}
