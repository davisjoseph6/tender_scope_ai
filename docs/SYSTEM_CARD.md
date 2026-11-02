# TenderScope AI — system card (prototype, 2 November 2026)

**Purpose / user:** French SME bid coordinators, first-pass analysis of public procurement materials.

**Scope:** Multiple locally loaded documents, page-bound citations, keyword extraction, an optional Groq structured extractor, optional on-device Ollama question answering and hybrid BM25/embedding retrieval, preliminary date conflict flags, manually confirmed bid/no-bid checklist.

**Out of scope:** Legal advice, authoritative deadline determination, autonomous submission, guaranteed eligibility, confidential data sent to Groq without consent. Demo data are explicitly fictional.

**Models/data:** Groq `openai/gpt-oss-20b` when configured; local Ollama `qwen2.5:7b` and `bge-m3` when installed. These are configurable, not included. External public tender PDF for existing evaluation is not committed; see `eval/README.md`. Demo fictional documents live in `data/demo/`.

**Safety:** Source documents are untrusted, exact quotation existence is verified when generating structured results, no automatic bid submission, Groq transmission requires explicit user permission. Citation presence does not validate factual interpretation or version authority.

**Known limitations:** No OCR; deadline pattern matching is incomplete; no official amendment chronology; no guaranteed semantic support, no automatic legal compliance determination. Evaluation spans 20 initial references from a single tender, not yet independently validated.

**Human review:** Required for all operational decisions, official deadlines, applicability and document version control.
