import json

import streamlit as st

from core.pdf_reader import extract_pages
from core.doc_types import detect_doc_type
from ui.workspace import FIELDS, activate, archive_loaded_dossier, clear_widgets, new_dossier


def render():
    st.caption("ESPACE PME / MARCHÉS PUBLICS")
    heading, action = st.columns([4, 1], vertical_alignment="center")
    heading.title("Mes appels d’offres")
    action.button("Nouvelle analyse", icon=":material/add:", on_click=new_dossier)
    st.caption("Dossiers conservés pendant la session uniquement. Exportez vos résultats pour les garder.")
    name = st.text_input("Nom du nouveau dossier", placeholder="Ex. Maintenance informatique — Ville de Lyon")
    left, right = st.columns([2, 1], gap="large")
    with left:
        with st.container(border=True):
            st.subheader(":material/upload_file: Ajoutez votre dossier")
            st.write("Importez plusieurs documents d’un même appel d’offres.")
            files = st.file_uploader(
                "Documents PDF", type=["pdf"], accept_multiple_files=True,
                help="Avis BOAMP, règlement de consultation, CCTP et autres pièces du DCE.",
            )
            st.caption("Import local. Les appels Groq se déclenchent séparément dans les écrans d’analyse.")
    with right:
        with st.container(border=True):
            st.markdown("#### Préparer l’analyse")
            st.badge("Import local · Aucun appel LLM", color="blue")
            st.markdown("**Avis BOAMP** · Vue d’ensemble du marché\n\n**RC** · Règles et modalités de candidature\n\n**CCTP** · Besoins et spécifications techniques")
            st.caption("Privilégiez les PDF avec du texte sélectionnable. L’OCR des scans sera ajouté ultérieurement.")

    if st.button("Charger ces documents", type="primary", disabled=not files):
        all_pages = []
        documents = []
        for index, uploaded in enumerate(files or []):
            try:
                with st.spinner(f"Lecture de {uploaded.name}…"):
                    pages = extract_pages(uploaded.getvalue(), uploaded.name)
                documents.append((index, uploaded.name, pages))
                all_pages.extend(pages)
            except Exception:
                st.error(f"{uploaded.name} : PDF illisible ou protégé par mot de passe.")
        if documents:
            archive_loaded_dossier(all_pages, documents, name.strip() or documents[0][1])
            st.success("Dossier chargé. Consultez Analyse intelligente pour retrouver les passages clés.")
        else:
            st.warning("Aucun PDF lisible : le dossier actif a été conservé.")
    history = st.session_state.get("dossiers", {})
    loaded = {key: d for key, d in history.items() if d.get("documents")}
    if loaded:
        with st.expander(f"Historique de session · {len(loaded)} dossier(s)"):
            identifiers = list(loaded)
            identifier = st.selectbox("Dossier à ouvrir", identifiers, format_func=lambda key: loaded[key]["dossier_name"])
            if st.button("Ouvrir ce dossier"):
                activate(identifier)
                st.rerun()
    all_pages = st.session_state.get("pages", [])
    documents = st.session_state.get("documents", [])

    empty = [p for p in all_pages if not p["text"].strip()]
    st.subheader("Votre dossier en un regard")
    cols = st.columns(3)
    cols[0].metric("Documents lus", len(documents), border=True)
    cols[1].metric("Pages extraites", len(all_pages), border=True)
    cols[2].metric("Pages sans texte", len(empty), border=True)

    if not documents:
        with st.container(border=True):
            st.markdown("#### :material/folder_open: Votre dossier est prêt à accueillir ses documents")
            st.write("Commencez par ajouter le règlement de consultation. Vous pourrez ensuite parcourir les pages et télécharger le texte avec ses sources.")
    else:
        st.subheader(":material/menu_book: Consultez les documents")
        if st.button("Vider le dossier"):
            active = st.session_state.pop("active_dossier", None)
            st.session_state.get("dossiers", {}).pop(active, None)
            clear_widgets()
            for key in list(st.session_state):
                if key in FIELDS:
                    del st.session_state[key]
            st.rerun()
        if empty:
            st.warning("Certaines pages n’ont pas de texte extrait. Vérifiez si elles sont blanches ou si elles nécessitent un OCR.")
        for index, name, pages in documents:
            with st.expander(f"{name} · {detect_doc_type(name, chr(10).join(p['text'] for p in pages))} · {len(pages)} page(s)", expanded=len(documents) == 1):
                if not pages:
                    st.warning("Ce document ne contient aucune page.")
                    continue
                missing = [str(p["page"]) for p in pages if not p["text"].strip()]
                if missing:
                    st.caption("Pages sans texte : " + ", ".join(missing))
                selected = st.selectbox("Page à consulter", range(1, len(pages) + 1), key=f"page_{index}")
                st.caption(f"Source : {name} · page {selected}")
                with st.container(height=350, border=True):
                    st.text(pages[selected - 1]["text"] or "Aucun texte extrait.")
        if all_pages:
            st.download_button(
                "Exporter le texte et ses sources", json.dumps(all_pages, ensure_ascii=False, indent=2),
                file_name="documents_extraits.json", mime="application/json",
                icon=":material/download:", type="primary",
            )
