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
        self.documents = [  # 入力辞書をLangChainのDocument形式へ変換した一覧を作る
            Document(
                page_content=d["text"],  # 本文をページ内容として設定する
                metadata={  # 検索やグラフ化に使う付加情報をまとめる
                    "title": d["title"],  # 文書タイトルを保持する
                    "id": d["id"],  # 文書IDを保持する
                    "source": d.get("source", d["title"]),  # 元ソースがあれば使い、なければタイトルを使う
                    "parent_id": d.get("parent_id", d["id"]),  # 親文書IDを保持する
                    "chunk_index": d.get("chunk_index", 0),  # チャンク番号を保持する
                },
            )
            for d in docs
        ]
        self.llm = ChatOpenAI(  # LLMを初期化する
            model=settings.chat_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )
        self.embeddings = OpenAIEmbeddings(  # 埋め込みモデルを初期化する
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.graph = Neo4jGraph(  # Neo4jグラフデータベースへの接続を作る
            url=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            refresh_schema=False,
        )
        self.vectorstore = FAISS.from_documents(self.documents, self.embeddings)  # 文書ベクトル検索用のインデックスを作成し、Neo4j のグラフ検索だけでは拾いにくい「意味が近い文書」を先に探す

    def refresh_graph(self):
        """文書から Neo4j のグラフを再構築します。

        戻り値:
            GraphTransformer が生成した graph documents を返します。
        """
        transformer = LLMGraphTransformer(llm=self.llm)  # 文書からグラフ構造を抽出する変換器を用意する
        graph_docs = transformer.convert_to_graph_documents(self.documents)  # 文書をグラフドキュメントへ変換する
        self.graph.query("MATCH (n) DETACH DELETE n")  # 既存のノードとリレーションをすべて削除する
        self.graph.add_graph_documents(graph_docs, baseEntityLabel=True, include_source=True)  # 変換結果をNeo4jへ登録する
        try:  # スキーマ更新で失敗するケースに備える
            self.graph.refresh_schema()  # スキーマ情報を再取得する
        except Exception as e:  # 例外が発生したら
            print(f"skip refresh_schema: {e}")  # スキーマ更新をスキップしたことを通知する
        return graph_docs  # 生成したグラフドキュメントを返す


    def graph_context(self, question: str, k: int = 4) -> str:
        """質問に対するセマンティック文脈とグラフ文脈を組み立てます。

        引数:
            question: ユーザーからの質問です。
            k: 類似文書として取得するチャンク数です。

        戻り値:
            セマンティック文脈とグラフ近傍情報を連結した文字列を返します。
        """
        docs = self.vectorstore.similarity_search(question, k=k)  # 質問に近い文書チャンクを検索する
        seed_titles = [d.metadata["title"] for d in docs]  # 検索結果からタイトル一覧を取り出す
        cypher = """
        //Documentラベルを持つノードを起点に探す
        MATCH (s:Document)
        
        // パラメータtitlesに含まれるタイトルだけを対象にする
        WHERE s.title IN $titles
        
        //起点ノードから1〜2ホップ先の関連ノードを探す
        OPTIONAL MATCH (s)-[*1..2]-(n)

        // 起点文書のタイトルをsourceとして返す
        // 近傍ノードのラベルを重複なしで集め、最大10件に絞る
        // 近傍ノードの識別用値を重複なしで集め、最大10件に絞る
        RETURN s.title AS source,
               collect(DISTINCT labels(n))[0..10] AS neighbor_labels,
               collect(DISTINCT coalesce(n.id, n.name, n.title))[0..10] AS neighbor_values
        
        // 返す行数を20件までに制限する
        LIMIT 20
        """  # 関連文書と隣接ノードを取得するCypherクエリを定義する
        rows = self.graph.query(cypher, params={"titles": seed_titles})  # タイトルを条件にグラフを問い合わせる
        serialized_rows = []  # 取得結果を文字列化して格納するリストを用意する
        for row in rows:  # 各行を順に処理する
            serialized_rows.append(  # 行ごとの情報を1つの文字列にまとめて追加する
                f"source={row.get('source')}, "
                f"neighbor_labels={row.get('neighbor_labels')}, "
                f"neighbor_values={row.get('neighbor_values')}"
            )

        semantic_context = "\n".join(  # セマンティック検索結果(本文そのものに近い検索結果)を改行区切りで結合する
            [
                f"[{d.metadata['title']} / chunk={d.metadata['chunk_index']}] {d.page_content}"  # タイトルとチャンク番号付きで本文を整形する
                for d in docs
            ]
        )
        graph_context = "\n".join(serialized_rows)  # グラフ検索結果（本文に書かれた関係性の構造）を改行区切りで結合する
        return (
            f"Semantic Context:\n{semantic_context}\n\n"
            f"Graph Context:\n{graph_context}"
        )  # 両方のコンテキストをまとめて返す


    def answer(self, question: str):
        """グラフ文脈を含めて回答を生成します。

        引数:
            question: ユーザーからの質問です。

        戻り値:
            生成した回答と使用したコンテキストを含む辞書を返します。
        """
        context = self.graph_context(question)  # 質問に対するコンテキストを生成する
        print(f"context: {context}")
        prompt = (  # LLMに渡すプロンプトを組み立てる
            "あなたはGraphRAGアプリの回答アシスタントです。意味検索で得られた文脈と、グラフから得られた関係情報の両方を用いて回答してください。\n"
            f"質問: {question}\n"
            f"コンテキスト:\n{context}\n"
            "回答は日本語で記述してください。エンティティ同士の関係が分かるように、関係の流れを順序立てて説明してください。根拠が十分でない場合は、不足している情報を明確に示してください。"
        )
        response = self.llm.invoke(prompt)  # プロンプトをLLMに投げて応答を得る
        return {"answer": response.content, "context": context}  # 回答本文と使ったコンテキストを返す
