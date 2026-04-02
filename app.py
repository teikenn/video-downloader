from flask import Flask, request, send_file, render_template_string, session, redirect, Response, jsonify, stream_with_context
import subprocess, os, glob, json, re, threading, secrets, time
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('YTDL_SECRET_KEY', 'yt_secret_2026')
DOWNLOAD_DIR = '/root/ytdl/downloads'
USERS_FILE = '/root/ytdl/users.json'
COOKIES_FILE = '/root/ytdl/cookies.txt'
ADMIN_PASSWORD = os.environ.get('YTDL_ADMIN_PASSWORD', 'admin123')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

task = {'running': False, 'percent': 0, 'msg': '', 'success': None, 'error': '', 'filename': ''}
task_lock = threading.Lock()
download_tokens = {}
tokens_lock = threading.Lock()

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE) as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def is_valid(user):
    if user.get('expires') == 'never':
        return True
    try:
        return datetime.strptime(user['expires'], '%Y-%m-%d') >= datetime.now()
    except:
        return False

def get_files():
    all_files = []
    for ext in ['*.mp4', '*.m4a', '*.webm', '*.opus', '*.mp3']:
        all_files.extend(glob.glob(f'{DOWNLOAD_DIR}/{ext}'))
    files = []
    for f in sorted(all_files, key=os.path.getmtime, reverse=True):
        name = os.path.basename(f)
        size = os.path.getsize(f)
        mtime = datetime.fromtimestamp(os.path.getmtime(f)).strftime('%m-%d %H:%M')
        size_str = f'{size/1024/1024:.1f} MB'
        files.append({'name': name, 'size': size_str, 'time': mtime})
    return files

def get_cookies_args():
    if os.path.exists(COOKIES_FILE):
        return ['--cookies', COOKIES_FILE]
    return []

def generate_token(filename):
    token = secrets.token_urlsafe(32)
    expires = time.time() + 86400
    with tokens_lock:
        expired = [k for k, v in download_tokens.items() if v['expires'] < time.time()]
        for k in expired:
            del download_tokens[k]
        download_tokens[token] = {'filename': filename, 'expires': expires}
    return token

def run_download(url, fmt, overwrite):
    global task
    with task_lock:
        task.update({'running': True, 'percent': 0, 'msg': 'preparing...', 'success': None, 'error': '', 'filename': ''})
    try:
        cmd = ['yt-dlp', '-o', f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
               '--merge-output-format', 'mp4', '--newline',
               '-f', fmt] + get_cookies_args() + [url]
        if overwrite:
            cmd.append('--force-overwrites')
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in proc.stdout:
            line = line.strip()
            m = re.search(r'(\d+\.?\d*)%', line)
            if m:
                pct = float(m.group(1))
                with task_lock:
                    task['percent'] = pct
                    task['msg'] = line[:80]
        stderr_output = proc.stderr.read()
        proc.wait()
        with task_lock:
            if proc.returncode == 0:
                task['success'] = True
                task['percent'] = 100
                task['msg'] = 'done'
            else:
                task['success'] = False
                if 'Sign in' in stderr_output or 'bot' in stderr_output or 'cookies' in stderr_output.lower():
                    task['error'] = 'cookie_expired'
                else:
                    task['error'] = 'download failed'
    except Exception as e:
        with task_lock:
            task['success'] = False
            task['error'] = str(e)[:100]
    finally:
        with task_lock:
            task['running'] = False

