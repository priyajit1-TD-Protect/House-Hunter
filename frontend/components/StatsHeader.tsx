"use client";

import { useState } from "react";
import { Stats } from "@/lib/types";
import { formatPrice } from "@/lib/utils";

interface StatsHeaderProps {
  stats: Stats | null;
  onScrapeTriggered?: () => void;
  isDev?: boolean;
}

function StatTile({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="flex flex-col items-center sm:items-start px-4 py-3 border-r border-white/10 last:border-0">
      <p className="text-td-gold text-xs font-semibold uppercase tracking-widest mb-0.5">
        {label}
      </p>
      <p className="text-white text-2xl font-black tabular-nums leading-none">
        {value}
      </p>
      {sub && <p className="text-white/50 text-xs mt-0.5">{sub}</p>}
    </div>
  );
}

export function StatsHeader({ stats, onScrapeTriggered, isDev }: StatsHeaderProps) {
  const [scraping, setScraping] = useState(false);
  const [lastSync, setLastSync] = useState<Date | null>(null);

  const handleScrape = async () => {
    setScraping(true);
    try {
      await fetch("/api/scrape", { method: "POST" });
      setLastSync(new Date());
      onScrapeTriggered?.();
    } catch {
      // silent
    } finally {
      setTimeout(() => setScraping(false), 3000);
    }
  };

  return (
    <header className="bg-td-premiumGreen">
      <div className="max-w-7xl mx-auto px-4 pt-6 pb-4">
        {/* Title row */}
        <div className="flex items-start justify-between mb-5">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-td-gold text-xs font-bold uppercase tracking-widest">
                GTA House Hunter
              </span>
              <span className="flex items-center gap-1 bg-td-digitalGreen/20 border border-td-digitalGreen/30 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-td-digitalGreen animate-pulse" />
                <span className="text-td-digitalGreen text-xs font-semibold">Live</span>
              </span>
            </div>
            <h1 className="text-white font-display font-black text-2xl sm:text-3xl leading-tight">
              Toronto Homes
            </h1>
            <p className="text-white/50 text-sm mt-1">
              3+ bed · 2+ bath · 1,500+ sqft · ≤$1.7M · School 8+ · Union &lt;40 min
            </p>
          </div>

          <div className="flex flex-col items-end gap-2">
            {isDev && (
              <button
                onClick={handleScrape}
                disabled={scraping}
                className="flex items-center gap-2 bg-td-gold/10 border border-td-gold/30 text-td-gold
                  text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-td-gold/20 transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {scraping ? (
                  <>
                    <span className="animate-spin">⟳</span>
                    Scraping…
                  </>
                ) : (
                  <>⟳ Trigger Scrape</>
                )}
              </button>
            )}
            {lastSync && (
              <p className="text-white/30 text-xs">
                Synced {lastSync.toLocaleTimeString()}
              </p>
            )}
          </div>
        </div>

        {/* Stats tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-4 border border-white/10 rounded-xl overflow-hidden">
          <StatTile
            label="Active Listings"
            value={stats ? String(stats.active_count) : "—"}
          />
          <StatTile
            label="Avg Score"
            value={stats ? `${stats.avg_score}` : "—"}
            sub="out of 100"
          />
          <StatTile
            label="Best Score"
            value={stats ? `${stats.best_score}` : "—"}
            sub="top match"
          />
          <StatTile
            label="Price Range"
            value={
              stats
                ? `${formatPrice(stats.min_price)}–${formatPrice(stats.max_price)}`
                : "—"
            }
          />
        </div>
      </div>
    </header>
  );
}
