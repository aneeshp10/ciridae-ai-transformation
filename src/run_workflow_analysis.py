import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parents[1]
PDFS = [
    {
        "fund": "Bain Capital",
        "source": "Ciridae AI Transformation Opportunity Scan_Bain.pdf",
        "path": ROOT / "pdfs" / "Ciridae AI Transformation Opportunity Scan_Bain.pdf",
        "first_profile_page": 21,
    },
    {
        "fund": "Aquiline",
        "source": "Ciridae AI Transformation Opportunity Scan_Aquiline.pdf",
        "path": ROOT / "pdfs" / "Ciridae AI Transformation Opportunity Scan_Aquiline.pdf",
        "first_profile_page": 17,
    },
    {
        "fund": "Blackstone",
        "source": "Ciridae AI Transformation Opportunity Scan_Blackstone.pdf",
        "path": ROOT / "pdfs" / "Ciridae AI Transformation Opportunity Scan_Blackstone.pdf",
        "first_profile_page": 22,
    },
]

KIT_TAXONOMY = [
    "Document Intake & Extraction Kit",
    "Workflow Orchestration Kit",
    "Human Review & Approval Kit",
    "Compliance / Audit Trail Kit",
    "Claims / Payment / Revenue Cycle Kit",
    "Scheduling / Dispatch / Capacity Kit",
    "Customer Support / Contact Center Kit",
    "Knowledge / Policy RAG Kit",
    "Data Reconciliation Kit",
    "Forecasting / Optimization Kit",
    "Sales / Marketing Personalization Kit",
    "R&D / Scientific Intelligence Kit",
    "Software Delivery Automation Kit",
    "Analytics / Executive Intelligence Kit",
    "Field / Physical Ops Assist Kit",
    "Agentic Transaction / Trust Kit",
    "Other",
]

HIL_MAP = {"low": 1, "medium": 2, "high": 3}
CONF_MAP = {"low": 0.4, "medium": 0.7, "high": 1.0}


