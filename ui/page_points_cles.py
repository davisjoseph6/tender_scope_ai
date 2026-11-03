import json

import streamlit as st

from core.extraction import RULES, extract_key_info
from core.llm import LLMError, RateLimitError, extract_requirements
from core.local_llm import LocalModelError
from core.ollama_extraction import extract_requirements_ollama
from ui.ai_controls import allow_request, remember_rate_limit


def render_llm(pages):
    st.badge("Groq · Extraction structurée", color="blue")
    st.caption("Les pages avec texte sont découpées en fragments. Les citations sont vérifiées automatiquement ; leur interprétation reste à relire.")
    enabled = allow_request("consent_extraction")
    checkpoint = st.session_state.get("ai_checkpoint")
    if checkpoint:
        st.caption(f"Extraction en attente : {checkpoint['next_chunk']}/{checkpoint['total_chunks']} fragments traités. Le bouton reprend les lots restants si le dossier et le modèle sont identiques.")
    if st.button("Extraire les exigences avec Groq", type="primary", disabled=not enabled):
        try:
            progress = st.progress(checkpoint["next_chunk"] / checkpoint["total_chunks"] if checkpoint else 0, text="Reprise de l’extraction" if checkpoint else "Préparation de l’extraction")
            def save_progress(state):
                st.session_state["ai_checkpoint"] = state
                progress.progress(state["next_chunk"] / state["total_chunks"], text=f"{state['next_chunk']}/{state['total_chunks']} fragments traités")
            with st.spinner("Extraction structurée en cours…"):
                result = extract_requirements(pages, checkpoint=checkpoint, on_progress=save_progress)
            st.session_state["ai_extraction"] = result
            st.session_state["ai_checkpoint"] = None
            st.success("Extraction terminée ; les citations affichées ont été retrouvées dans les fragments transmis.")
        except RateLimitError as error:
            remember_rate_limit(error)
            st.warning(str(error))
        except LLMError as error:
            st.error(str(error))
    result = st.session_state.get("ai_extraction")
    if not result:
        saved = st.session_state.get("ai_checkpoint")
        if saved:
            st.info(f"Analyse incomplète : {saved['next_chunk']}/{saved['total_chunks']} fragments sauvegardés. Les exigences déjà sourcées sont exportables ci-dessous.")
            st.download_button("Exporter les résultats partiels", json.dumps({"complete": False, "chunks_processed": saved["next_chunk"], "total_chunks": saved["total_chunks"], "requirements": saved["findings"], "rejected_requirements": saved["rejected"]}, ensure_ascii=False, indent=2), "extraction_partielle.json", "application/json")
        else:
            st.info("Aucune extraction IA complète enregistrée pour ce dossier.")
        return
    st.caption(f"Dernier résultat · {result['model']} · {result['chunks_processed']} fragments traités")
    if result.get("rejected_requirements", 0):
        st.warning(f"Extraction partielle : {result['rejected_requirements']} proposition(s) écartée(s) car leurs citations ne sont pas vérifiables. Seules les exigences avec citations retrouvées sont affichées.")
    if result["pages_without_text"]:
        st.warning(f"{result['pages_without_text']} page(s) sans texte : contenu non analysé, OCR nécessaire si elles sont scannées.")
    st.warning("Les citations exactes ne garantissent ni l’exhaustivité ni la justesse du résumé. La comparaison automatique au profil n’est pas encore activée.")
    if not result["requirements"]:
        st.info("Aucune exigence extraite. Cela ne prouve pas l’absence d’exigences.")
    for item in result["requirements"]:
        with st.container(border=True):
            st.markdown(f"**{item['category']}** · Obligatoire : {item['mandatory']}")
            st.text(item["summary"])
            for citation in item["citations"]:
                st.caption(f"{citation['document']} · page {citation['page']}")
                st.text(citation["quote"])
    st.download_button("Exporter l’extraction IA", json.dumps(result, ensure_ascii=False, indent=2), "extraction_ia.json", "application/json")


