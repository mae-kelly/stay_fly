-- Elite Alpha Mirror Bot - Production Database Schema

-- Create database and user
CREATE DATABASE elite_bot_prod;
CREATE USER elite_bot WITH ENCRYPTED PASSWORD 'CHANGE_THIS_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE elite_bot_prod TO elite_bot;

-- Connect to the database
\c elite_bot_prod;

-- Create tables for production
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    whale_wallet VARCHAR(42) NOT NULL,
    token_address VARCHAR(42) NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL')),
    amount_usd DECIMAL(15,2) NOT NULL,
    amount_eth DECIMAL(20,8) NOT NULL,
    gas_price BIGINT NOT NULL,
    tx_hash VARCHAR(66),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    token_address VARCHAR(42) NOT NULL UNIQUE,
    token_symbol VARCHAR(20),
    entry_price DECIMAL(20,8) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    quantity DECIMAL(30,18) NOT NULL,
    usd_invested DECIMAL(15,2) NOT NULL,
    whale_wallet VARCHAR(42) NOT NULL,
    stop_loss DECIMAL(20,8),
    take_profit DECIMAL(20,8),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS elite_wallets (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) NOT NULL UNIQUE,
    wallet_type VARCHAR(20) NOT NULL,
    confidence_score DECIMAL(3,2) NOT NULL,
    avg_multiplier DECIMAL(10,2) NOT NULL,
    success_rate DECIMAL(3,2) NOT NULL,
    total_trades INTEGER DEFAULT 0,
    last_activity TIMESTAMPTZ,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(100),
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,6) NOT NULL,
    metric_unit VARCHAR(20),
    tags JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_trades_whale_wallet ON trades(whale_wallet);
CREATE INDEX idx_trades_token_address ON trades(token_address);
CREATE INDEX idx_positions_token_address ON positions(token_address);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_elite_wallets_address ON elite_wallets(address);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX idx_system_metrics_name ON system_metrics(metric_name);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO elite_bot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO elite_bot;

-- Insert initial system metrics
INSERT INTO system_metrics (metric_name, metric_value, metric_unit) VALUES
('system_initialized', 1, 'boolean'),
('database_version', 1.0, 'version');
