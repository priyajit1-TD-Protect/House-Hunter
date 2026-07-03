import useSWR from "swr";
import { Stats, Strategy } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useStats(strategy: Strategy = "nucleus") {
  const { data, error, isLoading } = useSWR<Stats>(
    `/api/stats?strategy=${strategy}`,
    fetcher,
    { refreshInterval: 60_000 }
  );
  return { stats: data ?? null, error, isLoading };
}
