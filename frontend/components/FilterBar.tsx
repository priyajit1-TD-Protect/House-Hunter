"use client";

import { useEffect, useState } from "react";
import { FilterState, Neighbourhood, SortOption } from "@/lib/types";
import { formatPrice } from "@/lib/utils";

interface FilterBarProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  listingCount: number;
}

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "score",      label: "Best Match" },
  { value: "price_asc",  label: "Price ↑" },
  { value: "price_desc", label: "Price ↓" },
  { value: "transit",    label: "Closest to Union" },
  { value: "school",     label: "Best School" },
];

export function FilterBar({ filters, onChange, listingCount }: FilterBarProps) {
  const [neighbourhoods, setNeighbourhoods] = useState<Neighbourhood[]>([]);

  useEffect(() => {
    fetch("/api/neighbourhoods")
      .then((r) => r.json())
      .then((data) => setNeighbourhoods(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  const update = (patch: Partial<FilterState>) =>
    onChange({ ...filters, ...patch });

  return (
    <div className="bg-white border-b border-td-grey sticky top-0 z-10 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex flex-wrap items-center gap-4">
          {/* Result count */}
          <div className="flex-shrink-0">
            <span className="text-sm font-bold text-td-nearBlack tabular-nums">
              {listingCount}
            </span>
            <span className="text-sm text-td-greenGrey ml-1">listings</span>
          </div>

          <div className="h-5 w-px bg-td-grey hidden sm:block" />

          {/* Neighbourhood dropdown */}
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-td-greenGrey uppercase tracking-wide whitespace-nowrap">
              Area
            </label>
            <select
              value={filters.neighbourhood}
              onChange={(e) => update({ neighbourhood: e.target.value })}
              className="text-sm border border-td-grey rounded-lg px-3 py-1.5 text-td-nearBlack
                bg-white focus:outline-none focus:border-td-digitalGreen focus:ring-1
                focus:ring-td-digitalGreen min-w-[160px]"
            >
              <option value="All">All Neighbourhoods</option>
              {neighbourhoods.map((n) => (
                <option key={n.id} value={n.name}>
                  {n.name}
                </option>
              ))}
            </select>
          </div>

          {/* Sort dropdown */}
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-td-greenGrey uppercase tracking-wide whitespace-nowrap">
              Sort
            </label>
            <select
              value={filters.sortBy}
              onChange={(e) => update({ sortBy: e.target.value as SortOption })}
              className="text-sm border border-td-grey rounded-lg px-3 py-1.5 text-td-nearBlack
                bg-white focus:outline-none focus:border-td-digitalGreen focus:ring-1
                focus:ring-td-digitalGreen"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="h-5 w-px bg-td-grey hidden sm:block" />

          {/* Max price slider */}
          <div className="flex items-center gap-3 flex-1 min-w-[200px]">
            <label className="text-xs font-semibold text-td-greenGrey uppercase tracking-wide whitespace-nowrap">
              Max Price
            </label>
            <input
              type="range"
              min={1000000}
              max={1700000}
              step={25000}
              value={filters.maxPrice}
              onChange={(e) => update({ maxPrice: Number(e.target.value) })}
              className="flex-1 accent-td-digitalGreen"
            />
            <span className="text-sm font-bold text-td-nearBlack tabular-nums whitespace-nowrap">
              {formatPrice(filters.maxPrice)}
            </span>
          </div>

          {/* Min score slider */}
          <div className="flex items-center gap-3 min-w-[160px]">
            <label className="text-xs font-semibold text-td-greenGrey uppercase tracking-wide whitespace-nowrap">
              Min Score
            </label>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={filters.minScore}
              onChange={(e) => update({ minScore: Number(e.target.value) })}
              className="flex-1 accent-td-digitalGreen"
            />
            <span className="text-sm font-bold text-td-nearBlack tabular-nums w-6">
              {filters.minScore}
            </span>
          </div>

          {/* Reset */}
          {(filters.minScore > 0 ||
            filters.maxPrice < 1700000 ||
            filters.neighbourhood !== "All") && (
            <button
              onClick={() =>
                onChange({
                  maxPrice: 1700000,
                  minScore: 0,
                  neighbourhood: "All",
                  sortBy: "score",
                })
              }
              className="text-xs text-td-greenGrey hover:text-td-nearBlack underline underline-offset-2"
            >
              Reset
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
