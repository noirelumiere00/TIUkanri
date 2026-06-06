# オープンキャンパス管理システム

オープンキャンパスの相談ブース（テーブル）と来場者の待機列を管理する Flask アプリです。

## 機能

- **テーブル管理** (`/table_management`)
  - 相談ブースごとに「開始 / 終了 / 休憩 / 再開」を操作
  - 経過時間をリアルタイム表示し、制限時間（既定15分）超過で赤く点滅警告
  - 二重開始・未使用ブースの終了を防ぐ状態ガード付き
  - 終了時に対応履歴を記録
  - 「⚙ ブース管理」からブースの追加・改名・削除が可能
  - 「全ブースを空きに戻す」で途中再起動後の固まった状態を復旧
- **待機列管理** (`/queue_management`)
  - 番号札・性別・人数・相談内容・その他を登録
  - 番号札の重複（UNIQUE制約）・空欄チェック
  - 待機時間を表示、長時間待ち（既定30分）を赤字で強調
  - 「対応済」は確認ダイアログ付きの**論理削除**。対応済み一覧から**取り消し**可能
- **本日の統計** (`/api/stats`)
  - 対応件数・平均対応時間
- 時刻はすべて日本時間（JST / Asia/Tokyo）で統一
- SQLite は WAL モードで複数端末の同時アクセスに強くしています

## 設定（環境変数）

| 変数 | 既定値 | 説明 |
| --- | --- | --- |
| `TIME_LIMIT_MIN` | `15` | 相談ブースの制限時間（分） |
| `LONG_WAIT_MIN` | `30` | 待機列の長時間待ち閾値（分） |
| `DB_PATH` | `./opencampus.db` | SQLite ファイルの場所（Drive等に変更可） |
| `PORT` | `5000` | 待受ポート |
| `FLASK_DEBUG` | `0` | `1` でデバッグモード（本番では `0` 推奨） |
| `APP_PASSWORD` | （未設定） | 設定するとBASIC認証が有効（合言葉での簡易保護） |
| `APP_TIMEZONE` | `Asia/Tokyo` | タイムゾーン |

## テスト

```bash
pip install pytest
python -m pytest tests/ -q
```

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

ブラウザで http://127.0.0.1:5000 を開きます。
ポートを変えたい場合は `PORT=8000 python app.py`。

## Google Colab で使う場合（ngrok で外部公開）

同梱の **`opencampus_colab.ipynb`** を Colab で開き、上から順にセルを実行するだけです。

1. ライブラリのインストール
2. GitHub からリポジトリを取得（clone / pull）
3. ngrok の authtoken を設定
   （事前に https://dashboard.ngrok.com/get-started/your-authtoken で無料取得）
4. アプリ起動 → 公開URLが表示される

> ngrok は無料プランでも authtoken が必須です。公開URLは起動のたびに変わります。
> `opencampus.db` はランタイム終了で消えるため、永続化したい場合は Google Drive をマウントしてください。

## 構成

```
.
├── app.py                       # Flask アプリ本体（ルーティング・API）
├── models.py                    # DBモデル（Table / Queue / History）
├── config.py                    # 設定の集約（環境変数で上書き可能）
├── tables.json                  # ブース初期名称
├── opencampus_colab.ipynb       # Colab + ngrok 起動ノートブック
├── requirements.txt
├── tests/
│   └── test_app.py              # API スモークテスト
├── templates/
│   ├── index.html               # トップ（ダッシュボード）
│   ├── table_management.html    # テーブル管理
│   └── queue_management.html    # 待機列管理
└── static/
    ├── style.css
    └── common.js                # 画面共通のJSヘルパー
```

データベース（`opencampus.db`）は初回起動時に自動生成され、相談ブースの初期データが投入されます。
2回目以降の起動では既存データを保持します。

## 主な API

| メソッド | パス | 説明 |
| --- | --- | --- |
| POST | `/api/table/start/<id>` | 相談開始 |
| POST | `/api/table/end/<id>` | 相談終了（履歴記録） |
| POST | `/api/table/break/<id>` | 休憩 |
| POST | `/api/table/resume/<id>` | 再開 |
| POST | `/api/table/add` | ブース追加 |
| POST | `/api/table/rename/<id>` | ブース改名 |
| POST | `/api/table/delete/<id>` | ブース削除（使用中は不可） |
| POST | `/api/table/reset_all` | 全ブースを空きに戻す |
| GET  | `/api/table/list` | テーブル状態一覧 |
| POST | `/api/queue/add` | 待機列に追加 |
| POST | `/api/queue/remove/<id>` | 対応済みにする（論理削除） |
| POST | `/api/queue/undo/<id>` | 対応済みを取り消す |
| GET  | `/api/queue/list` | 待機列一覧（未対応） |
| GET  | `/api/queue/done_list` | 対応済み一覧 |
| GET  | `/api/stats` | 本日の統計 |
| GET  | `/api/config` | 画面共有設定（制限時間など） |
| GET  | `/api/server_time` | サーバー時刻（JST） |
