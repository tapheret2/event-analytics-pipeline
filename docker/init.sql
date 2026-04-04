-- =============================================================================
-- PostgreSQL Initialization Script
-- Creates schemas and tables for the Event Analytics Pipeline
-- =============================================================================

-- Create schemas for Medallion Architecture layers
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- =============================================================================
-- Bronze Layer: Raw event data (mirrors CSV structure)
-- =============================================================================
CREATE TABLE IF NOT EXISTS bronze.raw_events (
    event_id        VARCHAR(64) NOT NULL,
    user_id         VARCHAR(64) NOT NULL,
    event_type      VARCHAR(32) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    event_date      DATE NOT NULL,
    page_url        VARCHAR(512),
    product_id      VARCHAR(64),
    product_name    VARCHAR(256),
    product_category VARCHAR(128),
    product_price   DECIMAL(12, 2),
    quantity        INTEGER,
    revenue         DECIMAL(12, 2),
    cashback_amount DECIMAL(12, 2),
    device_type     VARCHAR(32),
    browser         VARCHAR(64),
    country         VARCHAR(64),
    city            VARCHAR(128),
    session_id      VARCHAR(64),
    referrer        VARCHAR(256),
    -- Metadata
    ingested_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_file     VARCHAR(256),
    batch_id        VARCHAR(64)
);

-- Index for common query patterns
CREATE INDEX IF NOT EXISTS idx_bronze_event_date ON bronze.raw_events(event_date);
CREATE INDEX IF NOT EXISTS idx_bronze_user_id ON bronze.raw_events(user_id);
CREATE INDEX IF NOT EXISTS idx_bronze_event_type ON bronze.raw_events(event_type);

-- =============================================================================
-- Silver Layer: Cleaned and validated events
-- =============================================================================
CREATE TABLE IF NOT EXISTS silver.cleaned_events (
    event_id            VARCHAR(64) PRIMARY KEY,
    user_id             VARCHAR(64) NOT NULL,
    event_type          VARCHAR(32) NOT NULL,
    event_timestamp     TIMESTAMP NOT NULL,
    event_date          DATE NOT NULL,
    event_hour          INTEGER,
    page_url            VARCHAR(512),
    product_id          VARCHAR(64),
    product_name        VARCHAR(256),
    product_category    VARCHAR(128),
    product_price       DECIMAL(12, 2) DEFAULT 0,
    quantity            INTEGER DEFAULT 0,
    revenue             DECIMAL(12, 2) DEFAULT 0,
    cashback_amount     DECIMAL(12, 2) DEFAULT 0,
    device_type         VARCHAR(32) DEFAULT 'unknown',
    browser             VARCHAR(64) DEFAULT 'unknown',
    country             VARCHAR(64) DEFAULT 'unknown',
    city                VARCHAR(128) DEFAULT 'unknown',
    session_id          VARCHAR(64),
    referrer            VARCHAR(256),
    -- Quality metadata
    is_valid            BOOLEAN DEFAULT TRUE,
    quality_flags       VARCHAR(256),
    cleaned_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_silver_event_date ON silver.cleaned_events(event_date);
CREATE INDEX IF NOT EXISTS idx_silver_user_id ON silver.cleaned_events(user_id);
CREATE INDEX IF NOT EXISTS idx_silver_event_type ON silver.cleaned_events(event_type);

-- =============================================================================
-- Gold Layer: dbt will manage these tables, but we create the schema
-- Tables created by dbt: fact_events, dim_users, daily_kpis,
--                        funnel_analysis, retention
-- =============================================================================

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA bronze TO pipeline;
GRANT ALL PRIVILEGES ON SCHEMA silver TO pipeline;
GRANT ALL PRIVILEGES ON SCHEMA gold TO pipeline;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA bronze TO pipeline;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA silver TO pipeline;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gold TO pipeline;

-- Ensure future tables also get permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA bronze GRANT ALL ON TABLES TO pipeline;
ALTER DEFAULT PRIVILEGES IN SCHEMA silver GRANT ALL ON TABLES TO pipeline;
ALTER DEFAULT PRIVILEGES IN SCHEMA gold GRANT ALL ON TABLES TO pipeline;
