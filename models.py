from flask_sqlalchemy import SQLAlchemy

from config import now_jst_naive, STATUS_EMPTY, STATUS_BUSY, TIME_LIMIT_MIN

db = SQLAlchemy()


class Table(db.Model):
    """相談ブース（テーブル）"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default=STATUS_EMPTY)  # 空き / 使用中 / 休憩中
    start_time = db.Column(db.DateTime)

    def get_elapsed_time(self):
        """経過時間を計算（分）。JST naive 同士で差分を取る。"""
        if self.start_time and self.status == STATUS_BUSY:
            elapsed = now_jst_naive() - self.start_time
            return int(elapsed.total_seconds() / 60)
        return 0

    def is_over_time(self, limit=TIME_LIMIT_MIN):
        """制限時間超過チェック"""
        return self.get_elapsed_time() > limit


class Queue(db.Model):
    """待機列"""
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), nullable=False, unique=True)  # 番号札（重複不可）
    gender = db.Column(db.String(10))                                       # 性別
    party_size = db.Column(db.Integer)                                      # 人数
    consultation_topic = db.Column(db.String(100))                         # 相談内容
    other_notes = db.Column(db.String(200))                                # その他
    registered_time = db.Column(db.DateTime, default=now_jst_naive)
    is_done = db.Column(db.Boolean, default=False, nullable=False)          # 対応済みフラグ（論理削除）
    done_time = db.Column(db.DateTime)                                      # 対応済みにした時刻

    def get_waiting_time(self):
        """待機時間を計算（分）"""
        elapsed = now_jst_naive() - self.registered_time
        return int(elapsed.total_seconds() / 60)


class History(db.Model):
    """対応履歴"""
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)
    # JST の日付で記録（統計集計と基準を揃える）
    date = db.Column(db.Date, default=lambda: now_jst_naive().date())
