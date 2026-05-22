import pandas as pd
import streamlit as st

from core.sample_data import SAMPLE_DOCUMENTS
from core.document_loader import load_documents
from core.chunker import chunk_documents
from core.rag import StandardRAG
from core.graphrag import GraphRAG
from core.config import settings

DEFAULT_QUESTIONS = [  # UIで選べるサンプル質問
    "製品Xの不良率上昇には、どの設備とどの担当者が関わっていますか。",
    "成形機M-12 に関する問題は、いつから兆候があり、最終的にどの対応が行われましたか。",
    "搬送ロボットR-3 の位置ずれは、どの現象や対応策と関係していますか。",
    "品質分析責任者、運用責任者、保全部門リーダーは、それぞれ何を担当しましたか。",
    "不良率上昇の原因と復旧策を、設備、症状、担当者の関係が分かるように説明してください。",
]


def resolve_documents(prefer_files: bool):
    """読み込み対象の文書群を決定して返す。

    Args:
        prefer_files: True の場合は data/ 配下のファイルを優先する。

    Returns:
        tuple: (文書リスト, 利用データの説明ラベル)
    """
    loaded = load_documents("data") if prefer_files else []  # data/ を優先して文書読込
    if loaded:  # data/ に読み込める文書がある場合
        return loaded, "data/ 配下のファイル"  # 外部ファイルを利用
    return SAMPLE_DOCUMENTS, "sample_data.py の組み込み文書"  # fallbackで組み込み文書を利用


def ensure_state():
    """Session State に必要なキーを初期化する。

    Returns:
        None
    """
    if "std" not in st.session_state:  # StandardRAGインスタンス保持領域が未作成
        st.session_state.std = None  # 初期値を設定
    if "graph" not in st.session_state:  # GraphRAGインスタンス保持領域が未作成
        st.session_state.graph = None  # 初期値を設定
    if "chunks" not in st.session_state:  # 現在のチャンク保持領域が未作成
        st.session_state.chunks = []  # 空配列で初期化
    if "std_result" not in st.session_state:  # StandardRAGの回答保持領域が未作成
        st.session_state.std_result = None  # 初期値を設定
    if "graph_result" not in st.session_state:  # GraphRAGの回答保持領域が未作成
        st.session_state.graph_result = None  # 初期値を設定
    if "last_chunk_params" not in st.session_state:  # 前回のチャンク条件保持領域が未作成
        st.session_state.last_chunk_params = None  # 初期値を設定


def render_standard_chunks(docs):
    """Standard RAG が取得したチャンク一覧を整形表示する。

    Args:
        docs: 取得コンテキストとなった Document のリスト。

    Returns:
        None
    """
    for i, d in enumerate(docs, start=1):  # チャンクを順番に表示
        with st.container(border=True):  # 各チャンクを枠付きコンテナで表示
            st.markdown(f"### Chunk {i}")  # チャンク番号表示
            meta1, meta2, meta3 = st.columns(3)  # メタ情報を3列で表示
            meta1.metric("Title", d.metadata["title"])  # 文書タイトル表示
            meta2.metric("Chunk", d.metadata["chunk_index"])  # チャンク番号表示
            meta3.metric("Source", d.metadata["source"])  # ソース表示
            st.markdown(  # チャンク本文を小さめの文字で表示
                f"""
                <div style="
                    font-size: 0.85rem;
                    line-height: 1.5;
                    white-space: pre-wrap;
                ">
                    {d.page_content}
                </div>
                """,
                unsafe_allow_html=True,  # HTML をそのまま解釈して表示
            )


def parse_graph_context(raw: str):
    """GraphRAG のコンテキスト文字列を Semantic 部分と関係チェーンに分解する。

    Args:
        raw: GraphRAG が返したコンテキスト文字列。

    Returns:
        tuple[str, list[str]]: (semantic context, relationship chains)
    """
    semantic, graph = raw, ""  # 初期状態では全文をsemantic扱いにする
    if "Graph Context:" in raw:  # Graph Context 区切りが含まれる場合
        parts = raw.split("Graph Context:", 1)  # Semantic部とGraph部に一度だけ分割
        semantic = parts[0].replace("Semantic Context:", "").strip()  # Semantic部を整形
        graph = parts[1].strip()  # Graph部を整形

    chains = []  # 関係チェーン格納用
    for line in graph.splitlines():  # Graph部を1行ずつ処理
        line = line.strip()  # 前後空白を除去
        if not line:  # 空行は無視
            continue  # 次の行へ
        chains.append(line)  # 有効な関係チェーンを追加

    return semantic, chains  # 分解結果を返却


