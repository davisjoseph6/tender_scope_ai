import json

import streamlit as st


def render():
    st.title("Profil entreprise")
    st.write("Centralisez les capacités de votre PME pour préparer vos vérifications.")
    profile = st.session_state.get("company_profile", {})
    with st.form("company_profile_form"):
        name = st.text_input("Nom de l’entreprise", value=profile.get("name", ""))
        a, b = st.columns(2)
        turnover = a.number_input("Chiffre d’affaires annuel (€)", min_value=0, value=profile.get("turnover", 0), step=10000)
        year = b.text_input("Exercice de référence", value=profile.get("year", ""), placeholder="Ex. 2025")
        staff = st.number_input("Effectif", min_value=0, value=profile.get("staff", 0))
        certifications = st.text_area("Certifications (une par ligne)", value="\n".join(profile.get("certifications", [])))
        skills = st.text_area("Compétences (une par ligne)", value="\n".join(profile.get("skills", [])))
        references = st.text_area("Références de projets", value=profile.get("references", ""))
        if st.form_submit_button("Enregistrer le profil", type="primary"):
            profile = {"name": name, "turnover": turnover, "year": year, "staff": staff,
                       "certifications": [s.strip() for s in certifications.splitlines() if s.strip()],
                       "skills": [s.strip() for s in skills.splitlines() if s.strip()], "references": references}
            st.session_state["company_profile"] = profile
            st.success("Profil enregistré pour cette session.")
    st.caption("Le profil reste en session. La comparaison automatique aux exigences n’est pas encore activée.")
    if profile:
        st.download_button("Exporter le profil", json.dumps(profile, ensure_ascii=False, indent=2), "profil_entreprise.json", "application/json")
