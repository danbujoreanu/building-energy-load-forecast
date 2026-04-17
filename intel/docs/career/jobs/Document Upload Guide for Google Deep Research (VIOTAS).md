---
title: "Preparing for VIOTAS AI Lead Assessment Task — Document Upload Guide for Google Deep Research (VIOTAS)"
document_type: job_spec
tier: career
company: Preparing for VIOTAS AI Lead Assessment Task
role_title: Document Upload Guide for Google Deep Research (VIOTAS)
date_added: "2026-02-09"
application_status: evaluating
status: active
---

# Document Upload Guide for Google Deep Research (VIOTAS)

To give Google Deep Research (or Claude) the best possible context for your VIOTAS market analysis, you should upload the following documents alongside the prompt. This will ground the AI in the specific academic frameworks and recent market intelligence you want to reference.

---

## Core Documents to Upload

### 1. Academic & Strategic Frameworks

These documents provide the theoretical lens for the analysis.

| Filename | Purpose |
| :--- | :--- |
| `CourseOutline-BMGT44000CompetitiveStrategy2024-25.docx` | Provides Grant & Porter frameworks |
| `ModuleOutline-DigitalStrategyandTransformationDEFrev13_02_2025.pdf` | Provides Teece, O'Reilly, Christensen frameworks |
| `BMGT41040OperationsInnovationandManagementStudyGuide2025.pdf` | Provides Operations Management context |
| `Beasequoianotabonsai.pdf` | Provides the "Sequoia vs. Bonsai" philosophy |

### 2. AI & Technology Trends

These documents provide context on the latest AI trends.

| Filename | Purpose |
| :--- | :--- |
| `2026AgenticCodingTrendsReport.pdf` | Provides context on agentic coding and SDLC changes |
| `IT_Revolution_Article.pdf` (or text) | Provides the System 1 / System 2 framework |

### 3. Market Intelligence

These documents provide the latest market signals.

| Filename | Purpose |
| :--- | :--- |
| `Googleisspend_ingbigtobuildaleadintheAIenergyrace.pdf` | Details Google's entry into the energy market |
| `EirGrid_Capacity_Market_Documents` (folder) | Any specific EirGrid auction results or reports you have downloaded |

---

## How to Upload

Most AI research tools (including Google AI Studio and Claude) have a paperclip icon or similar button that allows you to attach files to your prompt. You can typically upload multiple files at once.

### Example Prompt Structure:

```
[Start of Prompt]

<Attached Files>
- CourseOutline-BMGT44000CompetitiveStrategy2024-25.docx
- ModuleOutline-DigitalStrategyandTransformationDEFrev13_02_2025.pdf
- ... (and so on)

# Prompt for Google Deep Research: VIOTAS Market & Competitive Intelligence Report (Multi-Horizon Analysis)

## 1. ROLE AND GOAL

You are a senior strategy consultant... (rest of the prompt)

[End of Prompt]
```

By providing these documents, you are essentially creating a mini-RAG (Retrieval-Augmented Generation) system for your research. The AI will prioritize the information in these documents, ensuring your final report is grounded in the specific frameworks and market intelligence you want to highlight.

---

## Regarding the SSE Trading Statement

You asked if the SSE trading statement is relevant. While it provides general market color, it is **less critical** than the Google announcement or the EirGrid auction data. SSE is a large, diversified utility, and their trading statement covers many areas beyond demand response. For the purpose of this focused report, you can safely omit it to keep the AI focused on the most relevant information.
