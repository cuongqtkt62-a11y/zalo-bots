-- ============================================================
-- init.sql — Database Schema Initialization
-- ============================================================
-- File này tự động chạy khi PostgreSQL container khởi động
-- lần đầu tiên (thông qua docker-entrypoint-initdb.d)
-- ============================================================

-- ── Extension ────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Users Table ──────────────────────────────────────────
-- Lưu thông tin người dùng Zalo tương tác với OA
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zalo_user_id    VARCHAR(255) UNIQUE NOT NULL,
    display_name    VARCHAR(255),
    phone_number    VARCHAR(20),
    avatar_url      TEXT,
    is_follower     BOOLEAN DEFAULT true,
    -- Lead scoring
    lead_score      INTEGER DEFAULT 0,
    lead_notes      TEXT DEFAULT '',
    lead_status     VARCHAR(50) DEFAULT 'new',  -- new, contacted, qualified, converted
    -- Tracking
    interaction_count INTEGER DEFAULT 1,
    first_interaction TIMESTAMPTZ DEFAULT NOW(),
    last_interaction  TIMESTAMPTZ DEFAULT NOW(),
    -- Metadata
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_zalo_id ON users(zalo_user_id);
CREATE INDEX idx_users_lead_score ON users(lead_score DESC);
CREATE INDEX idx_users_last_interaction ON users(last_interaction DESC);

-- ── Conversation History Table ───────────────────────────
-- Lưu lịch sử hội thoại cho AI context
CREATE TABLE IF NOT EXISTS conversation_history (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     VARCHAR(255) NOT NULL,
    role        VARCHAR(20) NOT NULL,  -- 'user' hoặc 'assistant'
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conv_user_id ON conversation_history(user_id);
CREATE INDEX idx_conv_created ON conversation_history(created_at DESC);

-- Auto-cleanup: Xóa lịch sử hội thoại cũ hơn 30 ngày
-- (Chạy bằng n8n scheduled workflow hoặc pg_cron)

-- ── Message Logs Table ───────────────────────────────────
-- Log tất cả tin nhắn để phân tích và báo cáo
CREATE TABLE IF NOT EXISTS message_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         VARCHAR(255) NOT NULL,
    direction       VARCHAR(10) NOT NULL,   -- 'incoming' hoặc 'outgoing'
    message_type    VARCHAR(50) NOT NULL,    -- 'text', 'image', 'command', etc.
    content         TEXT,
    ai_provider     VARCHAR(20),             -- 'gemini', 'openai', null
    response_time_ms INTEGER,                -- Thời gian phản hồi AI (ms)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_msg_user_id ON message_logs(user_id);
CREATE INDEX idx_msg_created ON message_logs(created_at DESC);
CREATE INDEX idx_msg_direction ON message_logs(direction);

-- ── Token Storage Table ──────────────────────────────────
-- Lưu access token & refresh token (để persist qua restart)
CREATE TABLE IF NOT EXISTS token_storage (
    id              SERIAL PRIMARY KEY,
    service         VARCHAR(50) UNIQUE NOT NULL,  -- 'zalo_oa'
    access_token    TEXT NOT NULL,
    refresh_token   TEXT NOT NULL,
    expires_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Auto-update timestamp trigger ────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Initial Data ─────────────────────────────────────────
INSERT INTO token_storage (service, access_token, refresh_token)
VALUES ('zalo_oa', 'initial_token', 'initial_refresh')
ON CONFLICT (service) DO NOTHING;

-- ── Summary View ─────────────────────────────────────────
-- View thống kê nhanh cho Power BI / Dashboard
CREATE OR REPLACE VIEW daily_summary AS
SELECT 
    DATE(created_at) as report_date,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_messages,
    COUNT(*) FILTER (WHERE direction = 'incoming') as incoming,
    COUNT(*) FILTER (WHERE direction = 'outgoing') as outgoing,
    AVG(response_time_ms) FILTER (WHERE response_time_ms IS NOT NULL) as avg_response_ms
FROM message_logs
GROUP BY DATE(created_at)
ORDER BY report_date DESC;
