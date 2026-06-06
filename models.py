from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Table(db.Model):
    """相談ブース（テーブル）"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='空き')  # 空き / 使用中 / 休憩中
    start_time = db.Column(db.DateTime)

    def get_elapsed_time(self):
        """経過時間を計算（分）"""
        if self.start_time and self.status == '使用中':
            elapsed = datetime.now() - self.start_time
            return int(elapsed.total_seconds() / 60)
        return 0

    def is_over_time(self, limit=15):
        """制限時間超過チェック"""
        return self.get_elapsed_time() > limit


class Queue(db.Model):
    """待機列"""
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), nullable=False)   # 番号札
    gender = db.Column(db.String(10))                          # 性別
    party_size = db.Column(db.Integer)                         # 人数
    consultation_topic = db.Column(db.String(100))            # 相談内容
    other_notes = db.Column(db.String(200))                   # その他
    registered_time = db.Column(db.DateTime, default=datetime.now)

    def get_waiting_time(self):
        """待機時間を計算（分）"""
        elapsed = datetime.now() - self.registered_time
        return int(elapsed.total_seconds() / 60)


class History(db.Model):
    """対応履歴"""
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)
    # 修正: datetime.now().date だと「読み込み時刻の日付」で固定されてしまうため、
    #       レコード作成時に評価される callable（lambda）にする
    date = db.Column(db.Date, default=lambda: datetime.now().date())
