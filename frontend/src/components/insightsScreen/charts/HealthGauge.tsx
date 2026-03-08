import React from "react";

interface HealthGaugeProps {
  score: number; // 0-100
  size?: number;
}

function scoreColor(score: number): string {
  if (score >= 80) return "#22c55e"; // green
  if (score >= 60) return "#eab308"; // yellow
  if (score >= 40) return "#f97316"; // orange
  return "#ef4444"; // red
}

function scoreLabel(score: number): string {
  if (score >= 80) return "Healthy";
  if (score >= 60) return "Needs Attention";
  if (score >= 40) return "At Risk";
  return "Critical";
}

export function HealthGauge({ score, size = 120 }: HealthGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);
  const color = scoreColor(clamped);
  const center = size / 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="currentColor"
          className="text-muted/30"
          strokeWidth={8}
        />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div
        className="absolute flex flex-col items-center justify-center"
        style={{ width: size, height: size }}
      >
        <span className="text-2xl font-bold" style={{ color }}>{clamped}</span>
        <span className="text-[10px] text-muted-foreground font-medium">/ 100</span>
      </div>
      <span className="text-xs font-medium" style={{ color }}>{scoreLabel(clamped)}</span>
    </div>
  );
}