def normalize_company_name(name: str) -> str:
    value = re.sub(r"\s+", " ", name.lower()).strip()
    value = re.sub(r"\s*\(formerly .+?\)", "", value)
    value = re.sub(r"[^a-z0-9 ]+", "", value)
    value = re.sub(r"\b(inc|llc|ltd|limited|group|holdings|technologies|technology)\b", "", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def title_case_name(raw: str) -> str:
    special = {
        "IQUW": "IQUW",
        "FRISS": "FRISS",
        "STADA": "STADA",
        "JAMCO": "JAMCO",
        "HSO": "HSO",
        "LEEO": "LEEO",
        "LEGALMATION": "LegalMation",
        "FULLSTEAM": "Fullsteam",
        "WEATHERPROMISE": "WeatherPromise",
        "PARTSSOURCE": "PartsSource",
        "CENTRALSQUARE TECHNOLOGIES": "CentralSquare Technologies",
        "ITP Aero": "ITP Aero",
        "VXI": "VXI",
        "XTEL": "XTEL",
    }
    raw = raw.strip()
    if raw.upper() in special:
        return special[raw.upper()]
    if raw.isupper():
        return raw.title().replace(" Dds", " DDS").replace(" Ai ", " AI ").replace("'S", "'s")
    return raw


def section(text: str, start: str, stops: list[str]) -> str:
    pattern = re.escape(start) + r"\n"
    m = re.search(pattern, text)
    if not m:
        return ""
    tail = text[m.end():]
    end = len(tail)
    for stop in stops:
        sm = re.search(r"\n" + re.escape(stop) + r"\n", tail)
        if sm:
            end = min(end, sm.start())
    return clean_text(tail[:end])


def parse_scores(text: str) -> tuple[float, float, float]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    ai_score = None
    for i, line in enumerate(lines[:8]):
        if re.fullmatch(r"\d+\.\d", line):
            ai_score = float(line)
            break
    totals = [float(x) for x in re.findall(r"\nTotal\n(\d+\.\d)", text)]
    durability = totals[0] if len(totals) >= 1 else None
    opportunity = totals[1] if len(totals) >= 2 else None
    return ai_score, durability, opportunity


def parse_profile(pdf_meta: dict, doc: fitz.Document, page_index: int) -> dict:
    text = doc[page_index].get_text("text")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = title_case_name(lines[0])
    industry = lines[1]
    vertical = industry.split("(", 1)[0].strip()
    ai_score, durability, opportunity = parse_scores(text)
    overview = section(text, "OVERVIEW", ["EXECUTIVE SUMMARY"])
    executive_summary = section(text, "EXECUTIVE SUMMARY", ["DURABILITY RATIONALE"])
    durability_rationale = section(text, "DURABILITY RATIONALE", ["OPPORTUNITY RATIONALE"])
    opportunity_rationale = section(text, "OPPORTUNITY RATIONALE", ["DURABILITY"])
    ai_initiatives = section(text, "AI & TECH INITIATIVES", ["PUBLIC COMPS", "EXECUTIVES", "PE / OWNERSHIP HISTORY"])
    if not ai_initiatives:
        ai_initiatives = None
    ai_applicability = ""
    m = re.search(r"AI Applicability\n\d+\n(.+?)(?:\nImprovement Magnitude\n|\nTotal\n)", text, re.S)
    if m:
        ai_applicability = clean_text(m.group(1))
    return {
        "company_name": name,
        "normalized_company_name": normalize_company_name(name),
        "associated_funds": [pdf_meta["fund"]],
        "source_documents": [pdf_meta["source"]],
        "vertical": vertical,
        "industry": industry,
        "ai_score": ai_score,
        "durability_score": durability,
        "opportunity_score": opportunity,
        "overview": overview,
        "executive_summary": executive_summary,
        "durability_rationale": durability_rationale,
        "opportunity_rationale": opportunity_rationale,
        "ai_applicability_description": ai_applicability,
        "ai_initiatives": ai_initiatives,
        "_profile_text": clean_text(text),
    }


def durable_control_point(profile: dict) -> str:
    text = " ".join([profile["industry"], profile["overview"], profile["durability_rationale"]]).lower()
    if any(k in text for k in ["patent", "drug", "molecule", "therapeutic", "biotech"]):
        return "IP"
    if any(k in text for k in ["license", "licensed", "regulatory", "lloyd", "carrier", "insurer", "banking"]):
        return "regulatory-license"
    if any(k in text for k in ["physical", "manufactur", "factory", "aircraft", "restaurant", "retail store", "branch", "distribution", "real estate"]):
        return "physical-asset"
    if any(k in text for k in ["system-of-record", "system of record", "core administrative", "erp", "emr", "practice management"]):
        return "system-of-record"
    if any(k in text for k in ["proprietary data", "data corpus", "dataset", "imagery", "risk data", "market data"]):
        return "proprietary-data"
    if any(k in text for k in ["embedded", "workflow", "switching costs", "integration"]):
        return "workflow-embedding"
    return "customer-relationship"


def kit_categories(profile: dict) -> list[str]:
    text = " ".join([
        profile["industry"],
        profile["overview"],
        profile["executive_summary"],
        profile["opportunity_rationale"],
        profile["ai_applicability_description"],
        profile.get("ai_initiatives") or "",
    ]).lower()
    kits = []

    def add(kit: str) -> None:
        if kit not in kits:
            kits.append(kit)

    industry = profile["industry"].lower()

    # Vertical-specific kits are evaluated first so generic words like "document"
    # do not crowd out the actual workflow family.
    if (
        any(k in industry for k in ["biotechnology", "pharmaceutical", "drug manufacturers"])
        or any(k in text for k in ["r&d", "drug discovery", "target discovery", "trial design", "molecule", "compound screening", "compound optimization", "biomarker", "experiment prioritization", "literature synthesis"])
    ):
        add("R&D / Scientific Intelligence Kit")
    if (
        any(k in industry for k in ["insurance", "healthcare", "financial services"])
        and any(k in text for k in ["claims", "claim processing", "claims processing", "revenue cycle", "rcm", "denial", "prior authorization", "collections", "billing", "premium calculation", "payment integrity", "adjudication"])
    ):
        add("Claims / Payment / Revenue Cycle Kit")
    if any(k in text for k in ["reconciliation", "matching", "duplicate detection", "data quality", "eligibility", "custodian", "nav calculation", "fund accounting", "invoice-vs", "claim-vs"]):
        add("Data Reconciliation Kit")
    if any(k in text for k in ["identity", "e-signature", "esignature", "digital trust", "verified transaction", "agent delegation", "agentic economy", "certified communications"]):
        add("Agentic Transaction / Trust Kit")
    if any(k in text for k in ["software engineering", "code generation", "testing", "implementation", "developer", "devops", "software delivery", "systems implementation"]):
        add("Software Delivery Automation Kit")
    if (
        any(k in industry for k in ["manufacturing", "construction", "logistics", "aerospace", "automotive", "industrial", "airlines", "transportation"])
        and any(k in text for k in ["field service", "technician", "maintenance", "inspection", "mro", "repair", "diagnostic", "fleet", "predictive maintenance"])
    ):
        add("Field / Physical Ops Assist Kit")
    if any(k in text for k in ["customer service", "contact center", "support ticket", "ticket triage", "voice agent", "chat", "call summarization", "agent assist", "cx platform"]):
        add("Customer Support / Contact Center Kit")
    if any(k in text for k in ["scheduling", "dispatch", "appointment", "capacity", "resource allocation", "staffing", "clinician scheduling"]):
        add("Scheduling / Dispatch / Capacity Kit")
    if any(k in text for k in ["forecast", "optimization", "optimisation", "demand planning", "inventory optimization", "pricing optimization", "pricing optimisation", "yield optimization", "yield optimisation", "churn prediction", "resource allocation", "supply chain"]):
        add("Forecasting / Optimization Kit")
    if any(k in text for k in ["marketing", "personalization", "personalisation", "campaign", "segmentation", "retention", "next-best", "sales outreach", "customer analytics"]):
        add("Sales / Marketing Personalization Kit")
    if any(k in text for k in ["analytics", "dashboard", "business intelligence", "kpi", "anomaly", "reporting", "insight", "portfolio analytics", "risk analytics", "operating insight"]):
        add("Analytics / Executive Intelligence Kit")
    if any(k in text for k in ["compliance", "audit", "regulatory", "hipaa", "kyc", "aml", "tax", "vat", "340b", "pharmacovigilance", "evidence logging"]):
        add("Compliance / Audit Trail Kit")
    if any(k in text for k in ["knowledge management", "policy search", "sop", "rag", "regulatory interpretation", "legal research", "literature synthesis", "case data querying", "manuals"]):
        add("Knowledge / Policy RAG Kit")
    if any(k in text for k in ["submission processing", "document intake", "contract review", "invoice", "forms", "medical record", "clinical documentation", "regulatory document", "claim document", "legal document"]):
        add("Document Intake & Extraction Kit")
    if any(k in text for k in ["workflow", "routing", "orchestration", "task queue", "approval", "case management", "front-desk automation", "operating system"]):
        add("Workflow Orchestration Kit")
    if any(k in text for k in ["human review", "review queue", "exception handling", "confidence threshold", "adjuster", "expert review", "concierge", "approval workflow"]):
        add("Human Review & Approval Kit")

    if not kits and "software" in industry:
        add("Workflow Orchestration Kit")
        add("Analytics / Executive Intelligence Kit")
    if not kits and any(k in industry for k in ["manufacturing", "construction", "food", "retail", "logistics", "aerospace"]):
        add("Forecasting / Optimization Kit")
        add("Field / Physical Ops Assist Kit")

    deduped = []
    for kit in kits:
        if kit not in deduped:
            deduped.append(kit)
    if not deduped:
        deduped = ["Other"]
    return deduped[:4]


def workflow_surfaces(profile: dict, kits: list[str]) -> list[str]:
    mapping = {
        "Document Intake & Extraction Kit": "document intake and structured data extraction",
        "Workflow Orchestration Kit": "case routing, task queues, SLAs, and exception handling",
        "Human Review & Approval Kit": "confidence-based review queues and escalation",
        "Compliance / Audit Trail Kit": "regulatory compliance monitoring and audit evidence",
        "Claims / Payment / Revenue Cycle Kit": "claims, billing, payment, and revenue-cycle operations",
        "Scheduling / Dispatch / Capacity Kit": "scheduling, dispatch, capacity, and staffing decisions",
        "Customer Support / Contact Center Kit": "customer support triage, summarization, and escalation",
        "Knowledge / Policy RAG Kit": "internal policy, SOP, and domain knowledge retrieval",
        "Data Reconciliation Kit": "record matching, data quality, and reconciliation",
        "Forecasting / Optimization Kit": "demand, inventory, pricing, and yield optimization",
        "Sales / Marketing Personalization Kit": "sales targeting, retention, and campaign personalization",
        "R&D / Scientific Intelligence Kit": "scientific discovery, clinical analysis, and research prioritization",
        "Software Delivery Automation Kit": "software delivery, testing, documentation, and implementation",
        "Analytics / Executive Intelligence Kit": "operating dashboards, KPI summaries, and anomaly detection",
        "Field / Physical Ops Assist Kit": "field, maintenance, repair, and inspection assistance",
        "Agentic Transaction / Trust Kit": "identity, e-signature, verified transactions, and agent delegation",
        "Other": "narrow AI support workflows described in the profile",
    }
    surfaces = [mapping[k] for k in kits]
    if "software" in profile["industry"].lower() and "customer support" not in " ".join(surfaces):
        surfaces.append("product analytics and AI feature development")
    if len(surfaces) < 3:
        surfaces.append("management reporting and operating insight generation")
    return surfaces[:6]


def hypotheses(profile: dict, kits: list[str]) -> list[str]:
    name = profile["company_name"]
    templates = {
        "Document Intake & Extraction Kit": f"{name} document-to-workflow intake for forms, records, contracts, and submissions",
        "Workflow Orchestration Kit": f"{name} exception routing and SLA workflow copilot",
        "Human Review & Approval Kit": f"{name} confidence-scored human review queue for edge cases",
        "Compliance / Audit Trail Kit": f"{name} compliance evidence and audit-trail automation",
        "Claims / Payment / Revenue Cycle Kit": f"{name} claims, billing, denial, or payment workflow automation",
        "Scheduling / Dispatch / Capacity Kit": f"{name} scheduling and capacity optimization assistant",
        "Customer Support / Contact Center Kit": f"{name} AI contact-center triage, summarization, and escalation workflow",
        "Knowledge / Policy RAG Kit": f"{name} policy and domain-knowledge RAG assistant",
        "Data Reconciliation Kit": f"{name} cross-system reconciliation and data-quality workbench",
        "Forecasting / Optimization Kit": f"{name} forecasting and margin optimization workflow",
        "Sales / Marketing Personalization Kit": f"{name} customer segmentation and next-best-action workflow",
        "R&D / Scientific Intelligence Kit": f"{name} R&D literature, trial, and candidate-prioritization workflow",
        "Software Delivery Automation Kit": f"{name} software delivery and implementation automation",
        "Analytics / Executive Intelligence Kit": f"{name} executive KPI, anomaly, and operating-insight copilot",
        "Field / Physical Ops Assist Kit": f"{name} field diagnostics, maintenance, and inspection assistant",
        "Agentic Transaction / Trust Kit": f"{name} verified transaction and agent-delegation governance workflow",
        "Other": f"{name} profile-specific AI workflow automation",
    }
    return [templates[k] for k in kits[:4]]


def likely_owner(kits: list[str], profile: dict) -> str:
    if "Claims / Payment / Revenue Cycle Kit" in kits:
        if profile["vertical"] == "Healthcare":
            return "Head of RCM"
        return "Head of Claims"
    if "Compliance / Audit Trail Kit" in kits or "Agentic Transaction / Trust Kit" in kits:
        return "Compliance Lead"
    if "Customer Support / Contact Center Kit" in kits:
        return "Head of Support"
    if "Software Delivery Automation Kit" in kits:
        return "CTO"
    if "R&D / Scientific Intelligence Kit" in kits:
        return "Product Lead"
    if "Sales / Marketing Personalization Kit" in kits:
        return "CPO"
    if "Analytics / Executive Intelligence Kit" in kits:
        return "CFO"
    return "Operations Lead"


def readiness(profile: dict) -> int:
    text = profile["_profile_text"].lower()
    score = 3
    if any(k in text for k in ["ai-native", "production", "launched", "deployed", "already-live", "ai agents", "proprietary platform"]):
        score += 1
    if any(k in text for k in ["system-of-record", "platform", "saas", "api", "cloud", "data infrastructure"]):
        score += 1
    if any(k in text for k in ["physical production", "modest", "limited", "no massive", "almost no meaningful"]):
        score -= 1
    return max(1, min(5, score))


def potential(kits: list[str]) -> int:
    horizontal = {
        "Document Intake & Extraction Kit", "Workflow Orchestration Kit", "Human Review & Approval Kit",
        "Compliance / Audit Trail Kit", "Customer Support / Contact Center Kit", "Knowledge / Policy RAG Kit",
        "Data Reconciliation Kit", "Forecasting / Optimization Kit", "Sales / Marketing Personalization Kit",
        "Analytics / Executive Intelligence Kit",
    }
    if any(k in horizontal for k in kits):
        return 5 if len([k for k in kits if k in horizontal]) >= 2 else 4
    if any(k in kits for k in ["Claims / Payment / Revenue Cycle Kit", "Software Delivery Automation Kit", "Field / Physical Ops Assist Kit", "Agentic Transaction / Trust Kit"]):
        return 4
    if "R&D / Scientific Intelligence Kit" in kits:
        return 3
    return 2


def risk_and_hil(profile: dict, kits: list[str]) -> tuple[str, str, str]:
    text = profile["_profile_text"].lower()
    regulated = any(k in text for k in ["regulatory", "clinical", "licensed", "insurance", "claims", "compliance", "legal", "drug", "patient"])
    if regulated:
        risk = "high" if any(k in kits for k in ["R&D / Scientific Intelligence Kit", "Claims / Payment / Revenue Cycle Kit", "Compliance / Audit Trail Kit"]) else "medium"
        hil = "high"
    elif any(k in kits for k in ["Customer Support / Contact Center Kit", "Sales / Marketing Personalization Kit", "Analytics / Executive Intelligence Kit"]):
        risk = "medium"
        hil = "medium"
    else:
        risk = "low"
        hil = "medium"
    confidence = "high" if profile["opportunity_rationale"] and profile["ai_applicability_description"] else "medium"
    return risk, hil, confidence


def enrich(profile: dict) -> dict:
    kits = kit_categories(profile)
    ready = readiness(profile)
    kit_pot = potential(kits)
    risk, hil, conf = risk_and_hil(profile, kits)
    business_model = profile["overview"].split(".")[0].strip() + "."
    out = {
        k: v for k, v in profile.items()
        if k not in ["_profile_text"]
    }
    out.update({
        "business_model_summary": business_model,
        "durable_control_point": durable_control_point(profile),
        "workflow_surfaces": workflow_surfaces(profile, kits),
        "top_workflow_automation_hypotheses": hypotheses(profile, kits),
        "likely_workflow_owner": likely_owner(kits, profile),
        "reusable_kit_categories": kits,
        "kit_reuse_rationale": "The profile describes repeatable information, workflow, compliance, analytics, or operations patterns that recur across PE-backed companies beyond this single asset.",
        "deployment_readiness_score": ready,
        "deployment_readiness_rationale": f"Readiness score reflects the profile evidence of existing platforms, data, AI initiatives, and workflow clarity for {profile['company_name']}.",
        "kit_potential_score": kit_pot,
        "kit_potential_rationale": "The assigned kits generalize across multiple portfolio companies when the same workflow pattern appears outside this company's vertical.",
        "risk_level": risk,
        "human_in_loop_need": hil,
        "confidence": conf,
    })
    return out


def read_profiles(pdf_metas: list[dict]) -> list[dict]:
    profiles = []
    for meta in pdf_metas:
        doc = fitz.open(meta["path"])
        for page_index in range(meta["first_profile_page"], doc.page_count):
            profiles.append(parse_profile(meta, doc, page_index))
    return profiles


def dedupe(profiles: list[dict]) -> tuple[list[dict], list[dict]]:
    by_norm = {}
    possible = []
    for profile in profiles:
        key = profile["normalized_company_name"]
        if key in by_norm:
            existing = by_norm[key]
            existing["associated_funds"] = sorted(set(existing["associated_funds"]) | set(profile["associated_funds"]))
            existing["source_documents"] = sorted(set(existing["source_documents"]) | set(profile["source_documents"]))
            if not existing.get("ai_initiatives") and profile.get("ai_initiatives"):
                existing["ai_initiatives"] = profile["ai_initiatives"]
        else:
            by_norm[key] = profile

    names = list(by_norm.values())
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a["company_name"].split()[0].lower() == b["company_name"].split()[0].lower() and a["normalized_company_name"] != b["normalized_company_name"]:
                if abs(len(a["normalized_company_name"]) - len(b["normalized_company_name"])) <= 6:
                    possible.append({
                        "company_pair": [a["company_name"], b["company_name"]],
                        "note": "Names share a leading token but are not clearly the same entity from the profile text, so they were not merged.",
                    })
    return list(by_norm.values()), possible


def aggregate(companies: list[dict]) -> list[dict]:
    buckets = defaultdict(list)
    for company in companies:
        for kit in company["reusable_kit_categories"]:
            buckets[kit].append(company)
    records = []
    for kit, comps in buckets.items():
        funds = sorted({fund for c in comps for fund in c["associated_funds"]})
        exposure = sum(len(c["associated_funds"]) for c in comps)
        avg_opp = sum(c["opportunity_score"] or 0 for c in comps) / len(comps)
        avg_ready = sum(c["deployment_readiness_score"] for c in comps) / len(comps)
        avg_pot = sum(c["kit_potential_score"] for c in comps) / len(comps)
        avg_hil = sum(HIL_MAP[c["human_in_loop_need"]] for c in comps) / len(comps)
        avg_conf = sum(CONF_MAP[c["confidence"]] for c in comps) / len(comps)
        priority = len(comps) * avg_ready * avg_pot * avg_conf
        examples = [c["company_name"] for c in sorted(comps, key=lambda x: (x["opportunity_score"] or 0), reverse=True)[:5]]
        records.append({
            "kit_category": kit,
            "unique_company_count": len(comps),
            "unique_fund_count": len(funds),
            "company_fund_exposure_count": exposure,
            "avg_opportunity_score": round(avg_opp, 2),
            "avg_deployment_readiness_score": round(avg_ready, 2),
            "avg_kit_potential_score": round(avg_pot, 2),
            "avg_human_in_loop_need": round(avg_hil, 2),
            "avg_confidence_weight": round(avg_conf, 2),
            "example_companies": examples,
            "why_this_kit_matters": f"{kit} appears across repeatable PE portfolio workflows and can be productized once for reuse across multiple assets.",
            "reusable_kit_priority_score": round(priority, 2),
        })
    return sorted(records, key=lambda r: r["reusable_kit_priority_score"], reverse=True)


def slugify(value: str) -> str:
    value = value.lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def summary_sentence(title: str, aggregation: list[dict], possible_duplicates: list[dict]) -> str:
    top = aggregation[0]
    frequent = ", ".join(row["kit_category"] for row in aggregation[:5])
    return (
        f"The most actionable insight for {title} is that `{top['kit_category']}` has the strongest build-first signal, "
        f"with {top['unique_company_count']} deduplicated companies and a priority score of {top['reusable_kit_priority_score']}. "
        f"The most frequent reusable workflow patterns are {frequent}. "
        "The highest-fit archetypes are companies with repeatable information-heavy workflows, regulated operating constraints, embedded software/data platforms, or large cognitive-labor surfaces. "
        "Deployability is strongest where the profiles mention existing SaaS platforms, APIs, proprietary datasets, AI initiatives, or clear operational workflows. "
        f"Duplicate handling found {len(possible_duplicates)} possible duplicate pair(s) that were not auto-merged unless clearly the same entity."
    )


def write_outputs(
    companies: list[dict],
    aggregation: list[dict],
    possible_duplicates: list[dict],
    title: str,
    slug: str,
) -> None:
    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)
    payload = {
        "company_level_records": companies,
        "kit_level_aggregation_records": aggregation,
        "possible_duplicates": possible_duplicates,
    }
    (out_dir / f"{slug}_workflow_analysis.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with (out_dir / f"{slug}_chart_ready.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "kit_category",
            "unique_company_count",
            "unique_fund_count",
            "avg_deployment_readiness_score",
            "avg_kit_potential_score",
            "reusable_kit_priority_score",
            "example_companies",
        ])
        writer.writeheader()
        for row in aggregation:
            writer.writerow({
                "kit_category": row["kit_category"],
                "unique_company_count": row["unique_company_count"],
                "unique_fund_count": row["unique_fund_count"],
                "avg_deployment_readiness_score": row["avg_deployment_readiness_score"],
                "avg_kit_potential_score": row["avg_kit_potential_score"],
                "reusable_kit_priority_score": row["reusable_kit_priority_score"],
                "example_companies": ", ".join(row["example_companies"]),
            })
    summary_lines = [
        f"# {title} Workflow Kit Analysis",
        "",
        f"Unique companies: {len(companies)}",
        f"Kit categories represented: {len(aggregation)}",
        "",
        "## Chart-Ready Table",
        "",
        "| kit_category | unique_company_count | unique_fund_count | avg_deployment_readiness_score | avg_kit_potential_score | reusable_kit_priority_score | example_companies |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in aggregation:
        summary_lines.append(
            f"| {row['kit_category']} | {row['unique_company_count']} | {row['unique_fund_count']} | "
            f"{row['avg_deployment_readiness_score']} | {row['avg_kit_potential_score']} | "
            f"{row['reusable_kit_priority_score']} | {', '.join(row['example_companies'])} |"
        )
    summary_lines.extend([
        "",
        "## Executive Summary",
        "",
        summary_sentence(title, aggregation, possible_duplicates),
        "",
        "## Possible Duplicates",
        "",
    ])
    if possible_duplicates:
        for item in possible_duplicates:
            summary_lines.append(f"- {item['company_pair'][0]} / {item['company_pair'][1]}: {item['note']}")
    else:
        summary_lines.append("- None.")
    (out_dir / f"{slug}_workflow_analysis.md").write_text("\n".join(summary_lines), encoding="utf-8")


def run_analysis(pdf_metas: list[dict], title: str, slug: str) -> dict:
    profiles = read_profiles(pdf_metas)
    unique_profiles, possible_duplicates = dedupe(profiles)
    companies = [enrich(profile) for profile in unique_profiles]
    aggregation = aggregate(companies)
    write_outputs(companies, aggregation, possible_duplicates, title, slug)
    return {
        "title": title,
        "slug": slug,
        "parsed_profiles": len(profiles),
        "unique_companies": len(companies),
        "kit_categories": len(aggregation),
        "top_kit": aggregation[0]["kit_category"],
        "top_score": aggregation[0]["reusable_kit_priority_score"],
    }


def main() -> None:
    summaries = []
    for meta in PDFS:
        summaries.append(run_analysis([meta], meta["fund"], slugify(meta["fund"])))
    summaries.append(run_analysis(PDFS, "Bain + Aquiline + Blackstone", "bain_aquiline_blackstone"))
    for summary in summaries:
        print(
            f"{summary['slug']}: parsed_profiles={summary['parsed_profiles']} "
            f"unique_companies={summary['unique_companies']} kit_categories={summary['kit_categories']} "
            f"top_kit={summary['top_kit']} score={summary['top_score']}"
        )


if __name__ == "__main__":
    main()