BASE_STYLE = (
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    '<style>\n'
    '* { box-sizing: border-box; margin: 0; padding: 0; }\n'
    'body { font-family: Georgia, serif; background: #1a1a1a; color: #eee; min-height: 100vh; padding: 20px 16px; }\n'
    '@media (max-width: 600px) {\n'
    '  body { padding: 16px 12px; }\n'
    '  .wrap { max-width: 100%; }\n'
    '  button { padding: 8px 14px; font-size: 0.88em; }\n'
    '  .btn-sm { padding: 5px 10px; font-size: 0.8em; }\n'
    '  .card { padding: 16px; }\n'
    '  h2 { font-size: 1.1em; }\n'
    '  h3 { font-size: 0.95em; }\n'
    '  .modal { padding: 20px; }\n'
    '  .modal-btns { flex-direction: column; }\n'
    '  .modal-btns button { width: 100%; margin-right: 0; margin-bottom: 8px; }\n'
    '}\n'
    '.wrap { max-width: 700px; margin: 0 auto; }\n'
    'h2 { color: #e74c3c; border-left: 4px solid #e74c3c; padding-left: 12px; margin-bottom: 20px; font-size: 1.2em; }\n'
    'h3 { color: #aaa; margin: 28px 0 12px; font-size: 1em; border-bottom: 1px solid #333; padding-bottom: 6px; }\n'
    'input[type=text], input[type=password], input[type=date], select, textarea { width: 100%; padding: 10px 14px; background: #252525; border: 1px solid #444; border-radius: 6px; color: #eee; font-size: 0.95em; margin-bottom: 12px; }\n'
    'textarea { font-family: monospace; font-size: 0.82em; resize: vertical; }\n'
    'button { padding: 9px 18px; background: #e74c3c; color: #fff; border: none; border-radius: 6px; font-size: 0.93em; cursor: pointer; margin-right: 6px; margin-bottom: 6px; }\n'
    'button:hover { opacity: 0.85; }\n'
    '.btn-gray { background: #444; }\n'
    '.btn-green { background: #27ae60; }\n'
    '.btn-blue { background: #2980b9; }\n'
    '.btn-yellow { background: #d68910; }\n'
    '.btn-purple { background: #8e44ad; }\n'
    '.btn-sm { padding: 5px 12px; font-size: 0.83em; }\n'
    '.msg { margin: 14px 0; padding: 10px 14px; border-radius: 6px; font-size: 0.93em; }\n'
    '.ok { background: #1e3a2a; border-left: 4px solid #2ecc71; color: #aee; }\n'
    '.err { background: #3a1e1e; border-left: 4px solid #e74c3c; color: #eaa; }\n'
    '.warn { background: #3a2e1e; border-left: 4px solid #f39c12; color: #fda; }\n'
    '.meta { color: #888; font-size: 0.85em; margin-bottom: 20px; }\n'
    '.meta a { color: #e74c3c; text-decoration: none; margin-left: 10px; }\n'
    '.meta a.admin-link { color: #f39c12; }\n'
    '.tag-ok { color: #2ecc71; } .tag-exp { color: #e74c3c; }\n'
    '.empty { color: #555; text-align: center; padding: 30px; font-size: 0.9em; }\n'
    '.card { background: #242424; border-radius: 10px; padding: 24px; margin-bottom: 20px; }\n'
    '.progress-wrap { margin-top: 14px; }\n'
    '.progress-bar-bg { background: #333; border-radius: 6px; height: 10px; overflow: hidden; }\n'
    '.progress-bar { background: #e74c3c; height: 10px; width: 0%; transition: width 0.3s; border-radius: 6px; }\n'
    '.progress-text { color: #aaa; font-size: 0.85em; margin-top: 6px; }\n'
    '.input-row { display: flex; gap: 8px; margin-bottom: 10px; }\n'
    '.input-row input { margin-bottom: 0; flex: 1; min-width: 0; }\n'
    '.format-row { display: none; margin-bottom: 12px; }\n'
    '.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 100; justify-content: center; align-items: center; }\n'
    '.modal-overlay.show { display: flex; }\n'
    '.modal { background: #2a2a2a; border-radius: 10px; padding: 28px; max-width: 420px; width: 90%; }\n'
    '.modal h3 { color: #f39c12; border-left: 4px solid #f39c12; padding-left: 10px; margin-bottom: 14px; font-size: 1em; }\n'
    '.modal p { color: #aaa; font-size: 0.9em; margin-bottom: 20px; word-break: break-all; }\n'
    '.modal-btns { display: flex; gap: 10px; flex-wrap: wrap; }\n'
    'table { width: 100%; border-collapse: collapse; font-size: 0.9em; }\n'
    'th { background: #333; color: #fff; padding: 9px 12px; text-align: left; }\n'
    'td { padding: 9px 12px; border-bottom: 1px solid #2a2a2a; vertical-align: middle; }\n'
    '.file-card { background: #2a2a2a; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; }\n'
    '.file-name { font-size: 0.95em; color: #eee; word-break: break-all; margin-bottom: 6px; line-height: 1.5; }\n'
    '.file-meta { font-size: 0.82em; color: #888; margin-bottom: 10px; }\n'
    '.file-actions { display: flex; flex-wrap: wrap; gap: 6px; }\n'
    '</style>\n'
)

