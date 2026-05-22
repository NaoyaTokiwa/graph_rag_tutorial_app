# GraphRAG Sample App

OpenAI API、LangChain、Neo4j、Streamlit を用いて、通常RAGとGraphRAGを比較できるサンプルアプリです。

## 特徴

- Streamlit UI による比較画面
- OpenAI Chat Model: `gpt-4o-mini`
- OpenAI Embedding Model: `text-embedding-3-small`
- 通常RAG: `FAISS` を用いたベクトル検索
- GraphRAG: LangChain `LLMGraphTransformer` + Neo4j
- `data/` 配下の PDF / Markdown / Text ファイル読込対応
- 比較UIの強化, 取得チャンクとグラフ拡張コンテキストを確認可能
- Docker Compose による再現可能な環境構築

## ディレクトリ構成

```text
.
├── app
│   ├── core
│   │   ├── chunker.py
│   │   ├── config.py
│   │   ├── document_loader.py
│   │   ├── graphrag.py
│   │   ├── rag.py
│   │   └── sample_data.py
│   ├── ui
│   │   └── streamlit_app.py
│   └── main.py
├── data
├── scripts
│   └── init_neo4j.cypher
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── README.md
├── docs.md
└── requirements.txt
```

## セットアップ

1. `.env.example` をコピーして `.env` を作成します。
2. `OPENAI_API_KEY` を設定します。
3. 必要に応じて `data/` に PDF / Markdown / Text ファイルを追加します。
4. 以下を実行します。

```bash
cp .env.example .env
docker compose up --build
```

5. ブラウザで以下を開きます。
   - Streamlit: [http://localhost:8501](http://localhost:8501)
   - Neo4j Browser: [http://localhost:7474](http://localhost:7474)

## 使い方

1. Sidebar で `data/ のPDF・Markdown・Textを優先` を選択
2. `chunk_size` `chunk_overlap` `top_k` を調整
3. `比較エンジンを初期化` を実行
4. `知識グラフを再構築` を実行して知識グラフを生成
5. 同じ質問で `通常RAGで実行` と `GraphRAGで実行` を比較
6. 下部の Documents / Chunks プレビューで入力内容を確認

## PoC 重視にしたポイント

- 構成をシンプルに維持
- PDF / Markdown / Text の読込だけを追加
- 比較UIを強化し、通常RAGとGraphRAGの差を見やすくした
- チャンク分割パラメータをその場で試せるようにした
- 取得チャンクとグラフ拡張コンテキストを可視化した

## GitHub 公開向けのポイント

- `.env` はコミットせず、`.env.example` のみを公開
- Docker ベースで再現性を担保
- README と docs に設計意図・使い方・RAG と GraphRAG の違いを明記
- `data/` を差し替えるだけで独自データセットに転用しやすい


## 同梱サンプルデータ

- `sample_factory_overview.md`: 製造ライン監視システム「FactoryPulse」の概要データ
- `sample_factory_incident.md`: 不良率上昇インシデントの記録データ
- `sample_factory_maintenance.md`: 保全記録および復旧対応履歴データ
- `sample_factory_relations.md`: 設備・異常・原因・担当者・対応策の関係整理メモ


## Neo4j Console での知識グラフ確認方法
```
# グラフ内のノードと関係を最大50件取得して表示するクエリ
MATCH (n)-[r]->(m)
# 始点ノードn、関係r、終点ノードmをそのまま返す
RETURN n, r, m
# 取得件数を50件に制限する
LIMIT 50;
```

## APOCとは
* Neo4j の便利な補助機能集で、データの加工、CSV 読み込み、ファイル操作などに使用される
* 必要な範囲だけファイル入出力を許可するための設定が可能
* GraphRAG で Neo4j に知識グラフを入れたり、後からデータを書き出したりするときに役立つ
