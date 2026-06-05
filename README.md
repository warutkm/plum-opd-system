# 🏥 Plum OPD Claim Adjudication System

> **AI-Augmented, Deterministic-Decided** — A production-grade multi-agent pipeline for automated OPD insurance claim adjudication.

### 🌐 Live Deployments
* **Frontend Application (Vercel)**: [https://plum-opd-system.vercel.app](https://plum-opd-system.vercel.app)
* **Backend API Gateway (Render)**: [https://plum-opd-system.onrender.com/api/v1](https://plum-opd-system.onrender.com/api/v1)
* **Interactive API Docs (Render Swagger)**: [https://plum-opd-system.onrender.com/docs](https://plum-opd-system.onrender.com/docs)

[![Next.js](https://img.shields.io/badge/Frontend-Next.js_15-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?logo=supabase)](https://supabase.com/)
[![Gemini](https://img.shields.io/badge/AI-Gemini_2.5_Flash-4285F4?logo=google)](https://ai.google.dev/)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Language-Python_3.12-3776AB?logo=python)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Core Philosophy](#core-philosophy)
- [Architecture](#architecture)
- [Pipeline Stages](#pipeline-stages)
- [Decision Flow](#decision-flow)
- [ER Diagram](#er-diagram)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Assumptions](#assumptions)
- [Contributing](#contributing)

---

## Overview

The **Plum OPD Claim Adjudication System** is an AI-augmented, deterministic-decided platform for processing Outpatient Department (OPD) insurance claims. It combines multi-agent AI extraction with a strict deterministic rule engine to deliver transparent, auditable, and policy-compliant claim decisions.

### What It Does

1. **Accepts** medical documents (PDFs, images) via a clean submission UI
2. **Extracts** structured data using Gemini 2.5 Flash multimodal AI
3. **Validates** against policy terms using a deterministic rule engine
4. **Detects fraud** via rule-based and vector-similarity engines
5. **Generates decisions** with full audit trails and investigator reports
6. **Provides** a Policy Assistant (RAG) for natural language policy queries
7. **Queues** uncertain claims for human adjuster review

---

## Core Philosophy

> **"AI Reads. Rules Decide."**

This system enforces a strict responsibility boundary between AI and deterministic logic:

| Capability | AI Agents ✅ | Deterministic Engine ✅ |
|---|---|---|
| Read documents | ✅ | ❌ |
| Extract information | ✅ | ❌ |
| Assess medical necessity | ✅ | ❌ |
| Detect suspicious patterns | ✅ | ❌ |
| Generate explanations | ✅ | ❌ |
| Answer policy questions (RAG) | ✅ | ❌ |
| **Approve claims** | ❌ NEVER | ✅ |
| **Reject claims** | ❌ NEVER | ✅ |
| **Calculate payouts** | ❌ NEVER | ✅ |
| **Override policy rules** | ❌ NEVER | ✅ |
| **Determine financial decisions** | ❌ NEVER | ✅ |

---

## Architecture

### System Architecture Diagram

```mermaid
graph TB
    subgraph "🖥️ Frontend — Next.js 15 + TypeScript + TailwindCSS + shadcn/ui"
        UI_SUBMIT["📄 Claim Submission Page"]
        UI_TIMELINE["⏱️ Processing Timeline Page"]
        UI_DECISION["📊 Decision View Page"]
        UI_REPORT["📋 Investigator Report Page"]
        UI_DASHBOARD["🎛️ Adjuster Dashboard Page"]
        UI_RAG["💬 Policy Assistant (RAG Chat)"]
    end

    subgraph "🔗 API Gateway — FastAPI"
        API["FastAPI REST API"]
        WS["WebSocket (Real-time Updates)"]
    end

    subgraph "🤖 Phase 1 — Foundation"
        GW["🚪 Gateway Agent"]
        DOC_V["📑 Document Verification Agent"]
    end

    subgraph "🧠 Phase 2 — Extraction"
        EXTRACT["🔍 Multimodal AI Extraction Agent<br/>(Gemini 2.5 Flash)"]
        NORM["⚖️ Normalization Agent"]
        VALID["✅ Validation Agent"]
    end

    subgraph "🧠 Phase 3 — Medical Review"
        MED["🏥 Medical Necessity Agent<br/>(Gemini 2.5 Flash)"]
    end

    subgraph "⚙️ Phase 4 — Deterministic Rule Engine (NO LLM)"
        ELIG["Module A: Eligibility Validation"]
        DOC_VAL["Module B: Documentation Validation"]
        COV["Module C: Coverage Validation"]
        FIN["Module D: Financial Calculator"]
        PARTIAL["Module E: Partial Approval Logic"]
    end

    subgraph "🛡️ Phase 5 — Fraud Detection"
        RULE_FRAUD["🔴 Rule-Based Fraud Engine"]
        VEC_FRAUD["🟡 Vector Fraud Detection<br/>(pgvector)"]
        FRAUD_AGG["📊 Fraud Score Aggregator"]
    end

    subgraph "📝 Phase 6 — Decision & Reporting"
        DECISION["⚡ Decision Generator"]
        CONF["🎯 Confidence Engine"]
        TRACE["📒 Trace Ledger Builder"]
        INVEST["🔎 Investigator Report Generator"]
    end

    subgraph "📚 Policy Assistant — RAG"
        CHUNK["📄 Document Chunking"]
        EMBED_RAG["🔢 Embedding Generator"]
        RETRIEVE["🔍 Vector Retrieval (pgvector)"]
        RAG_GEN["💡 Gemini RAG Response"]
    end

    subgraph "🗃️ Database — Supabase PostgreSQL + pgvector"
        DB_CLAIMS["claims"]
        DB_DOCS["documents"]
        DB_EXTRACT["extracted_data"]
        DB_AUDIT["audit_traces"]
        DB_EMBED["claim_embeddings"]
        DB_POLICY["policy_embeddings"]
    end

    %% User Flow
    UI_SUBMIT -->|"Upload Documents"| API
    API --> GW
    GW -->|"CLM_2026_XXXX"| DOC_V
    DOC_V --> EXTRACT
    EXTRACT --> NORM
    NORM --> VALID
    VALID --> MED
    MED --> ELIG
    ELIG --> DOC_VAL
    DOC_VAL --> COV
    COV --> FIN
    FIN --> PARTIAL
    PARTIAL --> RULE_FRAUD
    RULE_FRAUD --> VEC_FRAUD
    VEC_FRAUD --> FRAUD_AGG
    FRAUD_AGG --> DECISION
    DECISION --> CONF
    CONF --> TRACE
    TRACE --> INVEST
    INVEST --> DB_CLAIMS

    %% Database connections
    GW -.->|"Write"| DB_CLAIMS
    GW -.->|"Write"| DB_DOCS
    EXTRACT -.->|"Write"| DB_EXTRACT
    TRACE -.->|"Write"| DB_AUDIT
    VEC_FRAUD -.->|"Read/Write"| DB_EMBED

    %% RAG Pipeline
    UI_RAG -->|"Policy Question"| API
    API --> CHUNK
    CHUNK --> EMBED_RAG
    EMBED_RAG --> RETRIEVE
    RETRIEVE -.->|"Query"| DB_POLICY
    RETRIEVE --> RAG_GEN

    %% Real-time updates
    WS -.->|"Status Updates"| UI_TIMELINE
    WS -.->|"Decision Updates"| UI_DECISION
    WS -.->|"Review Queue"| UI_DASHBOARD

    %% Styling
    classDef aiAgent fill:#4285F4,stroke:#1a73e8,color:#fff,stroke-width:2px
    classDef deterministicEngine fill:#34A853,stroke:#1e8e3e,color:#fff,stroke-width:2px
    classDef fraudEngine fill:#EA4335,stroke:#d93025,color:#fff,stroke-width:2px
    classDef database fill:#3ECF8E,stroke:#2da87a,color:#fff,stroke-width:2px
    classDef frontend fill:#1a1a2e,stroke:#e94560,color:#fff,stroke-width:2px
    classDef reporting fill:#FBBC04,stroke:#f29900,color:#000,stroke-width:2px

    class EXTRACT,MED,RAG_GEN aiAgent
    class ELIG,DOC_VAL,COV,FIN,PARTIAL deterministicEngine
    class RULE_FRAUD,VEC_FRAUD,FRAUD_AGG fraudEngine
    class DB_CLAIMS,DB_DOCS,DB_EXTRACT,DB_AUDIT,DB_EMBED,DB_POLICY database
    class UI_SUBMIT,UI_TIMELINE,UI_DECISION,UI_REPORT,UI_DASHBOARD,UI_RAG frontend
    class DECISION,CONF,TRACE,INVEST reporting
```

---

## Pipeline Stages

### Detailed Processing Pipeline

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (Next.js)
    participant API as FastAPI
    participant GW as Gateway Agent
    participant DV as Doc Verification
    participant EX as Extraction Agent (Gemini)
    participant NR as Normalization Agent
    participant VA as Validation Agent
    participant RE as Rule Engine
    participant MN as Medical Necessity (Gemini)
    participant RF as Rule Fraud Engine
    participant VF as Vector Fraud (pgvector)
    participant FA as Fraud Aggregator
    participant DG as Decision Generator
    participant CE as Confidence Engine
    participant TL as Trace Ledger
    participant IR as Investigator Report
    participant DB as Supabase DB

    User->>FE: Upload documents (PDF/JPG/PNG)
    FE->>API: POST /api/v1/claims/submit
    API->>GW: Initialize claim processing

    Note over GW: Phase 1 — Foundation
    GW->>GW: Validate MIME type & file size
    GW->>GW: Generate CLM_2026_XXXX
    GW->>DB: Create claim record
    GW->>TL: Append { step: "upload", status: "PASS" }
    GW->>DV: Forward documents

    DV->>DV: Check document completeness
    DV->>DV: Verify required documents present
    DV->>TL: Append { step: "doc_verification", status: "PASS/FAIL" }

    Note over EX: Phase 2 — Extraction (AI)
    EX->>EX: Gemini 2.5 Flash multimodal extraction
    EX->>EX: Few-shot prompting + JSON schema
    EX->>EX: Retry logic on failure
    EX->>DB: Store extracted data
    EX->>TL: Append { step: "extraction", status: "PASS" }

    NR->>NR: Normalize dates, amounts, registrations
    NR->>NR: Compute extraction confidence
    NR->>TL: Append { step: "normalization", status: "PASS" }

    VA->>VA: Cross-validate extracted fields
    VA->>TL: Append { step: "validation", status: "PASS/FAIL" }

    Note over MN: Phase 3 — Medical Necessity (AI)
    MN->>MN: Gemini single-call assessment
    MN->>TL: Append { step: "medical_necessity", status: "PASS/WARNING" }

    Note over RE: Phase 4 — Deterministic Rule Engine (NO LLM)
    RE->>RE: Module A: Eligibility (policy active, waiting period)
    RE->>TL: Append { step: "eligibility_check", status: "PASS/FAIL" }
    RE->>RE: Module B: Documentation (completeness, doctor reg)
    RE->>TL: Append { step: "doc_validation", status: "PASS/FAIL" }
    RE->>RE: Module C: Coverage (exclusions, covered services)
    RE->>TL: Append { step: "coverage_check", status: "PASS/FAIL" }
    RE->>RE: Module D: Financial (limits, copay, deductibles)
    RE->>TL: Append { step: "financial_check", status: "PASS/FAIL" }
    RE->>RE: Module E: Partial Approval Logic
    RE->>TL: Append { step: "partial_approval_check", status: "PASS/PARTIAL" }

    Note over RF,VF: Phase 5 — Fraud Detection
    RF->>RF: Rule-based checks (frequency, duplicates, age mismatch)
    RF->>TL: Append { step: "rule_fraud_check", status: "PASS/FLAG" }

    VF->>VF: Build fraud profile
    VF->>VF: Generate embedding
    VF->>DB: Similarity search (pgvector)
    VF->>VF: Check similarity > 0.96
    VF->>TL: Append { step: "vector_fraud_check", status: "PASS/FLAG" }

    FA->>FA: Aggregate fraud score (0-100)
    FA->>TL: Append { step: "fraud_aggregation", status: "PASS/REVIEW" }

    Note over DG,CE: Phase 6 — Decision & Reporting
    CE->>CE: Compute final confidence<br/>(40% extraction + 40% rules + 20% fraud/doc quality)
    DG->>DG: Generate APPROVED/REJECTED/PARTIAL/MANUAL_REVIEW
    DG->>DB: Store decision
    DG->>TL: Append { step: "decision", status: "COMPLETE" }

    TL->>DB: Store complete audit trail
    IR->>IR: Generate investigator report
    IR->>DB: Store report

    API->>FE: Return decision + trace + report
    FE->>User: Display results
```

---

## Decision Flow

### Claim Decision Flowchart

```mermaid
flowchart TD
    START([📄 Claim Submitted]) --> GW_CHECK{Gateway Agent:<br/>Valid MIME type?<br/>Valid file size?}
    GW_CHECK -->|❌ Invalid| REJECT_UPLOAD["REJECTED<br/>INVALID_DOCUMENT_FORMAT"]
    GW_CHECK -->|✅ Valid| GEN_ID["Generate CLM_2026_XXXX<br/>Initialize Trace Ledger"]

    GEN_ID --> DOC_CHECK{Document Verification:<br/>All required docs present?}
    DOC_CHECK -->|❌ Missing| REJECT_DOCS["REJECTED<br/>MISSING_DOCUMENTS"]
    DOC_CHECK -->|✅ Complete| EXTRACT

    EXTRACT["🧠 AI Extraction Agent<br/>(Gemini 2.5 Flash)<br/>Extract structured data"]
    EXTRACT --> NORMALIZE["Normalization Agent<br/>• Date normalization<br/>• Amount normalization<br/>• Registration normalization"]

    NORMALIZE --> VALIDATE{Validation Agent:<br/>Fields cross-validated?}
    VALIDATE -->|❌ Invalid| REJECT_VALID["REJECTED<br/>EXTRACTION_FAILED"]
    VALIDATE -->|✅ Valid| MED_CHECK

    MED_CHECK["🧠 Medical Necessity Agent<br/>(Gemini 2.5 Flash)<br/>Advisory assessment"]
    MED_CHECK --> ELIG_CHECK

    ELIG_CHECK{Module A: Eligibility<br/>• Policy active?<br/>• Member covered?<br/>• Waiting period OK?}
    ELIG_CHECK -->|❌ Inactive| REJECT_ELIG["REJECTED<br/>POLICY_INACTIVE"]
    ELIG_CHECK -->|❌ Not covered| REJECT_MEMBER["REJECTED<br/>MEMBER_NOT_COVERED"]
    ELIG_CHECK -->|❌ Waiting| REJECT_WAIT["REJECTED<br/>WAITING_PERIOD"]
    ELIG_CHECK -->|✅ Eligible| DOC_VALID

    DOC_VALID{Module B: Documentation<br/>• Doctor reg valid?<br/>• Patient match?<br/>• Date consistency?}
    DOC_VALID -->|❌ Invalid reg| REJECT_REG["REJECTED<br/>DOCTOR_REG_INVALID"]
    DOC_VALID -->|❌ Mismatch| REJECT_PATIENT["REJECTED<br/>PATIENT_MISMATCH"]
    DOC_VALID -->|✅ Valid| COV_CHECK

    COV_CHECK{Module C: Coverage<br/>• Service covered?<br/>• Not excluded?<br/>• Pre-auth if needed?}
    COV_CHECK -->|❌ Not covered| REJECT_COV["REJECTED<br/>SERVICE_NOT_COVERED"]
    COV_CHECK -->|❌ Excluded| REJECT_EXCL["REJECTED<br/>EXCLUDED_CONDITION"]
    COV_CHECK -->|❌ No pre-auth| REJECT_AUTH["REJECTED<br/>PRE_AUTH_MISSING"]
    COV_CHECK -->|⚠️ Partial| PARTIAL_CHECK
    COV_CHECK -->|✅ Covered| FIN_CHECK

    FIN_CHECK{Module D: Financial<br/>• Annual limit OK?<br/>• Sub-limit OK?<br/>• Per-claim limit OK?}
    FIN_CHECK -->|❌ Annual exceeded| REJECT_ANN["REJECTED<br/>ANNUAL_LIMIT_EXCEEDED"]
    FIN_CHECK -->|❌ Sub exceeded| REJECT_SUB["REJECTED<br/>SUB_LIMIT_EXCEEDED"]
    FIN_CHECK -->|❌ Per-claim exceeded| REJECT_PER["REJECTED<br/>PER_CLAIM_EXCEEDED"]
    FIN_CHECK -->|✅ Within limits| COPAY_CALC

    COPAY_CALC["Module D: Apply<br/>• Copay %<br/>• Deductibles<br/>• Network discounts"]

    PARTIAL_CHECK["Module E: Partial Approval<br/>Split covered vs excluded items"]
    PARTIAL_CHECK --> COPAY_CALC

    COPAY_CALC --> FRAUD_RULE

    FRAUD_RULE["🔴 Rule-Based Fraud Engine<br/>• 2+ claims in 24h?<br/>• 5+ same provider in 7d?<br/>• Diagnosis-age mismatch?<br/>• Duplicate bill number?"]
    FRAUD_RULE --> FRAUD_VEC

    FRAUD_VEC["🟡 Vector Fraud Engine<br/>• Generate embedding<br/>• pgvector similarity search<br/>• Threshold > 0.96 = flag"]
    FRAUD_VEC --> FRAUD_AGG

    FRAUD_AGG["📊 Fraud Score Aggregator<br/>Combine rule + vector signals<br/>Score: 0–100"]
    FRAUD_AGG --> FRAUD_DECIDE{Fraud score high?}

    FRAUD_DECIDE -->|"🔴 High (>70)"| MANUAL_REVIEW["MANUAL_REVIEW<br/>Sent to Adjuster Dashboard"]
    FRAUD_DECIDE -->|"🟡 Medium (40-70)"| CONF_CHECK
    FRAUD_DECIDE -->|"🟢 Low (<40)"| CONF_CHECK

    CONF_CHECK["🎯 Confidence Engine<br/>40% Extraction + 40% Rules + 20% Fraud/Doc"]
    CONF_CHECK --> CONF_DECIDE{Confidence >= 0.70?}

    CONF_DECIDE -->|❌ Low confidence| MANUAL_REVIEW
    CONF_DECIDE -->|✅ High confidence| FINAL_DECISION

    FINAL_DECISION{Final Decision}
    FINAL_DECISION -->|All checks pass| APPROVED["✅ APPROVED<br/>Full approved amount"]
    FINAL_DECISION -->|Partial coverage| PARTIAL_APPROVED["⚠️ PARTIAL<br/>Covered portion only"]

    %% Styling
    classDef approve fill:#34A853,stroke:#1e8e3e,color:#fff,stroke-width:3px
    classDef reject fill:#EA4335,stroke:#d93025,color:#fff,stroke-width:2px
    classDef review fill:#FBBC04,stroke:#f29900,color:#000,stroke-width:2px
    classDef ai fill:#4285F4,stroke:#1a73e8,color:#fff,stroke-width:2px
    classDef engine fill:#7C4DFF,stroke:#651FFF,color:#fff,stroke-width:2px

    class APPROVED,PARTIAL_APPROVED approve
    class REJECT_UPLOAD,REJECT_DOCS,REJECT_VALID,REJECT_ELIG,REJECT_MEMBER,REJECT_WAIT,REJECT_REG,REJECT_PATIENT,REJECT_COV,REJECT_EXCL,REJECT_AUTH,REJECT_ANN,REJECT_SUB,REJECT_PER reject
    class MANUAL_REVIEW review
    class EXTRACT,MED_CHECK ai
    class COPAY_CALC,PARTIAL_CHECK engine
```

---

## ER Diagram

### Database Entity-Relationship Diagram

```mermaid
erDiagram
    CLAIMS ||--o{ DOCUMENTS : "has"
    CLAIMS ||--|| EXTRACTED_DATA : "produces"
    CLAIMS ||--o{ AUDIT_TRACES : "logs"
    CLAIMS ||--|| CLAIM_EMBEDDINGS : "embeds"
    CLAIMS ||--o{ FRAUD_SIGNALS : "flags"
    CLAIMS ||--|| INVESTIGATOR_REPORTS : "generates"
    CLAIMS }o--|| MEMBERS : "belongs_to"
    MEMBERS }o--|| POLICIES : "covered_by"
    POLICIES ||--o{ POLICY_EMBEDDINGS : "indexes"

    MEMBERS {
        uuid member_id PK
        string employee_id UK
        string name
        string email
        date date_of_birth
        int age
        string gender
        date join_date
        string relationship
        uuid policy_id FK
        boolean is_active
        timestamp created_at
    }

    POLICIES {
        uuid policy_id PK
        string policy_code UK
        string policy_name
        string company_name
        date effective_date
        date expiry_date
        jsonb coverage_details
        jsonb waiting_periods
        jsonb exclusions
        jsonb network_hospitals
        boolean is_active
        timestamp created_at
    }

    CLAIMS {
        uuid id PK
        string claim_id UK
        uuid member_id FK
        string status
        decimal claim_amount
        decimal approved_amount
        string decision
        float confidence_score
        float fraud_score
        jsonb rejection_reasons
        jsonb decision_metadata
        string reviewer_id
        text reviewer_notes
        timestamp submitted_at
        timestamp processed_at
        timestamp reviewed_at
        timestamp created_at
    }

    DOCUMENTS {
        uuid id PK
        string document_id UK
        uuid claim_id FK
        string document_type
        string file_url
        string file_name
        string mime_type
        bigint file_size
        string storage_path
        timestamp uploaded_at
    }

    EXTRACTED_DATA {
        uuid id PK
        uuid claim_id FK
        string patient_name
        string age
        string doctor_name
        string doctor_registration
        string diagnosis
        jsonb medicines
        jsonb procedures
        jsonb tests
        string provider_name
        decimal bill_amount
        date treatment_date
        float extraction_confidence
        jsonb raw_extraction
        jsonb normalized_data
        timestamp extracted_at
    }

    AUDIT_TRACES {
        uuid id PK
        string trace_id UK
        uuid claim_id FK
        string step
        string status
        jsonb details
        int step_order
        bigint duration_ms
        timestamp timestamp
    }

    CLAIM_EMBEDDINGS {
        uuid id PK
        uuid claim_id FK
        vector_1536 embedding
        jsonb metadata
        timestamp created_at
    }

    FRAUD_SIGNALS {
        uuid id PK
        uuid claim_id FK
        string signal_type
        string engine
        string description
        float severity
        jsonb details
        timestamp detected_at
    }

    INVESTIGATOR_REPORTS {
        uuid id PK
        uuid claim_id FK
        jsonb claim_summary
        jsonb coverage_analysis
        jsonb limit_analysis
        jsonb fraud_analysis
        jsonb decision_rationale
        jsonb what_if_analysis
        jsonb policy_references
        text full_report_text
        timestamp generated_at
    }

    POLICY_EMBEDDINGS {
        uuid id PK
        uuid policy_id FK
        string chunk_text
        string chunk_source
        int chunk_index
        vector_1536 embedding
        timestamp created_at
    }

    MANUAL_REVIEW_QUEUE {
        uuid id PK
        uuid claim_id FK
        string priority
        string reason
        string assigned_to
        string status
        jsonb adjuster_notes
        string override_decision
        decimal override_amount
        timestamp queued_at
        timestamp assigned_at
        timestamp resolved_at
    }
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 15 | React framework with App Router |
| **Language** | TypeScript | Type-safe frontend development |
| **Styling** | TailwindCSS | Utility-first CSS framework |
| **UI Components** | shadcn/ui | Accessible, composable components |
| **Backend** | FastAPI | High-performance Python API |
| **AI/LLM** | Gemini 2.5 Flash | Multimodal extraction & medical assessment |
| **Database** | PostgreSQL (Supabase) | Primary data store |
| **Vector Store** | pgvector | Embedding similarity search |
| **File Storage** | Supabase Storage | Document upload storage |
| **Auth** | Supabase Auth | Authentication (optional) |
| **Deployment (FE)** | Vercel | Frontend hosting |
| **Deployment (BE)** | Render | Backend API hosting |
| **Deployment (DB)** | Supabase | Managed PostgreSQL |
| **CI/CD** | GitHub Actions | Automated testing & deployment |
| **Containerization** | Docker / Docker Compose | Local development & deployment |

---

## Project Structure

```
plum-opd-system/
│
├── docs/                               # 📚 System architecture, assumptions, and design guides
├── database/                           # 🗃️ Database schema init, seed, and migrations SQL
│
├── backend/                            # 🐍 FastAPI Backend
│   ├── api/                            # REST route definitions (routes.py)
│   ├── app/                            # Multi-agent engines, deterministic rules, models, and services
│   ├── tests/                          # 84-case automated test suite
│   ├── main.py                         # Application entrypoint
│   └── requirements.txt                # Python dependencies
│
├── frontend/                           # ⚛️ Next.js 15 Frontend
│   ├── components/                     # React widgets (Timeline, Investigator Report)
│   ├── lib/                            # API fetch utility helper (api.ts)
│   └── src/app/                        # App Router Pages (Submission form, Decision Q&A, Adjuster Dashboard)
│
├── .github/workflows/                  # 🔄 CI/CD pipelines
└── reference/                          # 📎 Original assignment terms, rules, and test cases
```

## Getting Started

### Prerequisites

- **Node.js** >= 20.x
- **Python** >= 3.12
- **Docker** & **Docker Compose** (for local development)
- **Supabase** account (free tier)
- **Google AI** API key (Gemini 2.5 Flash)

### Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/plum-opd-system.git
cd plum-opd-system

# 2. Copy environment variables
cp .env.example .env
# Edit .env with your actual keys

# 3. Start all services with Docker Compose
docker-compose up -d

# 4. Initialize the database
# (Supabase auto-runs init.sql, or manually:)
psql $DATABASE_URL -f database/init.sql
psql $DATABASE_URL -f database/seed.sql

# 5. Start the backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 6. Start the frontend
cd frontend
npm install
npm run dev
```

### Quick Start with Docker

```bash
docker-compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Environment Variables

| Variable | Description | Required |
|----------|------------|----------|
| `SUPABASE_URL` | Supabase project URL | ✅ |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | ✅ |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | ✅ |
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `GEMINI_API_KEY` | Gemini API key (Google AI Studio) | ✅ |
| `GEMINI_MODEL` | Gemini model name (default: `gemini-3.1-flash-lite`) | ❌ |
| `NEXT_PUBLIC_API_URL` | Backend API URL | ✅ |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | ✅ |
| `CORS_ORIGINS` | Allowed CORS origins | ✅ |
| `LOG_LEVEL` | Logging level (INFO/DEBUG) | ❌ |
| `MAX_FILE_SIZE_MB` | Max upload file size (default: 10) | ❌ |
| `FRAUD_SIMILARITY_THRESHOLD` | Vector fraud threshold (default: 0.96) | ❌ |
| `CONFIDENCE_THRESHOLD` | Manual review threshold (default: 0.70) | ❌ |

---

## API Documentation

### Core Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| `POST` | `/api/v1/claims/submit` | Submit new claim with documents |
| `GET` | `/api/v1/claims/{claim_id}` | Get claim details |
| `GET` | `/api/v1/claims` | List all claims (paginated) |
| `GET` | `/api/v1/claims/{claim_id}/decision` | Get claim decision |
| `GET` | `/api/v1/claims/{claim_id}/trace` | Get audit trace ledger |
| `GET` | `/api/v1/claims/{claim_id}/report` | Get investigator report |
| `GET` | `/api/v1/claims/{claim_id}/fraud` | Get fraud signals |
| `POST` | `/api/v1/policy/ask` | Ask RAG policy question |
| `GET` | `/api/v1/review/queue` | Get manual review queue |
| `PUT` | `/api/v1/review/{claim_id}` | Submit review decision |
| `GET` | `/api/v1/health` | Health check |
| `WS` | `/ws/{claim_id}` | Real-time processing updates |

### Full OpenAPI Specification
* **Local Development**: `http://localhost:8000/docs`
* **Live Production Server**: [https://plum-opd-system.onrender.com/docs](https://plum-opd-system.onrender.com/docs)

---

## Testing

### Run All Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app --cov-report=html

# Frontend tests
cd frontend
npm test

# Integration tests (TC001-TC010)
cd backend
pytest tests/test_cases_integration.py -v
```

### Test Cases

| ID | Name | Expected Decision |
|----|------|-------------------|
| TC001 | Simple Consultation | ✅ APPROVED (₹1,350) |
| TC002 | Dental Treatment (Mixed) | ⚠️ PARTIAL (₹8,000) |
| TC003 | Limit Exceeded | ❌ REJECTED (PER_CLAIM_EXCEEDED) |
| TC004 | Missing Documents | ❌ REJECTED (MISSING_DOCUMENTS) |
| TC005 | Pre-existing Condition | ❌ REJECTED (WAITING_PERIOD) |
| TC006 | Alternative Medicine | ✅ APPROVED (₹4,000) |
| TC007 | Pre-auth Required | ❌ REJECTED (PRE_AUTH_MISSING) |
| TC008 | Fraud Detection | 🔶 MANUAL_REVIEW |
| TC009 | Excluded Treatment | ❌ REJECTED (SERVICE_NOT_COVERED) |
| TC010 | Network Hospital | ✅ APPROVED (₹3,600 cashless) |

---

## Deployment

### Frontend → Vercel

1. Import your GitHub repository into [Vercel](https://vercel.com/).
2. Set the **Root Directory** to `frontend`.
3. Configure the environment variable:
   - `NEXT_PUBLIC_API_URL`: Your deployed Render backend URL (`https://<your-service>.onrender.com/api/v1`).
4. Click **Deploy**.

### Backend → Render

1. Create a new **Web Service** on [Render](https://render.com/).
2. Connect your GitHub repository.
3. Choose the **Docker** runtime.
4. Set up environment variables (`DATABASE_URL`, `GEMINI_API_KEY`, `JWT_SECRET`).
5. Click **Deploy Web Service**.

### Database → Supabase

1. Create a new Supabase project
2. Run `database/init.sql` in the SQL editor
3. Run `database/seed.sql` for initial data
4. Enable the `vector` extension

---

## Assumptions

1. **Policy Configuration**: Using the provided `policy_terms.json` as the single policy configuration
2. **Member Data**: Pre-seeded member records for test case employees (EMP001–EMP010)
3. **Doctor Registration**: Format validated as `[StateCode]/[Number]/[Year]` or `AYUR/[StateCode]/[Number]/[Year]`
4. **Copay Calculation**: 10% copay on consultation fees as defined in policy terms
5. **Network Discount**: 20% discount applied to consultation fees at network hospitals
6. **Per-claim Limit**: Strict ₹5,000 per-claim ceiling — claims exceeding this are REJECTED
7. **Sub-limit Enforcement**: Each coverage category (consultation, pharmacy, dental, etc.) has independent sub-limits
8. **Fraud Score Thresholds**: >70 = MANUAL_REVIEW, 40-70 = flagged but proceeds, <40 = clean
9. **Confidence Threshold**: Claims with confidence < 0.70 are sent to MANUAL_REVIEW
10. **Vector Similarity**: Threshold of 0.96 for POTENTIAL_DUPLICATE_PATTERN detection
11. **File Size Limit**: Maximum 10MB per uploaded document
12. **Supported Formats**: PDF, JPG, JPEG, PNG only
13. **Claim ID Format**: `CLM_YYYY_XXXX` where YYYY is current year, XXXX is zero-padded sequence
14. **Currency**: All amounts in Indian Rupees (₹ / INR)
15. **Timezone**: All timestamps in UTC, displayed in IST for the UI
16. **Pre-authorization**: MRI and CT Scan require pre-auth for claims above ₹10,000

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for Plum Insurance**
