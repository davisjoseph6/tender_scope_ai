import streamlit as st

from ui import page_assistant, page_dashboard, page_decision, page_dossier, page_points_cles, page_profile, page_local_demo
from ui.sidebar import render_sidebar
from ui.styles import inject_css
from ui.workspace import save_active

st.set_page_config(page_title="Bid/No-Bid Copilot", page_icon=":material/fact_check:", layout="wide")
inject_css()
save_active()
page = render_sidebar()
# Compatibilité avec les modules de navigation d’une session déjà ouverte.
page = {"Dossier": "Mes appels d’offres", "Points clés": "Analyse intelligente", "Décision": "Décision Bid/No-Bid"}.get(page, page)
routes = {
    "Tableau de bord": page_dashboard,
    "Mes appels d’offres": page_dossier,
    "Analyse intelligente": page_points_cles,
    "Profil entreprise": page_profile,
    "Décision Bid/No-Bid": page_decision,
    "Assistant IA": page_assistant,
    "Prototype local": page_local_demo,
}
routes.get(page, page_dashboard).render()
save_active()
