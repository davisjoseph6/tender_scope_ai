# TenderScope AI — system card (2 November 2026)

**Purpose/user:** French SMEs and bid coordinators assessing *public procurement notices*.

**Data scope:** Read-only public BOAMP/DILA OpenDataSoft notice records by `idweb` and their BOAMP URL. No scraping or automated login to procurement-platform buyer profiles; no assumption that RC, CCTP, CCAP or annexes are obtainable. Optional user-supplied PDFs only when legally accessible. Fictional demo dossier labelled as fictional.

**Inputs/outputs:** BOAMP notice ID -> published field values with API field identifiers, DILA attribution and official URL; local public PDFs/text -> provisional cited passage candidates, date contradiction indicators, checklist export, optional RAG Q&A. The case of inconsistent deadlines is displayed as **REQUIRES VERIFICATION**, without selecting an authoritative date.

**Model:** Groq `openai/gpt-oss-20b` optional, with consent; local Ollama `qwen2.5:7b` optional for offline generation, `bge-m3` for optional hybrid retrieval. Neither embedding model nor Groq key is bundled. Offline BM25 and rule extraction need no network.

**Safety:** Human review is mandatory for date authority, applicability, amendments and bid/no-bid judgment. Models have no procurement submission tools. Documents are untrusted. Existence of a citation does NOT verify its meaning. `GROQ_API_KEY` is excluded from source control.

**Evaluation:** Historical 20 cases from one 2024 RC: 10/20 strict phrase+source proxy, 0/1 deadline exact match; Wilson intervals are descriptive only. Structured Groq historical export is not a prompt-only baseline. Reproducible prompt-only comparison script provided, but not yet executed.

**Limitations:** No authenticated DCE access, no OCR, no guaranteed amendment chronology, no semantic correctness certification, no BOAMP multi-notice held-out gold set, no legal advice. BOAMP information can change; verify official source before action.

**Classroom fallback:** A public BOAMP record snapshot (26-99630) is bundled for demonstrations when the OpenDataSoft service or classroom network fails. Its provenance and offline status are displayed; its response deadline is not asserted. It is not a substitute for a live API request.


**Grok (xAI) integration:** The third model provider uses XAI_API_KEY and XAI_MODEL, the xAI Responses API and per-request explicit permission. It is not Groq, is not local, may incur charges, and uses the same source-bound citation filter. No web-search or procurement-submission tools are granted. It remains a prototype and needs a real API smoke test on the user's machine.
