---
title: "CRU202517 Smart Meter Data Access Code — Appendix A Draft Application"
source_org: "CRU"
source_url: "https://www.cru.ie/document_group/smart-metering-programme/"
publication_date: "2025-02-19"
effective_date: "2026-06-01"
document_type: "consultation_draft"
tier: "operational"
roadmap_tags: ["E-30", "D-29", "P-12"]
status: "active"
---
# CRU202517 Smart Meter Data Access Code — Appendix A Draft Application

**Status**: DRAFT — ready to submit once (1) company incorporated in Ireland and (2) ESB Networks opens SMDS for testing/applications.

**Reference**: CRU202517, Published 19/02/2025
**Applicant category**: Eligible Party — Energy Service Company (ESCO)
**Access is FREE** for Eligible Parties (Section 14.1 of CRU202517: "Eligible Parties shall not be liable to pay charges to the DSP to access the Smart Meter Data or the Smart Meter Data System.")

---

## PART A: Company & Contact Details

| Field | Value |
|-------|-------|
| Full Company Name | [COMPANY NAME] Ltd |
| User Category | Energy Service Company (ESCO) |
| Company Number | [CRO Number — to be assigned on incorporation] |
| Registered Republic of Ireland office address | [Registered office address — Ireland] |
| Domicile of Head Office | Republic of Ireland |
| Registered website address | [TBD — e.g. www.[product].ie] |
| Contact Person | Dan Alexandru Bujoreanu |
| Job Title | Chief Executive Officer / Founder |
| Email Address | [company email] |
| Telephone Number | [company phone] |
| Name of DPO | [DPO name — may be founder initially; document with CRU] |
| Email Address of DPO | [DPO email] |
| Telephone Number of DPO | [DPO phone] |

---

## PART B: About the Data

### Data Items Requested

All data items below are defined in Appendix B (Data Dictionary) of CRU202517.

| Data Item | Identifier | Reason Required |
|-----------|-----------|-----------------|
| 30-minute Interval Consumption Data — Active Import (kW) | Interval Data | Core input to load forecasting model. 30-min granularity required for H+1 and H+24 horizon forecasting. |
| 30-minute Interval Channel Consumption Data — Active Export (kW) | Interval Data | Required to identify solar self-consumption patterns and net load calculation for customers with micro-generation. |
| 24-hr Cumulative Active Import Register (kWh) — daily snapshot | Register Data | Used for daily energy budget calculations and plan optimisation. |
| Midnight Snapshot of SST Day / Peak / Night Import Register (kWh) | Register Data | Required to calculate cost under Standard Smart Tariff (SST) and time-of-use tariff plans, enabling plan optimisation recommendations. |
| Validated Historical Metering and Consumption Data — up to 24 months | Historical | Required for model training and cold-start period (minimum 30 days; 24 months preferred for seasonal coverage). |

**Note**: We do NOT require Event and Instrumentation Data. We do NOT request data for any purpose beyond those stated below.

### Date of Application

[Date of submission — once SMDS is open for applications]

### End Date for Data Use

Open-ended for the duration of the Active Permission granted by each Final Customer, subject to the Final Customer's right to revoke at any time.

---

### Use Case

**Purpose for which data will be processed:**

[COMPANY NAME] Ltd is an Energy Service Company providing AI-powered electricity load forecasting and energy management recommendations to Irish residential and SME electricity consumers. We process Smart Meter Data for the following specific purposes:

1. **Energy Load Forecasting**: Training and running machine learning models (gradient-boosted trees; LightGBM architecture) to produce 30-minute-resolution electricity consumption forecasts at H+1 and H+24 horizons for each consenting Final Customer. Forecasts are used to generate personalised daily energy briefs and identify optimal appliance scheduling windows.

2. **Tariff & Plan Optimisation**: Analysing a Final Customer's historical import/export profile against available electricity tariff structures (including SST Day/Peak/Night registers and Free Time tariffs) to identify the most cost-effective plan and quantify potential savings. This includes recommendations on time-of-use shifting aligned to the customer's actual consumption pattern.

3. **Demand Flexibility Recommendations**: Identifying periods when grid carbon intensity and electricity prices are lowest and recommending load-shifting to those windows, contributing to demand flexibility objectives consistent with the DSO's market facilitation role.

4. **Personalised Energy Efficiency Reporting**: Generating monthly consumption summaries, trend analysis, and behavioural insights for Final Customers, presented via a mobile application and/or web dashboard.

**Confirmation that [COMPANY NAME] Ltd will act as Data Controller**: Yes. [COMPANY NAME] Ltd acts as Data Controller for all Smart Meter Data transferred to it from the Smart Meter Data System. We accept full responsibility and liability for that data once transferred.

**Legal basis relied upon**: Active Permission from the Final Customer. Each Final Customer provides explicit, informed, revocable consent via the ESB Networks Permission Administration interface before any of their Smart Meter Data is accessed. We do not rely on any other legal basis for access to Smart Meter Data. The Active Permission is granted on a per-MPRN, per-use-case basis.

**Confirmation that intended use is within the EEA**: Yes. All data processing infrastructure is hosted on AWS eu-west-1 (Dublin, Ireland). No raw Smart Meter Data is transmitted outside the EEA. Specifically, pre-computed aggregate statistics (not raw interval data) are used as inputs to third-party AI services, where applicable.

**Agreement to comply with the Code**: Yes. By submitting this application, [COMPANY NAME] Ltd agrees to comply with the CRU Smart Meter Data Access Code (CRU202517) in full, including all schedules and appendices, as updated from time to time.

