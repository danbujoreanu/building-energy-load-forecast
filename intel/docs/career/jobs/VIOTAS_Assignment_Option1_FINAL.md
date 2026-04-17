---
title: "VIOTAS_Deliverables — VIOTAS_Assignment_Option1_FINAL"
document_type: job_spec
tier: career
company: VIOTAS_Deliverables
role_title: VIOTAS_Assignment_Option1_FINAL
date_added: "2026-01-30"
application_status: evaluating
status: active
---

# VIOTAS AI & Energy Optimisation Assessment: Option 1

**Candidate:** Dan Bujoreanu  
**Date:** January 30, 2026

---

## Option 1: AI for Operational Optimisation

This response outlines a pragmatic approach to embedding AI into VIOTAS's core operations, focusing on delivering measurable value quickly while building a foundation for long-term strategic advantage. The proposed solutions are based on my experience scaling operations and implementing AI systems at Meta and in applied research.

### 1A. Identify Optimisation Opportunities

Based on my experience in operationally complex and regulated environments, inefficiencies often arise where manual processes intersect with large volumes of data and multi-stakeholder workflows. I assume VIOTAS, as a dynamic and growing company, faces similar challenges.

| Inefficiency Area | Description & Affected Teams | Potential Improvement |
| :--- | :--- | :--- |
| **1. Client Onboarding & Asset Integration** | The process of bringing a new commercial or industrial client's assets into the portfolio is likely data-intensive, bespoke, and requires significant manual effort. This involves validating technical specifications, analyzing historical energy data, and configuring systems. **Affected Teams:** Sales, Engineering, Operations. | **Time & Cost Reduction:** Dramatically shorten the sales-to-revenue cycle. **Increased Scalability:** Allow VIOTAS to onboard more clients without a linear increase in headcount. **Improved Client Experience:** Faster, data-driven onboarding process. |
| **2. Regulatory Reporting & Compliance** | Generating reports for multiple grid operators and regulatory bodies across different jurisdictions is often a manual, repetitive task. It involves collating data from various systems, formatting it to specific templates, and ensuring accuracy under tight deadlines. **Affected Teams:** Compliance, Legal, Operations. | **Error Reduction & Risk Mitigation:** Automate data aggregation and formatting to minimize human error and ensure auditability. **Time Savings:** Free up the compliance team to focus on strategic regulatory analysis rather than report generation. |
| **3. Market Bidding & Strategy** | Formulating daily bidding strategies likely relies on a combination of experienced traders analyzing market data and complex spreadsheets. This can be slow, prone to cognitive biases, and may not fully leverage all available data signals (e.g., weather, unscheduled outages). **Affected Teams:** Trading, Commercial, Data Analytics. | **Improved Decision Quality:** Leverage AI to analyze more variables and identify profitable opportunities that a human might miss. **Increased Speed & Consistency:** Enable faster, more consistent bidding decisions, especially in volatile market conditions. |

### 1B. Deep Dive: Client Onboarding & Asset Integration

Of these opportunities, optimising **Client Onboarding & Asset Integration** offers the most significant strategic value. It is the primary bottleneck to growth and the area where a pragmatic AI solution can create a powerful competitive advantage, transforming a cost centre into a proactive growth engine.

#### 1. The Problem

Currently, the onboarding process is likely a reactive, linear, and manual workflow:

*   **High Friction:** Sales teams identify a lead, but qualifying them requires a slow back-and-forth to gather technical data (e.g., meter readings, asset specifications) in inconsistent formats (PDFs, spreadsheets).
*   **Manual Validation:** The engineering team must manually validate this data, a process that is both time-consuming and error-prone. This diverts highly skilled engineers from value-added work like improving the core platform.
*   **Slow Decision-Making:** It is difficult to accurately forecast the potential revenue from a new asset, making it hard to prioritize high-value clients. Decisions are based on experience and intuition rather than data-driven simulation.

This inefficiency directly constrains VIOTAS's ability to capitalize on market opportunities, such as the rapid expansion of data centres in Ireland. Competitors with smoother onboarding processes can capture market share more quickly.

