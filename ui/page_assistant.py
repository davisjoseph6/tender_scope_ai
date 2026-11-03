import streamlit as st

from core.search import search_passages
from core.llm import LLMError, RateLimitError, answer_question
from core.grok import GrokError, answer_question_grok
from ui.xai_controls import allow_xai
from ui.ai_controls import allow_request, remember_rate_limit


def render():
    st.title("Assistant IA")
    st.write("Retrouvez les passages de vos documents à partir d’une question ou de mots-clés.")
    pages = st.session_state.get("pages", [])
    if not pages:
        st.info("Chargez un dossier dans Mes appels d’offres pour commencer.")
        return
    query = st.text_input("Que souhaitez-vous retrouver ?", placeholder="Ex. chiffre d’affaires, ISO 27001, pénalités…", key="assistant_query")
    mode = st.radio("Mode de réponse", ["Recherche locale", "Groq + RAG BM25", "Grok (xAI) + RAG BM25"], horizontal=True)
    if mode == "Groq + RAG BM25":
        st.badge("RAG lexical BM25 + Groq", color="blue")
        enabled = allow_request("consent_question")
        if st.button("Poser la question à Groq", type="primary", disabled=not enabled or not query.strip()):
            try:
                with st.spinner("Recherche des sources puis réponse Groq…"):
                    result = answer_question(pages, query)
                st.session_state["ai_answer"] = {"question": query, **result}
            except RateLimitError as error:
                remember_rate_limit(error)
                st.warning(str(error))
            except LLMError as error:
                st.error(str(error))
        answer = st.session_state.get("ai_answer")
        if answer and answer["question"] == query:
            st.caption(answer["mode"] + " · " + answer["status"])
            st.text(answer["answer"])
            for citation in answer["citations"]:
                with st.container(border=True):
                    st.caption(f"{citation['document']} · page {citation['page']}")
                    st.text(citation["quote"])
            st.caption("Réponse limitée aux passages retrouvés. Vérifiez la pertinence des citations avant toute décision.")
        return
    if mode == "Grok (xAI) + RAG BM25":
        st.badge("xAI Grok + BM25", color="blue")
        enabled = allow_xai("consent_grok_question")
        if st.button("Poser la question à Grok (xAI)", type="primary", disabled=not enabled or not query.strip()):
            try:
                with st.spinner("Grok : sélection des sources puis génération..."):
                    result = answer_question_grok(pages, query)
                st.session_state["grok_answer"] = {"question": query, **result}
            except GrokError as error:
                st.error(str(error))
            except LLMError as error:
                st.error(str(error))
        answer = st.session_state.get("grok_answer")
        if answer and answer.get("question") == query:
            st.caption(answer["mode"] + " · " + answer["status"])
            st.text(answer["answer"])
            for citation in answer["citations"]:
                st.caption(f"{citation['document']} · page {citation['page']}")
                st.text(citation["quote"])
            st.warning("Interprétation à vérifier humainement, même quand les citations existent.")
        return
    st.badge("Recherche lexicale · Aucun appel LLM", color="blue")
    st.caption("Les résultats sont des extraits exacts classés par mots communs. Aucune réponse générée, interprétation ou vérification exhaustive n’est effectuée.")
    if query:
        results = search_passages(pages, query)
        if not results:
            st.info("Aucun passage trouvé avec ces termes. Essayez d’autres mots-clés et vérifiez les documents officiels.")
        for result in results:
            with st.container(border=True):
                st.caption(f"{result['document']} · page {result['page']}")
                st.text(result["quote"])
