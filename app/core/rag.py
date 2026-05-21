from typing import Dict, List

from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from core.config import settings


class StandardRAG:
    """ベクトル検索ベースのシンプルな RAG パイプラインです。"""

    def __init__(self, docs: List[Dict]):
        """検索対象の文書を初期化し、埋め込みと LLM を準備します。

        引数:
            docs: インデックス対象の文書辞書のリストです。
        """
        self.documents = [  # 入力辞書をLangChainのDocument形式へ変換した一覧を作る
            Document(  # 1件分の文書オブジェクトを生成する
                page_content=d["text"],  # 本文をページ内容として設定する
                metadata={  # 検索時に使う付加情報をまとめる
                    "title": d["title"],  # 文書タイトルを保持する
                    "id": d["id"],  # 文書IDを保持する
                    "source": d.get("source", d["title"]),  # 元ソースがあれば使い、なければタイトルを使う
                    "parent_id": d.get("parent_id", d["id"]),  # 親文書IDを保持する
                    "chunk_index": d.get("chunk_index", 0),  # チャンク番号を保持する
                },
            )
            for d in docs
        ]
        self.embeddings = OpenAIEmbeddings(  # 埋め込みモデルを初期化する
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.llm = ChatOpenAI(  # LLMを初期化する
            model=settings.chat_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )
        self.vectorstore = FAISS.from_documents(self.documents, self.embeddings)  # 文書ベクトル検索用のインデックスを作成する


    def retrieve(self, question: str, k: int = 4):
        """質問に関連するチャンクを検索します。

        引数:
            question: 検索したい質問文です。
            k: 取得するチャンク数です。

        戻り値:
            関連度の高い LangChain Document のリストを返します。
        """
        return self.vectorstore.similarity_search(question, k=k)  # 質問に近い文書チャンクを検索して返す


    def answer(self, question: str):
        """検索結果をコンテキストとして回答を生成します。

        引数:
            question: ユーザーからの質問です。

        戻り値:
            生成した回答と参照コンテキストを含む辞書を返します。
        """
        docs = self.retrieve(question)  # 質問に対する関連文書を取得する
        context = "\n\n".join(  # 検索結果の本文を改行区切りで結合する
            [
                f"[{d.metadata['title']} / chunk={d.metadata['chunk_index']}] {d.page_content}"  # タイトルとチャンク番号付きで本文を整形する
                for d in docs
            ]
        )
        prompt = (  # LLMに渡すプロンプトを組み立てる
            "あなたは親切なアシスタントです。回答は必ず与えられたコンテキストの内容のみに基づいてください。\n"
            f"質問: {question}\n"
            f"コンテキスト:\n{context}\n"
            "回答は日本語で記述してください。根拠が不十分な場合は、その旨を明確に示してください。"
        )
        response = self.llm.invoke(prompt)  # プロンプトをLLMに投げて応答を得る
        return {"answer": response.content, "contexts": docs}  # 回答本文と参照した文書群を返す
