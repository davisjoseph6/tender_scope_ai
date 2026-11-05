"""Offline demonstrator: provenance, deadline conflicts, local retrieval and optional Ollama."""
import json
import hashlib
from pathlib import Path
import streamlit as st

from core.deadlines import deadline_candidates
from core.extraction import extract_key_info
from core.hybrid import HybridRetrievalError, retrieve_hybrid
from core.local_llm import LocalModelError, request_local_json
from core.llm import Answer, SYSTEM, LLMError, validate_citations
from core.rag import chunk_pages, retrieve
from ui.workspace import archive_loaded_dossier

DEMO = Path(__file__).resolve().parents[1] / "data" / "demo"


def load_demo():
    pages = [{"document": path.name, "page": 1, "text": path.read_text(encoding="utf-8")}
             for path in sorted(DEMO.glob("*_FICTIF.txt"))]
    archive_loaded_dossier(pages, [(i, p["document"], [p]) for i, p in enumerate(pages)],
                           "Démonstration fictive — maintenance informatique")


def render():
    st.title("Prototype local — TenderScope AI")
    st.caption("Démonstration reproductible, aucune action de candidature. Les données intégrées sont fictives.")
    if st.button("Charger le dossier fictif (3 documents)", type="primary"):
        load_demo()
        st.success("Trois documents fictifs chargés en mémoire.")
    pages = st.session_state.get("pages", [])
    if not pages:
        st.info("Chargez le dossier fictif ou importez vos PDF dans « Mes appels d’offres ».")
        return
    if any(not p["text"].strip() for p in pages):
        st.warning("Au moins une page n'a pas de texte : ce contenu n'a pas été analysé.")
    st.subheader("1. Échéances et contradictions potentielles")
    report = deadline_candidates(pages)
    if report["requires_review"]:
        st.error("REQUIRES VERIFICATION / À VÉRIFIER — " + report["warning"])
    else:
        st.warning("À vérifier — " + report["warning"])
    for item in report["candidates"]:
        with st.container(border=True):
            st.write(f"**{item['date']} {item['time'] or '(heure inconnue)'}**")
            st.caption(f"{item['document']} · page {item['page']}")
            st.text(item["quote"])
    st.caption("Les dates sont des candidates repérées automatiquement, pas un calendrier juridiquement validé.")
    st.subheader("2. Passages à vérifier et préparation de l'offre")
    results = extract_key_info(pages)
    st.write(f"{len(results)} passages trouvés par règles ; liste non exhaustive.")
    for result in results[:35]:
        with st.expander(f"{result['category']} · {result['document']} · page {result['page']}"):
            st.text(result["quote"])
    st.download_button("Exporter la checklist de revue (JSON)",
        json.dumps({"review_status": "human_verification_required", "candidate_deadlines": report,
                    "candidate_passages": results}, ensure_ascii=False, indent=2),
        "tenderscope_revue.json", "application/json")
    st.subheader("3. Question-réponse sourcée")
    query = st.text_input("Question sur le dossier", value="Quelle est la date limite de remise des offres ?", key="local_demo_question")
    method = st.radio("Recherche", ["BM25 hors ligne", "Hybrid BM25 + embeddings Ollama"], horizontal=True)
    chunks = chunk_pages(pages)
    fingerprint = hashlib.sha256(json.dumps(pages, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    if st.button("Rechercher les passages", disabled=not query.strip()):
        try:
            found = (retrieve_hybrid(chunks, query) if method.startswith("Hybrid") else retrieve(chunks, query))
            st.session_state["demo_retrieved"] = {"question": query, "method": method, "fingerprint": fingerprint, "chunks": found}
        except HybridRetrievalError as exc:
            st.error(str(exc))
    saved = st.session_state.get("demo_retrieved", {})
    if saved.get("question") == query and saved.get("method") == method and saved.get("fingerprint") == fingerprint:
        for chunk in saved["chunks"]:
            with st.expander(f"{chunk['document']} · page {chunk['page']} · {chunk['id']}"):
                st.text(chunk["text"])
        if not saved["chunks"]:
            st.info("Aucun fragment trouvé. Aucun résultat ne signifie pas absence d'exigence.")
        st.caption("Synthèse facultative : Ollama doit être installé et le modèle chargé sur votre ordinateur.")
        if st.button("Générer une réponse avec Ollama", disabled=not saved["chunks"]):
            try:
                result = request_local_json(Answer, SYSTEM,
                    "Réponds en français à la question suivante, seulement avec des citations exactes : " + query,
                    saved["chunks"])
                if result.status == "Réponse sourcée":
                    citations = validate_citations(result.citations, saved["chunks"])
                    st.session_state["demo_answer"] = {"question": query, "fingerprint": fingerprint, "answer": result.answer, "citations": citations}
                else:
                    st.session_state["demo_answer"] = {"question": query, "fingerprint": fingerprint,
                        "answer": "Information insuffisante : vérifier les documents officiels.", "citations": []}
            except (LocalModelError, LLMError) as exc:
                st.error(str(exc))
        answer = st.session_state.get("demo_answer", {})
        if answer.get("question") == query and answer.get("fingerprint") == fingerprint:
            st.write(answer["answer"])
            for citation in answer["citations"]:
                st.caption(f"{citation['document']} · page {citation['page']}")
                st.text(citation["quote"])
            st.warning("Citation textuellement vérifiée, interprétation et pertinence à contrôler humainement.")
