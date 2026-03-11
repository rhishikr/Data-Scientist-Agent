-- 005_raw_datasets.sql
-- Create PostgreSQL tables for raw retail data (source of truth).
-- All columns use TEXT / DOUBLE PRECISION to accept dirty data (5% null rate, mixed casing).

-- 1. Customers
CREATE TABLE IF NOT EXISTS raw_customers (
    id BIGSERIAL PRIMARY KEY,
    customer_id TEXT,
    name TEXT,
    email TEXT,
    age DOUBLE PRECISION,
    gender TEXT,
    location TEXT,
    device_type TEXT,
    loyalty_status TEXT,
    total_spend DOUBLE PRECISION,
    acquisition_date TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Products
CREATE TABLE IF NOT EXISTS raw_products (
    id BIGSERIAL PRIMARY KEY,
    sku TEXT,
    product_name TEXT,
    category TEXT,
    brand TEXT,
    cost_price DOUBLE PRECISION,
    retail_price DOUBLE PRECISION,
    profit_margin DOUBLE PRECISION,
    discount_percent DOUBLE PRECISION,
    average_rating DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Inventory
CREATE TABLE IF NOT EXISTS raw_inventory (
    id BIGSERIAL PRIMARY KEY,
    sku TEXT,
    stock_quantity DOUBLE PRECISION,
    reorder_level DOUBLE PRECISION,
    warehouse_location TEXT,
    supplier TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Transactions
CREATE TABLE IF NOT EXISTS raw_transactions (
    id BIGSERIAL PRIMARY KEY,
    order_id TEXT,
    customer_id TEXT,
    sku TEXT,
    quantity DOUBLE PRECISION,
    unit_price DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,
    discount_amount DOUBLE PRECISION,
    order_status TEXT,
    order_datetime TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Transactions with session
CREATE TABLE IF NOT EXISTS raw_transactions_with_session (
    id BIGSERIAL PRIMARY KEY,
    order_id TEXT,
    customer_id TEXT,
    sku TEXT,
    quantity DOUBLE PRECISION,
    unit_price DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,
    discount_amount DOUBLE PRECISION,
    order_status TEXT,
    order_datetime TEXT,
    session_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. Payments
CREATE TABLE IF NOT EXISTS raw_payments (
    id BIGSERIAL PRIMARY KEY,
    order_id TEXT,
    payment_method TEXT,
    payment_status TEXT,
    transaction_fee DOUBLE PRECISION,
    currency TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 7. Marketing
CREATE TABLE IF NOT EXISTS raw_marketing (
    id BIGSERIAL PRIMARY KEY,
    campaign_id TEXT,
    channel TEXT,
    campaign_type TEXT,
    campaign_name TEXT,
    start_date TEXT,
    end_date TEXT,
    ad_spend DOUBLE PRECISION,
    impressions DOUBLE PRECISION,
    clicks DOUBLE PRECISION,
    conversions DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 8. Campaign performance
CREATE TABLE IF NOT EXISTS raw_campaign_performance (
    id BIGSERIAL PRIMARY KEY,
    date TEXT,
    campaign_id TEXT,
    channel TEXT,
    campaign_name TEXT,
    impressions DOUBLE PRECISION,
    clicks DOUBLE PRECISION,
    spend DOUBLE PRECISION,
    sessions DOUBLE PRECISION,
    orders DOUBLE PRECISION,
    attributed_revenue DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 9. Sessions
CREATE TABLE IF NOT EXISTS raw_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT,
    customer_id TEXT,
    session_start TEXT,
    session_end TEXT,
    session_duration_sec DOUBLE PRECISION,
    pages_viewed DOUBLE PRECISION,
    device_type TEXT,
    landing_page TEXT,
    traffic_source TEXT,
    campaign_name TEXT,
    converted_flag TEXT,
    revenue DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 10. Events
CREATE TABLE IF NOT EXISTS raw_events (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT,
    session_id TEXT,
    customer_id TEXT,
    event_type TEXT,
    event_datetime TEXT,
    sku TEXT,
    quantity DOUBLE PRECISION,
    unit_price DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 11. Web analytics
CREATE TABLE IF NOT EXISTS raw_web_analytics (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT,
    session_id TEXT,
    customer_id TEXT,
    event_datetime TEXT,
    page_type TEXT,
    action TEXT,
    add_to_cart TEXT,
    referral_source TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 12. Funnel summary
CREATE TABLE IF NOT EXISTS raw_funnel_summary (
    id BIGSERIAL PRIMARY KEY,
    date TEXT,
    sessions DOUBLE PRECISION,
    product_views DOUBLE PRECISION,
    add_to_cart DOUBLE PRECISION,
    checkout_started DOUBLE PRECISION,
    purchases DOUBLE PRECISION,
    conversion_rate DOUBLE PRECISION,
    cart_abandonment_rate DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes on ID columns used by simulate_update.py
CREATE INDEX IF NOT EXISTS idx_raw_customers_cid ON raw_customers(customer_id);
CREATE INDEX IF NOT EXISTS idx_raw_products_sku ON raw_products(sku);
CREATE INDEX IF NOT EXISTS idx_raw_inventory_sku ON raw_inventory(sku);
CREATE INDEX IF NOT EXISTS idx_raw_transactions_oid ON raw_transactions(order_id);
CREATE INDEX IF NOT EXISTS idx_raw_transactions_ws_oid ON raw_transactions_with_session(order_id);
CREATE INDEX IF NOT EXISTS idx_raw_sessions_sid ON raw_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_raw_events_eid ON raw_events(event_id);
CREATE INDEX IF NOT EXISTS idx_raw_web_analytics_eid ON raw_web_analytics(event_id);
CREATE INDEX IF NOT EXISTS idx_raw_marketing_cid ON raw_marketing(campaign_id);

-- Disable RLS for these tables (same pattern as 002_disable_rls.sql)
ALTER TABLE raw_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_transactions_with_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_marketing ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_campaign_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_web_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_funnel_summary ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for service role" ON raw_customers FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_products FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_inventory FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_transactions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_transactions_with_session FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_payments FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_marketing FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_campaign_performance FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_events FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_web_analytics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service role" ON raw_funnel_summary FOR ALL USING (true) WITH CHECK (true);