def render_ollama(pages):
    st.badge("Ollama · extraction locale", color="blue")
    st.caption("Utilise qwen2.5:7b par défaut, sur votre ordinateur. Aucun texte transmis à Groq. Vérifiez chaque résumé, les dates et les sources.")
    checkpoint = st.session_state.get("ollama_checkpoint")
    if checkpoint:
        st.caption(f"Reprise disponible : {checkpoint['next_chunk']}/{checkpoint['total_chunks']} fragments.")
    if st.button("Extraire localement avec Ollama", type="primary"):
        try:
            progress = st.progress(0, text="Extraction locale")
            def save_progress(state):
                st.session_state["ollama_checkpoint"] = state
                progress.progress(state["next_chunk"] / state["total_chunks"],
                                  text=f"{state['next_chunk']}/{state['total_chunks']} fragments")
            with st.spinner("Ollama : extraction et vérification des citations..."):
                result = extract_requirements_ollama(pages, checkpoint=checkpoint, on_progress=save_progress)
            st.session_state["ollama_extraction"] = result
            st.session_state["ollama_checkpoint"] = None
            st.success("Extraction locale terminée : contrôle de présence des citations effectué.")
        except (LocalModelError, LLMError) as error:
            st.error(str(error))
        except Exception:
            st.error("Erreur inattendue durant l'extraction locale ; consulter les logs de Streamlit.")
    result = st.session_state.get("ollama_extraction")
    if not result:
        partial = st.session_state.get("ollama_checkpoint")
        if partial:
            st.warning(f"Analyse incomplète : {partial['next_chunk']}/{partial['total_chunks']}. Relancez pour reprendre.")
            st.download_button("Exporter les résultats partiels Ollama",
                json.dumps({"complete": False, **partial}, ensure_ascii=False, indent=2),
                "ollama_partiel.json", "application/json")
        else:
            st.info("Pas encore d'extraction Ollama enregistrée.")
        return
    st.caption(f"Modèle {result['model']} · {result['chunks_processed']} fragments traités")
    if result["rejected_requirements"]:
        st.warning(f"{result['rejected_requirements']} proposition(s) rejetée(s) pour citations introuvables.")
    if result["pages_without_text"]:
        st.warning(f"{result['pages_without_text']} page(s) sans texte.")
    st.warning("REQUIRES VERIFICATION / À VÉRIFIER : preuve textuelle ≠ interprétation correcte, surtout pour les dates, négations et versions.")
    for item in result["requirements"]:
        with st.container(border=True):
            st.markdown(f"**{item['category']}** · Obligatoire : {item['mandatory']}")
            st.write(item["summary"])
            for citation in item["citations"]:
                st.caption(f"{citation['document']} · page {citation['page']}")
                st.text(citation["quote"])
    if not result["requirements"]:
        st.info("Aucune exigence retenue. Cela ne prouve pas l'absence d'exigences.")
    st.download_button("Exporter l'extraction Ollama",
        json.dumps(result, ensure_ascii=False, indent=2), "extraction_ollama.json", "application/json")



def render():
    st.title("Analyse intelligente")
    pages = st.session_state.get("pages", [])
    if not pages:
        st.info("Importez d’abord vos PDF dans Mes appels d’offres.")
        return
    mode = st.radio("Moteur d’extraction", ["Règles locales", "Groq · IA", "Ollama · local"], horizontal=True)
    if mode == "Groq · IA":
        render_llm(pages)
        return
    if mode == "Ollama · local":
        render_ollama(pages)
        return
    st.badge("Extraction par règles · Aucun appel LLM", color="blue")
    st.warning("Repérage indicatif par mots-clés : vérifiez chaque passage dans le document officiel. Les négations et contradictions ne sont pas interprétées.")
    findings = extract_key_info(pages)
    category = st.selectbox("Catégorie", ["Toutes", *RULES])
    shown = [f for f in findings if category == "Toutes" or f["category"] == category]
    st.caption(f"{len(shown)} passage(s) repéré(s)")
    for finding in shown:
        with st.container(border=True):
            st.markdown(f"**{finding['category']}**")
            st.caption(f"{finding['document']} · page {finding['page']}")
            st.text(finding["quote"])
    absent = [c for c in RULES if not any(f["category"] == c for f in findings)]
    if absent:
        st.info("Aucun passage repéré pour : " + ", ".join(absent) + ". Cela ne prouve pas l’absence d’exigence.")
    st.download_button("Exporter les passages et leurs sources", json.dumps(findings, ensure_ascii=False, indent=2), "points_cles.json", "application/json")
