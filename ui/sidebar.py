import streamlit as st
from core.llm import settings


def render_sidebar():
    options = ["Tableau de bord", "Mes appels d’offres", "Analyse intelligente", "Profil entreprise", "Décision Bid/No-Bid", "Assistant IA"]
    previous = st.session_state.get("navigation", options[0])
    migrated = {"Dossier": "Mes appels d’offres", "Points clés": "Analyse intelligente", "Décision": "Décision Bid/No-Bid"}.get(previous, previous)
    if migrated not in options:
        migrated = options[0]
    if previous != migrated:
        st.session_state["navigation"] = migrated
    with st.sidebar:
        st.markdown("### :material/fact_check: Bid/No-Bid\nCopilot")
        st.caption("L’espace de préparation de vos candidatures")
        st.divider()
        page = st.radio("Espace de travail", options, key="navigation")
        st.divider()
        config = settings()
        st.badge("Groq configuré" if config["api_key"] else "Mode local · Groq à configurer", color="blue")
        checkpoint = st.session_state.get("ai_checkpoint")
        st.caption("Extraction IA effectuée" if st.session_state.get("ai_extraction") else f"Extraction IA en pause · {checkpoint['next_chunk']}/{checkpoint['total_chunks']} fragments" if checkpoint else "Extraction IA non exécutée sur ce dossier")
        st.caption("Dossier actif : " + st.session_state.get("dossier_name", "aucun"))
        st.caption(":material/lock: Import local · Envoi Groq sur demande")
        st.caption("Version 0.4 · Groq et RAG lexical")
    return page