LOGIN_HTML = BASE_STYLE + '''
<div style="display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px">
<div style="background:#242424;border-radius:10px;padding:30px;width:100%;max-width:420px">
  <h2>Video Downloader</h2>
  <form method="post" action="/login">
    <input type="text" name="username" placeholder="Username">
    <input type="password" name="password" placeholder="Password">
    <button type="submit" style="width:100%">Login</button>
  </form>
  {% if error %}<div class="msg err" style="margin-top:14px">{{ error }}</div>{% endif %}
</div></div>
<script src="/static/main.js"></script>
'''

MAIN_HTML = BASE_STYLE + '''
<div class="wrap">
  <h2 id="i18n-pageTitle">Video Downloader</h2>
  <p class="meta">
    <span id="i18n-account-label">Account</span>: {{ username }}
    &nbsp;|&nbsp;
    <span id="i18n-expires-label">Expires</span>: {{ expires }}
    <a href="/logout" id="i18n-logout">Logout</a>
    {% if is_admin %}<a href="/admin" class="admin-link" id="i18n-adminPanel">Admin Panel</a>{% endif %}
  </p>
  <div class="card">
    <div class="input-row">
      <input type="text" id="urlInput" placeholder="Paste video URL (YouTube, etc.)">
      <button class="btn-yellow" id="i18n-pasteBtn" onclick="pasteUrl()">Paste</button>
      <button class="btn-gray" id="i18n-clearBtn" onclick="clearUrl()">Clear</button>
    </div>
    <div class="format-row" id="formatRow">
      <select id="formatSelect"></select>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button id="fetchBtn" onclick="fetchFormats()">Get Quality</button>
      <button id="dlbtn" class="btn-green" onclick="startDownload(false)" style="display:none">Save to Server</button>
      <button id="streambtn" class="btn-blue" onclick="startStream()" style="display:none">Direct Download</button>
    </div>
    <div id="taskArea"></div>
    <div id="msgBox"></div>
  </div>
  <h3><span id="i18n-cachedFiles">Cached Files</span>(<span id="fileCount">{{ files|length }}</span>)</h3>
  <div id="fileList">
  {% if files %}
    {% for f in files %}
    <div class="file-card">
      <div class="file-name">{{ f.name }}</div>
      <div class="file-meta">{{ f.size }} &nbsp;.&nbsp; {{ f.time }}</div>
      <div class="file-actions">
        <a href="/file/{{ f.name }}"><button class="btn-blue btn-sm">Download</button></a>
        <button class="btn-purple btn-sm" onclick="copyLink('{{ f.name | e }}')">Copy Link</button>
        <button class="btn-gray btn-sm" onclick="deleteFile('{{ f.name | e }}')">Delete</button>
      </div>
    </div>
    {% endfor %}
  {% else %}
  <div class="empty" id="i18n-noFiles">No cached files</div>
  {% endif %}
  </div>
</div>

<div class="modal-overlay" id="existsModal">
  <div class="modal">
    <h3 id="i18n-existsTitle">File already exists</h3>
    <p id="existsFilename"></p>
    <div class="modal-btns">
      <button class="btn-green" id="i18n-overwriteBtn" onclick="confirmOverwrite()">Overwrite</button>
      <button class="btn-gray" id="i18n-cancelExists" onclick="closeModal('existsModal')">Cancel</button>
    </div>
  </div>
</div>

<div class="modal-overlay" id="streamWarnModal">
  <div class="modal">
    <h3 id="i18n-streamWarnTitle">Format not supported for direct download</h3>
    <p id="i18n-streamWarnMsg">Best quality requires merging. Switch to server save?</p>
    <div class="modal-btns">
      <button class="btn-green" id="i18n-streamWarnSave" onclick="closeModal('streamWarnModal');startDownload(false)">Save to Server</button>
      <button class="btn-gray" id="i18n-streamWarnCancel" onclick="closeModal('streamWarnModal')">Cancel</button>
    </div>
  </div>
</div>

<div class="modal-overlay" id="linkModal">
  <div class="modal">
    <h3 id="i18n-linkTitle">Direct Link (valid 24h)</h3>
    <p id="linkText" style="background:#1a1a1a;padding:10px;border-radius:6px;font-size:0.82em;font-family:monospace;color:#aef;word-break:break-all"></p>
    <div class="modal-btns" style="margin-top:16px">
      <button class="btn-purple" id="i18n-copyLinkBtn" onclick="doCopyLink()">Copy</button>
      <button class="btn-gray" id="i18n-closeLinkBtn" onclick="closeModal('linkModal')">Close</button>
    </div>
  </div>
</div>

<div class="modal-overlay" id="streamLinkModal">
  <div class="modal">
    <h3 id="i18n-streamLinkTitle">Direct Download Link (valid 24h)</h3>
    <p id="streamLinkText" style="background:#1a1a1a;padding:10px;border-radius:6px;font-size:0.82em;font-family:monospace;color:#aef;word-break:break-all"></p>
    <div class="modal-btns" style="margin-top:16px">
      <button class="btn-blue" id="i18n-streamDownloadBtn" onclick="doStreamDownload()">Download</button>
      <button class="btn-purple" id="i18n-streamCopyBtn" onclick="doStreamCopy()">Copy</button>
      <button class="btn-gray" id="i18n-streamCancelBtn" onclick="closeModal('streamLinkModal')">Cancel</button>
    </div>
  </div>
</div>

<script src="/static/main.js"></script>
'''

