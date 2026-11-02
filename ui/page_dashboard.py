import streamlit as st

from core.extraction import extract_key_info
from core.scoring import score_requirements
from ui.workspace import new_dossier


def render():
    st.caption("VUE D’ENSEMBLE / ESPACE PME")
    title, action = st.columns([4, 1], vertical_alignment="center")
    title.title("Analysez vos appels d’offres avec l’IA")
    action.button("Nouvelle analyse", type="primary", icon=":material/add:", on_click=new_dossier)
    st.write("De vos documents à une décision de candidature documentée.")
    st.caption("Règles locales · Extraction Groq et RAG BM25 disponibles sur demande · Décision humaine")
    dossiers = [d for d in st.session_state.get("dossiers", {}).values() if d.get("documents")]
    verdicts = [score_requirements(d.get("requirements", []), review_complete=d.get("review_complete", False))["verdict"] for d in dossiers]
    cols = st.columns(4)
    cols[0].metric("Dossiers chargés", len(dossiers), border=True)
    cols[1].metric("Go validés manuellement", verdicts.count("Go"), border=True)
    cols[2].metric("Dossiers No-Go", verdicts.count("No-Go"), border=True)
    cols[3].metric("Revues à terminer", verdicts.count("À vérifier"), border=True)
    main, progress = st.columns([2, 1], gap="large")
    with main:
        with st.container(border=True):
            st.subheader("Vos dossiers récents")
            if not dossiers:
                st.write("Votre espace est prêt. Créez une analyse, puis ajoutez les PDF du marché.")
                st.button("Importer un premier dossier", on_click=new_dossier)
            for dossier in reversed(dossiers[-5:]):
                result = score_requirements(dossier.get("requirements", []), review_complete=dossier.get("review_complete", False))
                st.markdown(f"**{dossier.get('dossier_name', 'Appel d’offres')}**")
                st.caption(f"{len(dossier['documents'])} document(s) · {len(dossier.get('pages', []))} page(s) · {result['verdict']}")
        with st.container(border=True):
            st.subheader("Échéances à vérifier")
            candidates = [f for f in extract_key_info(st.session_state.get("pages", [])) if f["category"] == "Date limite"]
            if not candidates:
                st.caption("Aucune échéance repérée dans le dossier actif. Consultez le RC pour la confirmer.")
            for finding in candidates[:3]:
                st.text(finding["quote"])
                st.caption(f"{finding['document']} · page {finding['page']} · date non validée")
    with progress:
        with st.container(border=True):
            st.subheader("Avancement du dossier actif")
            pages = st.session_state.get("pages", [])
            requirements = st.session_state.get("requirements", [])
            flags = [bool(pages), bool(requirements), bool(requirements) and bool(st.session_state.get("review_complete"))]
            st.progress(sum(flags) / 3)
            for label, done in zip(["Documents chargés", "Checklist renseignée", "Revue humaine confirmée"], flags):
                st.write((":material/check_circle: " if done else ":material/radio_button_unchecked: ") + label)
            st.divider()
            st.caption("Extraction Groq : " + ("effectuée" if st.session_state.get("ai_extraction") else "non exécutée"))
            st.caption("Question RAG : " + ("résultat disponible" if st.session_state.get("ai_answer") else "non exécutée"))
            st.caption("Historique limité à la session. Téléchargez vos exports pour les conserver.")
