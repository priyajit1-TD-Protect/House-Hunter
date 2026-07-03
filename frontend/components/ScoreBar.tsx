"use client";

import { getScoreColor } from "@/lib/utils";

interface ScoreBarProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  animated?: boolean;
}

export function ScoreBar({
  score,
  size = "md",
  showLabel = false,
  animated = true,
}: ScoreBarProps) {
  const heightClass = {
    sm: "h-1.5",
    md: "h-2",
    lg: "h-3",
  }[size];

  return (
    <div className="flex items-center gap-2">
      <div className={`flex-1 bg-td-grey rounded-full overflow-hidden ${heightClass}`}>
        <div
          className={`${heightClass} rounded-full ${getScoreColor(score)} ${
            animated ? "transition-all duration-700 ease-out" : ""
          }`}
          style={{ width: `${score}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-bold text-td-nearBlack w-7 text-right tabular-nums">
          {score}
        </span>
      )}
    </div>
  );
}