![Reactive vs Proactive Business Model](reactive_vs_proactive.png)
*Figure 1: Transformation from Reactive to Proactive Business Model*

#### 2. A Pragmatic AI-Enabled Solution: The "80/20 Proactive Onboarding System"

I propose an AI-assisted system designed to **automate 80% of the routine onboarding work**, freeing up experts to focus on the 20% of complex, high-value tasks. This system shifts VIOTAS from a reactive to a **proactive** model.

**The Role of AI:**

1.  **Proactive Lead Identification (AI Assistant):** An AI agent continuously scans public data sources (e.g., planning permissions, industry news APIs) to identify and pre-qualify potential high-value clients, such as new data centres or manufacturing plants, before they even consider demand-side flexibility.

2.  **Automated Data Ingestion & Validation (AI Validator):** When a client provides their energy data, an AI-powered workflow ingests it (using OCR for PDFs if needed), validates it against a predefined set of rules (e.g., checking for missing values, anomalous readings), and flags exceptions for human review. This is the core of the "80%" automation.

3.  **Digital Twin Simulation & Proposal Generation (AI Decision Support):** For qualified clients, the system uses the validated data to create a lightweight "Digital Twin" of the asset. It then runs simulations against historical market data to generate a data-backed forecast of potential earnings. This transforms the sales pitch from "we can help you" to "we can generate an estimated €X for you, and here's the data to prove it." This directly leverages my research in time-series forecasting with tree-based models, which are perfect for this task due to their high accuracy and low computational cost.

4.  **Intelligent Workflow Orchestration:** The entire process is managed by an agentic workflow tool (e.g., **LangGraph** or **n8n**). This AI "supervisor" routes tasks between systems, notifies the correct teams of exceptions, and provides a real-time dashboard of the entire onboarding pipeline.

**Data Sources:**
*   **External:** Public planning portals, news APIs, corporate registries.
*   **Client-Provided:** Electricity bills (PDF), meter data (CSV/XLS), asset specification sheets (PDF).
*   **Internal:** VIOTAS historical market data, existing asset performance data.

**Implementation Timeline:**

![Implementation Timeline](implementation_timeline.png)
*Figure 2: Phased Implementation Timeline (9 Months)*

The implementation follows a pragmatic, phased approach:

*   **Phase 1 (Months 1-3): Foundation & Quick Wins** - Focus on process mapping and deploying the automated data validator to deliver immediate value.
*   **Phase 2 (Months 4-6): Intelligence & Simulation** - Build the Digital Twin simulation engine and proactive lead identification system.
*   **Phase 3 (Months 7-9): Integration & Scaling** - Integrate all components with full workflow orchestration and roll out to the entire organization.

#### 3. What Success Looks Like (3-6 Months)

Success is measured by the speed and efficiency of growth.

| Metric | Baseline (Estimate) | Target (6 Months) | Rationale |
| :--- | :--- | :--- | :--- |
| **Time to Onboard** (Initial contact to live asset) | 4-6 Weeks | 1-2 Weeks | **75% Reduction.** Faster time-to-revenue. |
| **Assets Onboarded per Quarter** | X | 2X | **100% Increase.** Directly measures scalability. |
| **Engineering Time on Onboarding** | 20 hours/asset | <5 hours/asset | **75% Reduction.** Frees up expert resources for innovation. |
| **Sales Conversion Rate** | Y% | Y + 15% | Data-backed proposals increase client confidence. |

### Risk & Governance

A pragmatic approach requires building robust guardrails from day one.

**Key Risks & Mitigations:**

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Data Protection (GDPR)** | Regulatory fines, reputational damage | All client data processed in secure, isolated environment. Data minimization principles. Full DPIA before deployment. |
| **Incorrect Outputs (Hallucination/Error)** | Poor client experience, financial loss | Human-in-the-loop design. AI suggests, humans decide. Revenue forecasts presented with confidence intervals. |
| **Over-reliance by Users** | Degraded decision quality, skill atrophy | Comprehensive training program. Transparent UI showing AI reasoning. Regular calibration exercises. |
| **System Downtime** | Onboarding delays, client frustration | Fallback to manual processes. Robust monitoring and alerting. |

