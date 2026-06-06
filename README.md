# オープンキャンパス管理システム

オープンキャンパスの相談ブース（テーブル）と来場者の待機列を管理する Flask アプリです。

## 機能

- **テーブル管理** (`/table_management`)
  - 相談ブースごとに「開始 / 終了 / 休憩 / 再開」を操作
  - 経過時間をリアルタイム表示し、制限時間（15分）超過で赤く点滅警告
  - 終了時に対応履歴を記録
- **待機列管理** (`/queue_management`)
  - 番号札・性別・人数・相談内容・その他を登録
  - 待機時間を表示、対応済みで削除
  - 番号札の重複・空欄チェック
- **本日の統計** (`/api/stats`)
  - 対応件数・平均対応時間
- 時刻はすべて日本時間（JST / Asia/Tokyo）

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
├── requirements.txt
├── templates/
│   ├── index.html               # トップ（ダッシュボード）
│   ├── table_management.html    # テーブル管理
│   └── queue_management.html    # 待機列管理
└── static/
    └── style.css
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
| GET  | `/api/table/list` | テーブル状態一覧 |
| POST | `/api/queue/add` | 待機列に追加 |
| POST | `/api/queue/remove/<id>` | 待機列から削除 |
| GET  | `/api/queue/list` | 待機列一覧 |
| GET  | `/api/stats` | 本日の統計 |
| GET  | `/api/server_time` | サーバー時刻（JST） |
