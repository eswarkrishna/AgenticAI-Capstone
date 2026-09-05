#!/usr/bin/env python3
"""Write Phase 2 eval markdown, labels.json, and competency KB files."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JDS = ROOT / "data" / "eval" / "jds"
RESUMES = ROOT / "data" / "eval" / "resumes"
KB = ROOT / "data" / "competency_kb"
LABELS = ROOT / "data" / "eval" / "labels.json"


def jd(title: str, family: str, must: list[str], nice: list[str], years: str, education: str, extra: str = "") -> str:
    must_l = "\n".join(f"- {x}" for x in must)
    nice_l = "\n".join(f"- {x}" for x in nice)
    block = f"""# {title}

role_family: {family}

## Must-haves
{must_l}

## Nice-to-haves
{nice_l}

## Years
{years}

## Education
{education}
"""
    if extra:
        block += f"\n## Notes\n{extra}\n"
    return block.strip() + "\n"


def resume(name: str, title: str, summary: str, skills: list[str], experience: str, education: str, extras: str = "") -> str:
    skills_l = ", ".join(skills)
    body = f"""# {name}

## Summary
{title}. {summary}

## Skills
{skills_l}

## Experience
{experience}

## Education
{education}
"""
    if extras:
        body += f"\n{extras}\n"
    return body.strip() + "\n"


CASES: list[dict] = [
    # --- engineering strong_match (4) ---
    {
        "id": "eng-sm-01",
        "role_family": "engineering",
        "label": "strong_match",
        "notes": "Senior backend profile matches Python, APIs, and PostgreSQL must-haves.",
        "jd": jd(
            "Backend Software Engineer",
            "engineering",
            ["Python", "REST APIs", "PostgreSQL", "Docker"],
            ["Kubernetes", "AWS"],
            "5+",
            "bachelor in computer science or equivalent",
        ),
        "resume": resume(
            "Jordan Hale",
            "Senior Backend Engineer, 7 years",
            "Ships Python services, REST APIs, and PostgreSQL schemas for B2B SaaS.",
            ["Python", "FastAPI", "PostgreSQL", "Docker", "pytest", "AWS"],
            """### Senior Backend Engineer, Northwind Cloud (2021-2026)
Owned payment and billing APIs in Python/FastAPI. Designed PostgreSQL schemas, added Dockerized CI, and cut p95 latency 40%.

### Backend Engineer, Riverbank Systems (2019-2021)
Built REST services and worker queues. Introduced integration tests and on-call runbooks.""",
            "B.S. Computer Science, State University, 2018",
        ),
    },
    {
        "id": "eng-sm-02",
        "role_family": "engineering",
        "label": "strong_match",
        "notes": "Data engineer with Spark, SQL, and warehouse experience.",
        "jd": jd(
            "Data Engineer",
            "engineering",
            ["SQL", "Apache Spark", "data warehousing", "Python"],
            ["dbt", "Airflow", "Snowflake"],
            "4+",
            "bachelor",
        ),
        "resume": resume(
            "Samira Chen",
            "Data Engineer, 6 years",
            "Builds Spark batches, SQL models, and warehouse pipelines.",
            ["Python", "SQL", "Spark", "Airflow", "Snowflake", "dbt"],
            """### Data Engineer, Lakeside Analytics (2022-2026)
Spark jobs and dbt models into Snowflake. Airflow DAGs for daily loads; SLA 99.5%.

### Analytics Engineer, Harbor Retail (2020-2022)
SQL marts and Python quality checks for merchandising data.""",
            "B.S. Information Systems, 2019",
        ),
    },
    {
        "id": "eng-sm-03",
        "role_family": "engineering",
        "label": "strong_match",
        "notes": "Frontend engineer with React and TypeScript depth.",
        "jd": jd(
            "Frontend Engineer",
            "engineering",
            ["React", "TypeScript", "CSS", "accessibility"],
            ["Next.js", "GraphQL"],
            "4+",
            "bachelor or equivalent experience",
        ),
        "resume": resume(
            "Riley Okonkwo",
            "Frontend Engineer, 5 years",
            "React/TypeScript UI, design-system work, and WCAG fixes.",
            ["React", "TypeScript", "CSS", "Next.js", "Jest", "GraphQL"],
            """### Frontend Engineer, Lumen Apps (2021-2026)
Led checkout UI in React and TypeScript. WCAG 2.2 AA on core flows. Next.js app router migration.

### UI Engineer, PixelForge (2019-2021)
Component library and CSS architecture for a design system.""",
            "B.A. Interactive Media, 2019",
        ),
    },
    {
        "id": "eng-sm-04",
        "role_family": "engineering",
        "label": "strong_match",
        "notes": "hard case: synonym skills (k8s vs Kubernetes)",
        "jd": jd(
            "Platform / SRE Engineer",
            "engineering",
            ["Kubernetes", "containers", "Google Cloud", "CI/CD", "observability"],
            ["Terraform", "Go"],
            "5+",
            "bachelor",
        ),
        "resume": resume(
            "Morgan Voss",
            "SRE, 6 years",
            "Runs production clusters; writes platform tooling.",
            ["k8s", "Docker", "GCP", "Terraform", "Prometheus", "Go"],
            """### SRE, Orbit Pay (2021-2026)
Operated k8s on GCP. Helm charts, Docker images, Prometheus/Grafana. Terraform for GKE node pools.

