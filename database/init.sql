-- ============================================================================
-- PLUM OPD CLAIM ADJUDICATION SYSTEM — Database Schema
-- ============================================================================
-- Database: PostgreSQL 15+ (Supabase)
-- Extensions: pgvector, uuid-ossp, pg_trgm
-- Run this file once in your Supabase SQL Editor to bootstrap the schema.
-- ============================================================================

-- ============================================================================
-- 1. SUPABASE AUTH SCHEMA MOCK (For Local Vanilla Postgres Compatibility)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS auth;
CREATE OR REPLACE FUNCTION auth.role() RETURNS text AS $$
  SELECT 'service_role'::text;
$$ LANGUAGE sql STABLE;

-- ============================================================================
-- 1. EXTENSIONS
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for embedding similarity search (fraud + RAG)
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enable trigram search for fuzzy text matching
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- 2. CUSTOM ENUM TYPES
-- ============================================================================

-- Claim lifecycle status
CREATE TYPE claim_status AS ENUM (
    'SUBMITTED',        -- Claim submitted, awaiting processing
    'PROCESSING',       -- Pipeline is actively processing
    'EXTRACTION',       -- AI extraction in progress
    'VALIDATION',       -- Rule engine validation in progress
    'FRAUD_CHECK',      -- Fraud detection in progress
    'DECISION_PENDING', -- All checks done, decision being generated
    'DECIDED',          -- Final decision rendered
    'MANUAL_REVIEW',    -- Sent to human adjuster
    'REVIEWED',         -- Adjuster reviewed the claim
    'CLOSED',           -- Claim fully resolved
    'ERROR'             -- Processing error occurred
);

-- Final claim decision
CREATE TYPE claim_decision AS ENUM (
    'APPROVED',         -- Fully approved
    'REJECTED',         -- Fully rejected
    'PARTIAL',          -- Partially approved
    'MANUAL_REVIEW',    -- Requires human review
    'PENDING'           -- Not yet decided
);

-- Document types accepted in the system
CREATE TYPE document_type AS ENUM (
    'PRESCRIPTION',     -- Doctor's prescription
    'MEDICAL_BILL',     -- Hospital / clinic bill
    'DIAGNOSTIC_REPORT',-- Lab / diagnostic report
    'PHARMACY_BILL',    -- Pharmacy receipt
    'OTHER'             -- Any other supporting document
);

-- MIME types supported for upload
CREATE TYPE mime_type AS ENUM (
    'application/pdf',
    'image/jpeg',
    'image/jpg',
    'image/png'
);

-- Audit trace step status
CREATE TYPE trace_status AS ENUM (
    'PASS',
    'FAIL',
    'WARNING',
    'SKIP',
    'ERROR',
    'PENDING'
);

-- Fraud signal engine source
CREATE TYPE fraud_engine AS ENUM (
    'RULE_BASED',       -- Rule-based fraud engine
    'VECTOR_SIMILARITY' -- Vector (pgvector) fraud engine
);

-- Fraud signal severity
CREATE TYPE fraud_severity AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
);

-- Manual review priority
CREATE TYPE review_priority AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'URGENT'
);

-- Manual review status
CREATE TYPE review_status AS ENUM (
    'QUEUED',           -- Waiting in queue
    'ASSIGNED',         -- Assigned to adjuster
    'IN_PROGRESS',      -- Adjuster actively reviewing
    'RESOLVED',         -- Decision made by adjuster
    'ESCALATED'         -- Escalated to senior reviewer
);

-- Member relationship to policy holder
CREATE TYPE member_relationship AS ENUM (
    'SELF',
    'SPOUSE',
    'CHILD',
    'PARENT',
    'DEPENDENT'
);

-- Gender
CREATE TYPE gender_type AS ENUM (
    'MALE',
    'FEMALE',
    'OTHER'
);

