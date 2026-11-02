"""A BOAMP-only, read-only demo with no buyer-portal access."""
import json
import streamlit as st
from core.boamp import BOAMPError, get_notice, notice_evidence, notice_as_pages
from ui.workspace import archive_loaded_dossier


def render():
    st.title("Avis publics BOAMP — accès ouvert")
    st.write("Recherche par identifiant d'avis BOAMP, sans connexion à un profil acheteur.")
    st.caption("Source : DILA / BOAMP, API OpenDataSoft. Aucune récupération de DCE protégé.")
    idweb = st.text_input("Identifiant de l'avis BOAMP", value="26-106035",
                          help="Exemple public du 2 novembre 2026 ; disponibilité et contenu à vérifier en direct.")
    if st.button("Lire cet avis BOAMP", type="primary"):
        try:
            st.session_state["boamp_notice"] = get_notice(idweb)
        except BOAMPError as error:
            st.session_state.pop("boamp_notice", None)
            st.error(str(error))
    row = st.session_state.get("boamp_notice")
    if not row or row.get("idweb") != idweb.strip():
        st.info("Le dossier fictif reste disponible sur la page « Prototype local » sans réseau.")
        return
    st.subheader(row.get("objet") or "Objet non disponible")
    st.link_button("Consulter l'avis officiel", row["source_url"])
    st.info("Information issue de l'avis seulement : le RC, le CCTP et les pièces privées ne sont pas supposés accessibles.")
    if row["requires_verification"]:
        st.error("REQUIRES VERIFICATION / À VÉRIFIER — rectificatif, avis lié ou échéance absente : vérifier la dernière version officielle avant toute décision.")
    else:
        st.warning("Date et conditions à vérifier dans la dernière version officielle, même si aucun rectificatif n'est identifié ici.")
    st.subheader("Champs extraits avec provenance")
    for item in notice_evidence(row):
        with st.container(border=True):
            st.markdown("**" + item["field"] + "**")
            st.write(item["value"])
            st.caption("BOAMP · " + item["idweb"] + " · champ API : " + item["field"])
    st.download_button("Exporter les champs et leur provenance",
        json.dumps({"notice": row, "fields": notice_evidence(row), "human_review_required": True},
                   ensure_ascii=False, indent=2), "avis_boamp.json", "application/json")

    st.divider()
    st.caption("Pour expérimenter le RAG sur des avis réellement publics, vous pouvez importer ces champs API dans le dossier courant. Il s'agit d'une page **virtuelle** construite à partir de champs BOAMP, pas du texte complet d'un RC.")
    if st.button("Ouvrir les champs BOAMP pour la recherche locale"):
        pages = notice_as_pages(row)
        archive_loaded_dossier(pages, [(0, pages[0]["document"], pages)], "BOAMP " + row["idweb"])
        st.success("Avis ajouté comme fiche API avec provenance. Ouvrez « Prototype local » pour rechercher ou « Assistant IA » pour poser des questions.")
