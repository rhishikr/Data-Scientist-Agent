// dashboard/data.ts
import kpiSnapshot from "../../../../../backend/data/kpi_outputs/kpi_snapshot.json";
import cardsJson from "../../../../../backend/data/kpi_outputs/cards.json";
import customersJson from "../../../../../backend/data/kpi_outputs/customers.json";
import productsJson from "../../../../../backend/data/kpi_outputs/products.json";

import type { Snapshot, KpiCardRow, CustomerRow } from "./types";

export const snapshot = kpiSnapshot as unknown as Snapshot;
export const cards = cardsJson as unknown as KpiCardRow[];
export const customers = customersJson as unknown as CustomerRow[];
export const products = productsJson as unknown as any[];