def render_graph_chains(raw: str):
    """GraphRAG のコンテキストを Semantic Seeds と Relationship Chains に分けて表示する。

    Args:
        raw: GraphRAG が返したコンテキスト文字列。

    Returns:
        None
    """
    semantic, chains = parse_graph_context(raw)  # 表示用にコンテキストを分解
    with st.container(border=True):  # 全体を枠付きコンテナで表示
        st.markdown("### Semantic Seeds")  # Semantic部見出し
        st.code(semantic if semantic else "No semantic seed context")  # Semantic部表示
        st.markdown("### Relationship Chains")  # 関係チェーン見出し
        if not chains:  # 関係チェーンが存在しない場合
            st.info(
                "知識グラフ由来の関係チェーンがまだありません。先に『知識グラフを再構築』を実行してください。"
            )  # ユーザー向け案内
            return  # チェーン表示処理を終了

        for idx, chain in enumerate(chains, start=1):  # 各チェーンを順番に表示
            with st.container(border=True):  # 各チェーンを個別枠で表示
                st.markdown(f"#### Chain {idx}")  # チェーン番号表示
                st.code(chain)  # チェーン本文表示


def reset_results():
    """保持中のRAG実行結果をクリアする。

    Returns:
        None
    """
    st.session_state.std_result = None  # StandardRAG結果を消去
    st.session_state.graph_result = None  # GraphRAG結果を消去


