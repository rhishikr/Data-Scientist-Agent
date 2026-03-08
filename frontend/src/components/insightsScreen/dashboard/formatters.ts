// dashboard/formatters.ts
import type { KpiCardRow, Snapshot } from "./types";

export const fmtCurrency = (n: number) =>
  `$${(Number.isFinite(n) ? n : 0).toLocaleString(undefined, {
    maximumFractionDigits: 0,
  })}`;

export const fmtCurrency2 = (n: number) =>
  `$${(Number.isFinite(n) ? n : 0).toLocaleString(undefined, {
    maximumFractionDigits: 2,
  })}`;

export const fmtPercent = (n: number, digits = 1) =>
  `${((Number.isFinite(n) ? n : 0) * 100).toFixed(digits)}%`;

export const clamp01 = (n: number) => Math.max(0, Math.min(1, n));

export const safeNum = (v: any, fallback = 0) =>
  Number.isFinite(Number(v)) ? Number(v) : fallback;

export const getCardValue = (cards: KpiCardRow[], id: string, fallback: any = 0) => {
  const row = cards.find((c) => c.id === id);
  if (!row) return fallback;
  // If fallback is a string, return raw value as string (text KPIs)
  if (typeof fallback === "string") return row.value != null ? String(row.value) : fallback;
  return safeNum(row.value, fallback);
};

export const getAsOfLabel = (snap: Snapshot) => {
  const raw = snap?.meta?.as_of ?? "";
  if (!raw) return "";
  return raw.split(".")[0];
};
