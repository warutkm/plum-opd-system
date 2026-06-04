# Adjudication Decision Tree Flow

This document details the rule-engine decision tree used to evaluate claims against policy limits.

```mermaid
graph TD
    classDef startEnd fill:#f8fafc,stroke:#cbd5e1,stroke-width:2px;
    classDef check fill:#eff6ff,stroke:#bfdbfe,stroke-width:2px;
    classDef pass fill:#f0fdf4,stroke:#bbf7d0,stroke-width:2px;
    classDef fail fill:#fef2f2,stroke:#fecaca,stroke-width:2px;

    Start([Incoming Claim Payload]) --> ActiveCheck{Is Policy Active &<br/>Patient a Member?}
    
    ActiveCheck -- No --> ActiveFail[REJECTED<br/>Reason: POLICY_INACTIVE / INVALID_MEMBER]
    ActiveCheck -- Yes --> DocCheck{Are Bill & Prescription<br/>Uploaded?}
    
    DocCheck -- No --> DocFail[REJECTED<br/>Reason: MISSING_DOCUMENTS]
    DocCheck -- Yes --> NameCheck{Does Patient Name Match<br/>Member Record >85%?}
    
    NameCheck -- No --> NameFail[REJECTED<br/>Reason: PATIENT_MISMATCH]
    NameCheck -- Yes --> DateCheck{Does Visit Date Match<br/>Invoice within 3 Days?}
    
    DateCheck -- No --> DateFail[REJECTED<br/>Reason: DATE_MISMATCH]
    DateCheck -- Yes --> ExcludeCheck{Is Diagnosis/Treatment<br/>on Excluded List?}
    
    ExcludeCheck -- Yes --> ExcludeFail[REJECTED<br/>Reason: SERVICE_NOT_COVERED / COSMETIC_EXCLUSION]
    ExcludeCheck -- No --> WaitCheck{Has Condition Waiting<br/>Period Passed?}
    
    WaitCheck -- No --> WaitFail[REJECTED<br/>Reason: WAITING_PERIOD]
    WaitCheck -- Yes --> PreAuthCheck{Is Claim >₹10,000 &<br/>Requires Pre-Auth?}
    
    PreAuthCheck -- Yes (No Auth) --> PreAuthFail[REJECTED<br/>Reason: PRE_AUTH_MISSING]
    PreAuthCheck -- No (Or Approved) --> LimitCheck{Does Claim Exceed<br/>Per-Claim/Sub-Limits?}
    
    LimitCheck -- Yes (Entirely) --> LimitFail[REJECTED<br/>Reason: PER_CLAIM_EXCEEDED]
    LimitCheck -- Yes (Partially) --> PartialApp[PARTIAL APPROVAL<br/>Payout capped at sub-limits]
    LimitCheck -- No --> FullApp[APPROVED<br/>Apply co-pay & discounts]

    class Start FullApp,PartialApp pass;
    class ActiveFail,DocFail,NameFail,DateFail,ExcludeFail,WaitFail,PreAuthFail,LimitFail fail;
    class ActiveCheck,DocCheck,NameCheck,DateCheck,ExcludeCheck,WaitCheck,PreAuthCheck,LimitCheck check;
```
