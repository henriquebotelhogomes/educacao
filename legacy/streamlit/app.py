import os
import tempfile
from pathlib import Path

# --- CORREÇÃO PARA O ERRO [WinError 1314] NO WINDOWS ---
# Isto impede o Hugging Face de tentar criar Symbolic Links (atalhos) que exigem permissões de Administrador.
# TEM de estar no topo do ficheiro, antes das importações pesadas.
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

from dotenv import load_dotenv
import streamlit as st
from docx import Document

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_docling import DoclingLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import create_retriever_tool

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()

st.set_page_config(
    page_title="Tutor Inteligente IA",
    page_icon="🎓",
    layout="wide"
)

# Estilização
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# Inicialização de variáveis de sessão
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "retriever" not in st.session_state:
    st.session_state.retriever = None


# --- LÓGICA DE NEGÓCIO ---

def get_llm():
    """Inicializa o modelo de linguagem via Groq."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("Chave GROQ_API_KEY não encontrada no ficheiro .env")
        return None
    return ChatGroq(model="llama-3.3-70b-versatile", api_key=api_key, temperature=0.5)


def process_document(uploaded_files):
    """Processa múltiplos documentos usando Docling e armazena no Qdrant."""
    tmp_paths = []

    # Guarda todos os ficheiros carregados em ficheiros temporários
    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_paths.append(tmp.name)

    try:
        docs = []
        # Carregamento inteligente com Docling para cada ficheiro
        for tmp_path in tmp_paths:
            loader = DoclingLoader(file_path=[tmp_path])
            docs.extend(loader.load())

        # Divisão do texto mantendo o sentido das frases
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        splits = text_splitter.split_documents(docs)

        # Embeddings (agora sem o erro de symlink)
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # Armazenamento vetorial na Qdrant Cloud
        vectorstore = QdrantVectorStore.from_documents(
            documents=splits,
            embedding=embeddings,
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
            collection_name="educacao_rag",
            force_recreate=True
        )

        st.session_state.retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        return True
    except Exception as e:
        st.error(f"Erro no processamento dos documentos: {e}")
        return False
    finally:
        # Limpa todos os ficheiros temporários
        for tmp_path in tmp_paths:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


# --- INTERFACE DO UTILIZADOR ---

def main():
    st.title("🎓 Sistema Educacional IA: Tutor Profissional")

    tabs = st.tabs(["📝 Gerador de Exercícios", "📚 Treinar Tutor (RAG)", "🤖 Chat com Tutor"])

    # ABA 1: GERADOR
    with tabs[0]:
        st.header("Criação de Material Didático")
        materia = st.text_input("Disciplina", "Ciências")
        if st.button("Gerar Lista de Exercícios"):
            llm = get_llm()
            if llm:
                with st.spinner("A IA está a redigir as questões..."):
                    res = llm.invoke(
                        f"Gere 5 exercícios de múltipla escolha sobre {materia}. Inclua o gabarito no final.")

                    doc = Document()
                    doc.add_heading(f'Exercícios: {materia}', 0)
                    doc.add_paragraph(res.content)

                    path = f"exercicios_{materia.lower()}.docx"
                    doc.save(path)

                    st.success("Documento gerado com sucesso!")
                    with open(path, "rb") as f:
                        st.download_button("Descarregar Ficheiro Word", f, file_name=path)

    # ABA 2: TREINAMENTO
    with tabs[1]:
        st.header("Alimentar Base de Conhecimento")
        # Alterado para aceitar múltiplos ficheiros PDF
        files = st.file_uploader("Carregar PDFs para o Tutor", type="pdf", accept_multiple_files=True)

        if files and st.button("Sincronizar Conhecimento"):
            with st.spinner("A analisar os PDFs... A primeira vez pode demorar para descarregar os modelos de visão."):
                if process_document(files):
                    st.success(f"Base de dados atualizada com sucesso! ({len(files)} ficheiro(s) processado(s))")

    # ABA 3: CHAT/AGENTE
    with tabs[2]:
        st.header("Atendimento ao Aluno")
        if st.session_state.retriever is None:
            st.warning(
                "⚠️ O Tutor ainda não possui documentos específicos na memória. Carregue PDFs na aba 'Treinar Tutor'.")

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Tire a sua dúvida aqui..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                llm = get_llm()
                if llm:
                    tools = []
                    if st.session_state.retriever:
                        tools.append(create_retriever_tool(
                            st.session_state.retriever,
                            "consultar_biblioteca",
                            "Busque nos PDFs enviados para responder a perguntas específicas."
                        ))

                    agent_prompt = ChatPromptTemplate.from_messages([
                        ("system",
                         "É um tutor amigável e académico. Use as ferramentas de busca para garantir a precisão dos factos."),
                        MessagesPlaceholder(variable_name="chat_history"),
                        ("human", "{input}"),
                        MessagesPlaceholder(variable_name="agent_scratchpad"),
                    ])

                    try:
                        agent = create_tool_calling_agent(llm, tools, agent_prompt)
                        exec = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
                        response = exec.invoke({"input": prompt, "chat_history": st.session_state.chat_history[:-1]})
                        st.markdown(response["output"])
                        st.session_state.chat_history.append({"role": "assistant", "content": response["output"]})
                    except Exception as e:
                        st.error(f"Erro no processamento do Agente: {e}")


if __name__ == "__main__":
    main()