**Explicit Prohibitions:**
*   The system will **never** be allowed to automatically sign contracts or make financial commitments on behalf of VIOTAS.
*   It will **never** share data between clients, even if anonymized.
*   It will **not** perform any real-time control actions on a client's assets. Its role is strictly limited to the onboarding and simulation phase.

---

## Part 3: The Future of AI Platforms & Strategic Resilience

This section addresses the strategic challenge of navigating the rapidly evolving AI landscape. My philosophy is to design for **resilience and optionality**, avoiding vendor lock-in while leveraging the best capabilities available. This is based on my experience at Meta, where we frequently built internal systems on top of open-source foundations to maintain flexibility.

### 3A. Your View of the AI Platform Landscape

I view the AI platform landscape not as a single race, but as a multi-layered ecosystem with different leaders emerging in different niches.

**Evolution of Enterprise AI Usage (Next 2-3 Years):**

1.  **From Ad-Hoc to Embedded:** AI usage will move from standalone tools like ChatGPT to being deeply embedded within core business workflows (like the onboarding system I proposed).

2.  **Rise of the AI "Supervisor":** We will see the proliferation of agentic workflows and AI orchestrators (like LangGraph or n8n) that act as the "brains" of a business process, intelligently routing tasks to the best model (whether it's an LLM, a forecasting model, or a simple rules engine) for the job.

3.  **Small, Fine-Tuned Models for Specific Tasks:** While large foundation models are powerful, the trend will be towards using smaller, open-source models (e.g., Llama 3, Mistral) that are fine-tuned on a company's specific data for superior performance on narrow tasks (like classifying client support tickets or forecasting energy load for a specific asset type).

**Key Differentiators Between Major Platforms:**

| Platform/Ecosystem | Key Differentiator & Strength | Best For... |
| :--- | :--- | :--- |
| **OpenAI (ChatGPT)** | **Raw Capability & Brand:** Still the leader in general reasoning and creative text generation. Strongest API and developer mindshare. | Rapid prototyping, user-facing chatbots, tasks requiring high-level reasoning. |
| **Microsoft Copilot/Azure AI** | **Enterprise Integration & Security:** Deeply integrated into the Microsoft 365 ecosystem. Strong on security, compliance, and data governance. | Regulated industries, companies heavily invested in the Microsoft stack. |
| **Google Gemini/Vertex AI** | **Data & Multimodality:** Best-in-class for handling multimodal inputs (text, image, video). Tightly integrated with Google's powerful data and analytics ecosystem (BigQuery, etc.). | Complex data analysis, building sophisticated RAG systems (Vertex AI Search), and orchestrating complex ML pipelines. |
| **Open-Source (Llama, Mistral)** | **Control & Cost-Effectiveness:** Offers complete control over the model and data. Can be significantly cheaper to run for specific, high-volume tasks. | Fine-tuning on proprietary data, building specialized models, avoiding vendor lock-in. |

### 3B. "Which LLM will win?" (and why that may be the wrong question)

Asking "which LLM will win?" is like asking "which tool should a carpenter use?" The answer is: it depends on the job. Betting on a single AI platform is not only unrealistic, it's strategically unwise. The real winner will be the company that builds a flexible architecture capable of leveraging the best tool for each task.

*   **When to Favor One Platform:** I would favor **Microsoft Copilot/Azure AI** for tasks that involve sensitive employee or client data that already resides within the Microsoft 365 ecosystem. Their enterprise-grade security and data residency guarantees are critical in a regulated context. However, I would favor **Google Vertex AI** for building the core ML pipelines for our forecasting and simulation models, due to its superior MLOps capabilities.

*   **Where Lock-in Risk Exists:**
    *   **Genuine Risk:** Lock-in is a genuine risk at the **data and workflow integration layer**. If all your data pipelines, monitoring, and user interfaces are built using a single vendor's proprietary tools (e.g., building everything inside Vertex AI or Azure ML Studio), it becomes incredibly difficult and expensive to switch.
    *   **Overstated Risk:** Lock-in at the **model layer** is overstated. The cost of switching a model API call from OpenAI to Google or an open-source model is relatively low, provided the application is architected correctly.

### 3C. Designing for Resilience and Optionality

To ensure VIOTAS is not overly exposed, I would implement the following design principles for all AI solutions:

![AI Core Architecture](ai_core_architecture.png)
*Figure 3: VIOTAS AI Core Architecture - Modular and Vendor-Neutral*

**1. The Abstraction Layer ("VIOTAS AI Gateway")**

We will build a simple, internal "VIOTAS AI Gateway" service. All applications in the company will make calls to this internal gateway, not directly to OpenAI or Google. This gateway will be responsible for routing the request to the best and most cost-effective model for the task. If we want to switch from GPT-4 to Claude 3, we change one line of code in the gateway, and every application is instantly updated. This is a common pattern at large tech companies.

**2. Modular, API-First Architecture**

Every component of our AI system (the data validator, the digital twin simulator, the reporting tool) will be built as an independent microservice with a clean API. This allows us to swap out, upgrade, or replace individual components without having to rebuild the entire system.

**3. Prioritize Open-Source for Core Logic**

The "connective tissue" of our AI systems—the workflow orchestration—should be built on open-source tools like **n8n** or **LangGraph**. This gives us maximum control and flexibility, preventing a vendor from holding our core business logic hostage.

**4. Data Sovereignty**

We will maintain our own "golden source" of data in a vendor-neutral format (e.g., in a cloud-agnostic data warehouse). We can then grant AI models access to this data, but we never cede ownership of it to the AI vendor.

**The Trade-off:** This approach requires slightly more upfront design and engineering effort than simply using a single vendor's all-in-one platform. However, this small investment in **speed and simplicity** today pays massive dividends in **long-term optionality and resilience** tomorrow. It is the only responsible way to build strategic AI systems in a rapidly changing world.

---

## Final Task — Executive Communication

**To:** VIOTAS Leadership Team  
**From:** Dan Bujoreanu  
**Subject:** A Pragmatic Path to AI-Driven Growth

Team,

My analysis shows a significant opportunity to accelerate our growth by tackling a key operational bottleneck: **client onboarding**. We can use a pragmatic AI system to automate 80% of this manual work, doubling our onboarding capacity within 6 months and freeing up our expert engineers.

This aligns perfectly with the current Irish market, where the boom in data centres creates a massive opportunity for our demand-side flexibility services. By using AI to proactively identify and onboard these high-value clients, we can outmaneuver larger competitors.

The key is to build this with a **modular, vendor-neutral architecture**. This ensures we leverage the best AI capabilities available today while maintaining the flexibility to adapt as the technology landscape evolves. We avoid the strategic risk of vendor lock-in.

However, we must be clear-eyed about the risk: AI is a powerful tool, but it is not infallible. We must design these systems with robust governance, human oversight, and explicit guardrails to ensure they enhance, rather than replace, human judgement in critical decisions.

I would welcome the opportunity to discuss this proposal in detail.

---

## Optional: Information to Validate in First Two Weeks

Before committing to this solution, I would seek to validate my assumptions and understand the landscape by:

1.  **Mapping the Process:** Shadow the sales, engineering, and operations teams to create a detailed process map of the current onboarding workflow. I would use process mining techniques to identify the exact duration and friction points of each step.

2.  **Interviewing Stakeholders:**
    *   **Head of Sales:** What are the biggest client objections? Where do deals stall?
    *   **Head of Engineering:** What are the most common data quality issues? How much time is spent on manual validation?
    *   **Compliance Officer:** What are the specific data residency and regulatory constraints for each market we operate in?

3.  **Auditing Data:** Get access to a sample of anonymized client data (successful and unsuccessful onboardings) to understand the real-world complexity and quality. This would allow me to test the feasibility of the AI validator and Digital Twin components.

4.  **Reviewing the Tech Stack:** Understand the existing CRM, data warehouse, and core platform technologies to ensure the proposed solution can be integrated effectively.

This initial discovery phase is crucial for refining the solution and ensuring it delivers maximum impact with minimum disruption.

---

**End of Submission**
