-- ============================================================================
-- PLUM OPD CLAIM ADJUDICATION SYSTEM — Database Seed
-- ============================================================================

-- Seed Policy
INSERT INTO policies (id, policy_code, policy_name, company_name, effective_date, coverage_details, waiting_periods, exclusions, network_hospitals, claim_requirements, cashless_facilities)
VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'PLUM_OPD_2024',
    'Plum OPD Advantage',
    'TechCorp Solutions Pvt Ltd',
    '2024-01-01',
    '{
      "annual_limit": 50000,
      "per_claim_limit": 5000,
      "family_floater_limit": 150000,
      "consultation_fees": { "covered": true, "sub_limit": 2000, "copay_percentage": 10, "network_discount": 20 },
      "diagnostic_tests": { "covered": true, "sub_limit": 10000, "pre_authorization_required": false, "covered_tests": ["Blood tests", "Urine tests", "X-rays", "ECG", "Ultrasound", "MRI (with pre-auth)", "CT Scan (with pre-auth)"] },
      "pharmacy": { "covered": true, "sub_limit": 15000, "generic_drugs_mandatory": true, "branded_drugs_copay": 30 },
      "dental": { "covered": true, "sub_limit": 10000, "routine_checkup_limit": 2000, "procedures_covered": ["Filling", "Extraction", "Root canal", "Cleaning"], "cosmetic_procedures": false },
      "vision": { "covered": true, "sub_limit": 5000, "eye_test_covered": true, "glasses_contact_lenses": true, "lasik_surgery": false },
      "alternative_medicine": { "covered": true, "sub_limit": 8000, "covered_treatments": ["Ayurveda", "Homeopathy", "Unani"], "therapy_sessions_limit": 20 }
    }'::jsonb,
    '{
      "initial_waiting": 30,
      "pre_existing_diseases": 365,
      "maternity": 270,
      "specific_ailments": { "diabetes": 90, "hypertension": 90, "joint_replacement": 730 }
    }'::jsonb,
    '["Cosmetic procedures", "Weight loss treatments", "Infertility treatments", "Experimental treatments", "Self-inflicted injuries", "Adventure sports injuries", "War and nuclear risks", "HIV/AIDS treatment", "Alcoholism/drug abuse treatment", "Non-allopathic treatments (except listed)", "Vitamins and supplements (unless prescribed for deficiency)"]'::jsonb,
    '["Apollo Hospitals", "Fortis Healthcare", "Max Healthcare", "Manipal Hospitals", "Narayana Health"]'::jsonb,
    '{
      "documents_required": ["Original bills and receipts", "Prescription from registered doctor", "Diagnostic test reports (if applicable)", "Pharmacy bills with prescription", "Doctor''s registration number must be visible", "Patient details must match policy records"],
      "submission_timeline_days": 30,
      "minimum_claim_amount": 500
    }'::jsonb,
    '{
      "available": true,
      "network_only": true,
      "pre_approval_required": false,
      "instant_approval_limit": 5000
    }'::jsonb
) ON CONFLICT (id) DO NOTHING;

-- Seed Members
INSERT INTO members (employee_id, name, join_date, policy_id) VALUES
('EMP001', 'Rajesh Kumar', '2024-01-01', '550e8400-e29b-41d4-a716-446655440000'),
('EMP002', 'Priya Singh', '2024-01-01', '550e8400-e29b-41d4-a716-446655440000'),
('EMP003', 'Amit Verma', '2024-01-01', '550e8400-e29b-41d4-a716-446655440000'),
('EMP004', 'Sneha Reddy', '2024-01-01', '550e8400-e29b-41d4-a716-446655440000'),
('EMP005', 'Vikram Joshi', '2024-09-01', '550e8400-e29b-41d4-a716-446655440000'),
('EMP006', 'Kavita Nair', '2024-01-01', '550e8400-e29b-41d4-a716-446655440000'),
('EMP007', 'Suresh Patil', '2024-01-01', '550e8400-e29b-41d4-a716-446655440000'),
('EMP008', 'Ravi Menon', '2024-01-01', '550e8400-e29b-41d4-a716-446655440000'),
('EMP009', 'Anita Desai', '2024-01-01', '550e8400-e29b-41d4-a716-446655440000'),
('EMP010', 'Deepak Shah', '2024-01-01', '550e8400-e29b-41d4-a716-446655440000')
ON CONFLICT (employee_id) DO NOTHING;
