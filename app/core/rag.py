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
        self.documents = [
            Document(
                page_content=d["text"],
                metadata={
                    "title": d["title"],
                    "id": d["id"],
                    "source": d.get("source", d["title"]),
                    "parent_id": d.get("parent_id", d["id"]),
                    "chunk_index": d.get("chunk_index", 0),
                },
            )
            for d in docs
        ]
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.llm = ChatOpenAI(
            model=settings.chat_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )
        self.vectorstore = FAISS.from_documents(self.documents, self.embeddings)

    def retrieve(self, question: str, k: int = 4):
        """質問に関連するチャンクを検索します。

        引数:
            question: 検索したい質問文です。
            k: 取得するチャンク数です。

        戻り値:
            関連度の高い LangChain Document のリストを返します。
        """
        return self.vectorstore.similarity_search(question, k=k)

    def answer(self, question: str):
        """検索結果をコンテキストとして回答を生成します。

        引数:
            question: ユーザーからの質問です。

        戻り値:
            生成した回答と参照コンテキストを含む辞書を返します。
        """
        docs = self.retrieve(question)
        context = "\n\n".join(
            [
                f"[{d.metadata['title']} / chunk={d.metadata['chunk_index']}] {d.page_content}"
                for d in docs
            ]
        )
        prompt = (
            "あなたは親切なアシスタントです。回答は必ず与えられたコンテキストの内容のみに基づいてください。\n"
            f"質問: {question}\n"
            f"コンテキスト:\n{context}\n"
            "回答は日本語で記述してください。根拠が不十分な場合は、その旨を明確に示してください。"
        )
        response = self.llm.invoke(prompt)
        return {"answer": response.content, "contexts": docs}