ADMIN_HTML = BASE_STYLE + '''
<div class="wrap">
  <h2 id="i18n-adminTitle">Admin Panel</h2>
  <p class="meta"><a href="/" id="i18n-backToDownload" style="color:#aaa">Back to Download</a></p>
  <div class="card">
    <h3 id="i18n-createAccountTitle" style="margin-top:0">Create Account</h3>
    <form method="post" action="/admin/create">
      <input type="text" name="username" placeholder="Username">
      <input type="password" name="password" placeholder="Password">
      <select name="expires">
        <option value="7">7 days</option>
        <option value="30">30 days</option>
        <option value="90">90 days</option>
        <option value="never">Permanent</option>
      </select>
      <button class="btn-green" id="i18n-createBtn">Create</button>
    </form>
    {% if msg and msg_type != "cookies_ok" %}<div class="msg {{ msg_type }}" style="margin-top:14px">{{ msg }}</div>{% endif %}
  </div>
  <div class="card">
    <h3 id="i18n-updateCookiesTitle" style="margin-top:0">Update Cookies</h3>
    <p id="i18n-cookiesHint" style="color:#888;font-size:0.88em;margin-bottom:12px">Export cookies.txt from browser and paste below to save.</p>
    <form method="post" action="/admin/cookies">
      <textarea name="cookies" rows="8" placeholder="Paste cookies.txt content...">{{ cookies_content }}</textarea>
      <button class="btn-yellow" id="i18n-saveCookiesBtn">Save Cookies</button>
    </form>
    {% if msg and msg_type == "cookies_ok" %}<div class="msg ok" style="margin-top:14px">{{ msg }}</div>{% endif %}
  </div>
  <h3 id="i18n-accountListTitle">Account List</h3>
  <table>
    <tr>
      <th id="i18n-colUsername">Username</th>
      <th id="i18n-colExpires">Expires</th>
      <th id="i18n-colStatus">Status</th>
      <th id="i18n-colActions">Actions</th>
    </tr>
    {% for u, info in users.items() %}
    <tr>
      <td>{{ u }}</td>
      <td>{{ info.expires }}</td>
      <td>{% if info.valid %}<span class="tag-ok">Valid</span>{% else %}<span class="tag-exp">Expired</span>{% endif %}</td>
      <td>
        <form method="post" action="/admin/delete" style="display:inline">
          <input type="hidden" name="username" value="{{ u }}">
          <button type="submit" class="btn-gray btn-sm">Delete</button>
        </form>
      </td>
    </tr>
    {% endfor %}
  </table>
</div>
<script src="/static/main.js"></script>
'''

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_file('/root/ytdl/static/' + filename)