def run_app():
    """Streamlit アプリ全体を構築して実行する。

    Returns:
        None
    """
    st.set_page_config(page_title="GraphRAG Sample", layout="wide")  # ページ設定
    st.title("GraphRAG vs Standard RAG Demo")  # タイトル表示
    st.caption("PoC-focused: PDF/Markdown loading + structured comparison UI + Neo4j GraphRAG")  # 補足説明
    ensure_state()  # session_state 初期化

    if not settings.openai_api_key:  # APIキー未設定時
        st.warning("OPENAI_API_KEY が未設定です。.env を作成して設定してください。")  # 警告表示

    st.sidebar.header("データ設定")  # サイドバー見出し
    prefer_files = st.sidebar.toggle("data/ のPDF・Markdown・Textを優先", value=True)  # data/優先切替
    chunk_size = st.sidebar.slider("chunk_size", 100, 1200, 300, 50)  # chunk_size設定
    chunk_overlap = st.sidebar.slider("chunk_overlap", 0, 300, 50, 10)  # chunk_overlap設定

    docs, source_label = resolve_documents(prefer_files)  # 利用文書とデータ種別を決定
    chunks = chunk_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)  # 文書をチャンク化
    st.session_state.chunks = chunks  # 現在のチャンクを保持

    current_chunk_params = (prefer_files, chunk_size, chunk_overlap, len(docs))  # 現在の分割条件をまとめる
    if st.session_state.last_chunk_params is None:  # 初回起動時
        st.session_state.last_chunk_params = current_chunk_params  # 初回条件を保存
    elif st.session_state.last_chunk_params != current_chunk_params:  # 条件変更を検知
        reset_results()  # 旧結果をクリア
        st.session_state.std = None  # StandardRAGインスタンスを再生成対象に戻す
        st.session_state.graph = None  # GraphRAGインスタンスを再生成対象に戻す
        st.session_state.last_chunk_params = current_chunk_params  # 最新条件を保存

    st.sidebar.markdown(f"**使用データ:** {source_label}")  # 利用データ表示
    st.sidebar.metric("Documents", len(docs))  # 文書数表示
    st.sidebar.metric("Chunks", len(chunks))  # チャンク数表示

    with st.expander("使い方", expanded=False):  # 使い方説明エリア
        st.markdown(
            "1. `data/` に PDF / Markdown / Text を置くか、組み込みサンプルを使います。\n"
            "2. `比較エンジンを初期化` を押します。\n"
            "3. `知識グラフを再構築` を押して GraphRAG のグラフを作成します。\n"
            "4. 質問の入力方法を選び、通常RAGとGraphRAGに投げて違いを比較します。"
        )  # 操作手順を表示

    controls1, controls2 = st.columns([1, 1])  # 制御ボタンを2列配置

    if controls1.button("比較エンジンを初期化", use_container_width=True):  # 初期化ボタン押下時
        st.session_state.std = StandardRAG(chunks)  # StandardRAGを初期化
        st.session_state.graph = GraphRAG(chunks)  # GraphRAGを初期化
        reset_results()  # 既存結果をクリア
        st.success("通常RAG / GraphRAG を初期化しました。")  # 完了通知

    if controls2.button("知識グラフを再構築", use_container_width=True):  # グラフ再構築ボタン押下時
        if st.session_state.graph is None:  # GraphRAG未初期化なら
            st.session_state.graph = GraphRAG(chunks)  # GraphRAGを生成
        graph_docs = st.session_state.graph.refresh_graph()  # グラフを再構築
        st.session_state.graph_result = None  # 古いGraphRAG結果のみクリア
        st.success(f"知識グラフを再構築しました。graph documents: {len(graph_docs)}")  # 完了通知

    st.subheader("質問入力")  # 質問入力セクション見出し

    question_mode = st.radio(  # 入力方式を明示的に選択
        "質問の入力方法",
        ["サンプル質問を使う", "自由入力を使う"],
        horizontal=True,
    )

    selected_question = st.selectbox(  # サンプル質問選択
        "サンプル質問",
        DEFAULT_QUESTIONS,
        disabled=question_mode != "サンプル質問を使う",
    )

    custom_question = st.text_area(  # 自由入力欄
        "自由入力",
        placeholder="ここに質問を入力してください。",
        height=100,
        disabled=question_mode != "自由入力を使う",
    )

    if question_mode == "サンプル質問を使う":  # サンプル質問を採用
        question = selected_question  # 選択中のサンプル質問を実行対象にする
    else:  # 自由入力を採用
        question = custom_question.strip()  # 前後空白を除去した自由入力を実行対象にする

    st.caption(f"今回実行される質問: {question if question else '未入力です'}")  # 実行対象の質問を明示
    is_question_ready = bool(question)  # 実行可能な質問があるかを判定

    action1, action2, action3 = st.columns(3)  # 実行ボタンを3列配置
    run_std = action1.button(  # StandardRAG実行ボタン
        "通常RAGで実行",
        use_container_width=True,
        disabled=not is_question_ready,
    )
    run_graph = action2.button(  # GraphRAG実行ボタン
        "GraphRAGで実行",
        use_container_width=True,
        disabled=not is_question_ready,
    )
    run_both = action3.button(  # 両方同時実行ボタン
        "両方で実行",
        use_container_width=True,
        disabled=not is_question_ready,
    )

    if not is_question_ready:  # 質問未入力時
        st.info("質問を入力するか、サンプル質問を選択してください。")  # 実行前の案内を表示

    if run_std:  # StandardRAG実行時
        if st.session_state.std is None:  # 未初期化なら
            st.session_state.std = StandardRAG(chunks)  # StandardRAGを生成
        st.session_state.std_result = st.session_state.std.answer(question)  # 回答結果を保持

    if run_graph:  # GraphRAG実行時
        if st.session_state.graph is None:  # 未初期化なら
            st.session_state.graph = GraphRAG(chunks)  # GraphRAGを生成
        st.session_state.graph_result = st.session_state.graph.answer(question)  # 回答結果を保持

    if run_both:  # 両方実行時
        if st.session_state.std is None:  # StandardRAG未初期化なら
            st.session_state.std = StandardRAG(chunks)  # StandardRAGを生成
        if st.session_state.graph is None:  # GraphRAG未初期化なら
            st.session_state.graph = GraphRAG(chunks)  # GraphRAGを生成
        st.session_state.std_result = st.session_state.std.answer(question)  # StandardRAG結果を保持
        st.session_state.graph_result = st.session_state.graph.answer(question)  # GraphRAG結果を保持

    st.subheader("比較表示")  # 比較表示セクション見出し
    col1, col2 = st.columns(2)  # 結果表示を左右2列に配置

    with col1:  # 左列: Standard RAG
        st.markdown("## Standard RAG")  # 見出し表示
        if st.session_state.std_result:  # 結果がある場合
            st.markdown("### 回答")  # 回答見出し
            st.write(st.session_state.std_result["answer"])  # 回答本文表示
            st.markdown("### 取得チャンク")  # チャンク見出し
            render_standard_chunks(st.session_state.std_result["contexts"])  # 取得チャンク表示
        else:  # 結果がない場合
            st.info("『通常RAGで実行』を押すと、取得チャンクを整形表示します。")  # 案内表示

    with col2:  # 右列: GraphRAG
        st.markdown("## GraphRAG")  # 見出し表示
        if st.session_state.graph_result:  # 結果がある場合
            st.markdown("### 回答")  # 回答見出し
            st.write(st.session_state.graph_result["answer"])  # 回答本文表示
            render_graph_chains(st.session_state.graph_result["context"])  # 関係チェーン表示
        else:  # 結果がない場合
            st.info("『GraphRAGで実行』を押すと、関係チェーンを整形表示します。")  # 案内表示

    st.subheader("データプレビュー")  # データ確認セクション見出し
    preview_tab1, preview_tab2 = st.tabs(["Documents", "Chunks"])  # プレビュータブ生成

    with preview_tab1:  # Documentsタブ
        st.dataframe(pd.DataFrame(docs), use_container_width=True)  # 文書一覧表示

    with preview_tab2:  # Chunksタブ
        st.dataframe(pd.DataFrame(chunks), use_container_width=True)  # チャンク一覧表示


if __name__ == "__main__":  # スクリプト直接実行時
    run_app()  # アプリ起動
