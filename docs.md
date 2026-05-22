# docs.md

## アプリ概要

このアプリは、通常RAGとGraphRAGの回答差分を確認するための PoC 重視サンプルです。実務機能を増やしすぎず、PDF / Markdown / Text の読み込みと、比較しやすい UI に重点を置いています。

## 実装機能

### 1. ドキュメント読込

- `data/` 配下の `.pdf` `.md` `.txt` を読み込み
- ファイルがない場合は `sample_data.py` の組み込み文書を利用
- 最小限の拡張で PoC を始めやすい構成

### 2. チャンク分割

- `RecursiveCharacterTextSplitter` を利用
- `chunk_size` と `chunk_overlap` を UI から調整可能
- 比較実験に必要な粒度調整だけに絞った構成

### 3. 通常RAG

- `OpenAIEmbeddings(text-embedding-3-small)` で埋め込み生成
- `FAISS` に格納し、類似チャンクを取得
- `ChatOpenAI(gpt-4o-mini)` で回答生成

### 4. GraphRAG

- `LLMGraphTransformer` を用いてチャンクからノード・リレーションを抽出
- Graph Document を Neo4j に投入
- ベクトル検索で関連チャンクを選び、その文書タイトルを起点にグラフ近傍を取得
- セマンティックコンテキストとグラフコンテキストを合わせて回答生成

### 5. Streamlit UI

- データソース切替
- チャンクパラメータ調整
- 通常RAG / GraphRAG の回答比較
- 取得チャンク表示
- グラフ拡張コンテキスト表示
- Documents / Chunks プレビュー

## RAG と GraphRAG の違い

| 項目 | 通常RAG | GraphRAG |
|---|---|---|
| 主な検索軸 | ベクトル類似度 | ベクトル類似度 + エンティティ関係 |
| 強み | シンプルで理解しやすい | 関係性の説明、多段的なつながり把握に強い |
| 弱み | 文書間の関係を扱いにくい | 準備にグラフ構築が必要 |
| 向いている用途 | まずPoCを試したいとき | 関係性の価値を検証したいとき |

## 今回の設計意図

- 複雑な実務機能は入れすぎない
- 最小限の追加で PDF / Markdown 読込に対応する
- 比較UIで差分観察をしやすくする
- GraphRAG の学習・検証用サンプルとして扱いやすくする

## 各ファイルの役割

- `app/core/config.py`: 環境変数のロード
- `app/core/document_loader.py`: PDF / Markdown / Text の読込
- `app/core/chunker.py`: 文書チャンク分割
- `app/core/sample_data.py`: A社の問い合わせ支援AIを題材にした組み込みサンプル文書
- `app/core/rag.py`: 通常RAGロジック
- `app/core/graphrag.py`: GraphRAGロジック、Neo4j 登録、近傍探索
- `app/ui/streamlit_app.py`: 比較UI
- `scripts/init_neo4j.cypher`: Neo4j 初期化用 Cypher

## 注意点

- `LLMGraphTransformer` は LLM 出力依存のため、抽出結果は毎回完全一致しない可能性があります。
- 本サンプルは PoC 向けのため、評価基盤、アクセス制御、監視、永続運用は含めていません。
- GraphRAG を比較するには、先に `知識グラフを再構築` を実行しておく必要があります。



## 用語集
### APOCとは
* Neo4j の便利な補助機能集で、データの加工、CSV 読み込み、ファイル操作などに使用される
* 必要な範囲だけファイル入出力を許可するための設定が可能
* GraphRAG で Neo4j に知識グラフを入れたり、後からデータを書き出したりするときに役立つ
