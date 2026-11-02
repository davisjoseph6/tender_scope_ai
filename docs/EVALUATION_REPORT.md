# Evaluation report — provisional, not a completed final evaluation

**Baseline:** The repository contains 20 annotated examples from one historical French procurement RC and an exported extraction with 52 requirements. The existing source-matching evaluation reports 15/20 reference passages covered, 55/55 citations present in their cited pages, and 17 cases flagged for review.

**Interpretation:** Citation existence is not citation support. The report does *not* demonstrate semantic precision, legal accuracy or generalisation across tenders. The initial annotations require independent review. One exported summary reverses the meaning of a “no surcharge” clause.

**Next evaluation:** Collect at least 50 labeled cases from multiple legally accessible tender dossiers; compare prompt-only, BM25 and hybrid BM25+embeddings on answer correctness *and* supported citations. Include deadline, contradiction, abstention, invalid quote and prompt-injection cases. Report bootstrap confidence intervals at the **dossier** level when enough independent dossiers exist, plus costs and latency.

**Do not claim:** 80% accuracy or validated semantic correctness until actually measured.
