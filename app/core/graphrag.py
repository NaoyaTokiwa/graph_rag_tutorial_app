from typing import Dict, List

from langchain.schema import Document
from langchain_community.graphs import Neo4jGraph
from langchain_community.vectorstores import FAISS
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from core.config import settings



class GraphRAG:
    """セマンティック検索とグラフ探索を組み合わせた GraphRAG です。"""

    def __init__(self, docs: List[Dict]):
        """文書を初期化し、Neo4j とベクトル検索の準備を行います。

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
        self.llm = ChatOpenAI(
            model=settings.chat_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.graph = Neo4jGraph(
            url=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            refresh_schema=False,
        )
        self.vectorstore = FAISS.from_documents(self.documents, self.embeddings)

    def refresh_graph(self):
        """文書から Neo4j のグラフを再構築します。

        戻り値:
            GraphTransformer が生成した graph documents を返します。
        """
        transformer = LLMGraphTransformer(llm=self.llm)
        graph_docs = transformer.convert_to_graph_documents(self.documents)
        self.graph.query("MATCH (n) DETACH DELETE n")
        self.graph.add_graph_documents(graph_docs, baseEntityLabel=True, include_source=True)
        try:
            self.graph.refresh_schema()
        except Exception as e:
            print(f"skip refresh_schema: {e}")
        return graph_docs

    def graph_context(self, question: str, k: int = 4) -> str:
        """質問に対するセマンティック文脈とグラフ文脈を組み立てます。

        引数:
            question: ユーザーからの質問です。
            k: 類似文書として取得するチャンク数です。

        戻り値:
            セマンティック文脈とグラフ近傍情報を連結した文字列を返します。
        """
        docs = self.vectorstore.similarity_search(question, k=k)
        seed_titles = [d.metadata["title"] for d in docs]
        cypher = """
        MATCH (s:Document)
        WHERE s.title IN $titles
        OPTIONAL MATCH (s)-[*1..2]-(n)
        RETURN s.title AS source,
               collect(DISTINCT labels(n))[0..10] AS neighbor_labels,
               collect(DISTINCT coalesce(n.id, n.name, n.title))[0..10] AS neighbor_values
        LIMIT 20
        """
        rows = self.graph.query(cypher, params={"titles": seed_titles})
        serialized_rows = []
        for row in rows:
            serialized_rows.append(
                f"source={row.get('source')}, "
                f"neighbor_labels={row.get('neighbor_labels')}, "
                f"neighbor_values={row.get('neighbor_values')}"
            )

        semantic_context = "\n".join(
            [
                f"[{d.metadata['title']} / chunk={d.metadata['chunk_index']}] {d.page_content}"
                for d in docs
            ]
        )
        graph_context = "\n".join(serialized_rows)
        return (
            f"Semantic Context:\n{semantic_context}\n\n"
            f"Graph Context:\n{graph_context}"
        )

    def answer(self, question: str):
        """グラフ文脈を含めて回答を生成します。

        引数:
            question: ユーザーからの質問です。

        戻り値:
            生成した回答と使用したコンテキストを含む辞書を返します。
        """
        context = self.graph_context(question)
        prompt = (
            "あなたはGraphRAGアプリの回答アシスタントです。意味検索で得られた文脈と、グラフから得られた関係情報の両方を用いて回答してください。\n"
            f"質問: {question}\n"
            f"コンテキスト:\n{context}\n"
            "回答は日本語で記述してください。エンティティ同士の関係が分かるように、関係の流れを順序立てて説明してください。根拠が十分でない場合は、不足している情報を明確に示してください。"
        )
        response = self.llm.invoke(prompt)
        return {"answer": response.content, "context": context}
