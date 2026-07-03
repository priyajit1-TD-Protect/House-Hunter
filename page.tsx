"use client";

import { useState } from "react";
import { FilterState } from "@/lib/types";
import { getScore } from "@/lib/utils";
import { useListings } from "@/hooks/useListings";
import { useStats } from "@/hooks/useStats";
import { StatsHeader } from "@/components/StatsHeader";
import { FilterBar } from "@/components/FilterBar";
import { InsightBanner } from "@/components/InsightBanner";
import { ListingCard } from "@/components/ListingCard";
import { ListingCardSkeleton } from "@/components/ListingCardSkeleton";
import { EmptyState } from "@/components/EmptyState";

const DEFAULT_FILTERS: FilterState = {
  maxPrice: 1_700_000,
  minScore: 0,
  neighbourhood: "All",
  sortBy: "score",
};

const isDev = process.env.NODE_ENV === "development";

export default function HomePage() {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  const { listings, isLoading, error, mutate } = useListings({
    maxPrice: filters.maxPrice,
    minScore: filters.minScore,
    neighbourhood: filters.neighbourhood,
    sortBy: filters.sortBy,
  });

  const { stats } = useStats();

  const topMatch = listings.length > 0
    ? listings.reduce((a, b) => (getScore(a) >= getScore(b) ? a : b))
    : null;

  const resetFilters = () => setFilters(DEFAULT_FILTERS);

  return (
    <div className="min-h-screen flex flex-col">
      <StatsHeader
        stats={stats}
        isDev={isDev}
        onScrapeTriggered={() => mutate()}
      />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6 space-y-5">
        {/* Top match banner */}
        {!isLoading && topMatch && (
          <InsightBanner listing={topMatch} />
        )}

        {/* Filters */}
        <FilterBar
          filters={filters}
          onChange={setFilters}
          listingCount={listings.length}
        />

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
            <strong>Couldn't load listings.</strong> Make sure the FastAPI backend is running on port 8000.
          </div>
        )}

        {/* Listings grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {isLoading
            ? Array.from({ length: 6 }).map((_, i) => (
                <ListingCardSkeleton key={i} />
              ))
            : listings.length === 0
            ? <EmptyState onReset={resetFilters} />
            : listings.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
        </div>
      </main>

      <footer className="bg-td-premiumGreen mt-12">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <span className="text-white/30 text-xs">
            GTA House Hunter · Data via Realtor.ca · Updates every 6 hours
          </span>
          <span className="text-td-gold/50 text-xs">
            Built for Sachi
          </span>
        </div>
      </footer>
    </div>
  );
}