### DevOps Engineer, Stackyard (2018-2021)
CI/CD with Cloud Build; containerized legacy JVMs.""",
            "B.S. Computer Engineering, 2018",
        ),
    },
    # --- engineering possible_fit (3) ---
    {
        "id": "eng-pf-01",
        "role_family": "engineering",
        "label": "possible_fit",
        "notes": "hard case: missing degree but strong experience",
        "jd": jd(
            "Staff Backend Engineer",
            "engineering",
            ["Python", "distributed systems", "PostgreSQL", "mentoring"],
            ["Kafka", "gRPC"],
            "8+",
            "bachelor in CS required",
        ),
        "resume": resume(
            "Chris Delgado",
            "Backend engineer, 11 years, no degree",
            "Self-taught. Led Python platform work and on-call for payments.",
            ["Python", "PostgreSQL", "Redis", "Kafka", "gRPC", "AWS"],
            """### Staff Engineer, Tidepool Payments (2019-2026)
Owned ledger services. Mentored 4 engineers. Kafka outbox, gRPC internals, PostgreSQL partitioning.

### Software Engineer, indie and contract (2014-2019)
Python APIs for logistics and billing clients.""",
            "No formal degree. Completed community college CS courses; 11 years professional experience.",
        ),
    },
    {
        "id": "eng-pf-02",
        "role_family": "engineering",
        "label": "possible_fit",
        "notes": "Mobile engineer applying to backend; overlapping systems skill, missing API depth.",
        "jd": jd(
            "Backend Software Engineer",
            "engineering",
            ["Go", "gRPC", "PostgreSQL", "service design"],
            ["Kubernetes"],
            "4+",
            "bachelor",
        ),
        "resume": resume(
            "Avery Shin",
            "iOS engineer, 5 years",
            "Ships Swift apps; some Node scripts for BFF endpoints.",
            ["Swift", "iOS", "Combine", "Node.js", "REST", "SQLite"],
            """### iOS Engineer, Trailmap (2021-2026)
Offline-first Swift app. Wrote a small Node BFF that calls REST backends.

### Mobile Developer, Campfire (2019-2021)
Swift UI and SQLite local cache.""",
            "B.S. Computer Science, 2019",
        ),
    },
    {
        "id": "eng-pf-03",
        "role_family": "engineering",
        "label": "possible_fit",
        "notes": "hard case: JD with uncommon tool names",
        "jd": jd(
            "Distributed Systems Engineer",
            "engineering",
            ["Temporal workflows", "NATS messaging", "Nix builds", "Go"],
            ["WebAssembly", "eBPF"],
            "5+",
            "bachelor",
            extra="Uncommon stack: Temporal, NATS, Nix. Candidates may know adjacent tools (Airflow, Kafka, Bazel) without these names.",
        ),
        "resume": resume(
            "Priya Raman",
            "Backend engineer, 6 years",
            "Go services, Kafka, Bazel CI. Has not used Temporal, NATS, or Nix.",
            ["Go", "Kafka", "gRPC", "PostgreSQL", "Bazel", "Docker"],
            """### Backend Engineer, Meshline (2020-2026)
Go microservices, Kafka event bus, Bazel monorepo. Explored workflow engines but production is cron plus Kafka.

### Engineer, Blue Harbor (2018-2020)
Go APIs and Docker deploys.""",
            "B.S. Computer Science, 2018",
        ),
    },
    # --- engineering not_relevant (3) ---
    {
        "id": "eng-nr-01",
        "role_family": "engineering",
        "label": "not_relevant",
        "notes": "hard case: keyword-stuffed weak resume",
        "jd": jd(
            "Senior Backend Engineer",
            "engineering",
            ["Python", "system design", "PostgreSQL", "production ownership"],
            ["Kubernetes"],
            "6+",
            "bachelor",
        ),
        "resume": resume(
            "Taylor Quinn",
            "Career changer, 8 months bootcamp",
            "Lists many tools with no production ownership or depth.",
            [
                "Python", "Java", "C++", "Go", "Rust", "Kubernetes", "Docker",
                "AWS", "Azure", "GCP", "PostgreSQL", "MongoDB", "Redis",
                "React", "Machine Learning", "Blockchain", "Agile", "Scrum",
            ],
            """### Student, RapidCode Bootcamp (2025-2026)
Completed tutorial projects. No production on-call, no shipped backend at work.

### Barista, various cafes (2019-2025)
Customer service. No software engineering role.""",
            "Bootcamp certificate, 2026. No CS degree.",
            extras="## Projects\nTodo app and copy-pasted Kubernetes YAML from a blog. Keyword list is not backed by job evidence.",
        ),
    },
    {
        "id": "eng-nr-02",
        "role_family": "engineering",
        "label": "not_relevant",
        "notes": "Graphic designer applying to backend engineering.",
        "jd": jd(
            "Backend Software Engineer",
            "engineering",
            ["Python", "APIs", "SQL"],
            ["AWS"],
            "3+",
            "bachelor",
        ),
        "resume": resume(
            "Eden Laurent",
            "Graphic designer, 6 years",
            "Brand and print work. No software engineering jobs.",
            ["Adobe Illustrator", "InDesign", "Photoshop", "Figma", "typography"],
            """### Graphic Designer, Studio North (2020-2026)
Campaigns, packaging, and brand kits.

### Junior Designer, City Arts (2018-2020)
Print layout and photo retouching.""",
            "B.F.A. Graphic Design, 2018",
        ),
    },
    {
        "id": "eng-nr-03",
        "role_family": "engineering",
        "label": "not_relevant",
        "notes": "New graduate vs staff-level years and systems bar.",
        "jd": jd(
            "Staff Software Engineer",
            "engineering",
            ["distributed systems", "Python or Go", "mentoring", "incident leadership"],
            ["Kubernetes"],
            "10+",
            "bachelor",
        ),
        "resume": resume(
            "Noah Patel",
            "New graduate intern",
            "One internship; coursework only.",
            ["Python", "Java", "Git"],
            """### SWE Intern, Campus Labs (summer 2025)
