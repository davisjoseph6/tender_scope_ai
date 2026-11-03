# TenderScope AI

**Evidence-grounded public procurement analysis and bid-preparation prototype**

TenderScope AI helps small and medium-sized businesses inspect French public tender notices, extract requirements from accessible documents, investigate relevant passages, flag uncertain deadlines, and prepare a **human-reviewed** bid/no-bid checklist. It is a Python + Streamlit research/course prototype—not a procurement portal, autonomous bidding agent, legal advisor, or authenticity-certification system.

The interface is primarily **in French**; this README is in English.

> **Principle:** Show where an answer came from, expose uncertainty, and leave consequential procurement decisions to the user. An exact quotation is not proof that the AI interpreted it correctly.

## Quick start (Ubuntu 24.04 / WSL2)

Requires Python 3.10+ (with `venv`/`pip`), Git, and an internet connection for the **live** BOAMP lookup. The fictional dossier, local rules, and BM25 search do not require an external AI key or internet access.

```bash
git clone https://github.com/davisjoseph6/tender_scope_ai.git
cd tender_scope_ai
git switch feature/local-demo-scoping-alignment

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py --server.headless true --server.address 127.0.0.1
```

Open **http://localhost:8501** in your Windows browser. Leave the Streamlit terminal running; stop with `Ctrl+C`. If you already cloned the project, run `git pull --ff-only` on the feature branch instead of cloning again. The branch linked above is the current prototype; its changes are also under review in [PR #1](https://github.com/davisjoseph6/tender_scope_ai/pull/1).

### Windows PowerShell alternative

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Do not expose this development server to the public internet. The application has not been hardened as a multi-user production service.

## Try it in two minutes — no external LLM required

1. Open **Prototype local** and click **Charger le dossier fictif (3 documents)**.
2. Inspect the two candidate submission deadlines: **15 December 2026 at 12:00** (`RC_FICTIF.txt`) and **18 December 2026 at 12:00** (`AVENANT_FICTIF.txt`). The application deliberately displays **REQUIRES VERIFICATION / À VÉRIFIER**, without choosing the legally authoritative date.
3. Ask the prefilled question, “Quelle est la date limite de remise des offres ?”, select **BM25 hors ligne**, and click **Rechercher les passages**. Open the retrieved source fragments.
4. Optionally export the JSON review checklist. The demo files in `data/demo/` are **fictional** and must not be used for a real tender.

### Try a genuine public BOAMP notice

Go to **Avis BOAMP**, enter `26-99630`, and click **Lire cet avis BOAMP**. The application queries the DILA/BOAMP OpenDataSoft API, displays published metadata (including the deadline field if available), preserves field provenance, and links to the official notice. A direct HTTP 200 response for this notice was observed on 3 November 2026; API availability and the notice's current status must still be checked at use time.

If live access fails, click **Charger un exemple réel BOAMP (copie hors ligne)**. This is a **labeled, non-live snapshot**, not a fresh API response. The **Ouvrir les champs BOAMP pour la recherche locale** action creates a searchable *virtual page of API fields*; it does **not** retrieve a complete original consultation regulation or private DCE.

## Features and screens

| Screen (French UI label) | Implemented purpose |
| --- | --- |
| **Tableau de bord** | Session overview and review progress |
| **Mes appels d’offres** | Upload multiple text-based PDFs, inspect extracted text and pages, export source-indexed JSON, switch dossiers |
| **Analyse intelligente** | Candidate extraction by local rules or structured extraction via Groq, local Ollama, or Grok (xAI) |
| **Profil entreprise** | Record company turnover, skills, certifications, staffing and references for manual review; export JSON |
| **Décision Bid/No-Bid** | Manual compliance checklist with conservative `Go` / `No-Go` / `À vérifier` logic |
| **Assistant IA** | Local lexical passage search or BM25-grounded questions to Groq/Grok |
| **Prototype local** | Reproducible fictitious dossier, deadline-conflict flags, BM25 or optional BGE-M3 hybrid retrieval, optional local Qwen answer |
| **Avis BOAMP** | Read-only lookup of a public notice ID and published metadata through BOAMP |