-- ============================================================================
-- 3. TABLES
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 3.1 POLICIES — Insurance policy configuration
-- ---------------------------------------------------------------------------
CREATE TABLE policies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_code     VARCHAR(50) NOT NULL UNIQUE,
    policy_name     VARCHAR(255) NOT NULL,
    company_name    VARCHAR(255) NOT NULL,
    effective_date  DATE NOT NULL,
    expiry_date     DATE,
    
    -- Full policy configuration stored as JSONB for flexibility
    coverage_details    JSONB NOT NULL DEFAULT '{}',
    waiting_periods     JSONB NOT NULL DEFAULT '{}',
    exclusions          JSONB NOT NULL DEFAULT '[]',
    network_hospitals   JSONB NOT NULL DEFAULT '[]',
    claim_requirements  JSONB NOT NULL DEFAULT '{}',
    cashless_facilities JSONB NOT NULL DEFAULT '{}',
    
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 3.2 MEMBERS — Insured employees and dependents
-- ---------------------------------------------------------------------------
CREATE TABLE members (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id     VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    email           VARCHAR(255),
    date_of_birth   DATE,
    age             INTEGER,
    gender          gender_type,
    join_date       DATE NOT NULL,
    relationship    member_relationship NOT NULL DEFAULT 'SELF',
    
    policy_id       UUID NOT NULL REFERENCES policies(id) ON DELETE RESTRICT,
    
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_members_employee_id ON members(employee_id);
CREATE INDEX idx_members_policy_id ON members(policy_id);
CREATE INDEX idx_members_name_trgm ON members USING gin(name gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- 3.3 CLAIMS — Core claim records
-- ---------------------------------------------------------------------------
CREATE TABLE claims (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id            VARCHAR(20) NOT NULL UNIQUE,  -- CLM_2026_0001 format
    member_id           UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    
    -- Financial
    claim_amount        DECIMAL(12, 2) NOT NULL CHECK (claim_amount >= 0),
    approved_amount     DECIMAL(12, 2) DEFAULT 0 CHECK (approved_amount >= 0),
    
    -- Decision
    status              claim_status NOT NULL DEFAULT 'SUBMITTED',
    decision            claim_decision NOT NULL DEFAULT 'PENDING',
    confidence_score    FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    fraud_score         FLOAT CHECK (fraud_score >= 0 AND fraud_score <= 100),
    rejection_reasons   JSONB DEFAULT '[]',
    decision_metadata   JSONB DEFAULT '{}',
    
    -- Manual review
    reviewer_id         VARCHAR(100),
    reviewer_notes      TEXT,
    
    -- Claim details
    hospital_name       VARCHAR(255),
    treatment_date      DATE,
    is_cashless         BOOLEAN DEFAULT FALSE,
    is_network_hospital BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at        TIMESTAMPTZ,
    reviewed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claims_claim_id ON claims(claim_id);
CREATE INDEX idx_claims_member_id ON claims(member_id);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_decision ON claims(decision);
CREATE INDEX idx_claims_submitted_at ON claims(submitted_at DESC);
CREATE INDEX idx_claims_treatment_date ON claims(treatment_date);
CREATE INDEX idx_claims_fraud_score ON claims(fraud_score DESC);

-- Composite index for fraud detection: same member, recent claims
CREATE INDEX idx_claims_member_recent ON claims(member_id, submitted_at DESC);

-- ---------------------------------------------------------------------------
-- 3.4 DOCUMENTS — Uploaded claim documents
-- ---------------------------------------------------------------------------
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     VARCHAR(50) NOT NULL UNIQUE,
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    
    document_type   document_type NOT NULL,
    file_url        TEXT NOT NULL,
    file_name       VARCHAR(500) NOT NULL,
    mime_type       VARCHAR(50) NOT NULL,
    file_size       BIGINT NOT NULL CHECK (file_size > 0),
    storage_path    TEXT,
    
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_claim_id ON documents(claim_id);
CREATE INDEX idx_documents_document_type ON documents(document_type);

-- ---------------------------------------------------------------------------
-- 3.5 EXTRACTED_DATA — AI-extracted structured data from documents
-- ---------------------------------------------------------------------------
CREATE TABLE extracted_data (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id                UUID NOT NULL UNIQUE REFERENCES claims(id) ON DELETE CASCADE,
    
    -- Extracted fields
    patient_name            VARCHAR(255),
    age                     VARCHAR(20),
    doctor_name             VARCHAR(255),
    doctor_registration     VARCHAR(100),
    diagnosis               TEXT,
    medicines               JSONB DEFAULT '[]',
    procedures              JSONB DEFAULT '[]',
    tests                   JSONB DEFAULT '[]',
    provider_name           VARCHAR(255),
    bill_amount             DECIMAL(12, 2),
    treatment_date          DATE,
    
    -- Extraction metadata
    extraction_confidence   FLOAT CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
    raw_extraction          JSONB DEFAULT '{}',   -- Raw Gemini response
    normalized_data         JSONB DEFAULT '{}',   -- Post-normalization data
    validation_results      JSONB DEFAULT '{}',   -- Cross-field validation results
    
    extracted_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_extracted_data_claim_id ON extracted_data(claim_id);
CREATE INDEX idx_extracted_data_diagnosis ON extracted_data USING gin(to_tsvector('english', COALESCE(diagnosis, '')));
CREATE INDEX idx_extracted_data_provider ON extracted_data(provider_name);

-- ---------------------------------------------------------------------------
-- 3.6 AUDIT_TRACES — Complete audit trail for every pipeline step
-- ---------------------------------------------------------------------------
CREATE TABLE audit_traces (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id        VARCHAR(50) NOT NULL UNIQUE,
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    
    step            VARCHAR(100) NOT NULL,
    status          trace_status NOT NULL,
    details         JSONB DEFAULT '{}',
    step_order      INTEGER NOT NULL,     -- Ordering within claim pipeline
    duration_ms     BIGINT,               -- Step execution time in milliseconds
    
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_traces_claim_id ON audit_traces(claim_id);
CREATE INDEX idx_audit_traces_step ON audit_traces(step);
CREATE INDEX idx_audit_traces_claim_order ON audit_traces(claim_id, step_order ASC);

-- ---------------------------------------------------------------------------
-- 3.7 CLAIM_EMBEDDINGS — Vector embeddings for semantic fraud detection
-- ---------------------------------------------------------------------------
CREATE TABLE claim_embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id        UUID NOT NULL UNIQUE REFERENCES claims(id) ON DELETE CASCADE,
    
    -- pgvector embedding (768-dimensional for Gemini embeddings)
    embedding       vector(768) NOT NULL,
    
    -- Metadata for the embedding (diagnosis, provider, amount, etc.)
    metadata        JSONB DEFAULT '{}',
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claim_embeddings_claim_id ON claim_embeddings(claim_id);

-- IVFFlat index for approximate nearest neighbor search
-- Create after inserting initial data; requires at least 1 row
-- Lists = sqrt(number_of_rows), start with 100
CREATE INDEX idx_claim_embeddings_vector ON claim_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- 3.8 FRAUD_SIGNALS — Individual fraud detection signals
-- ---------------------------------------------------------------------------
CREATE TABLE fraud_signals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    
    signal_type     VARCHAR(100) NOT NULL,   -- e.g., DUPLICATE_CLAIM_24H, HIGH_FREQUENCY_PROVIDER
    engine          fraud_engine NOT NULL,    -- RULE_BASED or VECTOR_SIMILARITY
    description     TEXT NOT NULL,
    severity        fraud_severity NOT NULL DEFAULT 'LOW',
    score_impact    FLOAT DEFAULT 0,          -- How much this signal contributes to fraud score
    details         JSONB DEFAULT '{}',
    
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fraud_signals_claim_id ON fraud_signals(claim_id);
CREATE INDEX idx_fraud_signals_engine ON fraud_signals(engine);
CREATE INDEX idx_fraud_signals_severity ON fraud_signals(severity);

-- ---------------------------------------------------------------------------
-- 3.9 INVESTIGATOR_REPORTS — Comprehensive claim analysis reports
-- ---------------------------------------------------------------------------
CREATE TABLE investigator_reports (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id            UUID NOT NULL UNIQUE REFERENCES claims(id) ON DELETE CASCADE,
    
    -- Report sections (each stored as structured JSONB)
    claim_summary       JSONB DEFAULT '{}',
    coverage_analysis   JSONB DEFAULT '{}',
    limit_analysis      JSONB DEFAULT '{}',
    fraud_analysis      JSONB DEFAULT '{}',
    decision_rationale  JSONB DEFAULT '{}',
    what_if_analysis    JSONB DEFAULT '{}',
    policy_references   JSONB DEFAULT '[]',
    
    -- Full rendered report text (markdown or HTML)
    full_report_text    TEXT,
    
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_investigator_reports_claim_id ON investigator_reports(claim_id);

-- ---------------------------------------------------------------------------
-- 3.10 MANUAL_REVIEW_QUEUE — Claims sent for human adjuster review
-- ---------------------------------------------------------------------------
CREATE TABLE manual_review_queue (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id            UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    
    priority            review_priority NOT NULL DEFAULT 'MEDIUM',
    reason              TEXT NOT NULL,
    assigned_to         VARCHAR(100),
    status              review_status NOT NULL DEFAULT 'QUEUED',
    
    -- Adjuster actions
    adjuster_notes      JSONB DEFAULT '[]',
    override_decision   claim_decision,
    override_amount     DECIMAL(12, 2),
    override_reasons    JSONB DEFAULT '[]',
    
    -- Timestamps
    queued_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_at         TIMESTAMPTZ,
    resolved_at         TIMESTAMPTZ
);

CREATE INDEX idx_manual_review_claim_id ON manual_review_queue(claim_id);
CREATE INDEX idx_manual_review_status ON manual_review_queue(status);
CREATE INDEX idx_manual_review_priority ON manual_review_queue(priority DESC);
CREATE INDEX idx_manual_review_assigned ON manual_review_queue(assigned_to);

-- ---------------------------------------------------------------------------
-- 3.11 POLICY_EMBEDDINGS — Vector embeddings for RAG policy assistant
-- ---------------------------------------------------------------------------
CREATE TABLE policy_embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id       UUID REFERENCES policies(id) ON DELETE CASCADE,
    
    chunk_text      TEXT NOT NULL,
    chunk_source    VARCHAR(255) NOT NULL,   -- Source file (policy_terms.json, adjudication_rules.md)
    chunk_index     INTEGER NOT NULL,
    
    -- pgvector embedding (768-dimensional for Gemini embeddings)
    embedding       vector(768) NOT NULL,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_policy_embeddings_policy_id ON policy_embeddings(policy_id);
CREATE INDEX idx_policy_embeddings_source ON policy_embeddings(chunk_source);

-- HNSW index for RAG retrieval (better recall than IVFFlat for smaller datasets)
CREATE INDEX idx_policy_embeddings_vector ON policy_embeddings
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------------------
-- 3.12 CLAIM_ID_SEQUENCE — Sequence for generating CLM_YYYY_XXXX IDs
-- ---------------------------------------------------------------------------
CREATE SEQUENCE claim_id_seq START WITH 1 INCREMENT BY 1;

-- ============================================================================
-- 4. FUNCTIONS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 4.1 Generate Claim ID in CLM_YYYY_XXXX format
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION generate_claim_id()
RETURNS VARCHAR(20) AS $$
DECLARE
    seq_val INTEGER;
    year_str VARCHAR(4);
BEGIN
    seq_val := nextval('claim_id_seq');
    year_str := EXTRACT(YEAR FROM NOW())::VARCHAR;
    RETURN 'CLM_' || year_str || '_' || LPAD(seq_val::VARCHAR, 4, '0');
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- 4.2 Update the updated_at timestamp automatically
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- 4.3 Semantic similarity search for fraud detection
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION search_similar_claims(
    query_embedding vector(768),
    similarity_threshold FLOAT DEFAULT 0.96,
    max_results INTEGER DEFAULT 10,
    exclude_claim_id UUID DEFAULT NULL
)
RETURNS TABLE (
    claim_id UUID,
    similarity FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ce.claim_id,
        (1 - (ce.embedding <=> query_embedding))::FLOAT AS similarity,
        ce.metadata
    FROM claim_embeddings ce
    WHERE (exclude_claim_id IS NULL OR ce.claim_id != exclude_claim_id)
    AND (1 - (ce.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY ce.embedding <=> query_embedding ASC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- 4.4 RAG retrieval: find most relevant policy chunks
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION search_policy_chunks(
    query_embedding vector(768),
    max_results INTEGER DEFAULT 5,
    min_similarity FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    chunk_id UUID,
    chunk_text TEXT,
    chunk_source VARCHAR(255),
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pe.id AS chunk_id,
        pe.chunk_text,
        pe.chunk_source,
        (1 - (pe.embedding <=> query_embedding))::FLOAT AS similarity
    FROM policy_embeddings pe
    WHERE (1 - (pe.embedding <=> query_embedding)) >= min_similarity
    ORDER BY pe.embedding <=> query_embedding ASC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- 4.5 Get member's claims within a time window (for fraud detection)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_member_claims_in_window(
    p_member_id UUID,
    p_hours INTEGER DEFAULT 24,
    p_exclude_claim_id UUID DEFAULT NULL
)
RETURNS TABLE (
    claim_id VARCHAR(20),
    claim_amount DECIMAL(12, 2),
    submitted_at TIMESTAMPTZ,
    status claim_status
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.claim_id,
        c.claim_amount,
        c.submitted_at,
        c.status
    FROM claims c
    WHERE c.member_id = p_member_id
    AND c.submitted_at >= NOW() - (p_hours || ' hours')::INTERVAL
    AND (p_exclude_claim_id IS NULL OR c.id != p_exclude_claim_id)
    ORDER BY c.submitted_at DESC;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- 4.6 Get provider claim count in a time window (for fraud detection)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_provider_claims_in_window(
    p_provider_name VARCHAR,
    p_days INTEGER DEFAULT 7,
    p_exclude_claim_id UUID DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    claim_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO claim_count
    FROM claims c
    JOIN extracted_data ed ON ed.claim_id = c.id
    WHERE LOWER(TRIM(ed.provider_name)) = LOWER(TRIM(p_provider_name))
    AND c.submitted_at >= NOW() - (p_days || ' days')::INTERVAL
    AND (p_exclude_claim_id IS NULL OR c.id != p_exclude_claim_id);
    
    RETURN claim_count;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- 4.7 Calculate member's YTD utilization
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_member_ytd_utilization(
    p_member_id UUID,
    p_year INTEGER DEFAULT EXTRACT(YEAR FROM NOW())::INTEGER
)
RETURNS TABLE (
    total_approved DECIMAL(12, 2),
    total_claims INTEGER,
    category_breakdown JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(SUM(c.approved_amount), 0)::DECIMAL(12, 2) AS total_approved,
        COUNT(*)::INTEGER AS total_claims,
        COALESCE(
            jsonb_object_agg(
                COALESCE(ed.diagnosis, 'unknown'),
                c.approved_amount
            ) FILTER (WHERE c.approved_amount > 0),
            '{}'::JSONB
        ) AS category_breakdown
    FROM claims c
    LEFT JOIN extracted_data ed ON ed.claim_id = c.id
    WHERE c.member_id = p_member_id
    AND c.decision IN ('APPROVED', 'PARTIAL')
    AND EXTRACT(YEAR FROM c.submitted_at) = p_year;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 5. TRIGGERS
-- ============================================================================

-- Auto-update updated_at for claims
CREATE TRIGGER trg_claims_updated_at
    BEFORE UPDATE ON claims
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at for members
CREATE TRIGGER trg_members_updated_at
    BEFORE UPDATE ON members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at for policies
CREATE TRIGGER trg_policies_updated_at
    BEFORE UPDATE ON policies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 6. ROW LEVEL SECURITY (RLS)
-- ============================================================================
-- Supabase recommends enabling RLS on all tables.
-- For the service role (backend), we bypass RLS.
-- For anon/authenticated roles, we restrict access.

ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE members ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE claim_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE fraud_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigator_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE manual_review_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE policy_embeddings ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (used by FastAPI backend)
CREATE POLICY "Service role full access on policies"
    ON policies FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on members"
    ON members FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on claims"
    ON claims FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on documents"
    ON documents FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on extracted_data"
    ON extracted_data FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on audit_traces"
    ON audit_traces FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on claim_embeddings"
    ON claim_embeddings FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on fraud_signals"
    ON fraud_signals FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on investigator_reports"
    ON investigator_reports FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on manual_review_queue"
    ON manual_review_queue FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on policy_embeddings"
    ON policy_embeddings FOR ALL
    USING (auth.role() = 'service_role');

-- Anon role can read claims (for public status checking)
CREATE POLICY "Anon can read claims by claim_id"
    ON claims FOR SELECT
    USING (auth.role() = 'anon');

CREATE POLICY "Anon can read audit traces"
    ON audit_traces FOR SELECT
    USING (auth.role() = 'anon');

-- ============================================================================
-- 7. STORAGE BUCKET (Supabase Storage)
-- ============================================================================
-- Run this in the Supabase dashboard or via the Storage API:
--
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('claim-documents', 'claim-documents', false);
--
-- CREATE POLICY "Service role uploads"
--     ON storage.objects FOR INSERT
--     WITH CHECK (bucket_id = 'claim-documents' AND auth.role() = 'service_role');
--
-- CREATE POLICY "Service role reads"
--     ON storage.objects FOR SELECT
--     USING (bucket_id = 'claim-documents' AND auth.role() = 'service_role');

-- ============================================================================
-- 8. VIEWS (Convenience views for common queries)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 8.1 Claims overview with member and decision data
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_claims_overview AS
SELECT
    c.id,
    c.claim_id,
    c.claim_amount,
    c.approved_amount,
    c.status,
    c.decision,
    c.confidence_score,
    c.fraud_score,
    c.rejection_reasons,
    c.hospital_name,
    c.treatment_date,
    c.is_cashless,
    c.is_network_hospital,
    c.submitted_at,
    c.processed_at,
    m.employee_id,
    m.name AS member_name,
    m.email AS member_email,
    ed.diagnosis,
    ed.doctor_name,
    ed.provider_name,
    ed.extraction_confidence
FROM claims c
JOIN members m ON m.id = c.member_id
LEFT JOIN extracted_data ed ON ed.claim_id = c.id
ORDER BY c.submitted_at DESC;

-- ---------------------------------------------------------------------------
-- 8.2 Manual review queue with claim context
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_review_queue AS
SELECT
    mrq.id AS review_id,
    mrq.priority,
    mrq.reason,
    mrq.assigned_to,
    mrq.status AS review_status,
    mrq.queued_at,
    c.claim_id,
    c.claim_amount,
    c.fraud_score,
    c.confidence_score,
    c.decision,
    m.employee_id,
    m.name AS member_name,
    ed.diagnosis,
    ed.provider_name
FROM manual_review_queue mrq
JOIN claims c ON c.id = mrq.claim_id
JOIN members m ON m.id = c.member_id
LEFT JOIN extracted_data ed ON ed.claim_id = c.id
WHERE mrq.status IN ('QUEUED', 'ASSIGNED', 'IN_PROGRESS')
ORDER BY
    CASE mrq.priority
        WHEN 'URGENT' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
    END ASC,
    mrq.queued_at ASC;

-- ---------------------------------------------------------------------------
-- 8.3 Fraud dashboard view
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_fraud_dashboard AS
SELECT
    c.claim_id,
    c.claim_amount,
    c.fraud_score,
    c.confidence_score,
    c.decision,
    m.employee_id,
    m.name AS member_name,
    ed.diagnosis,
    ed.provider_name,
    COALESCE(
        (SELECT jsonb_agg(jsonb_build_object(
            'signal_type', fs.signal_type,
            'engine', fs.engine::TEXT,
            'severity', fs.severity::TEXT,
            'description', fs.description
        ))
        FROM fraud_signals fs
        WHERE fs.claim_id = c.id),
        '[]'::JSONB
    ) AS fraud_signals
FROM claims c
JOIN members m ON m.id = c.member_id
LEFT JOIN extracted_data ed ON ed.claim_id = c.id
WHERE c.fraud_score > 30
ORDER BY c.fraud_score DESC;

-- ============================================================================
-- 9. COMMENTS (Documentation)
-- ============================================================================

COMMENT ON TABLE policies IS 'Insurance policy configurations, loaded from policy_terms.json';
COMMENT ON TABLE members IS 'Insured employees and their dependents';
COMMENT ON TABLE claims IS 'Core claim records with lifecycle status and decision';
COMMENT ON TABLE documents IS 'Uploaded claim documents (PDF, JPG, PNG)';
COMMENT ON TABLE extracted_data IS 'AI-extracted structured data from claim documents';
COMMENT ON TABLE audit_traces IS 'Complete audit trail for every pipeline processing step';
COMMENT ON TABLE claim_embeddings IS 'pgvector embeddings for semantic fraud detection';
COMMENT ON TABLE fraud_signals IS 'Individual fraud detection signals from rule-based and vector engines';
COMMENT ON TABLE investigator_reports IS 'Comprehensive claim analysis reports with 6 sections';
COMMENT ON TABLE manual_review_queue IS 'Queue for claims requiring human adjuster review';
COMMENT ON TABLE policy_embeddings IS 'pgvector embeddings for RAG policy assistant retrieval';

COMMENT ON FUNCTION generate_claim_id() IS 'Generates claim IDs in CLM_YYYY_XXXX format';
COMMENT ON FUNCTION search_similar_claims IS 'Semantic similarity search for fraud detection using pgvector';
COMMENT ON FUNCTION search_policy_chunks IS 'RAG retrieval: find most relevant policy document chunks';
COMMENT ON FUNCTION get_member_claims_in_window IS 'Get member claims within N hours for fraud detection';
COMMENT ON FUNCTION get_provider_claims_in_window IS 'Count provider claims within N days for fraud detection';
COMMENT ON FUNCTION get_member_ytd_utilization IS 'Calculate member year-to-date approved amounts and claim counts';

-- ============================================================================
-- SCHEMA INITIALIZATION COMPLETE
-- ============================================================================
-- Next steps:
-- 1. Run seed.sql to populate test data (policies, members)
-- 2. Index policy documents for RAG (policy_embeddings)
-- 3. Configure Supabase Storage bucket for document uploads
-- ============================================================================