Bug fixes on an internal Python script. No on-call, no system design.

### Teaching assistant, intro CS (2024-2025)
Graded assignments.""",
            "B.S. Computer Science expected 2026",
        ),
    },
    # --- product_design strong_match (3) ---
    {
        "id": "pd-sm-01",
        "role_family": "product_design",
        "label": "strong_match",
        "notes": "B2B SaaS PM with roadmap, discovery, and stakeholder skills.",
        "jd": jd(
            "Senior Product Manager, B2B SaaS",
            "product_design",
            ["product discovery", "roadmapping", "B2B SaaS", "stakeholder management", "metrics"],
            ["SQL", "experimentation"],
            "5+",
            "bachelor",
        ),
        "resume": resume(
            "Casey Nguyen",
            "Senior PM, 7 years",
            "B2B SaaS roadmaps, discovery interviews, and activation metrics.",
            ["product discovery", "roadmapping", "JTBD", "SQL", "Amplitude", "stakeholder management"],
            """### Senior Product Manager, Ledgerbox (2021-2026)
Owned billing SKU. Discovery with 40 customers. Activation +18%. SQL in Amplitude and warehouse.

### Product Manager, Cloudcart (2018-2021)
Roadmaps for mid-market SaaS. Quarterly OKRs with sales and CS.""",
            "B.A. Economics, 2017",
        ),
    },
    {
        "id": "pd-sm-02",
        "role_family": "product_design",
        "label": "strong_match",
        "notes": "Product designer with Figma, UX flows, and design systems.",
        "jd": jd(
            "Product Designer",
            "product_design",
            ["Figma", "interaction design", "user flows", "design systems"],
            ["prototyping", "accessibility"],
            "4+",
            "bachelor in design or equivalent",
        ),
        "resume": resume(
            "Harper Diaz",
            "Product designer, 5 years",
            "Figma systems, end-to-end flows, and accessibility reviews.",
            ["Figma", "interaction design", "prototyping", "design systems", "WCAG"],
            """### Product Designer, Willow Health (2021-2026)
End-to-end flows for clinician tools. Design system tokens in Figma. Accessibility audits.

### UX Designer, Brightpath (2019-2021)
Mobile onboarding and prototype tests.""",
            "B.F.A. Interaction Design, 2019",
        ),
    },
    {
        "id": "pd-sm-03",
        "role_family": "product_design",
        "label": "strong_match",
        "notes": "UX researcher with mixed methods and insight delivery.",
        "jd": jd(
            "UX Researcher",
            "product_design",
            ["qualitative research", "usability testing", "surveys", "insight synthesis"],
            ["diary studies", "SQL"],
            "4+",
            "bachelor or master in HCI, psych, or related",
        ),
        "resume": resume(
            "Quinn Morales",
            "UX researcher, 6 years",
            "Mixed-methods studies and decision-ready insights.",
            ["usability testing", "interviews", "surveys", "thematic analysis", "Dovetail"],
            """### UX Researcher, Northstar Bank (2021-2026)
Usability tests, diary studies, and survey programs. Insights changed onboarding copy and cut drop-off.

### Researcher, CivicLab (2018-2021)
Interviews and synthesis for public-sector tools.""",
            "M.S. Human-Computer Interaction, 2018",
        ),
    },
    # --- product_design possible_fit (4) ---
    {
        "id": "pd-pf-01",
        "role_family": "product_design",
        "label": "possible_fit",
        "notes": "hard case: career-switcher",
        "jd": jd(
            "Associate Product Manager",
            "product_design",
            ["user empathy", "prioritization", "writing specs", "stakeholder communication"],
            ["SQL", "B2B"],
            "2+",
            "bachelor",
        ),
        "resume": resume(
            "Jamie Brooks",
            "Backend engineer switching to PM",
            "Eight years engineering. Led a squad informally; no full-time PM title.",
            ["Python", "system design", "stakeholder communication", "prioritization", "writing RFCs"],
            """### Staff Engineer / tech lead, Helio (2019-2026)
Wrote RFCs, prioritized backlog with a PM, ran customer calls for API design. Wants a PM seat.

### Software Engineer, Helio (2016-2019)
Backend Python services.""",
            "B.S. Computer Science, 2016",
        ),
    },
    {
        "id": "pd-pf-02",
        "role_family": "product_design",
        "label": "possible_fit",
        "notes": "Visual designer applying to product design; craft yes, product process thin.",
        "jd": jd(
            "Product Designer",
            "product_design",
            ["Figma", "user flows", "usability", "cross-functional collaboration"],
            ["design systems"],
            "4+",
            "design degree preferred",
        ),
        "resume": resume(
            "Sasha Idris",
            "Visual designer, 5 years",
            "Brand and marketing in Figma. Limited product UX process.",
            ["Figma", "illustration", "brand", "typography", "motion"],
            """### Visual Designer, Ember Ads (2021-2026)
Campaigns and landing pages in Figma. Occasional help on in-app empty states.

### Designer, freelance (2019-2021)
Logos and pitch decks.""",
            "B.F.A. Graphic Design, 2019",
        ),
    },
    {
        "id": "pd-pf-03",
        "role_family": "product_design",
        "label": "possible_fit",
        "notes": "Associate PM vs senior PM years and strategy bar.",
        "jd": jd(
            "Senior Product Manager",
            "product_design",
            ["strategy", "roadmapping", "executive communication", "outcome metrics"],
            ["pricing"],
            "6+",
            "bachelor",
        ),
        "resume": resume(
            "Drew Kim",
            "APM, 2 years",
            "Shipped small features; has not owned strategy or exec reviews.",
            ["Jira", "user stories", "standups", "Figma specs", "Mixpanel basics"],
            """### Associate Product Manager, SproutCRM (2023-2026)
