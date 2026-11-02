# TenderScope AI — evaluation report (2 November 2026)

## Dataset, question, and ground truth

One publicly available **historical** French procurement règlement de consultation (RC Cœur d'Hérault, 2024), twenty manually prepared field/reference expectations in `eval/gold_rc.jsonl`. Source PDF and SHA-256 pinned as described in `eval/README.md`. Independent human validation of the annotations is **still pending**. This case is NOT a BOAMP multi-notice evaluation.

**Research question:** Does a source-grounded structured extraction pipeline correctly report procurement field values, dates and evidence, compared with a prompt-only LLM run?

## Results actually measured on the historical structured export

| Metric | Historical structured Groq export | Wilson 95% interval |
| --- | ---: | --- |
| Gold cases with a matching cited passage (source coverage) | 15/20 (75%) | not the primary correctness measure |
| Required field phrases present in summary **and** matching cited passage | **10/20 (50%)** | **29.9%–70.1%** |
| Submission deadline date **and** time exact in model summary | **0/1 (0%)** | **0%–79.4%** |
| Citations textually found in original pages (existing audit) | 55/55 (100%) | citation existence only |
| Prompt-only LLM baseline | **NOT YET RUN** | no result to report |

The 10/20 value is a **strict automated phrase-matching proxy**, not adjudicated semantic accuracy. The earlier 15/20 and 55/55 are from `eval/reports/baseline.json`. This historical `eval/baseline_rc.json` is **structured Groq extraction**, *not* a prompt-only model output.

**Concrete errors:** rc01 cites the deadline but omits 01/08/2024 and 11 h from its summary; rc17 reverses a "ne saurait entraîner de surcoût" clause; rc13–rc15 omit the three principal weighting anchors.

### Reproduce, and then compare prompt-only

```bash
python -m eval.field_metrics
python -m eval.run_prompt_only --backend groq
python -m eval.field_metrics --compare eval/prompt_only_groq.json
```

For the prompt-only control, use the **same Groq model** with the *full RC as a single user input*, no retrieval, no embeddings, no reranker and a fixed structured schema. `eval/run_prompt_only.py` saves model identity. It requires an API key and sends the public PDF text to Groq only on user execution. Alternatively use `--backend ollama` and `--compare eval/prompt_only_ollama.json`, but **do not attribute any difference to RAG alone** when the model changes.

### Confidence intervals and limitations

The reported field confidence interval is Wilson score (z=1.96) treating each of the 20 **correlated within-one-tender** fields as if they were independent, solely as a descriptive check. It is NOT a population or out-of-sample confidence interval. The deadline has **n=1**, making any interval extremely wide. The dataset does not support generalization claims to BOAMP notices, semantic precision or eligibility advice. Once real BOAMP notices are collected, freeze a new gold set of independent notices and evaluate by notice-level bootstrap.

### Safety and demo

The local fictional RC and rectificatif disagree on their deadline. The app labels this **REQUIRES VERIFICATION / À VÉRIFIER**, quotes both, and does not automatically select one. The BOAMP screen flags `RECTIFICATIF`, linked notices and unavailable deadline data. None of this substitutes for human review of the official notice.
