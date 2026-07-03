import { Listing } from "./types";

export function formatPrice(price: number): string {
  if (price >= 1_000_000) {
    return `$${(price / 1_000_000).toFixed(2)}M`;
  }
  return `$${(price / 1_000).toFixed(0)}K`;
}

export function formatFullPrice(price: number): string {
  return `$${price.toLocaleString("en-CA")}`;
}

export function formatIncome(income: number): string {
  return `$${Math.round(income / 1000)}K`;
}

export function getScore(listing: Listing): number {
  return listing.listing_scores?.[0]?.total_score ?? 0;
}

export function getScoreTier(score: number): {
  label: string;
  color: string;
  bg: string;
  border: string;
} {
  if (score >= 80) {
    return {
      label: "STRONG MATCH",
      color: "text-td-digitalGreen",
      bg: "bg-td-lightGreen",
      border: "border-td-digitalGreen",
    };
  }
  if (score >= 65) {
    return {
      label: "GOOD FIT",
      color: "text-td-darkGrey",
      bg: "bg-td-grey",
      border: "border-td-greenGrey",
    };
  }
  return {
    label: "REVIEW",
    color: "text-orange-700",
    bg: "bg-orange-50",
    border: "border-orange-300",
  };
}

export function getScoreColor(score: number): string {
  if (score >= 80) return "bg-td-digitalGreen";
  if (score >= 65) return "bg-td-greenGrey";
  if (score >= 50) return "bg-yellow-400";
  return "bg-red-400";
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString("en-CA", { month: "short", day: "numeric" });
}

export function extractTags(listing: Listing): string[] {
  const tags: string[] = [];
  const raw = listing as any;
  const features: string = (raw.raw_json?.Land?.Features ?? "") +
    " " + (raw.raw_json?.Building?.Features ?? "");
  if (/garage|parking/i.test(features)) tags.push("Parking");
  if (/renovated|updated|reno/i.test(features)) tags.push("Renovated");
  if (/garden|backyard/i.test(features)) tags.push("Garden");
  if (/basement/i.test(features)) tags.push("Basement");
  if (/pool/i.test(features)) tags.push("Pool");
  if (listing.sqft && listing.sqft >= 2000) tags.push("2000+ sqft");
  return tags.slice(0, 4);
}
