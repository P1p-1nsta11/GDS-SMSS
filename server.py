import os
import json
import random
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATA_DIR = "users_data"
REPORTS_FILE = "reports.json"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if not os.path.exists(REPORTS_FILE):
    with open(REPORTS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)


def generate_unique_id():
    while True:
        rand_id = f"{random.randint(0, 999999999):09d}"
        file_path = os.path.join(DATA_DIR, f"{rand_id}.json")
        if not os.path.exists(file_path):
            return rand_id


def find_user_by_username(username):
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(DATA_DIR, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('username', '').lower() == username.lower():
                        return data
            except Exception:
                continue
    return None


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    age = data.get('age', '').strip()
    gender = data.get('gender', '').strip()

    if not username or not password:
        return jsonify({'error': 'Нікнейм та пароль обов\'язкові!'}), 400

    if find_user_by_username(username):
        return jsonify({'error': 'Цей нікнейм вже зайнятий!'}), 400

    user_id = generate_unique_id()
    user_data = {
        'id': user_id,
        'username': username,
        'password': password,
        'age': age if age else '?',
        'gender': gender if gender else '?',
        'following': [],  # Список ID на кого підписаний
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'messages': []
    }

    file_path = os.path.join(DATA_DIR, f"{user_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

    safe_user = user_data.copy()
    del safe_user['password']
    return jsonify({'status': 'ok', 'user': safe_user})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Введіть нік та пароль!'}), 400

    user_data = find_user_by_username(username)
    if not user_data or user_data.get('password') != password:
        return jsonify({'error': 'Невірний логін або пароль!'}), 401

    safe_user = user_data.copy()
    del safe_user['password']
    return jsonify({'status': 'ok', 'user': safe_user})


@app.route('/api/get_profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    file_path = os.path.join(DATA_DIR, f"{user_id}.json")
    if not os.path.exists(file_path):
        return jsonify({'error': 'Користувача не знайдено'}), 404

    with open(file_path, 'r', encoding='utf-8') as f:
        user_data = json.load(f)

    safe_user = user_data.copy()
    if 'password' in safe_user:
        del safe_user['password']
    return jsonify(safe_user)


@app.route('/api/get_user_info/<user_id>', methods=['GET'])
def get_user_info(user_id):
    """Повертає розширену інформацію про користувача (для списку підписок і карток)"""
    file_path = os.path.join(DATA_DIR, f"{user_id}.json")
    if not os.path.exists(file_path):
        return jsonify({'username': 'Unknown', 'age': '?', 'gender': '?'})
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return jsonify({
            'id': data.get('id'),
            'username': data.get('username', 'User'),
            'age': data.get('age', '?'),
            'gender': data.get('gender', '?')
        })


@app.route('/api/toggle_follow', methods=['POST'])
def toggle_follow():
    """Підписатися або відписатися від користувача"""
    data = request.json or {}
    user_id = data.get('user_id')
    target_id = data.get('target_id')

    if user_id == target_id:
        return jsonify({'error': 'Не можна підписатися на самого себе!'}), 400

    user_file = os.path.join(DATA_DIR, f"{user_id}.json")
    target_file = os.path.join(DATA_DIR, f"{target_id}.json")

    if not os.path.exists(user_file) or not os.path.exists(target_file):
        return jsonify({'error': 'Користувача не знайдено'}), 404

    with open(user_file, 'r+', encoding='utf-8') as f:
        udata = json.load(f)
        following = udata.get('following', [])

        is_following = target_id in following
        if is_following:
            following.remove(target_id)
            action = 'unfollowed'
        else:
            following.append(target_id)
            action = 'followed'

        udata['following'] = following
        f.seek(0)
        json.dump(udata, f, ensure_ascii=False, indent=2)
        f.truncate()

    return jsonify({'status': 'ok', 'action': action})


@app.route('/api/report', methods=['POST'])
def report_user():
    """Система репортів на гравців"""
    data = request.json or {}
    reporter_id = data.get('reporter_id')
    target_id = data.get('target_id')
    reason = data.get('reason', 'Без причини').strip()

    report_entry = {
        'reporter_id': reporter_id,
        'target_id': target_id,
        'reason': reason,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    try:
        with open(REPORTS_FILE, 'r+', encoding='utf-8') as f:
            reports = json.load(f)
            reports.append(report_entry)
            f.seek(0)
            json.dump(reports, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return jsonify({'status': 'reported'})


@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.json or {}
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    text = data.get('text', '').strip()
    img_data = data.get('image', None)

    if not text and not img_data:
        return jsonify({'error': 'Повідомлення не може бути порожнім!'}), 400

    receiver_file = os.path.join(DATA_DIR, f"{receiver_id}.json")
    sender_file = os.path.join(DATA_DIR, f"{sender_id}.json")

    if not os.path.exists(receiver_file) or not os.path.exists(sender_file):
        return jsonify({'error': 'Один із користувачів не існує'}), 404

    now = datetime.now()
    msg_obj_in = {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'text': text,
        'image': img_data,
        'time': now.strftime('%H:%M:%S'),
        'date': now.strftime('%Y-%m-%d'),
        'timestamp': now.timestamp(),
        'type': 'incoming'
    }

    msg_obj_out = {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'text': text,
        'image': img_data,
        'time': now.strftime('%H:%M:%S'),
        'date': now.strftime('%Y-%m-%d'),
        'timestamp': now.timestamp(),
        'type': 'outgoing'
    }

    # Зберігаємо одержувачу (ліміт 100)
    with open(receiver_file, 'r+', encoding='utf-8') as f:
        udata = json.load(f)
        udata['messages'].append(msg_obj_in)
        udata['messages'].sort(key=lambda x: x.get('timestamp', 0))
        if len(udata['messages']) > 100:
            udata['messages'] = udata['messages'][-100:]
        f.seek(0)
        json.dump(udata, f, ensure_ascii=False, indent=2)
        f.truncate()

    # Зберігаємо відправнику
    if sender_id != receiver_id:
        with open(sender_file, 'r+', encoding='utf-8') as f:
            udata = json.load(f)
            udata['messages'].append(msg_obj_out)
            udata['messages'].sort(key=lambda x: x.get('timestamp', 0))
            if len(udata['messages']) > 100:
                udata['messages'] = udata['messages'][-100:]
            f.seek(0)
            json.dump(udata, f, ensure_ascii=False, indent=2)
            f.truncate()

    return jsonify({'status': 'sent', 'message': msg_obj_out})


if __name__ == '__main__':
    print("=== GDS Messages Server Started on http://127.0.0.1:5000 ===")
    app.run(host='127.0.0.1', port=5000, debug=True)
