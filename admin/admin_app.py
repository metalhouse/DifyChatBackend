from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
import base64
import time
import random
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = 'difyadminsecret'
AGENTS_FILE = os.path.join(os.path.dirname(__file__), '../agents.json')
USERS_FILE = os.path.join(os.path.dirname(__file__), '../users.json')

# 加载配置
def load_agents():
    with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_agents(data):
    # 确保所有 dify_api_key 都加密
    for agent in data.get('agents', {}).values():
        key = agent.get('dify_api_key')
        # 若不是base64编码则加密
        try:
            base64.urlsafe_b64decode(key.encode('utf-8'))
        except Exception:
            agent['dify_api_key'] = encode_apikey(key)
    with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def mask_apikey(apikey):
    if not apikey or len(apikey) < 8:
        return '****'
    return apikey[:4] + '*' * (len(apikey)-8) + apikey[-4:]

def encode_apikey(apikey):
    return base64.urlsafe_b64encode(apikey.encode('utf-8')).decode('utf-8')

def decode_apikey(apikey_enc):
    try:
        return base64.urlsafe_b64decode(apikey_enc.encode('utf-8')).decode('utf-8')
    except Exception:
        return apikey_enc

def load_users():
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_password(raw, hashed):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest() == hashed

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        user = users.get(username)
        if user and not user.get('disabled') and check_password(password, user['password']) and user.get('admin'):
            session['admin_user'] = username
            return redirect(url_for('index'))
        flash('用户名或密码错误，或无后台权限，或账号已被禁用')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_user', None)
    flash('已退出登录')
    return redirect(url_for('login'))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@admin_required
def index():
    data = load_agents()
    agents = {}
    for aid, agent in data['agents'].items():
        agents[aid] = dict(agent)
        agents[aid]['masked_key'] = mask_apikey(decode_apikey(agent['dify_api_key']))
    users = load_users()
    return render_template('index.html', agents=agents, user_agents=data['user_agents'], users=users)

@app.route('/add_agent', methods=['POST'])
def add_agent():
    data = load_agents()
    # 自动生成唯一 agent_id，最多尝试10次
    for _ in range(10):
        agent_id = f"agent_{int(time.time())}_{random.randint(1000,9999)}"
        if agent_id not in data['agents']:
            break
    else:
        flash('生成唯一 Agent ID 失败，请重试')
        return redirect(url_for('index'))
    name = request.form['name']
    dify_api_key = encode_apikey(request.form['dify_api_key'])
    data['agents'][agent_id] = {'name': name, 'dify_api_key': dify_api_key}
    save_agents(data)
    flash(f'添加成功，Agent ID: {agent_id}')
    return redirect(url_for('index'))

@app.route('/delete_agent/<agent_id>')
def delete_agent(agent_id):
    data = load_agents()
    if agent_id in data['agents']:
        del data['agents'][agent_id]
        # 同步移除所有用户的分配
        for user in data['user_agents']:
            if agent_id in data['user_agents'][user]:
                data['user_agents'][user].remove(agent_id)
        save_agents(data)
        flash('删除成功')
    return redirect(url_for('index'))

@app.route('/assign_agent', methods=['POST'])
def assign_agent():
    data = load_agents()
    username = request.form['username']
    agent_ids = request.form.getlist('agent_id')
    if username not in data['user_agents']:
        data['user_agents'][username] = []
    added = 0
    for agent_id in agent_ids:
        if agent_id not in data['user_agents'][username]:
            data['user_agents'][username].append(agent_id)
            added += 1
    save_agents(data)
    if added:
        flash(f'分配成功（新增{added}个）')
    else:
        flash('该用户已拥有所选智能体')
    return redirect(url_for('index'))

@app.route('/remove_user_agent', methods=['POST'])
def remove_user_agent():
    data = load_agents()
    username = request.form['username']
    agent_id = request.form['agent_id']
    if username in data['user_agents'] and agent_id in data['user_agents'][username]:
        data['user_agents'][username].remove(agent_id)
        save_agents(data)
        flash('移除成功')
    return redirect(url_for('index'))

@app.route('/edit_agent/<agent_id>', methods=['GET', 'POST'])
def edit_agent(agent_id):
    data = load_agents()
    if request.method == 'POST':
        name = request.form['name']
        dify_api_key = request.form['dify_api_key']
        if agent_id in data['agents']:
            data['agents'][agent_id]['name'] = name
            data['agents'][agent_id]['dify_api_key'] = encode_apikey(dify_api_key)
            save_agents(data)
            flash('修改成功')
        return redirect(url_for('index'))
    agent = data['agents'].get(agent_id)
    # 编辑页显示明文
    agent_show = dict(agent)
    agent_show['dify_api_key'] = decode_apikey(agent['dify_api_key'])
    return render_template('edit_agent.html', agent_id=agent_id, agent=agent_show)

@app.route('/users')
@admin_required
def users_page():
    users = load_users()
    current_user = session.get('admin_user')
    return render_template('users.html', users=users, current_user=current_user)

@app.route('/add_user', methods=['POST'])
@admin_required
def add_user():
    users = load_users()
    username = request.form['username'].strip()
    password = request.form['password']
    is_admin = request.form.get('admin') == 'true'
    if not username or not password:
        flash('用户名和密码不能为空')
        return redirect(url_for('users_page'))
    if username in users:
        flash('用户名已存在')
        return redirect(url_for('users_page'))
    import hashlib
    users[username] = {
        'password': hashlib.sha256(password.encode('utf-8')).hexdigest(),
        'admin': is_admin
    }
    # 同步到 user_agents
    data = load_agents()
    if username not in data['user_agents']:
        data['user_agents'][username] = []
        save_agents(data)
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    flash('用户添加成功')
    return redirect(url_for('users_page'))

@app.route('/delete_user', methods=['POST'])
@admin_required
def delete_user():
    users = load_users()
    username = request.form['username']
    current_user = session.get('admin_user')
    if username == current_user:
        flash('不能删除当前登录用户')
        return redirect(url_for('users_page'))
    if username in users:
        users.pop(username)
        # 同步 user_agents
        data = load_agents()
        if username in data['user_agents']:
            data['user_agents'].pop(username)
            save_agents(data)
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        flash('用户已删除')
    else:
        flash('用户不存在')
    return redirect(url_for('users_page'))

@app.route('/edit_user/<username>', methods=['GET', 'POST'])
@admin_required
def edit_user(username):
    users = load_users()
    user = users.get(username)
    if not user:
        flash('用户不存在')
        return redirect(url_for('users_page'))
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        is_admin = request.form.get('admin') == 'true'
        is_disabled = request.form.get('disabled') == 'true'
        if password:
            user['password'] = hashlib.sha256(password.encode('utf-8')).hexdigest()
        user['admin'] = is_admin
        user['disabled'] = is_disabled
        users[username] = user
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        flash('用户信息已更新')
        return redirect(url_for('users_page'))
    # 兼容老数据
    if 'disabled' not in user:
        user['disabled'] = False
    return render_template('edit_user.html', username=username, user=user)

if __name__ == '__main__':
    app.run(port=5001, debug=True)
