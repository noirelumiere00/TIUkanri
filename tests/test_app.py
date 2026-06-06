"""API レベルのスモークテスト。一時DBを使い、本番DBを汚さない。"""
import os
import tempfile

import pytest

# app をインポートする前に一時DBを指定する
os.environ['DB_PATH'] = os.path.join(tempfile.mkdtemp(), 'test.db')

from app import app, db  # noqa: E402
from models import Queue, Table  # noqa: E402


@pytest.fixture()
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c
    # 各テスト後にデータをリセット
    with app.app_context():
        Queue.query.delete()
        for t in Table.query.all():
            t.status = '空き'
            t.start_time = None
        db.session.commit()


def first_table_id():
    with app.app_context():
        return Table.query.order_by(Table.id).first().id


def test_pages_ok(client):
    for path in ['/', '/table_management', '/queue_management']:
        assert client.get(path).status_code == 200


def test_start_then_double_start_blocked(client):
    tid = first_table_id()
    assert client.post(f'/api/table/start/{tid}').get_json()['success'] is True
    # 二重開始は 409 で拒否される
    res = client.post(f'/api/table/start/{tid}')
    assert res.status_code == 409
    assert res.get_json()['success'] is False


def test_end_without_start_blocked(client):
    tid = first_table_id()
    res = client.post(f'/api/table/end/{tid}')
    assert res.status_code == 409


def test_start_end_records_history_and_stats(client):
    tid = first_table_id()
    client.post(f'/api/table/start/{tid}')
    assert client.post(f'/api/table/end/{tid}').get_json()['success'] is True
    stats = client.get('/api/stats').get_json()
    assert stats['count'] >= 1


def test_queue_add_and_duplicate(client):
    res = client.post('/api/queue/add', json={'ticket_number': 'T-100', 'party_size': 2})
    assert res.get_json()['success'] is True
    # 同じ番号札は UNIQUE 制約で 409
    dup = client.post('/api/queue/add', json={'ticket_number': 'T-100'})
    assert dup.status_code == 409


def test_queue_empty_ticket_rejected(client):
    res = client.post('/api/queue/add', json={'ticket_number': '   '})
    assert res.status_code == 400


def test_queue_logical_delete_and_undo(client):
    client.post('/api/queue/add', json={'ticket_number': 'T-200'})
    qid = client.get('/api/queue/list').get_json()[0]['id']
    # 対応済みにすると待機列から消え、対応済み一覧に入る
    assert client.post(f'/api/queue/remove/{qid}').get_json()['success'] is True
    assert client.get('/api/queue/list').get_json() == []
    assert len(client.get('/api/queue/done_list').get_json()) == 1
    # 取り消すと待機列へ戻る
    assert client.post(f'/api/queue/undo/{qid}').get_json()['success'] is True
    assert len(client.get('/api/queue/list').get_json()) == 1


def test_table_crud(client):
    add = client.post('/api/table/add', json={'name': 'テスト卓'}).get_json()
    assert add['success'] is True
    new_id = add['id']
    assert client.post(f'/api/table/rename/{new_id}', json={'name': '改名卓'}).get_json()['name'] == '改名卓'
    assert client.post(f'/api/table/delete/{new_id}').get_json()['success'] is True


def test_config_endpoint(client):
    cfg = client.get('/api/config').get_json()
    assert 'time_limit_min' in cfg and 'long_wait_min' in cfg
