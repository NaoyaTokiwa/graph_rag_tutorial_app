import pandas as pd
import streamlit as st
from core.sample_data import SAMPLE_DOCUMENTS
from core.document_loader import load_documents
from core.chunker import chunk_documents
from core.rag import StandardRAG
from core.graphrag import GraphRAG
from core.config import settings


DEFAULT_QUESTIONS = [
    "製品Xの不良率上昇には、どの設備とどの担当者が関わっていますか。",
    "成形機M-12 に関する問題は、いつから兆候があり、最終的にどの対応が行われましたか。",
    "搬送ロボットR-3 の位置ずれは、どの現象や対応策と関係していますか。",
    "品質分析責任者、運用責任者、保全部門リーダーは、それぞれ何を担当しましたか。",
    "不良率上昇の原因と復旧策を、設備、症状、担当者の関係が分かるように説明してください。",
]


def resolve_documents(prefer_files: bool):
    loaded = load_documents("data") if prefer_files else []
    if loaded:
        return loaded, "data/ 配下のファイル"
    return SAMPLE_DOCUMENTS, "sample_data.py の組み込み文書"


def ensure_state():
    if "std" not in st.session_state:
        st.session_state.std = None
    if "graph" not in st.session_state:
        st.session_state.graph = None
    if "chunks" not in st.session_state:
        st.session_state.chunks = []


def render_standard_chunks(docs):
    for i, d in enumerate(docs, start=1):
        with st.container(border=True):
            st.markdown(f"### Chunk {i}")
            meta1, meta2, meta3 = st.columns(3)
            meta1.metric("Title", d.metadata['title'])
            meta2.metric("Chunk", d.metadata['chunk_index'])
            meta3.metric("Source", d.metadata['source'])
            st.write(d.page_content)


def parse_graph_context(raw: str):
    semantic, graph = raw, ""
    if "Graph Context:" in raw:
        parts = raw.split("Graph Context:", 1)
        semantic = parts[0].replace("Semantic Context:", "").strip()
        graph = parts[1].strip()
    chains = []
    for line in graph.splitlines():
        line = line.strip()
        if not line:
            continue
        chains.append(line)
    return semantic, chains


def render_graph_chains(raw: str):
    semantic, chains = parse_graph_context(raw)
    with st.container(border=True):
        st.markdown("### Semantic Seeds")
        st.code(semantic if semantic else "No semantic seed context")
    st.markdown("### Relationship Chains")
    if not chains:
        st.info("知識グラフ由来の関係チェーンがまだありません。先に『知識グラフを再構築』を実行してください。")
        return
    for idx, chain in enumerate(chains, start=1):
        with st.container(border=True):
            st.markdown(f"#### Chain {idx}")
            st.code(chain)


def run_app():
    st.set_page_config(page_title="GraphRAG Sample", layout="wide")
    st.title("GraphRAG vs Standard RAG Demo")
    st.caption("PoC-focused: PDF/Markdown loading + structured comparison UI + Neo4j GraphRAG")
    ensure_state()

    if not settings.openai_api_key:
        st.warning("OPENAI_API_KEY が未設定です。.env を作成して設定してください。")

    st.sidebar.header("データ設定")
    prefer_files = st.sidebar.toggle("data/ のPDF・Markdown・Textを優先", value=True)
    chunk_size = st.sidebar.slider("chunk_size", 100, 1200, 300, 50)
    chunk_overlap = st.sidebar.slider("chunk_overlap", 0, 300, 50, 10)

    docs, source_label = resolve_documents(prefer_files)
    chunks = chunk_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    st.session_state.chunks = chunks

    st.sidebar.markdown(f"**使用データ:** {source_label}")
    st.sidebar.metric("Documents", len(docs))
    st.sidebar.metric("Chunks", len(chunks))

    with st.expander("使い方", expanded=False):
        st.markdown(
            "1. `data/` に PDF / Markdown / Text を置くか、組み込みサンプルを使います。"
            "2. `比較エンジンを初期化` を押します。"
            "3. `知識グラフを再構築` を押して GraphRAG のグラフを作成します。"
            "4. 同じ質問を通常RAGとGraphRAGに投げて違いを比較します。"
        )

    controls1, controls2 = st.columns([1, 1])
    if controls1.button("比較エンジンを初期化", use_container_width=True):
        st.session_state.std = StandardRAG(chunks)
        st.session_state.graph = GraphRAG(chunks)
        st.success("通常RAG / GraphRAG を初期化しました。")
    if controls2.button("知識グラフを再構築", use_container_width=True):
        if st.session_state.graph is None:
            st.session_state.graph = GraphRAG(chunks)
        graph_docs = st.session_state.graph.refresh_graph()
        st.success(f"知識グラフを再構築しました。graph documents: {len(graph_docs)}")

    st.subheader("質問入力")
    selected = st.selectbox("サンプル質問", DEFAULT_QUESTIONS)
    question = st.text_input("自由入力", value=selected)

    action1, action2 = st.columns(2)
    run_std = action1.button("通常RAGで実行", use_container_width=True)
    run_graph = action2.button("GraphRAGで実行", use_container_width=True)

    std_result = None
    graph_result = None

    if run_std:
        if st.session_state.std is None:
            st.session_state.std = StandardRAG(chunks)
        std_result = st.session_state.std.answer(question)

    if run_graph:
        if st.session_state.graph is None:
            st.session_state.graph = GraphRAG(chunks)
        graph_result = st.session_state.graph.answer(question)

    st.subheader("比較表示")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("## Standard RAG")
        if std_result:
            st.markdown("### 回答")
            st.write(std_result["answer"])
            st.markdown("### 取得チャンク")
            render_standard_chunks(std_result["contexts"])
        else:
            st.info("『通常RAGで実行』を押すと、取得チャンクを整形表示します。")

    with col2:
        st.markdown("## GraphRAG")
        if graph_result:
            st.markdown("### 回答")
            st.write(graph_result["answer"])
            render_graph_chains(graph_result["context"])
        else:
            st.info("『GraphRAGで実行』を押すと、関係チェーンを整形表示します。")

    st.subheader("データプレビュー")
    preview_tab1, preview_tab2 = st.tabs(["Documents", "Chunks"])
    with preview_tab1:
        st.dataframe(pd.DataFrame(docs), use_container_width=True)
    with preview_tab2:
        st.dataframe(pd.DataFrame(chunks), use_container_width=True)
