"""Explicit user consent for outbound xAI Grok calls."""
import streamlit as st
from core.grok import grok_settings


def allow_xai(key):
    settings = grok_settings()
    st.caption(f"Fournisseur : xAI Grok · Modèle : {settings['model']} · envoi externe uniquement au clic")
    if not settings["api_key"]:
        st.info("Renseignez XAI_API_KEY dans le fichier .env à la racine ; ne partagez pas votre clé.")
    consent = st.checkbox("J'autorise explicitement l'envoi des extraits de ce dossier à xAI (service externe).", key=key)
    return bool(settings["api_key"]) and consent
