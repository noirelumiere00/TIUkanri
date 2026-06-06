import json
import logging
import os

from flask import Flask, Response, jsonify, render_template, request
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

import config
from config import (STATUS_BREAK, STATUS_BUSY, STATUS_EMPTY, now_jst,
                    now_jst_naive)
from models import History, Queue, Table, db

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{config.DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db.init_app(app)


# ===== SQLite の同時アクセス耐性を上げる（WAL + busy_timeout） =====
@event.listens_for(Engine, 'connect')
def _set_sqlite_pragma(dbapi_conn, _record):
    try:
        cur = dbapi_conn.cursor()
        cur.execute('PRAGMA journal_mode=WAL')
        cur.execute('PRAGMA busy_timeout=5000')
        cur.close()
    except Exception:
        # SQLite 以外のドライバでは無視
        pass


# ===== 任意のBASIC認証（APP_PASSWORD 設定時のみ有効） =====
@app.before_request
def _require_auth():
    if not config.APP_PASSWORD:
        return None
    auth = request.authorization
    if not auth or auth.password != config.APP_PASSWORD:
        return Response(
            '認証が必要です', 401,
            {'WWW-Authenticate': 'Basic realm="OpenCampus"'},
        )
    return None


def _load_table_names():
    """ブース初期名称を tables.json から読み込む（無ければ最小限の既定値）"""
    try:
        with open(config.TABLES_JSON, encoding='utf-8') as f:
            names = json.load(f)
        if isinstance(names, list) and names:
            return [str(n) for n in names]
    except (OSError, json.JSONDecodeError) as e:
        logger.warning('tables.json を読み込めませんでした: %s', e)
    return ['ブース1', 'ブース2', 'ブース3']


def init_db():
    """DBを初期化（無ければ作成し、空なら初期データを投入）"""
    with app.app_context():
        db.create_all()
        if Table.query.count() == 0:
            names = _load_table_names()
            for name in names:
                db.session.add(Table(name=name))
            db.session.commit()
            logger.info('✅ %d個のテーブルを作成しました', len(names))
        else:
            logger.info('✅ テーブルは既に初期化済みです')


# ===== ページ =====

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/table_management')
def table_management():
    tables = Table.query.all()
    return render_template('table_management.html', tables=tables)


@app.route('/queue_management')
def queue_management():
    queue = Queue.query.filter_by(is_done=False).order_by(Queue.registered_time).all()
    return render_template('queue_management.html', queue=queue)


# ===== テーブル操作 API =====

@app.route('/api/table/start/<int:table_id>', methods=['POST'])
def start_consultation(table_id):
    try:
        table = db.session.get(Table, table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404
        if table.status == STATUS_BUSY:
            return jsonify({'success': False, 'error': '既に使用中です'}), 409

        table.status = STATUS_BUSY
        table.start_time = now_jst_naive()
        db.session.commit()
        return jsonify({'success': True, 'start_time': table.start_time.isoformat()})
    except Exception as e:
        db.session.rollback()
        logger.exception('start_consultation 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/end/<int:table_id>', methods=['POST'])
def end_consultation(table_id):
    try:
        table = db.session.get(Table, table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404
        if table.status != STATUS_BUSY or not table.start_time:
            return jsonify({'success': False, 'error': '使用中ではありません'}), 409

        end_time = now_jst_naive()
        duration = int((end_time - table.start_time).total_seconds() / 60)
        db.session.add(History(
            table_name=table.name,
            start_time=table.start_time,
            end_time=end_time,
            duration=duration,
            date=now_jst().date(),
        ))

        table.status = STATUS_EMPTY
        table.start_time = None
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.exception('end_consultation 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/break/<int:table_id>', methods=['POST'])
def set_break(table_id):
    try:
        table = db.session.get(Table, table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404
        table.status = STATUS_BREAK
        table.start_time = None
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.exception('set_break 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/resume/<int:table_id>', methods=['POST'])
def resume_table(table_id):
    try:
        table = db.session.get(Table, table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404
        table.status = STATUS_EMPTY
        table.start_time = None
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.exception('resume_table 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== テーブル管理（CRUD） API =====

@app.route('/api/table/add', methods=['POST'])
def add_table():
    try:
        name = (request.get_json(silent=True) or {}).get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'ブース名を入力してください'}), 400
        table = Table(name=name)
        db.session.add(table)
        db.session.commit()
        return jsonify({'success': True, 'id': table.id, 'name': table.name})
    except Exception as e:
        db.session.rollback()
        logger.exception('add_table 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/rename/<int:table_id>', methods=['POST'])
def rename_table(table_id):
    try:
        table = db.session.get(Table, table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404
        name = (request.get_json(silent=True) or {}).get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'ブース名を入力してください'}), 400
        table.name = name
        db.session.commit()
        return jsonify({'success': True, 'name': table.name})
    except Exception as e:
        db.session.rollback()
        logger.exception('rename_table 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/delete/<int:table_id>', methods=['POST'])
def delete_table(table_id):
    try:
        table = db.session.get(Table, table_id)
        if not table:
            return jsonify({'success': False, 'error': 'テーブルが見つかりません'}), 404
        if table.status == STATUS_BUSY:
            return jsonify({'success': False, 'error': '使用中のブースは削除できません'}), 409
        db.session.delete(table)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.exception('delete_table 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/reset_all', methods=['POST'])
def reset_all_tables():
    """全ブースを空きに戻す（途中再起動で固まった状態の復旧用）"""
    try:
        for table in Table.query.all():
            table.status = STATUS_EMPTY
            table.start_time = None
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.exception('reset_all_tables 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/table/list')
def list_tables():
    """テーブルの状態をJSON形式で取得（画面の自動更新用）"""
    try:
        tables = Table.query.order_by(Table.id).all()
        return jsonify([{
            'id': t.id,
            'name': t.name,
            'status': t.status,
            'start_time': t.start_time.strftime('%Y-%m-%dT%H:%M:%S') if t.start_time else None,
        } for t in tables])
    except Exception as e:
        logger.exception('list_tables 失敗')
        return jsonify({'error': str(e)}), 500


# ===== 待機列 API =====

@app.route('/api/queue/add', methods=['POST'])
def add_to_queue():
    try:
        data = request.get_json(silent=True) or {}
        ticket_number = (data.get('ticket_number') or '').strip()
        if not ticket_number:
            return jsonify({'success': False, 'error': '番号札を入力してください'}), 400

        queue = Queue(
            ticket_number=ticket_number,
            gender=data.get('gender'),
            party_size=data.get('party_size'),
            consultation_topic=data.get('consultation_topic'),
            other_notes=data.get('other_notes', ''),
            registered_time=now_jst_naive(),
        )
        db.session.add(queue)
        db.session.commit()
        return jsonify({'success': True, 'ticket_number': ticket_number})
    except IntegrityError:
        # UNIQUE制約違反（番号札の重複）。同時登録の競合もここで確実に弾く。
        db.session.rollback()
        return jsonify({'success': False, 'error': 'この番号札は既に登録されています'}), 409
    except Exception as e:
        db.session.rollback()
        logger.exception('add_to_queue 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/queue/remove/<int:queue_id>', methods=['POST'])
def remove_from_queue(queue_id):
    """対応済みにする（論理削除）。取り消し可能。"""
    try:
        queue = db.session.get(Queue, queue_id)
        if not queue:
            return jsonify({'success': False, 'error': '待機列が見つかりません'}), 404
        queue.is_done = True
        queue.done_time = now_jst_naive()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.exception('remove_from_queue 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/queue/undo/<int:queue_id>', methods=['POST'])
def undo_queue(queue_id):
    """対応済みを取り消して待機列に戻す"""
    try:
        queue = db.session.get(Queue, queue_id)
        if not queue:
            return jsonify({'success': False, 'error': '待機列が見つかりません'}), 404
        queue.is_done = False
        queue.done_time = None
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.exception('undo_queue 失敗')
        return jsonify({'success': False, 'error': str(e)}), 500


def _serialize_queue(item):
    return {
        'id': item.id,
        'ticket_number': item.ticket_number,
        'gender': item.gender,
        'party_size': item.party_size,
        'consultation_topic': item.consultation_topic,
        'other_notes': item.other_notes,
        'registered_time': item.registered_time.strftime('%Y-%m-%dT%H:%M:%S'),
        'done_time': item.done_time.strftime('%Y-%m-%dT%H:%M:%S') if item.done_time else None,
    }


@app.route('/api/queue/list')
def list_queue():
    """待機中（未対応）の一覧"""
    try:
        queue = Queue.query.filter_by(is_done=False).order_by(Queue.registered_time).all()
        return jsonify([_serialize_queue(i) for i in queue])
    except Exception as e:
        logger.exception('list_queue 失敗')
        return jsonify({'error': str(e)}), 500


@app.route('/api/queue/done_list')
def list_done_queue():
    """対応済みの一覧（取り消し用）"""
    try:
        queue = Queue.query.filter_by(is_done=True).order_by(Queue.done_time.desc()).all()
        return jsonify([_serialize_queue(i) for i in queue])
    except Exception as e:
        logger.exception('list_done_queue 失敗')
        return jsonify({'error': str(e)}), 500


# ===== その他 API =====

@app.route('/api/stats')
def get_stats():
    try:
        today = now_jst().date()
        histories = History.query.filter_by(date=today).all()
        if not histories:
            return jsonify({'count': 0, 'average': 0})
        total = sum(h.duration for h in histories)
        return jsonify({'count': len(histories), 'average': round(total / len(histories), 1)})
    except Exception as e:
        logger.exception('get_stats 失敗')
        return jsonify({'count': 0, 'average': 0})


@app.route('/api/config')
def get_config():
    """画面側と共有する設定（制限時間など）"""
    return jsonify({
        'time_limit_min': config.TIME_LIMIT_MIN,
        'long_wait_min': config.LONG_WAIT_MIN,
    })


@app.route('/api/server_time')
def server_time():
    return jsonify({
        'server_time': now_jst_naive().isoformat(),
        'timezone': config.TIMEZONE,
    })


# アプリ起動時にDBを初期化
init_db()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG)
