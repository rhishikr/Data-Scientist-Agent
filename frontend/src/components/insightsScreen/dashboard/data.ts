// dashboard/data.ts
import kpiSnapshot from "../../../../../backend/data/kpi_outputs/kpi_snapshot.json";
import cardsJson from "../../../../../backend/data/mockJson/cards.json";
import customersJson from "../../../../../backend/data/mockJson/customers.json";
import productsJson from "../../../../../backend/data/mockJson/products.json";

import type { Snapshot, KpiCardRow, CustomerRow } from "./types";

export const snapshot = kpiSnapshot as unknown as Snapshot;
export const cards = cardsJson as unknown as KpiCardRow[];
export const customers = customersJson as unknown as CustomerRow[];
export const products = productsJson as unknown as any[];
