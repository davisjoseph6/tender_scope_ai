import streamlit as st
import time
import math

from core.llm import settings


def allow_request(key):
    config = settings()
    st.caption(f"Modèle : {config['model']} · Appel uniquement au clic sur le bouton")
    if not config["api_key"]:
        st.info("Configurez GROQ_API_KEY dans .env à la racine du projet. Ne collez pas la clé dans le chat.")
    consent = st.checkbox("J’autorise l’envoi du texte nécessaire de ce dossier à Groq pour cette analyse.", key=key)
    remaining = max(0, math.ceil(st.session_state.get("groq_retry_at", 0) - time.time()))
    if remaining:
        st.warning(f"Pause Groq : réessayez dans {remaining} seconde(s). Aucun nouvel appel ne sera envoyé pendant cette pause.")
        st.button("Actualiser le délai", key=key + "_refresh")
    return bool(config["api_key"]) and consent and not remaining


def remember_rate_limit(error):
    st.session_state["groq_retry_at"] = time.time() + error.retry_after
