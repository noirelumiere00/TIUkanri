"""アプリ全体の設定。環境変数で上書き可能（1か所に集約）。"""
import os
from datetime import datetime

import pytz

# タイムゾーン
TIMEZONE = os.environ.get('APP_TIMEZONE', 'Asia/Tokyo')
JST = pytz.timezone(TIMEZONE)


def now_jst():
    """タイムゾーン付きの現在時刻（JST）"""
    return datetime.now(JST)


def now_jst_naive():
    """tzinfoを外したJSTの現在時刻（DB保存用）"""
    return now_jst().replace(tzinfo=None)


# 業務設定
TIME_LIMIT_MIN = int(os.environ.get('TIME_LIMIT_MIN', '15'))    # 相談ブースの制限時間（分）
LONG_WAIT_MIN = int(os.environ.get('LONG_WAIT_MIN', '30'))      # 待機列の長時間待ち閾値（分）

# 実行設定
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.getcwd(), 'opencampus.db'))
PORT = int(os.environ.get('PORT', '5000'))
DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

# 任意のBASIC認証（APP_PASSWORD を設定したときだけ有効になる）
APP_PASSWORD = os.environ.get('APP_PASSWORD')

# ブース初期名称を読み込むJSONファイル
TABLES_JSON = os.environ.get('TABLES_JSON', os.path.join(os.path.dirname(__file__), 'tables.json'))

# ステータス定数（マジック文字列の散在を防ぐ）
STATUS_EMPTY = '空き'
STATUS_BUSY = '使用中'
STATUS_BREAK = '休憩中'