The automatic comparison of extracted requirements to company capabilities is **not implemented**. A `Go` outcome means the user has marked all checklist entries resolved and confirmed a complete review; it is **not** an independently verified eligibility verdict.

## How the engineering works

```text
Public BOAMP API ──> Published metadata + source provenance ───┐
                                                               │
User PDF upload ──> pypdf page text ──> document/page records ──┤
                                                               ├─> Rule/date checks
Fictional local dossier ────────────────────────────────────────┤
                                                               ├─> Chunking and retrieval
                                                               │      ├─ BM25 (lexical)
                                                               │      └─ Optional BGE-M3 dense embeddings
                                                               │            + cosine similarity + RRF
                                                               └─> Optional LLM extraction or Q&A
                                                                      ├─ Groq
                                                                      ├─ Grok (xAI)
                                                                      └─ Ollama (local)
                                                                            │
                                      Pydantic JSON schema + exact citation checks
                                                                            │
                                           Streamlit evidence and human review
```

**Ingestion.** `core/boamp.py` validates BOAMP IDs and reads *public* OpenDataSoft fields (`records[].record.fields`). `core/pdf_reader.py` uses `pypdf` to extract text with the original document name and page number. `core/doc_types.py` detects likely RC/CCTP/CCAP/AE/BOAMP types. A blank extracted page is reported; no OCR is provided.

**Deterministic analysis.** `core/extraction.py` uses French keyword/regex rules to identify candidate passages, not to make legal determinations. `core/deadlines.py` parses recognizable date/time candidates and flags zero or multiple distinct values for verification. An amendment's legal precedence is not established by this rule.

**Retrieval.** `core/rag.py` creates overlapping, page-bound text chunks (default 2,400 characters, 300 overlap), tokenizes text, and ranks fragments using BM25. In the optional **Prototype local** hybrid mode, `core/hybrid.py` asks local Ollama's `/api/embed` endpoint for dense embeddings with `bge-m3`, computes cosine similarity, and combines BM25 and semantic rankings using **reciprocal rank fusion (RRF)**. Embeddings are recomputed on request; there is **no persistent vector index, Chroma store, or cross-encoder reranker**. Standard Groq/Grok Q&A uses **BM25**, not the optional hybrid mode.

**Structured generation.** The AI clients submit system instructions and a JSON-serialized `{"task": ..., "sources": ...}` user message, then request output conforming to Pydantic schemas. Extraction and Q&A are distinct flows: extraction processes document chunks; BM25-grounded Q&A retrieves passages before generation. The project uses pre-trained models for **inference**, not fine-tuning or model training.

**Source checks.** `core/llm.py` rejects proposed quotations if their source ID was not supplied or the quoted text cannot be found in the corresponding fragment (minor whitespace variation is tolerated). Valid citation existence does **not** guarantee a correct summary, complete coverage, or correct interpretation of negations and deadlines. Final review remains human.

**State.** `ui/workspace.py` stores active dossiers, checkpoints and results in Streamlit `st.session_state`. Dossiers are **session-only**, not backed by a persistent document database. Export important results.

## Optional AI setup

The base demo works without an API key. AI calls are optional and may consume resources, tokens, or external-service credits. Only send documents to third-party providers when you are authorized to do so.

### Local Ollama — Qwen and BGE-M3

