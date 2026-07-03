import useSWR from "swr";
import { Listing, SortOption, Strategy } from "@/lib/types";

const fetcher = (url: string) =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error(`API error: ${r.status}`);
    return r.json();
  });

export function useListings(params: {
  maxPrice?: number;
  minScore?: number;
  neighbourhood?: string;
  sortBy?: SortOption;
  strategy?: Strategy;
}) {
  const qs = new URLSearchParams({
    max_price: String(params.maxPrice ?? 1700000),
    min_score: String(params.minScore ?? 0),
    sort_by: params.sortBy ?? "score",
    strategy: params.strategy ?? "nucleus",
    ...(params.neighbourhood && params.neighbourhood !== "All"
      ? { neighbourhood: params.neighbourhood }
      : {}),
  });

  const { data, error, isLoading, mutate } = useSWR<Listing[]>(
    `/api/listings?${qs}`,
    fetcher,
    { refreshInterval: 30_000 }
  );

  return { listings: data ?? [], error, isLoading, mutate };
}
