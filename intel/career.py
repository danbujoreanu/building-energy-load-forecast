"""
intel/career.py
===============
Career intelligence module — job spec analysis, resume gap detection,
and technology evaluation for Sparc Energy product decisions.

Uses the same ChromaDB + LlamaIndex infrastructure as the intel/ module,
with a dedicated `career` tier (ChromaDB collection: `intel_career`).

Two modes
---------
1. **Gap analysis** — compare a job spec against Dan's profile and return:
   - Strong matches
   - Gaps to address (with suggested framing)
   - Resume tailoring notes

2. **Tech evaluation** — extract technology mentions from job specs and flag
   which ones Sparc Energy should consider implementing.

Usage
-----
    from intel.career import match_job_spec, evaluate_tech_stack, ingest_job_spec

    # Ingest a job spec (from Obsidian or any .md file)
    ingest_job_spec("/path/to/job_spec.md")

    # Analyse fit
    result = match_job_spec("PartnerRe Senior AI Architect")
    print(result["fit_summary"])
    print(result["gaps"])
    print(result["resume_notes"])

    # Evaluate technologies across all ingested job specs
    tech_report = evaluate_tech_stack()
    print(tech_report["top_technologies"])
    print(tech_report["sparc_gaps"])
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CAREER_DOCS_DIR = Path(__file__).resolve().parent / "docs" / "career"
_JOBS_DIR = _CAREER_DOCS_DIR / "jobs"
_PROFILE_DIR = _CAREER_DOCS_DIR / "profile"

# Technology keywords to extract from job specs
_TECH_KEYWORDS = [
    # LLM / AI frameworks
    "LangChain", "LlamaIndex", "Semantic Kernel", "LangGraph", "AutoGen",
    "LlamaIndex", "Haystack", "CrewAI",
    # LLM models / APIs
    "GPT-4", "GPT-4o", "Claude", "Gemini", "Llama", "Mistral",
    "Azure OpenAI", "Amazon Bedrock", "Vertex AI",
    # Vector stores
    "Pinecone", "Weaviate", "Chroma", "ChromaDB", "Qdrant", "pgvector",
    "Azure AI Search", "Elasticsearch",
    # Cloud platforms
    "Azure", "AWS", "GCP", "Snowflake", "Databricks",
    "Azure ML", "AI Foundry", "SageMaker", "Vertex",
    # Orchestration
    "Airflow", "Prefect", "Azure Data Factory", "Dagster", "n8n",
    # Monitoring / MLOps
    "MLflow", "Weights & Biases", "DVC", "Great Expectations",
    "Prometheus", "Grafana", "CloudWatch", "Datadog",
    # Languages / frameworks
    "Python", "SQL", "TypeScript", "FastAPI", "Django", "Streamlit",
    "React", "Next.js",
    # Data
    "dbt", "Spark", "Kafka", "Flink", "Pandas",
]

# Sparc Energy's current tech stack (what we already have)
_SPARC_STACK = {
    "LlamaIndex", "ChromaDB", "FastAPI", "Python", "SQL",
    "Gemini", "Claude", "LightGBM", "Docker", "AWS", "Redis",
    "Pydantic", "Pandas", "Gradio", "Prometheus", "Grafana",
    "CloudWatch", "Next.js", "Supabase",
}


def ingest_job_spec(file_path: str | Path, copy_to_intel: bool = True) -> bool:
    """Ingest a job spec markdown file into the career intel tier.

    Parameters
    ----------
    file_path : str | Path
        Path to the .md job spec file (e.g. from Obsidian).
    copy_to_intel : bool
        If True, copies the file to intel/docs/career/jobs/ before ingesting.
        Useful when the source is an Obsidian vault outside the project.

    Returns
    -------
    bool
        True if ingested, False if already exists (deduplicated).
    """
    from intel.ingest import ingest_file

    file_path = Path(file_path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Job spec not found: {file_path}")

    target_path = file_path
    if copy_to_intel:
        _JOBS_DIR.mkdir(parents=True, exist_ok=True)
        target_path = _JOBS_DIR / file_path.name
        shutil.copy2(file_path, target_path)
        logger.info("Copied job spec to intel/docs/career/jobs/%s", file_path.name)

    return ingest_file(target_path, tier="career")


def ingest_career_profile(file_path: str | Path | None = None) -> bool:
    """Ingest Dan's profile/resume into the career tier.

    Parameters
    ----------
    file_path : str | Path | None
        Path to profile markdown. Defaults to the bundled profile at
        intel/docs/career/profile/DAN_BUJOREANU_PROFILE.md.
    """
    from intel.ingest import ingest_file

    if file_path is None:
        file_path = _PROFILE_DIR / "DAN_BUJOREANU_PROFILE.md"

    file_path = Path(file_path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Profile not found: {file_path}")

    return ingest_file(file_path, tier="career")


def _enrich_with_inferred_metadata(file_path: Path) -> None:
    """If a .md file has no YAML frontmatter, prepend auto-generated frontmatter.

    Infers:
    - company: from parent folder name (e.g. Applications/PartnerRe/ → "PartnerRe")
    - role_title: from file name, stripping leading date (e.g. "2026-04-18 Senior AI Architect.md")
    - date_added: from filename date if present, else file mtime

    Only adds frontmatter if the file does NOT already start with '---'.
    """
    import re as _re
    from datetime import datetime as _dt

    content = file_path.read_text(encoding="utf-8")
    if content.lstrip().startswith("---"):
        return  # Already has frontmatter — don't touch

    # Infer company from parent directory name
    company = file_path.parent.name

    # Infer role title from filename — strip date prefix if present
    stem = file_path.stem
    # Strip leading date patterns: "2026-04-18 " or "2026-04-18_" or "20260418 "
    date_prefix = _re.match(r"^(\d{4}-\d{2}-\d{2})[_ ]?", stem)
    date_added = date_prefix.group(1) if date_prefix else _dt.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d")
    role_title = _re.sub(r"^\d{4}-\d{2}-\d{2}[_ ]?", "", stem).strip()

    frontmatter = f"""---
