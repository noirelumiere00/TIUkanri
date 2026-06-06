from flask import Flask, render_template, request, jsonify
from datetime import datetime
import pytz
from models import db, Table, Queue, History
import os

app = Flask(__name__)

# 日本時間のタイムゾーン設定
JST = pytz.timezone('Asia/Tokyo')

# データベース設定
db_path = os.path.join(os.getcwd(), 'opencampus.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db.init_app(app)


def now_jst():
    """日本時間で現在時刻を取得"""
    return datetime.now(JST)


# 相談ブース（テーブル）の初期名称
DEFAULT_TABLE_NAMES = [
    '商：上野博', '商：賈曄', '国：杉本篤史',
    '国：上原伸元', '国：追加教員予定', '人(ス)：布川清彦', '人(ス)：赤池行平',
    '人(ス)：田中千晶', '人(心)：妙木浩之', '医：神戸晃男', '医：二宮省悟',
    '入試', '入試', '入試', '入試',
    '入試', '留学', '学生生活', '強化クラブ',
]


def init_db():
    """データベースを初期化（テーブルが無ければ作成し、空なら初期データを投入）"""
    with app.app_context():
        db.create_all()
        if Table.query.count() == 0:
            for name in DEFAULT_TABLE_NAMES:
                db.session.add(Table(name=name))
            db.session.commit()
            print(f"✅ {len(DEFAULT_TABLE_NAMES)}個のテーブルを作成しました")
        else:
            print("✅ テーブルは既に初期化済みです")


# ===== ルーティング =====

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/table_management')
def table_management():
    try:
        tables = Table.query.all()
        return render_template('table_management.html', tables=tables)
    except Exception as e:
        print(f"❌ エラー: {e}")
        return f"エラーが発生しました: {e}", 500


@app.route('/queue_management')
def queue_management():
    try:
        queue = Queue.query.order_by(Queue.registered_time).all()
        return render_template('queue_management.html', queue=queue)
    except Exception as e:
        print(f"❌ エラー: {e}")
        return f"エラーが発生しました: {e}", 500


# ===== API =====

@app.route('/api/table/start/<int:table_id>', methods=['POST'])
def start_consultation(table_id):
    try:
        table = Table.query.get(table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404

        table.status = '使用中'
        table.start_time = now_jst().replace(tzinfo=None)
        db.session.commit()

        return jsonify({'success': True, 'start_time': table.start_time.isoformat()})
    except Exception as e:
        print(f"❌ エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/end/<int:table_id>', methods=['POST'])
def end_consultation(table_id):
    try:
        table = Table.query.get(table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404

        if table.start_time:
            end_time = now_jst().replace(tzinfo=None)
            duration = int((end_time - table.start_time).total_seconds() / 60)

            history = History(
                table_name=table.name,
                start_time=table.start_time,
                end_time=end_time,
                duration=duration,
            )
            db.session.add(history)

        table.status = '空き'
        table.start_time = None
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        print(f"❌ エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/break/<int:table_id>', methods=['POST'])
def set_break(table_id):
    try:
        table = Table.query.get(table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404
        table.status = '休憩中'
        table.start_time = None
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/resume/<int:table_id>', methods=['POST'])
def resume_table(table_id):
    try:
        table = Table.query.get(table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404
        table.status = '空き'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/queue/add', methods=['POST'])
def add_to_queue():
    try:
        data = request.json

        ticket_number = data.get('ticket_number', '').strip()
        if not ticket_number:
            return jsonify({'success': False, 'error': '番号札を入力してください'}), 400

        existing = Queue.query.filter_by(ticket_number=ticket_number).first()
        if existing:
            return jsonify({'success': False, 'error': 'この番号札は既に登録されています'}), 400

        queue = Queue(
            ticket_number=ticket_number,
            gender=data.get('gender'),
            party_size=data.get('party_size'),
            consultation_topic=data.get('consultation_topic'),
            other_notes=data.get('other_notes', ''),
            registered_time=now_jst().replace(tzinfo=None),
        )
        db.session.add(queue)
        db.session.commit()

        return jsonify({'success': True, 'ticket_number': ticket_number})
    except Exception as e:
        print(f"❌ エラー: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/queue/remove/<int:queue_id>', methods=['POST'])
def remove_from_queue(queue_id):
    try:
        queue = Queue.query.get(queue_id)
        if not queue:
            return jsonify({'success': False, 'error': '待機列が見つかりません'}), 404

        db.session.delete(queue)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"❌ エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/queue/list')
def list_queue():
    """待機列データをJSON形式で取得"""
    try:
        queue = Queue.query.order_by(Queue.registered_time).all()
        queue_data = []
        for item in queue:
            queue_data.append({
                'id': item.id,
                'ticket_number': item.ticket_number,
                'gender': item.gender,
                'party_size': item.party_size,
                'consultation_topic': item.consultation_topic,
                'other_notes': item.other_notes,
                'registered_time': item.registered_time.strftime('%Y-%m-%dT%H:%M:%S'),
            })
        return jsonify(queue_data)
    except Exception as e:
        print(f"❌ エラー: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/table/list')
def list_tables():
    """テーブルの状態をJSON形式で取得（画面の自動更新用）"""
    try:
        tables = Table.query.all()
        data = []
        for t in tables:
            data.append({
                'id': t.id,
                'name': t.name,
                'status': t.status,
                'start_time': t.start_time.strftime('%Y-%m-%dT%H:%M:%S') if t.start_time else None,
            })
        return jsonify(data)
    except Exception as e:
        print(f"❌ エラー: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    try:
        today = now_jst().date()
        histories = History.query.filter_by(date=today).all()

        if not histories:
            return jsonify({'count': 0, 'average': 0})

        total_duration = sum(h.duration for h in histories)
        average = total_duration / len(histories)

        return jsonify({
            'count': len(histories),
            'average': round(average, 1),
        })
    except Exception as e:
        print(f"❌ エラー: {e}")
        return jsonify({'count': 0, 'average': 0})


@app.route('/api/server_time')
def server_time():
    return jsonify({
        'server_time': now_jst().replace(tzinfo=None).isoformat(),
        'timezone': 'Asia/Tokyo',
    })


# アプリ起動時にDBを初期化
init_db()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