Tickets, acceptance criteria, and QA. Shadowed senior PM on roadmap.

### Business analyst intern (2022)
Requirements docs.""",
            "B.S. Business, 2022",
        ),
    },
    {
        "id": "pd-pf-04",
        "role_family": "product_design",
        "label": "possible_fit",
        "notes": "Content designer applying to UX research; writing skill, research methods missing.",
        "jd": jd(
            "UX Researcher",
            "product_design",
            ["study design", "usability testing", "recruiting", "synthesis"],
            ["surveys"],
            "3+",
            "bachelor",
        ),
        "resume": resume(
            "Reese Lang",
            "Content designer, 4 years",
            "UX writing and content decks. Sat in on a few research sessions.",
            ["UX writing", "content strategy", "voice and tone", "Figma", "editing"],
            """### Content Designer, Atlas Travel (2021-2026)
In-product copy. Observed usability tests; did not moderate or write discussion guides.

### Copywriter, agency (2019-2021)
Web copy.""",
            "B.A. English, 2019",
        ),
    },
    # --- product_design not_relevant (3) ---
    {
        "id": "pd-nr-01",
        "role_family": "product_design",
        "label": "not_relevant",
        "notes": "Backend engineer with no product or design practice.",
        "jd": jd(
            "Product Designer",
            "product_design",
            ["Figma", "interaction design", "user research partnership"],
            ["prototyping"],
            "3+",
            "design background",
        ),
        "resume": resume(
            "Logan Barrett",
            "Backend engineer, 6 years",
            "APIs and databases. Does not use Figma or run studies.",
            ["Java", "Spring", "MySQL", "Kafka", "AWS"],
            """### Backend Engineer, Payline (2020-2026)
Java services. No design artifacts.

### Engineer, municipal IT (2018-2020)
Batch jobs.""",
            "B.S. Computer Science, 2018",
        ),
    },
    {
        "id": "pd-nr-02",
        "role_family": "product_design",
        "label": "not_relevant",
        "notes": "Account executive; sales motion not product discovery.",
        "jd": jd(
            "Senior Product Manager",
            "product_design",
            ["discovery", "roadmap", "B2B product strategy"],
            ["SQL"],
            "5+",
            "bachelor",
        ),
        "resume": resume(
            "Morgan Ellis",
            "Account executive, 7 years",
            "Quota-carrying sales. No PM or design roles.",
            ["Salesforce", "negotiation", "prospecting", "MEDDIC", "Excel"],
            """### Account Executive, CloudStack (2019-2026)
Enterprise SaaS sales, President's Club twice.

### SDR, CloudStack (2017-2019)
Outbound pipeline.""",
            "B.A. Communications, 2017",
        ),
    },
    {
        "id": "pd-nr-03",
        "role_family": "product_design",
        "label": "not_relevant",
        "notes": "Warehouse supervisor applying to UX research.",
        "jd": jd(
            "UX Researcher",
            "product_design",
            ["qualitative research", "usability testing", "synthesis"],
            ["surveys"],
            "3+",
            "bachelor",
        ),
        "resume": resume(
            "Pat Reynolds",
            "Warehouse supervisor, 9 years",
            "Shift leadership and safety. No research methods.",
            ["shift scheduling", "WMS", "forklift certified", "safety audits", "Excel"],
            """### Warehouse Supervisor, FastShip DC (2018-2026)
Crew of 22. Inventory accuracy and OSHA checks.

### Associate, FastShip DC (2015-2018)
Picking and packing.""",
            "High school diploma, 2014",
        ),
    },
    # --- operations strong_match (3) ---
    {
        "id": "ops-sm-01",
        "role_family": "operations",
        "label": "strong_match",
        "notes": "Supply chain manager with S&OP, inventory, and vendor work.",
        "jd": jd(
            "Supply Chain Manager",
            "operations",
            ["S&OP", "inventory planning", "vendor management", "ERP"],
            ["SAP", "SQL"],
            "6+",
            "bachelor in supply chain, operations, or related",
        ),
        "resume": resume(
            "Alex Romero",
            "Supply chain manager, 8 years",
            "S&OP cadence, inventory turns, and vendor scorecards in SAP.",
            ["S&OP", "inventory planning", "SAP", "vendor management", "Excel", "SQL"],
            """### Supply Chain Manager, Cinder Goods (2020-2026)
Monthly S&OP. Cut excess inventory 18%. SAP MRP and vendor QBRs.

### Planner, Cinder Goods (2016-2020)
Demand and supply plans for three categories.""",
            "B.S. Supply Chain Management, 2016",
        ),
    },
    {
        "id": "ops-sm-02",
        "role_family": "operations",
        "label": "strong_match",
        "notes": "Logistics / 3PL operations with TMS and carrier management.",
        "jd": jd(
            "Logistics Operations Lead",
            "operations",
            ["TMS", "carrier management", "inbound/outbound", "KPI reporting"],
            ["Lean", "WMS"],
            "5+",
            "bachelor preferred",
        ),
        "resume": resume(
            "Dana Whitaker",
            "Logistics lead, 7 years",
            "3PL multi-node network, TMS, and carrier scorecards.",
            ["TMS", "carrier management", "WMS", "Lean", "Excel", "OTIF"],
            """### Logistics Operations Lead, Harbor 3PL (2019-2026)