title: "{company} — {role_title}"
document_type: job_spec
tier: career
company: {company}
role_title: {role_title}
date_added: "{date_added}"
application_status: evaluating
status: active
---

"""
    file_path.write_text(frontmatter + content, encoding="utf-8")
    logger.info("Auto-generated frontmatter for: %s", file_path.name)


def ingest_obsidian_jobs(obsidian_applications_dir: str | Path | None = None) -> dict:
    """Scan an Obsidian Applications folder and ingest all .md job specs.

    Expected folder structure (flexible — all variants work):
    ::

        Applications/
          PartnerRe/
            Senior AI Architect.md
            2026-04-18 Data Scientist.md    ← date prefix optional
          AXA/
            Head of AI.md
          Active/                           ← status subfolders also work
            CompanyX/
              Role.md

    If a file has no YAML frontmatter, metadata (company, role, date) is
    inferred from the folder name and filename automatically.

    Parameters
    ----------
    obsidian_applications_dir : str | Path | None
        Path to the Obsidian Applications folder.
        Defaults to: ~/Personal Projects/Career/Applications/

    Returns
    -------
    dict with keys: ingested, skipped, errors
    """
    if obsidian_applications_dir is None:
        obsidian_applications_dir = Path.home() / "Personal Projects" / "Career" / "Applications"

    base_dir = Path(obsidian_applications_dir).resolve()
    if not base_dir.exists():
        raise FileNotFoundError(f"Obsidian Applications directory not found: {base_dir}")

    md_files = list(base_dir.rglob("*.md"))
    logger.info("Found %d markdown files in %s", len(md_files), base_dir)

    ingested = skipped = 0
    errors: list[str] = []

    for fp in md_files:
        # Skip README / index / template files
        if fp.stem.lower() in ("readme", "index", "_index", "template", "00_template"):
            continue
        try:
            # Auto-enrich with frontmatter if missing (infers company+role from path)
            _enrich_with_inferred_metadata(fp)
            result = ingest_job_spec(fp, copy_to_intel=True)
            if result:
                ingested += 1
                print(f"  ✓ {fp.relative_to(base_dir)}")
            else:
                skipped += 1
        except Exception as exc:
            errors.append(f"{fp.name}: {exc}")
            logger.error("Error ingesting %s: %s", fp.name, exc)

    return {"ingested": ingested, "skipped": skipped, "errors": errors}


def match_job_spec(query: str, top_k: int = 5) -> dict:
    """Find relevant job spec chunks and analyse fit against Dan's profile.

    Parameters
    ----------
    query : str
        Job title, company name, or natural language question.
        e.g. "PartnerRe Senior AI Architect" or "What tech stack is required?"
    top_k : int
        Number of chunks to retrieve.

    Returns
    -------
    dict with keys:
        job_context : str  — relevant job spec excerpts
        profile_context : str  — relevant profile excerpts
        fit_summary : str  — match/gap analysis
        gaps : list[str]  — technologies/skills missing from profile
        strengths : list[str]  — strong alignment areas
        resume_notes : str  — tailoring suggestions
        llm_used : bool
    """
    from intel.retrieval import query_tier

    # Retrieve job spec context
    job_result = query_tier("career", query, top_k=top_k)
    job_context = job_result["answer"]

    # Retrieve profile context (search for matching skills)
    profile_query = f"skills experience matching {query}"
    profile_result = query_tier("career", profile_query, top_k=3)
    profile_context = profile_result["answer"]

    # Extract technology gaps using LLM if available
    gemini_key = os.environ.get("GEMINI_API_KEY")
    llm_used = False
    fit_summary = ""
    gaps: list[str] = []
    strengths: list[str] = []
    resume_notes = ""

    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""You are a senior career advisor reviewing a job spec against a candidate profile.

JOB SPEC CONTEXT:
{job_context}

CANDIDATE PROFILE CONTEXT:
{profile_context}

Analyse the fit and provide:
1. FIT_SUMMARY: 2-3 sentences on overall alignment
2. STRENGTHS: bullet list of strong matches (max 5)
3. GAPS: bullet list of specific skills/tech missing (max 5), with one-line framing suggestion each
4. RESUME_NOTES: 3-4 specific resume tailoring recommendations
5. SPARC_TECH: Any technologies in the job spec that Sparc Energy should consider implementing

Format your response exactly as:
FIT_SUMMARY: [text]
STRENGTHS: [bullet list]
GAPS: [bullet list with framing]
RESUME_NOTES: [numbered list]
SPARC_TECH: [comma-separated list or "none"]
"""
            response = model.generate_content(prompt)
            text = response.text

            # Parse sections
            def _extract(label: str, text: str) -> str:
                pattern = re.compile(rf"{label}:\s*(.*?)(?=\n[A-Z_]+:|$)", re.DOTALL)
                m = pattern.search(text)
                return m.group(1).strip() if m else ""

            fit_summary = _extract("FIT_SUMMARY", text)
            strengths_text = _extract("STRENGTHS", text)
            gaps_text = _extract("GAPS", text)
            resume_notes = _extract("RESUME_NOTES", text)

            strengths = [s.strip("- •").strip() for s in strengths_text.split("\n") if s.strip()]
            gaps = [g.strip("- •").strip() for g in gaps_text.split("\n") if g.strip()]
            llm_used = True

        except Exception as exc:
            logger.warning("Gemini synthesis failed: %s. Using retrieval-only mode.", exc)

    if not fit_summary:
        fit_summary = f"Retrieved {len(job_context)} chars of job context and {len(profile_context)} chars of profile context. Set GEMINI_API_KEY for full analysis."

    return {
        "job_context": job_context,
        "profile_context": profile_context,
        "fit_summary": fit_summary,
        "strengths": strengths,
        "gaps": gaps,
        "resume_notes": resume_notes,
        "top_score": job_result["top_score"],
        "llm_used": llm_used,
    }