@app.route('/')
def index():
    if not session.get('logged_in'):
        return render_template_string(LOGIN_HTML, error=None)
    return render_template_string(MAIN_HTML,
        username=session['username'], expires=session['expires'],
        is_admin=session.get('is_admin'), files=get_files())

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    if username == 'admin' and password == ADMIN_PASSWORD:
        session.update({'logged_in': True, 'username': 'admin', 'expires': 'Permanent', 'is_admin': True})
        return redirect('/')
    users = load_users()
    u = users.get(username)
    if u and u['password'] == password:
        if not is_valid(u):
            return render_template_string(LOGIN_HTML, error='Account expired')
        session.update({'logged_in': True, 'username': username, 'expires': u['expires'], 'is_admin': False})
        return redirect('/')
    return render_template_string(LOGIN_HTML, error='Invalid username or password')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/formats')
def formats():
    if not session.get('logged_in'):
        return ('', 403)
    url = request.args.get('url', '').strip()
    try:
        cmd = ['yt-dlp', '-F'] + get_cookies_args() + [url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        lines = result.stdout.strip().split('\n')
        fmts = []
        fmts.append({'id': 'bestvideo+bestaudio/best', 'label': 'Best Quality (save to server)'})
        fmts.append({'id': 'best', 'label': 'Best Single File (direct download)'})
        fmts.append({'id': 'bestaudio/best', 'label': 'Best Audio (direct download)'})
        for line in lines:
            if re.match(r'^\d+\s', line):
                parts = line.split()
                fid = parts[0]
                ext = parts[1] if len(parts) > 1 else ''
                res = parts[2] if len(parts) > 2 else ''
                size_match = re.search(r'(\d+\.?\d*)(MiB|GiB|KiB)', line)
                size_str = ' | ' + size_match.group(1) + size_match.group(2) if size_match else ''
                if 'audio only' in line:
                    label = 'Audio only | ' + ext + size_str
                elif res and 'x' in res:
                    label = res + ' | ' + ext + size_str
                else:
                    label = ext + ' ' + res + size_str
                fmts.append({'id': fid, 'label': label})
        return json.dumps({'formats': fmts})
    except Exception as e:
        return json.dumps({'error': str(e)[:100]})

@app.route('/start', methods=['POST'])
def start_download():
    if not session.get('logged_in'):
        return ('', 403)
    data = request.get_json()
    url = data.get('url', '').strip()
    fmt = data.get('format', 'bestvideo+bestaudio/best')
    overwrite = data.get('overwrite', False)
    if not url:
        return jsonify({'error': 'Please enter a URL'})
    if task['running']:
        return jsonify({'error': 'Download in progress, please wait'})
    if not overwrite:
        title_cmd = ['yt-dlp', '--get-filename', '-o', '%(title)s.%(ext)s', '-f', fmt] + get_cookies_args() + [url]
        title_proc = subprocess.run(title_cmd, capture_output=True, text=True)
        filename = title_proc.stdout.strip()
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        if filename and os.path.exists(filepath):
            return jsonify({'exists': True, 'filename': filename})
    t = threading.Thread(target=run_download, args=(url, fmt, overwrite), daemon=True)
    t.start()
    return jsonify({'ok': True})

@app.route('/streamtoken', methods=['POST'])
def stream_token():
    if not session.get('logged_in'):
        return ('', 403)
    data = request.get_json()
    url = data.get('url', '').strip()
    fmt = data.get('format', 'best')
    if not url:
        return jsonify({'error': 'Please enter a URL'})
    token = secrets.token_urlsafe(32)
    expires = time.time() + 86400
    with tokens_lock:
        download_tokens[token] = {'stream_url': url, 'stream_fmt': fmt, 'expires': expires, 'filename': None}
    return jsonify({'token': token})

@app.route('/stream/<token>')
def stream_by_token(token):
    with tokens_lock:
        info = download_tokens.get(token)
    if not info or 'stream_url' not in info:
        return 'Link not found or expired', 404
    if info['expires'] < time.time():
        with tokens_lock:
            download_tokens.pop(token, None)
        return 'Link expired', 410
    url = info['stream_url']
    fmt = info['stream_fmt']
    title_cmd = ['yt-dlp', '--get-filename', '-o', '%(title)s.%(ext)s', '-f', fmt] + get_cookies_args() + [url]
    title_proc = subprocess.run(title_cmd, capture_output=True, text=True, timeout=30)
    filename = title_proc.stdout.strip() or 'video.mp4'
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'mp4'
    mime_map = {'mp4': 'video/mp4', 'webm': 'video/webm', 'm4a': 'audio/mp4', 'opus': 'audio/ogg', 'mp3': 'audio/mpeg'}
    mime = mime_map.get(ext, 'application/octet-stream')
    cmd = ['yt-dlp', '-o', '-', '-f', fmt] + get_cookies_args() + [url]
    def generate():
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            proc.kill()
    from urllib.parse import quote
    encoded_name = quote(filename)
    headers = {
        'Content-Disposition': "attachment; filename*=UTF-8''" + encoded_name,
        'Content-Type': mime,
        'X-Accel-Buffering': 'no'
    }
    return Response(stream_with_context(generate()), headers=headers)

@app.route('/stream')
def stream():
    if not session.get('logged_in'):
        return redirect('/')
    url = request.args.get('url', '').strip()
    fmt = request.args.get('format', 'best')
    if not url:
        return 'Missing URL', 400
    title_cmd = ['yt-dlp', '--get-filename', '-o', '%(title)s.%(ext)s', '-f', fmt] + get_cookies_args() + [url]
    title_proc = subprocess.run(title_cmd, capture_output=True, text=True, timeout=30)
    filename = title_proc.stdout.strip() or 'video.mp4'
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'mp4'
    mime_map = {'mp4': 'video/mp4', 'webm': 'video/webm', 'm4a': 'audio/mp4', 'opus': 'audio/ogg', 'mp3': 'audio/mpeg'}
    mime = mime_map.get(ext, 'application/octet-stream')
    cmd = ['yt-dlp', '-o', '-', '-f', fmt] + get_cookies_args() + [url]
    def generate():
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            proc.kill()
    from urllib.parse import quote
    encoded_name = quote(filename)
    headers = {
        'Content-Disposition': "attachment; filename*=UTF-8''" + encoded_name,
        'Content-Type': mime,
        'X-Accel-Buffering': 'no'
    }
    return Response(stream_with_context(generate()), headers=headers)

@app.route('/token', methods=['POST'])
def create_token():
    if not session.get('logged_in'):
        return ('', 403)
    data = request.get_json()
    filename = data.get('filename', '')
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if not filename or not os.path.exists(filepath):
        return jsonify({'error': 'File not found'})
    token = generate_token(filename)
    return jsonify({'token': token})

@app.route('/dl/<token>')
def download_by_token(token):
    with tokens_lock:
        info = download_tokens.get(token)
    if not info:
        return 'Link not found or expired', 404
    if info['expires'] < time.time():
        with tokens_lock:
            download_tokens.pop(token, None)
        return 'Link expired', 410
    path = os.path.join(DOWNLOAD_DIR, info['filename'])
    if not os.path.exists(path):
        return 'File not found', 404
    return send_file(path, as_attachment=True, download_name=info['filename'])

@app.route('/status')
def status():
    if not session.get('logged_in'):
        return ('', 403)
    with task_lock:
        return jsonify({
            'running': task['running'],
            'percent': task['percent'],
            'msg': task['msg'],
            'success': task['success'],
            'error': task['error']
        })

@app.route('/filelist')
def filelist():
    if not session.get('logged_in'):
        return ('', 403)
    return json.dumps(get_files())

@app.route('/delete', methods=['POST'])
def delete_file():
    if not session.get('logged_in'):
        return ('', 403)
    filename = request.form.get('filename', '')
    path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    return ('', 204)

@app.route('/file/<path:filename>')
def serve_file(filename):
    if not session.get('logged_in'):
        return redirect('/')
    path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name=filename)
    return 'File not found', 404

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect('/')
    users = load_users()
    for u in users.values():
        u['valid'] = is_valid(u)
    cookies_content = ''
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE) as f:
            cookies_content = f.read()
    return render_template_string(ADMIN_HTML, users=users, msg=None, msg_type=None, cookies_content=cookies_content)

