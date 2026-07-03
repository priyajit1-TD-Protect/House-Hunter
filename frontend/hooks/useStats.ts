import useSWR from "swr";
import { Stats } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useStats() {
  const { data, error, isLoading } = useSWR<Stats>(
    "/api/stats",
    fetcher,
    { refreshInterval: 60_000 }
  );
  return { stats: data ?? null, error, isLoading };
}