def evaluate_tech_stack(top_n: int = 20) -> dict:
    """Scan all ingested job specs and count technology mentions.

    Returns a report showing:
    - Top N technologies mentioned across all job specs
    - Which are already in Sparc's stack
    - Which are gaps worth adding to portfolio

    Returns
    -------
    dict with keys:
        tech_counts : dict[str, int]  — tech → mention count
        in_stack : list[str]  — already in Sparc stack
        gaps : list[str]  — not in Sparc stack, worth considering
        top_technologies : list[str]  — top N by frequency
    """
    import chromadb
    from intel.ingest import CHROMA_PATH

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        collection = client.get_collection("intel_career")
    except Exception:
        return {
            "tech_counts": {},
            "in_stack": [],
            "gaps": [],
            "top_technologies": [],
            "error": "Career tier not yet populated. Run ingest_obsidian_jobs() first.",
        }

    # Get all chunks from career collection
    all_docs = collection.get(include=["documents"])
    full_text = " ".join(all_docs.get("documents") or [])

    # Count tech keyword mentions (case-insensitive)
    tech_counts: dict[str, int] = {}
    for tech in _TECH_KEYWORDS:
        count = len(re.findall(tech, full_text, re.IGNORECASE))
        if count > 0:
            tech_counts[tech] = count

    # Sort by frequency
    sorted_tech = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_technologies = [t[0] for t in sorted_tech]

    in_stack = [t for t in top_technologies if t in _SPARC_STACK]
    gaps = [t for t in top_technologies if t not in _SPARC_STACK]

    return {
        "tech_counts": dict(sorted_tech),
        "in_stack": in_stack,
        "gaps": gaps,
        "top_technologies": top_technologies,
    }


def list_jobs() -> list[dict]:
    """List all ingested job specs from the career tier.

    Returns
    -------
    list of dicts with keys: file, company, role_title, status, date_added
    """
    import chromadb
    from intel.ingest import CHROMA_PATH

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        collection = client.get_collection("intel_career")
    except Exception:
        return []

    all_meta = collection.get(include=["metadatas"])
    seen_files: set[str] = set()
    jobs: list[dict] = []

    for meta in (all_meta.get("metadatas") or []):
        if not meta:
            continue
        source_file = meta.get("source_file", "unknown")
        if source_file in seen_files:
            continue
        seen_files.add(source_file)

        doc_type = meta.get("document_type", "")
        if doc_type == "job_spec":
            jobs.append({
                "file": source_file,
                "company": meta.get("company", "unknown"),
                "role_title": meta.get("role_title", "unknown"),
                "status": meta.get("application_status", "unknown"),
                "date_added": meta.get("date_added", "unknown"),
                "tech_stack": meta.get("tech_stack", ""),
            })

    return sorted(jobs, key=lambda x: x["date_added"], reverse=True)
