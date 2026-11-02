import json

import streamlit as st

from core.scoring import STATUSES, score_requirements


def render():
    st.title("Décision Bid/No-Bid")
    st.badge("Checklist humaine · Aucun verdict LLM", color="blue")
    st.write("Construisez une checklist à partir des pièces officielles et comparez-la aux capacités de votre PME.")
    if not st.session_state.get("pages"):
        st.info("Importez d’abord vos documents dans Mes appels d’offres.")
        return
    profile = st.session_state.get("company_profile", {})
    if profile:
        with st.expander("Profil entreprise de référence"):
            st.write(f"{profile['name']} · CA {profile['turnover']:,} € · {profile['staff']} salarié(s)")
            st.write("Certifications : " + (", ".join(profile["certifications"]) or "Non renseignées"))
    st.caption("Décision fondée sur vos vérifications manuelles. L’extraction Groq est disponible dans Analyse intelligente ; la comparaison automatique au profil reste à développer.")
    with st.form("add_requirement", clear_on_submit=True):
        label = st.text_input("Exigence à vérifier")
        source = st.text_input("Source (document, page et citation)")
        mandatory = st.checkbox("Exigence obligatoire", value=True)
        if st.form_submit_button("Ajouter à la checklist"):
            if label.strip() and source.strip():
                st.session_state.setdefault("requirements", []).append({
                    "label": label.strip(), "source": source.strip(), "mandatory": mandatory, "status": "À vérifier",
                })
                st.session_state["review_complete"] = False
                st.session_state.pop("_review_complete", None)
            else:
                st.warning("Renseignez l’exigence et sa source.")
    requirements = st.session_state.setdefault("requirements", [])
    for index, item in enumerate(requirements):
        with st.container(border=True):
            st.markdown(f"**{item['label']}**")
            st.text(item["source"])
            st.caption("Obligatoire" if item["mandatory"] else "Non obligatoire")
            item["status"] = st.selectbox("Résultat de la vérification", STATUSES, index=STATUSES.index(item["status"]), key=f"status_{index}")
    complete = st.checkbox(
        "J’ai relu l’intégralité des pièces officielles, vérifié l’échéance et confirmé que cette checklist couvre toutes les exigences applicables.",
        value=st.session_state.get("review_complete", False), key="_review_complete",
    )
    st.session_state["review_complete"] = complete
    result = score_requirements(requirements, review_complete=complete)
    display = {"Go": st.success, "No-Go": st.error, "À vérifier": st.warning}[result["verdict"]]
    display(f"{result['verdict']} — {result['reason']}")
    if requirements:
        st.download_button("Exporter la checklist et la décision", json.dumps({"requirements": requirements, "review_complete": complete, **result}, ensure_ascii=False, indent=2), "decision.json", "application/json")
