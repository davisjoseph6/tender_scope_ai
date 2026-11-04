# S1 — Agent Sheet: Workflow vs Agent

**Project:** TenderScope AI — evidence-grounded public procurement analysis and bid-preparation assistant  
**Course:** Agentic AI · Session 1 — What is an agent?  
**Deliverable:** Five realistic requests from an SME procurement user, each classified and justified.

## Classification rule

- **Workflow:** The application follows an explicitly defined sequence of actions, even if one step calls an LLM; it does not independently decide which tools and follow-up actions to pursue.
- **Agent:** The system is assigned a goal and must choose and adapt its actions/tools based on intermediate observations, within boundaries and subject to human approval for consequential actions.

## Five user requests

| # | Real user request (as a user would type it) | Workflow or agent? | One-sentence justification |
|---|---|---|---|
| **1** | "Find BOAMP notice **26-99630** and show me the buyer, contract subject, submission deadline, and link to the official notice." | **Workflow** | This requires a predefined sequence of validating the notice ID, querying a public API, and displaying the returned fields, with no autonomous planning. |
| **2** | "I uploaded the **RC and CCTP** for this tender; identify the mandatory requirements and show the exact document quotations and page numbers." | **Workflow** | The application can follow a fixed ingestion–extraction–citation-validation pipeline, even when optional LLM inference is used. |
| **3** | "Compare the submission deadlines in the **original RC and its amendment**, show both source passages, and warn me if they disagree." | **Workflow** | Known date-extraction and conflict-detection rules can complete this bounded task without choosing new tools or goals. |
| **4** | "Every weekday, check newly published **public BOAMP IT-maintenance notices**, investigate which opportunities match our capabilities, and notify me only about genuinely new promising tenders." | **Agent** | The system would need to repeatedly discover notices, decide which ones warrant deeper inspection, adapt to new evidence, and choose when to notify the user. |
| **5** | "For this tender, investigate **unresolved eligibility and technical questions**, identify what evidence is missing, draft clarification questions for the buyer, and update our review plan when official clarifications arrive; ask me before any message is sent." | **Agent** | The system would have to iteratively plan research steps, select appropriate evidence sources, respond to newly discovered information, and seek approval before any external communication. |

## Evidence from our project: what can be demonstrated today?

- **Request 1 — implemented workflow:** Open **Avis BOAMP** and look up `26-99630` using `ui/page_boamp.py` → `core/boamp.py`; if the API is down, clearly label the local snapshot as **not live**.
- **Request 2 — implemented workflow with limitations:** Upload text-based PDFs through **Mes appels d’offres** (`ui/page_dossier.py` → `core/pdf_reader.py`), then inspect candidate passages using **Analyse intelligente** (`core/extraction.py` and optionally `core/llm.py`, `core/ollama_extraction.py`, or `core/grok.py`). Exact citation existence is checked, but extraction is not guaranteed complete or semantically correct.
- **Request 3 — implemented workflow:** Open **Prototype local**, load the three **fictional** documents and observe the 15/18 December 2026 deadline conflict (`ui/page_local_demo.py` → `core/deadlines.py`). The program flags **REQUIRES VERIFICATION**; it does not decide which deadline is legally authoritative.
- **Requests 4 and 5 — proposed agent capabilities, not implemented:** Autonomous scheduled notice monitoring, dynamic multi-step investigation, buyer clarification follow-up, and notifications are **future work**. The current application has no autonomous buyer communication or bid submission.

## Boundaries for a future agent

Use only authorized, publicly available procurement information or documents explicitly provided by the user. Preserve sources, abstain on insufficient evidence, flag contradictions, and require a human to approve any external message, eligibility conclusion, or bid-related action. Never bypass protected buyer portals.

**Session 1 outcome:** We can distinguish repeatable workflows already available in TenderScope AI from genuinely agentic, goal-directed behavior that the final Agentic AI project would need to add.