Inbound/outbound for 4 DCs. TMS routing. OTIF 97%. Lean daily huddles.

### Dispatcher, Harbor 3PL (2016-2019)
Carrier booking and exception handling.""",
            "B.S. Logistics, 2016",
        ),
    },
    {
        "id": "ops-sm-03",
        "role_family": "operations",
        "label": "strong_match",
        "notes": "Procurement specialist with sourcing, contracts, and savings.",
        "jd": jd(
            "Procurement Specialist",
            "operations",
            ["strategic sourcing", "contract negotiation", "spend analysis", "supplier onboarding"],
            ["Coupa", "should-cost"],
            "4+",
            "bachelor",
        ),
        "resume": resume(
            "Mel Okada",
            "Procurement specialist, 5 years",
            "Indirect spend, RFPs, and contract redlines.",
            ["strategic sourcing", "negotiation", "Coupa", "spend analysis", "contracts"],
            """### Procurement Specialist, Helix Labs (2021-2026)
RFPs for facilities and IT. 11% savings. Coupa catalogs and supplier onboarding.

### Buyer, Helix Labs (2019-2021)
POs and invoice exceptions.""",
            "B.S. Business Administration, 2019",
        ),
    },
    # --- operations possible_fit (3) ---
    {
        "id": "ops-pf-01",
        "role_family": "operations",
        "label": "possible_fit",
        "notes": "Operations analyst vs manager scope; analysis yes, people leadership no.",
        "jd": jd(
            "Operations Manager",
            "operations",
            ["team leadership", "process improvement", "budget", "cross-site coordination"],
            ["Lean Six Sigma"],
            "6+",
            "bachelor",
        ),
        "resume": resume(
            "Robin Shah",
            "Operations analyst, 4 years",
            "Dashboards and kaizen support. Has not managed a team or P&L.",
            ["Excel", "SQL", "process mapping", "Power BI", "Lean basics"],
            """### Operations Analyst, MetroFulfill (2021-2026)
Cycle-time dashboards. Facilitated two kaizen events. No direct reports.

### Intern, MetroFulfill (2020)
Time studies.""",
            "B.S. Industrial Engineering, 2020",
        ),
    },
    {
        "id": "ops-pf-02",
        "role_family": "operations",
        "label": "possible_fit",
        "notes": "Customer success ops applying to supply chain; ops discipline, domain gap.",
        "jd": jd(
            "Supply Chain Planner",
            "operations",
            ["demand planning", "inventory", "ERP", "forecast accuracy"],
            ["SAP"],
            "4+",
            "bachelor",
        ),
        "resume": resume(
            "Kim Alvarez",
            "CS operations, 5 years",
            "Ticket SLAs and workforce planning. No demand or inventory planning.",
            ["Zendesk", "workforce planning", "SLA", "Salesforce", "Excel"],
            """### Customer Success Ops, Nimbus SaaS (2020-2026)
Staffing model for support. SLA reporting. No ERP or forecast work.

### Support lead, Nimbus SaaS (2018-2020)
Queue management.""",
            "B.A. Psychology, 2018",
        ),
    },
    {
        "id": "ops-pf-03",
        "role_family": "operations",
        "label": "possible_fit",
        "notes": "Military logistics to civilian ops; transferable, civilian ERP missing.",
        "jd": jd(
            "Distribution Center Supervisor",
            "operations",
            ["WMS", "people leadership", "safety", "throughput"],
            ["SAP EWM"],
            "5+",
            "bachelor preferred; equivalent military experience considered",
        ),
        "resume": resume(
            "Captain Lee Grant (ret.)",
            "Army logistics officer, 8 years",
            "Led 40 soldiers, convoy and supply accountability. No commercial WMS.",
            ["people leadership", "supply accountability", "safety", "planning", "Excel"],
            """### Logistics Officer, U.S. Army (2016-2024)
Company logistics. Inventories, safety, and throughput under field conditions.

### Platoon leader (2014-2016)
Team leadership.""",
            "B.S. History, 2014. No SAP/WMS certification.",
        ),
    },
    # --- operations not_relevant (4) ---
    {
        "id": "ops-nr-01",
        "role_family": "operations",
        "label": "not_relevant",
        "notes": "hard case: overqualified mismatch",
        "jd": jd(
            "Warehouse Coordinator",
            "operations",
            ["WMS data entry", "receiving", "cycle counts", "shift communication"],
            ["Excel"],
            "1-3",
            "high school",
        ),
        "resume": resume(
            "Dr. Evelyn Marsh",
            "VP of Engineering, 18 years, PhD",
            "Executive engineering leadership. Overqualified and mismatched to coordinator work.",
            ["engineering leadership", "org design", "budgeting", "hiring", "architecture"],
            """### VP Engineering, Atlas Robotics (2018-2026)
200-person org. Board reporting. No warehouse WMS work.

### Director of Engineering, Atlas Robotics (2012-2018)
Platform teams.""",
            "Ph.D. Computer Science, 2008. Not seeking a coordinator role; profile is a seniority and domain mismatch.",
        ),
    },
    {
        "id": "ops-nr-02",
        "role_family": "operations",
        "label": "not_relevant",
        "notes": "Frontend engineer applying to logistics.",
        "jd": jd(
            "Logistics Operations Lead",
            "operations",
            ["TMS", "carriers", "OTIF", "team leadership"],
            ["Lean"],
            "5+",
            "bachelor",
        ),
        "resume": resume(
            "Jules Park",
            "Frontend engineer, 5 years",
            "React apps. No logistics operations.",
            ["React", "TypeScript", "CSS", "Jest", "Webpack"],
            """### Frontend Engineer, Shopwave (2020-2026)