@app.route('/admin/cookies', methods=['POST'])
def update_cookies():
    if not session.get('is_admin'):
        return redirect('/')
    content = request.form.get('cookies', '').strip()
    with open(COOKIES_FILE, 'w') as f:
        f.write(content)
    users = load_users()
    for u in users.values():
        u['valid'] = is_valid(u)
    return render_template_string(ADMIN_HTML, users=users, msg='Cookies updated', msg_type='cookies_ok', cookies_content=content)

@app.route('/admin/create', methods=['POST'])
def create_user():
    if not session.get('is_admin'):
        return redirect('/')
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    days = request.form.get('expires')
    users = load_users()
    if not username or not password:
        for u in users.values():
            u['valid'] = is_valid(u)
        cookies_content = open(COOKIES_FILE).read() if os.path.exists(COOKIES_FILE) else ''
        return render_template_string(ADMIN_HTML, users=users, msg='Username and password cannot be empty', msg_type='err', cookies_content=cookies_content)
    expires = 'never' if days == 'never' else (datetime.now() + timedelta(days=int(days))).strftime('%Y-%m-%d')
    users[username] = {'password': password, 'expires': expires}
    save_users(users)
    for u in users.values():
        u['valid'] = is_valid(u)
    cookies_content = open(COOKIES_FILE).read() if os.path.exists(COOKIES_FILE) else ''
    return render_template_string(ADMIN_HTML, users=users, msg='Account ' + username + ' created', msg_type='ok', cookies_content=cookies_content)

@app.route('/admin/delete', methods=['POST'])
def delete_user():
    if not session.get('is_admin'):
        return redirect('/')
    username = request.form.get('username')
    users = load_users()
    users.pop(username, None)
    save_users(users)
    for u in users.values():
        u['valid'] = is_valid(u)
    cookies_content = open(COOKIES_FILE).read() if os.path.exists(COOKIES_FILE) else ''
    return render_template_string(ADMIN_HTML, users=users, msg='Account ' + username + ' deleted', msg_type='ok', cookies_content=cookies_content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, threaded=True)
