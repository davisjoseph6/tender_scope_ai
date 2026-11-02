# Five-minute final demo — BOAMP access and verification

**Preparation:** start Streamlit and verify `Avis BOAMP` works while online; also have `Prototype local` ready as a network-independent fallback. Never claim to access buyer documents behind authentication.

1. **0:00–0:45: user/problem.** A small French IT company scans BOAMP notices to find published subject, buyer, response date and a link to the public authoritative notice.
2. **0:45–1:45: BOAMP read-only retrieval.** In **Avis BOAMP**, enter an actual BOAMP identifier such as `26-106035`, click **Lire cet avis BOAMP**. Show the published field names and provenance. Open official BOAMP link. Explain that gated DCE access is intentionally out of scope.
3. **1:45–3:00: negative/verification case.** In **Prototype local**, click **Charger le dossier fictif (3 documents)**. Show the two differing candidate deadlines and the prominent **REQUIRES VERIFICATION / À VÉRIFIER** warning. Explain why we do not silently prefer a date; cite both sources.
4. **3:00–3:45: retrieval.** Ask the deadline question, show BM25 source passages. Hybrid BM25 + local embeddings and locally generated cited answer are optional, only if installed and previously tested.
5. **3:45–4:40: quantitative evidence.** Show `docs/EVALUATION_REPORT.md`: historical structured output **10/20 strict value+source checks**, **0/1 exact deadline**. One-tender and unvalidated gold caveats. If available, show a *real* prompt-only output from `eval/run_prompt_only.py`; otherwise explicitly say pending.
6. **4:40–5:00: limitations/safety.** No OCR or private buyer portal, no automated submission, review remains human.

**Offline backup:** bundled fictional texts always work without network or LLM. Avoid presenting artificial demo documents as actual BOAMP tenders.