Storefront UI.

### Junior Developer, Shopwave (2018-2020)
CSS and HTML.""",
            "B.S. Computer Science, 2018",
        ),
    },
    {
        "id": "ops-nr-03",
        "role_family": "operations",
        "label": "not_relevant",
        "notes": "Brand designer applying to procurement.",
        "jd": jd(
            "Procurement Specialist",
            "operations",
            ["sourcing", "contracts", "spend analysis"],
            ["Coupa"],
            "3+",
            "bachelor",
        ),
        "resume": resume(
            "Nina Costa",
            "Brand designer, 6 years",
            "Identity systems. No sourcing or contracts.",
            ["brand strategy", "Figma", "illustration", "art direction"],
            """### Brand Designer, Folio Studio (2019-2026)
Identity and campaigns.

### Junior Designer (2017-2019)
Social assets.""",
            "B.F.A. Communication Design, 2017",
        ),
    },
    {
        "id": "ops-nr-04",
        "role_family": "operations",
        "label": "not_relevant",
        "notes": "Academic researcher with no operations or supply-chain practice.",
        "jd": jd(
            "Supply Chain Manager",
            "operations",
            ["S&OP", "inventory", "vendors", "ERP"],
            ["SAP"],
            "6+",
            "bachelor",
        ),
        "resume": resume(
            "Dr. Farid Nasser",
            "Academic researcher, 10 years",
            "Publications in materials science. No S&OP or ERP.",
            ["MATLAB", "lab management", "grant writing", "publishing", "Python for analysis"],
            """### Research Scientist, University Lab (2016-2026)
Experiments and papers. Supervised graduate students in a lab, not a DC.

### Postdoc (2014-2016)
Materials characterization.""",
            "Ph.D. Materials Science, 2014",
        ),
    },
]


KB_FILES: dict[str, str] = {
    "backend-software-engineer.md": """# Backend Software Engineer
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
Python, Java, or Go; REST and gRPC APIs; PostgreSQL or similar RDBMS; Docker; automated testing; observability basics.
## Experience band
Mid to senior: 4-8 years shipping production services, on-call, and API design. Staff: deeper system design and mentoring.
## Education
Bachelor in computer science or equivalent practical experience is common. Degree is a signal, not a substitute for shipped systems.
## Related titles
Backend engineer, server engineer, API engineer, software engineer (backend).
""",
    "data-engineer.md": """# Data Engineer
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
SQL, Python, Spark or similar compute, warehouse platforms (Snowflake, BigQuery, Redshift), orchestration (Airflow), data modeling, dbt.
## Experience band
4+ years building reliable pipelines, SLAs, and quality checks. Senior roles add platform and cost control.
## Education
Bachelor in CS, IS, or quantitative field typical.
## Related titles
Analytics engineer, ETL engineer, warehouse engineer.
""",
    "frontend-engineer.md": """# Frontend Engineer
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
React or similar, TypeScript, CSS, accessibility (WCAG), component testing, performance, design-system consumption.
## Experience band
4+ years of production UI. Senior includes architecture and mentoring.
## Education
Bachelor or equivalent bootcamp plus strong portfolio of shipped product UI.
## Related titles
UI engineer, web engineer, client engineer.
""",
    "devops-sre.md": """# DevOps / Site Reliability Engineer
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
Kubernetes (k8s), containers, CI/CD, cloud (GCP, AWS, Azure), Terraform, Prometheus, incident response.
## Experience band
5+ years operating production systems. Synonyms: k8s for Kubernetes, GCP for Google Cloud.
## Education
Bachelor in CS or engineering common; operations experience weighted heavily.
## Related titles
Platform engineer, SRE, infrastructure engineer, DevOps engineer.
""",
    "mobile-engineer.md": """# Mobile Engineer
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
Swift/iOS or Kotlin/Android, mobile architecture, offline storage, platform APIs, release processes.
## Experience band
4+ years shipping store releases. Backend-adjacent BFF work is a plus, not a substitute for server ownership.
## Education
Bachelor or equivalent.
## Related titles
iOS engineer, Android engineer, mobile developer.
""",
    "ml-engineer.md": """# Machine Learning Engineer
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
Python, model training and evaluation, feature pipelines, serving, experiment tracking.
## Experience band
4+ years from prototype to production models.
## Education
Bachelor or master in CS, stats, or related.
## Related titles
ML engineer, applied scientist, MLOps engineer.
""",
    "security-engineer.md": """# Security Engineer
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
Application security, threat modeling, identity, detection, secure SDLC.
## Experience band
4+ years in security or heavily security-scoped engineering.
## Education
Bachelor; certifications (CISSP, OSCP) sometimes listed.
## Related titles
AppSec engineer, security software engineer, detection engineer.
""",
    "platform-engineer.md": """# Platform Engineer
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
Internal developer platforms, Kubernetes, CI, golden paths, golden images, self-service infra.
## Experience band
5+ years combining SWE and infrastructure.
## Education
Bachelor typical.
## Related titles
Developer productivity engineer, platform SRE.
""",
    "python-backend.md": """# Python backend skill cluster
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
CPython, FastAPI or Django, typing, pytest, packaging, async IO, SQLAlchemy or similar.
## Experience band
Used across backend, data, and automation roles. Depth shown by production services, not keyword lists.
## Education
Not degree-specific.
## Related titles
Python engineer, backend engineer.
""",
    "kubernetes-cloud.md": """# Kubernetes and cloud skill cluster
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
Kubernetes/k8s, Docker/containers, Helm, GKE/EKS/AKS, IAM, networking, autoscaling.
## Experience band
Production cluster operation, not tutorial YAML. Synonym matching: k8s equals Kubernetes; GCP equals Google Cloud.
## Education
Not degree-specific.
## Related titles
SRE, platform, cloud engineer.
""",
    "distributed-systems.md": """# Distributed systems skill cluster
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
Service design, consistency, queues (Kafka, NATS), workflows (Temporal, Airflow), gRPC, observability.
## Experience band
Senior/staff: incident leadership and capacity planning. Adjacent tools (Kafka vs NATS, Airflow vs Temporal) should be treated as related, not identical.
## Education
Bachelor common.
## Related titles
Distributed systems engineer, backend, platform.
""",
    "database-engineering.md": """# Database engineering skill cluster
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
PostgreSQL, schema design, indexing, transactions, replication, query plans.
## Experience band
4+ years owning data stores in production.
## Education
Bachelor typical.
## Related titles
Database engineer, backend engineer.
""",
    "qa-sdet.md": """# SDET / QA engineering
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
Test strategy, automation, CI, API testing, defect analysis.
## Experience band
3+ years; SDET leans toward code.
## Education
Bachelor or equivalent.
## Related titles
QA engineer, SDET, test engineer.
""",
    "react-typescript.md": """# React and TypeScript skill cluster