Install [Ollama](https://ollama.com/) and make sure its local service is running. Then:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b
ollama list
```

If Ollama is not running, start it with `ollama serve`; **do not** start a second instance if the system service is already active.

Configuration can be overridden using environment variables: `OLLAMA_MODEL` (default `qwen2.5:7b`), `OLLAMA_EMBED_MODEL` (default `bge-m3`), and `OLLAMA_BASE_URL` (default `http://127.0.0.1:11434`; localhost is required by the app). Local Ollama actions are exposed in **Analyse intelligente** and **Prototype local**. Ollama's model output is still subject to schema validation and source checks.

### Groq and xAI Grok — external services

Create a `.env` file in the project root (**ignored by Git**). Example, using only the credentials you actually intend to activate:

```dotenv
GROQ_API_KEY=replace_with_your_groq_key
GROQ_MODEL=openai/gpt-oss-20b

XAI_API_KEY=replace_with_your_xai_key
XAI_MODEL=grok-4.7
```

- **Groq** ([console](https://console.groq.com/keys)) uses its Python SDK and Chat Completions with structured JSON output. In **Analyse intelligente**, choose **Groq · IA**. In **Assistant IA**, choose **Groq + RAG BM25**.
- **Grok (xAI)** ([console](https://console.x.ai/)) is a **different provider** and uses the xAI Responses API. Choose **Grok · xAI** for extraction or **Grok (xAI) + RAG BM25** for questions.
- Each external AI workflow requires the corresponding authorization checkbox **and** button click. Check that your selected model is enabled for your account. A configured key alone does not prove authorization. External calls may incur charges.
- Never commit `.env`, paste secrets into issues, or publish screenshots containing credentials.

Provider errors, rate limits, and invalid structured outputs are surfaced as bounded failures. Long extraction jobs save completed chunk progress in the current session; incomplete work is not represented as fully processed. The LLM has no tool or permission to submit bids.

## Source code map

```text
tender_scope_ai/
├── app.py                    # Streamlit entry point and navigation
├── ui/
│   ├── page_dossier.py       # PDF uploader and document viewer
│   ├── page_boamp.py         # Public BOAMP notice lookup
│   ├── page_local_demo.py    # Offline demo and optional hybrid retrieval UI
│   ├── page_points_cles.py   # Rules / Groq / Ollama / Grok extraction
│   ├── page_assistant.py     # Search and BM25-grounded Q&A
│   ├── page_decision.py      # Human bid/no-bid checklist
│   ├── page_profile.py       # Company profile input
│   └── workspace.py          # Per-session dossier state
├── core/
│   ├── boamp.py              # Read-only public API adapter
│   ├── pdf_reader.py         # PDF page text extraction
│   ├── doc_types.py          # Document type heuristics
│   ├── extraction.py         # Deterministic requirement clues
│   ├── deadlines.py          # Deadline candidate parsing and conflict flagging
│   ├── rag.py                # Page chunking and BM25 ranking
│   ├── hybrid.py             # Local bge-m3 embeddings, cosine, RRF
│   ├── local_llm.py          # Local Ollama structured generation
│   ├── ollama_extraction.py  # Qwen extraction workflow
│   ├── llm.py                # Groq client, Pydantic schemas, citation checks
│   ├── grok.py               # xAI client and extraction / Q&A
│   └── scoring.py            # Conservative manual decision logic
├── data/demo/                # Three clearly labeled fictional text documents
├── eval/                     # Historical gold set, baselines and metrics
├── tests/                    # Deterministic unit and integration-style tests
├── docs/                     # System card, evaluation and demo references
└── .github/workflows/        # Automated tests and historical evaluation
```

## Evidence and evaluation

The existing historical evaluation uses **one public 2024 consultation regulation** (RC Cœur d'Hérault) and **20 manually prepared reference field checks**. These annotations still require independent expert review, and the 20 fields belong to **one tender**, not 20 independent tenders.

| Historical structured Groq export (not prompt-only) | Result |
| --- | ---: |
| Gold cases with matching source passage | 15/20 (75%) |
| Expected field phrases **and** corresponding source passage | **10/20 (50%)** |
| Exact deadline date **and time** in generated summary | **0/1** |
| Original exported quotations found in source pages | 55/55 (textual existence only) |

The 10/20 measure is a **strict string-matching proxy**, not expert-adjudicated semantic accuracy. A descriptive Wilson 95% interval is approximately **29.9%–70.1%**, but it must **not** be interpreted as an estimate of generalization across tenders. The incorrect/missing deadline detail and a negation error are important documented failure cases.

Read [the evaluation report](docs/EVALUATION_REPORT.md) and [evaluation dataset instructions](eval/README.md). To reproduce locally, first download the historical source PDF to `data/samples/RC_Coeur_Herault_2024.pdf` as described in `eval/README.md`. A pinned SHA-256 prevents silent substitution of another PDF version.

```bash
python -m eval.field_metrics

# Optional: a NEW prompt-only one-call experiment on the whole PDF.
# These commands invoke the configured provider and may incur charges.
python -m eval.run_prompt_only --backend groq
python -m eval.field_metrics --compare eval/prompt_only_groq.json

# Alternatives (different models; not controlled comparisons of RAG alone):
python -m eval.run_prompt_only --backend ollama
python -m eval.run_prompt_only --backend grok
```

The repository also contains `eval/prompt_only_ollama.json`, but it uses a **different model** from the historical Groq output; any score difference cannot be attributed solely to retrieval. A meaningful comparison requires a frozen dataset, the **same** model, consistent prompts/schema and independent human checks.

Run regression tests with:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions runs the unit tests and historical gold-set checks. API calls in unit tests are simulated; passing tests **does not** establish that external providers are accessible or that generated answers are correct. A source-PDF-dependent test can be skipped in CI if its untracked PDF is absent.

## Live presentation: three speakers, under 10 minutes

Suggested target **9 min 20 sec**, leaving **40 seconds** for delays:

| Time | Presenter | Live action |
| --- | --- | --- |
| 0:00–2:40 | **A — problem and provenance** | Introduce the use case; show **Avis BOAMP** and public notice `26-99630` (or honestly labeled offline snapshot) |
| 2:40–6:00 | **B — document intelligence** | Show the preloaded fictional dossier, both conflicting deadlines, and BM25 retrieval of the source passages |
| 6:00–9:20 | **C — LLM and evaluation** | Show a **previously executed and checked** Ollama extraction, explain JSON/schema/citation validation, and present the historical field+source metrics |

**Before presenting:** run the unit tests; test the real BOAMP connection; pre-load the fictional dossier; rehearse the Ollama result; open the evaluation report. If the model or network fails, fall back to the deterministic offline demo. Do **not** present a saved result as a fresh live inference or imply that the fictional tender is an official government notice. See [the shorter demonstration walkthrough](docs/DEMO_SCRIPT.md).

## Safety, scope, and limitations

- **No document authenticity verification:** the app does not compare uploaded PDFs against original government-hosted files, validate digital signatures, or establish that an uploaded document is the latest authoritative version.
- **Public data only:** BOAMP metadata is accessed read-only. No login bypass, protected buyer-profile scraping, automated retrieval of gated DCE documents, or bid submission.
- **No OCR:** scanned/image-only PDFs may contain no extractable text. Missing source text is reported, not invented.
- **No automated eligibility assessment:** company-profile comparison and full requirement coverage remain manual; the checklist is not legal advice.
- **No durable application storage:** dossier state is session-based, and exports must be saved by the user.
- **No guarantee of semantic correctness:** verified quotation existence does not imply that a summary is accurate, complete, timely, or legally applicable.
- **Not production-hardened:** further access controls, data retention policies, security reviews, provenance checks, version handling and independent multi-tender evaluation are required.

See [SYSTEM_CARD](docs/SYSTEM_CARD.md), [EVALUATION_REPORT](docs/EVALUATION_REPORT.md), and [RED_TEAM_LOG](docs/RED_TEAM_LOG.md) for additional context.

## Contributing and project status

This is a classroom/research prototype. Changes should be reviewed with `python -m unittest discover -s tests -v` and a manual Streamlit smoke test, especially for BOAMP and optional model providers. Do not add real API keys or sensitive tender files to Git.

The prototype and its documentation were developed with assistance from ChatGPT; contributors remain responsible for reviewing, testing and explaining the code, model behavior, and reported findings.