---

## PART D: Declaration

| Declaration | Confirmed |
|-------------|-----------|
| We confirm we operate in the User Category indicated (ESCO) and hold all necessary licences/permissions | Yes — [COMPANY NAME] Ltd is incorporated in the Republic of Ireland and operates as an Energy Service Company. No electricity supply licence is required for this activity. |
| We confirm all information in this application is true and complete and will remain so throughout data processing | Yes |
| We confirm we will comply with all applicable laws in respect of the use of the data, including all data protection laws | Yes |
| We undertake that data will not be processed in a way incompatible with the stated purposes | Yes |
| We acknowledge the Commission's right to verify compliance via audit | Yes |
| We confirm that Personal Data received from the DSP is processed securely and that appropriate technical and organisational measures are in place | Yes — see Security Annex below |
| We confirm that we are subject to CRU enforcement authority, including suspension or revocation of data access | Yes |

**Signature of Authorised Signatory**: _______________________
**Name and role**: Dan Alexandru Bujoreanu, Director
**Date**: [Date of submission]

---

## SECURITY ANNEX (Schedule 3 Compliance Summary)

This annex maps our technical and organisational security measures to Schedule 3 of CRU202517.

| Requirement | Our Implementation |
|-------------|-------------------|
| Information Security Policy | Documented ISMS aligned to ISO 27001 principles. Reviewed annually. |
| Data residency | AWS eu-west-1 (Dublin). No cross-border transfer of raw data. |
| Encryption at rest | AES-256 (AWS S3/RDS default encryption). |
| Encryption in transit | TLS 1.2+ for all API communication. |
| Access control | Role-based access control (RBAC). Principle of least privilege. MFA enforced for all staff accessing production systems. |
| Audit logging | All data access events logged with timestamp, party identifier, and permission identifier. Logs retained for [24 months / per DSP Data Retention Policy]. |
| Vulnerability assessments | Annual third-party penetration test. Automated dependency scanning (Dependabot/Snyk). |
| Breach notification | Notified to DSP and Commission without undue delay and in any event within 72 hours of becoming aware of a confirmed breach. |
| Staff training | All staff complete data protection and security awareness training on onboarding and annually. |
| Data Retention | Smart Meter Data deleted or anonymised in accordance with the DSP's Data Retention Policy and GDPR Art. 5(1)(e) storage limitation principle. Personal Data deleted within 30 days of permission revocation or service termination. |
| Sub-processors | Any sub-processor receiving Smart Meter Data is bound by equivalent contractual security obligations. Current sub-processors: AWS (infrastructure). |

---

## FILING CHECKLIST

Complete these steps before submission:

- [ ] Incorporate [COMPANY NAME] Ltd in Republic of Ireland (CRO registration)
- [ ] Obtain company CRO number
- [ ] Appoint Data Protection Officer (or document DPO exemption reasoning under GDPR Art. 37)
- [ ] Register with Data Protection Commission (DPC) as a Data Controller processing special-category / sensitive data (electricity data = occupancy proxy)
- [ ] Establish company email domain and website (required by Appendix A)
- [ ] Complete ISO 27001 self-assessment or equivalent ISMS documentation
- [ ] Monitor ESB Networks / CRU website for SMDS testing launch announcement (Section 7.7 — DSP must provide testing access before live; apply for testing access first)
- [ ] File Appendix A with DSP (ESB Networks) once SMDS open
- [ ] Request Code Panel observer status (Section 13) — gives early visibility of SMDS implementation timeline and use case approvals

---

## STRATEGIC NOTES

**Why we qualify as an ESCO (not "Other User")**:
CRU202517 Schedule 1 defines ESCO as: *"a party offering energy-related services to the Final Customer, but not directly active in the energy value chain or the physical infrastructure itself."* This is the precise definition of our product. This matters because:
- ESCOs are Eligible Parties → access is FREE
- ESCOs do not require a separate DSP approval process; the Appendix A form is sufficient
- ESCOs are named alongside suppliers, TSO, SEMO, aggregators as first-class parties

**Consent flow (our app)**:
Under Section 6.5, the DSP (ESB Networks) is the Permission Administrator. The Final Customer grants Active Permission via the ESB Networks portal. Our app will:
1. Direct the customer to the ESB Networks permission portal
2. Customer selects our company as an Eligible Party and grants permission for the specific data items above
3. ESB Networks logs the permission with timestamp and notifies our SMDS endpoint
4. We begin receiving data for that MPRN

This is analogous to the UK's N3rgy/DCC model but simpler: no intermediary like N3rgy — ESB Networks is both DSP and Permission Administrator.

**Timeline risk (competitive)**:
The Code is published (19/02/2025). ESB Networks must now build the SMDS. No public launch date confirmed. Estimate: SMDS testing access H2 2025–Q1 2026; live access Q2–Q3 2026. Any ESCO can apply once the DSP opens for applications. **First-mover advantage is in being ready to apply on day one and onboarding users immediately.**

**Immediate actions to stay ahead**:
1. Incorporate the company now (1–2 weeks, CRO online)
2. Monitor CRU website (cru.ie) and ESB Networks developer portal for SMDS launch
3. Request a pre-application meeting with ESB Networks DSP team — the Code obliges them to cooperate with Eligible Parties for testing (Section 7.7)
4. File for AWS Activate now (uses open-source repo, no company required) to fund infrastructure ahead of SMDS launch