role_family: engineering
source: O*NET-inspired public competency summary
## Typical skills
React, TypeScript, hooks, state, CSS, a11y, bundlers, testing library.
## Experience band
Production SPAs and design-system work beat tutorial to-do apps.
## Education
Not degree-specific.
## Related titles
Frontend engineer, UI engineer.
""",
    "product-manager.md": """# Product Manager
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
Discovery, roadmapping, prioritization, specs, stakeholder management, outcome metrics, B2B or B2C domain.
## Experience band
Associate 0-2 years; PM 3-5; senior 5+ with strategy and exec communication.
## Education
Bachelor typical; MBA optional, not required.
## Related titles
PM, product owner, group product manager.
""",
    "product-designer.md": """# Product Designer
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
Figma, interaction design, user flows, prototyping, design systems, pairing with research and engineering.
## Experience band
4+ years end-to-end product work. Visual-only craft without flows is a gap.
## Education
Design degree or strong product portfolio.
## Related titles
UX designer, product designer, interaction designer.
""",
    "ux-researcher.md": """# UX Researcher
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
Study design, usability testing, interviews, surveys, synthesis, recruiting, insight storytelling.
## Experience band
3-6 years mixed methods. Observing studies is not the same as moderating and synthesizing.
## Education
HCI, psychology, or related bachelor/master common.
## Related titles
User researcher, qualitative researcher, UX research specialist.
""",
    "visual-designer.md": """# Visual Designer
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
Typography, layout, brand, illustration, marketing surfaces, Figma or Adobe suite.
## Experience band
Product UI systems overlap partly; interaction and research remain gaps for product designer roles.
## Education
B.F.A. or equivalent portfolio.
## Related titles
Graphic designer, brand designer, visual designer.
""",
    "content-designer.md": """# Content Designer
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
UX writing, content strategy, voice and tone, in-product copy, localization awareness.
## Experience band
3+ years in product content. Adjacent to research but not a research substitute.
## Education
English, comms, or equivalent.
## Related titles
UX writer, content strategist, content designer.
""",
    "b2b-saas-pm.md": """# B2B SaaS product management
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
Packaging, pricing exposure, customer discovery, sales/CS partnership, activation and retention metrics, SQL or BI.
## Experience band
Senior PMs own outcomes and exec narrative, not only tickets.
## Education
Bachelor typical.
## Related titles
B2B PM, SaaS product manager.
""",
    "design-systems.md": """# Design systems skill cluster
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
Tokens, components, documentation, accessibility, Figma libraries, partnership with frontend.
## Experience band
2+ years contributing; senior owns governance.
## Education
Not degree-specific.
## Related titles
Design systems designer, product designer.
""",
    "user-research-methods.md": """# User research methods cluster
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
Usability tests, diary studies, surveys, thematic analysis, discussion guides, bias checks.
## Experience band
Practitioners can name methods and show decisions changed by insights.
## Education
Social science or HCI helpful.
## Related titles
UX researcher.
""",
    "interaction-design.md": """# Interaction design skill cluster
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
Flows, states, information architecture, prototyping, edge cases, platform conventions.
## Experience band
Core to product designer; weak in purely visual resumes.
## Education
Design or HCI.
## Related titles
IxD, product designer.
""",
    "accessibility-inclusive-design.md": """# Accessibility and inclusive design
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
WCAG, keyboard and screen-reader flows, contrast, inclusive research.
## Experience band
Valued across product design and frontend.
## Education
Not degree-specific.
## Related titles
Accessibility specialist, product designer, frontend.
""",
    "product-strategy.md": """# Product strategy skill cluster
