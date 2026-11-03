"""Dossiers conservés uniquement dans la session du navigateur."""
from copy import deepcopy
from uuid import uuid4

import streamlit as st

DEFAULTS = {"pages": [], "documents": [], "requirements": [], "review_complete": False,
            "dossier_name": "Dossier sans nom", "ai_extraction": None, "ai_answer": None, "ai_checkpoint": None,
            "ollama_extraction": None, "ollama_checkpoint": None}
FIELDS = tuple(DEFAULTS)


def save_active():
    active = st.session_state.get("active_dossier")
    if active:
        st.session_state.setdefault("dossiers", {})[active] = {
            key: deepcopy(st.session_state.get(key, DEFAULTS[key]))
            for key in FIELDS
        }


def clear_widgets():
    for key in list(st.session_state):
        if key.startswith(("status_", "page_", "consent_")) or key in ("assistant_query", "_review_complete"):
            del st.session_state[key]


def new_dossier():
    save_active()
    clear_widgets()
    st.session_state["active_dossier"] = uuid4().hex
    for key in FIELDS:
        st.session_state.pop(key, None)
    st.session_state["dossier_name"] = "Nouvel appel d’offres"
    st.session_state["navigation"] = "Mes appels d’offres"


def activate(identifier):
    save_active()
    clear_widgets()
    st.session_state["active_dossier"] = identifier
    for key in FIELDS:
        st.session_state.pop(key, None)
    for key, value in st.session_state["dossiers"][identifier].items():
        st.session_state[key] = deepcopy(value)


def archive_loaded_dossier(pages, documents, name):
    save_active()
    clear_widgets()
    st.session_state.update({
        "active_dossier": uuid4().hex, "pages": pages, "documents": documents,
        "requirements": [], "review_complete": False, "dossier_name": name,
        "ai_extraction": None, "ai_answer": None,
        "ai_checkpoint": None, "ollama_extraction": None, "ollama_checkpoint": None,
    })
    save_active()
