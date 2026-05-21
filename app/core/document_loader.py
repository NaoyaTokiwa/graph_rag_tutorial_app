from pathlib import Path
from typing import List, Dict
from PyPDF2 import PdfReader


SKIP_FILENAMES = {"readme.md", "readme.txt"}  # 読み込み対象から除外するREADME系ファイル名を定義する


def load_documents(data_dir: str = "data") -> List[Dict]:
    """指定ディレクトリ配下の文書を読み込みます。

    README 系の説明ファイルはデータセットに混ざらないよう除外します。

    引数:
        data_dir: 入力文書を格納しているルートディレクトリです。

    戻り値:
        文書 ID、タイトル、本文、ソースパスを含む辞書のリストを返します。
    """
    base = Path(data_dir)  # ルートディレクトリをPathオブジェクトとして扱う
    docs: List[Dict] = []  # 読み込んだ文書情報を格納するリストを初期化する

    for path in sorted(base.glob("**/*")):  # 配下のファイルとディレクトリを再帰的に走査する
        if path.is_dir():  # ディレクトリは読み込み対象ではないため
            continue  # 次の要素へ進む
        if path.name.lower() in SKIP_FILENAMES:  # README系のファイル名なら
            continue  # データセットに含めずスキップする


        suffix = path.suffix.lower()  # ファイル拡張子を小文字で取得する
        if suffix in {".md", ".txt"}:  # Markdownまたはテキストファイルなら
            text = path.read_text(encoding="utf-8", errors="ignore")  # UTF-8で読み込み、読めない文字は無視する
        elif suffix == ".pdf":  # PDFファイルなら
            reader = PdfReader(str(path))  # PDFを読み込むためのリーダーを生成する
            text = "\n".join(page.extract_text() or "" for page in reader.pages)  # 各ページの本文を結合する
        else:  # 対応していない拡張子なら
            continue  # 読み込み対象から外す


        cleaned = " ".join(text.split())  # 改行や余分な空白をまとめて整形する
        if cleaned:  # 整形後に本文が空でなければ
            docs.append({  # 文書情報を辞書として追加する
                "id": path.stem,  # 拡張子を除いたファイル名をIDにする
                "title": path.name,  # ファイル名をタイトルにする
                "text": cleaned,  # 整形済みの本文を保存する
                "source": str(path)  # 元ファイルのパスを保存する
            })
    return docs  # 文書一覧を返す