role_family: product_design
source: O*NET-inspired public competency summary
## Typical skills
Problem framing, bets, positioning, outcome metrics, executive communication.
## Experience band
Senior PM and above. Associate PMs rarely show this yet.
## Education
Not degree-specific.
## Related titles
Senior PM, group PM.
""",
    "supply-chain-manager.md": """# Supply Chain Manager
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
S&OP, inventory planning, vendor management, ERP (SAP and peers), forecast accuracy, cost and service tradeoffs.
## Experience band
6+ years with planning ownership. Analyst work without S&OP is a gap.
## Education
Bachelor in supply chain, operations, or related.
## Related titles
Supply chain manager, planning manager, SIOP lead.
""",
    "logistics-coordinator.md": """# Logistics Operations
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
TMS, carrier management, inbound/outbound, OTIF, exception handling, KPI reporting.
## Experience band
5+ years for lead roles; coordinators may be 1-3 years WMS/receiving focused.
## Education
Bachelor preferred for lead; high school plus experience for coordinator.
## Related titles
Logistics lead, transportation coordinator, 3PL operations.
""",
    "procurement-specialist.md": """# Procurement Specialist
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Strategic sourcing, RFP, contract negotiation, spend analysis, supplier onboarding, Coupa or similar P2P.
## Experience band
4+ years in sourcing, not only PO clerical work.
## Education
Bachelor in business or supply chain common.
## Related titles
Buyer, category specialist, sourcing manager.
""",
    "warehouse-operations.md": """# Warehouse operations
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
WMS, receiving, cycle counts, picking, safety, throughput, shift communication.
## Experience band
Coordinator: 1-3 years. Supervisor: people leadership plus WMS. VP Engineering profiles are an overqualified mismatch.
## Education
High school to bachelor depending on level.
## Related titles
Warehouse coordinator, DC supervisor, inventory control.
""",
    "operations-manager.md": """# Operations Manager
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Team leadership, process improvement, budget, cross-site coordination, Lean/Six Sigma.
## Experience band
6+ years with direct reports. Analyst-only backgrounds are possible fits, not automatic matches.
## Education
Bachelor typical.
## Related titles
Ops manager, site manager, area manager.
""",
    "inventory-planning.md": """# Inventory and demand planning
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Forecasting, safety stock, ERP, forecast accuracy, S&OP inputs.
## Experience band
4+ years in planning seats.
## Education
Bachelor quantitative or supply chain.
## Related titles
Demand planner, inventory analyst, supply planner.
""",
    "customer-success-ops.md": """# Customer success operations
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
SLA, workforce planning, ticketing (Zendesk), CRM, process documentation.
## Experience band
Adjacent to supply chain but different domain (service ops vs physical flow).
## Education
Bachelor common.
## Related titles
CS ops, support ops, business operations.
""",
    "quality-assurance-ops.md": """# Quality in operations
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Incoming quality, CAPA, ISO, audits, process control.
## Experience band
3+ years in manufacturing or DC quality.
## Education
Bachelor in engineering or quality often listed.
## Related titles
Quality engineer, QA supervisor.
""",
    "manufacturing-ops.md": """# Manufacturing operations
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Production planning, OEE, standard work, safety, supervision.
## Experience band
Supervisor and manager tracks.
## Education
Bachelor or equivalent shop-floor tenure.
## Related titles
Production supervisor, manufacturing manager.
""",
    "vendor-management.md": """# Vendor management skill cluster
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Scorecards, QBRs, contracts, risk, onboarding, performance management.
## Experience band
Used in procurement and supply chain manager roles.
## Education
Not degree-specific.
## Related titles
Supplier manager, procurement, supply chain.
""",
    "transportation-fleet.md": """# Transportation and fleet
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Routing, carriers, compliance, cost per mile, TMS.
## Experience band
3+ years dispatch to leadership.
## Education
Varies.
## Related titles
Fleet supervisor, transportation coordinator.
""",
    "demand-planning.md": """# Demand planning
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Statistical and consensus forecasting, promotions, forecast accuracy, S&OP.
## Experience band
4+ years.
## Education
Bachelor quantitative.
## Related titles
Demand planner, S&OP analyst.
""",
    "lean-process-improvement.md": """# Lean process improvement
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Kaizen, value-stream mapping, standard work, daily management, Six Sigma tools.
## Experience band
Green belt helpful; demonstrated events matter more than certificates alone.
## Education
Not degree-specific.
## Related titles
CI specialist, operations manager, logistics lead.
""",
    "erp-systems.md": """# ERP systems skill cluster
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
SAP, Oracle, NetSuite, item masters, MRP, purchasing, inventory transactions.
## Experience band
Planners and managers are expected to transact, not only export to Excel.
## Education
Not degree-specific.
## Related titles
Supply chain, procurement, operations manager.
""",
    "military-logistics.md": """# Military logistics transfer
role_family: operations
source: O*NET-inspired public competency summary
## Typical skills
Accountability, people leadership, planning under constraint, safety. Civilian WMS/ERP and TMS often need translation.
## Experience band
Possible fit for DC supervisor when leadership is strong; train on commercial systems.
## Education
Degree plus service, or equivalent experience.
## Related titles
Logistics officer, supply officer, DC supervisor.
""",
}


def main() -> None:
    JDS.mkdir(parents=True, exist_ok=True)
    RESUMES.mkdir(parents=True, exist_ok=True)
    KB.mkdir(parents=True, exist_ok=True)

    labels = []
    for case in CASES:
        cid = case["id"]
        (JDS / f"{cid}.md").write_text(case["jd"], encoding="utf-8")
        (RESUMES / f"{cid}.md").write_text(case["resume"], encoding="utf-8")
        labels.append(
            {
                "id": cid,
                "role_family": case["role_family"],
                "label": case["label"],
                "jd_path": f"data/eval/jds/{cid}.md",
                "resume_pdf": f"data/eval/resumes/{cid}.pdf",
                "notes": case["notes"],
            }
        )
    LABELS.write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")

    for name, body in KB_FILES.items():
        (KB / name).write_text(body.lstrip("\n"), encoding="utf-8")

    from collections import Counter

    fam = Counter(c["role_family"] for c in labels)
    lab = Counter(c["label"] for c in labels)
    print(f"wrote {len(labels)} cases family={dict(fam)} label={dict(lab)}")
    print(f"wrote {len(KB_FILES)} KB files")


if __name__ == "__main__":
    main()
