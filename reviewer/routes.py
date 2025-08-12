# reviewer/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, jsonify
from flask_mysqldb import MySQL
import uuid
from MySQLdb.cursors import DictCursor
import os
import csv
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from reviewer.services.analysis_service import start_analysis, analyze_frame, stop_analysis
import yt_dlp  # ✅ 유튜브 영상 다운로드용

reviewer_bp = Blueprint('reviewer', __name__, url_prefix='/reviewer')
mysql = MySQL()

def extract_video_id(url: str):
    parsed = urlparse(url or "")
    if 'youtube.com' in parsed.netloc:
        return parse_qs(parsed.query).get('v', [None])[0]
    elif 'youtu.be' in parsed.netloc:
        return parsed.path.lstrip('/')
    return None

# ----------------------------------------------------------------------
# 리뷰어 메인 홈 (마이룸)
# ----------------------------------------------------------------------
@reviewer_bp.route('/myroom')
def myroom():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cur = current_app.mysql.connection.cursor(DictCursor)

    # 코인(포인트) 조회
    cur.execute("SELECT balance FROM reviewer_points WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    coins = row['balance'] if row else 0
    cur.close()

    # (추후 구현) 팔로워/팔로잉
    followers = 0
    followings = 0

    # 템플릿에서 current_app 사용하지 않도록 여기서 존재여부 판단
    has_gift = 'reviewer.gift' in current_app.view_functions

    return render_template(
        'reviewer/myroom.html',
        coins=coins,
        followers=followers,
        followings=followings,
        has_gift=has_gift,
    )


# ----------------------------------------------------------------------
# 리뷰어 대시보드 (모집글 리스트)
# ----------------------------------------------------------------------
@reviewer_bp.route('/dashboard', methods=['GET'], endpoint='dashboard')
def dashboard():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    query = request.args.get('query', '').strip()
    cur = current_app.mysql.connection.cursor(DictCursor)

    if query:
        cur.execute("""
            SELECT * FROM posts
            WHERE is_recruiting = TRUE AND is_deleted = FALSE AND title LIKE %s
            ORDER BY id DESC
        """, (f"%{query}%",))
    else:
        cur.execute("""
            SELECT * FROM posts
            WHERE is_recruiting = TRUE AND is_deleted = FALSE
            ORDER BY id DESC
        """)
    posts = cur.fetchall()
    cur.close()

    return render_template('reviewer/dashboard.html', posts=posts)


# ----------------------------------------------------------------------
# 모집글 상세 보기
# ----------------------------------------------------------------------
@reviewer_bp.route('/post/<int:post_id>')
def view_post(post_id):
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cursor = current_app.mysql.connection.cursor(DictCursor)

    cursor.execute("SELECT * FROM posts WHERE id = %s AND is_deleted = FALSE", (post_id,))
    post = cursor.fetchone()
    if not post:
        cursor.close()
        return "해당 글을 찾을 수 없습니다.", 404

    cursor.execute("SELECT 1 FROM reviewer_post WHERE reviewer_id = %s AND post_id = %s", (user_id, post_id))
    has_accepted = cursor.fetchone() is not None
    cursor.close()

    return render_template('reviewer/view_post.html', post=post, has_accepted=has_accepted)


# ----------------------------------------------------------------------
# 감정 분석 입력 폼
# ----------------------------------------------------------------------
@reviewer_bp.route('/emotion_form')
def emotion_form():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    post_id = request.args.get('post_id', type=int)  # ★ 쿼리스트링에서 받기
    if not post_id:
        return "post_id가 누락되었습니다.", 400
    return render_template('reviewer/emotion_form.html', post_id=post_id)


# ----------------------------------------------------------------------
# 유튜브 링크 분석 시작
# ----------------------------------------------------------------------
@reviewer_bp.route('/analyze_url', methods=['POST'], endpoint='analyze_url')
def handle_analyze_url():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    youtube_url = request.form.get('youtube_url')
    post_id = request.form.get('post_id', type=int)
    if not post_id:
        return "post_id가 누락되었습니다.", 400

    # 전역에 정의한 extract_video_id 사용 (중첩 정의 제거)
    youtube_id = extract_video_id(youtube_url)
    if not youtube_id:
        return "유효하지 않은 유튜브 링크입니다.", 400

    # 고유한 task_id 생성
    task_id = str(uuid.uuid4())

    # ✅ 영상 다운로드 → reviewer/emotion_uploads/{task_id}.mp4 저장
    save_dir = os.path.join("reviewer", "emotion_uploads")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{task_id}.mp4")

    try:
        ydl_opts = {
            'outtmpl': save_path,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'quiet': True,
            'merge_output_format': 'mp4'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        return f"유튜브 영상 다운로드 실패: {e}", 500

    # 분석 중 페이지로 이동
    return redirect(url_for('reviewer.analyzing',
                            task_id=task_id,
                            youtube_id=youtube_id,
                            post_id=post_id))

# ----------------------------------------------------------------------
# 분석 중 페이지
# ----------------------------------------------------------------------

@reviewer_bp.route('/analyzing/<task_id>')
def analyzing(task_id):
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    youtube_id = request.args.get('youtube_id')
    post_id = request.args.get('post_id', type=int)
    if not youtube_id or not post_id:
        return "유튜브 ID 또는 post_id가 누락되었습니다.", 400

    return render_template('reviewer/analyzing.html', task_id=task_id, youtube_id=youtube_id, post_id=post_id)

# ----------------------------------------------------------------------
# 분석 시작 API
# ----------------------------------------------------------------------
@reviewer_bp.route('/start_analysis', methods=['POST'])
def start_analysis_route():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return jsonify({"status": "unauthorized"}), 403

    data = request.get_json()
    task_id = data.get('task_id')
    if not task_id:
        return jsonify({"status": "error", "message": "task_id is required"}), 400

    result = start_analysis(task_id)
    return jsonify(result)


# ----------------------------------------------------------------------
# 프레임 분석 API
# ----------------------------------------------------------------------
@reviewer_bp.route('/analyze_frame', methods=['POST'])
def analyze_frame_route():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return jsonify({"status": "unauthorized"}), 403

    data = request.get_json()
    image_base64 = data.get('image')
    task_id = data.get('task_id')
    video_time = data.get('video_time')

    if not image_base64 or not task_id:
        return jsonify({"status": "error", "message": "이미지 또는 task_id 누락"}), 400

    result = analyze_frame(image_base64, task_id, video_time)
    return jsonify(result)


# ----------------------------------------------------------------------
# 분석 종료 및 파이프라인 실행
# ----------------------------------------------------------------------
@reviewer_bp.route('/stop_analysis', methods=['POST'])
def stop_analysis_route():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return jsonify({"status": "unauthorized"}), 403

    data = request.get_json()
    task_id = data.get('task_id')
    if not task_id:
        return jsonify({"status": "error", "message": "task_id is required"}), 400

    result = stop_analysis(task_id)
    return jsonify(result)


# ----------------------------------------------------------------------
# 리뷰 신청
# ----------------------------------------------------------------------
@reviewer_bp.route('/accept/<int:post_id>', methods=['POST'])
def accept_post(post_id):
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cursor = current_app.mysql.connection.cursor(DictCursor)

    cursor.execute("SELECT id FROM posts WHERE id = %s AND is_deleted = FALSE", (post_id,))
    if cursor.fetchone() is None:
        cursor.close()
        return "해당 글이 존재하지 않거나 삭제되었습니다.", 400

    cursor.execute("INSERT IGNORE INTO reviewer_post (reviewer_id, post_id) VALUES (%s, %s)",
                   (user_id, post_id))
    current_app.mysql.connection.commit()
    cursor.close()

    return redirect(url_for('reviewer.view_post', post_id=post_id))


# ----------------------------------------------------------------------
# 숏폼 결과 선택/제출
# ----------------------------------------------------------------------
@reviewer_bp.route('/submit_result/<int:post_id>', methods=['POST'])
def submit_result(post_id):
    # 권한 체크
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return jsonify({'ok': False, 'msg': '로그인이 필요합니다.'}), 401

    reviewer_id = session.get('user_id')
    data = request.get_json(silent=True) or {}
    selected_ids = data.get('selected_ids', [])

    # 1~3개 확인
    if not isinstance(selected_ids, list) or not (1 <= len(selected_ids) <= 3):
        return jsonify({'ok': False, 'msg': '최소 1개, 최대 3개 선택'}), 400

    # 숫자 변환 (안전)
    try:
        ids = [int(x) for x in selected_ids]
    except (ValueError, TypeError):
        return jsonify({'ok': False, 'msg': '잘못된 ID 형식이 포함되어 있습니다.'}), 400

    placeholders = ",".join(["%s"] * len(ids))
    cur = current_app.mysql.connection.cursor(DictCursor)

    # 소유/일치 검증
    cur.execute(f"""
        SELECT COUNT(*) AS cnt
        FROM reviewer_results
        WHERE id IN ({placeholders}) AND post_id=%s AND reviewer_id=%s
    """, (*ids, post_id, reviewer_id))
    row = cur.fetchone() or {'cnt': 0}
    cnt = row.get('cnt', 0)
    if cnt != len(ids):
        cur.close()
        return jsonify({'ok': False, 'msg': '유효하지 않은 항목이 포함되어 있습니다.'}), 400

    # 기존 선택 초기화
    cur.execute("""
        UPDATE reviewer_results
        SET selected=0
        WHERE post_id=%s AND reviewer_id=%s
    """, (post_id, reviewer_id))

    # 선택 표시
    cur.execute(f"""
        UPDATE reviewer_results
        SET selected=1
        WHERE id IN ({placeholders}) AND post_id=%s AND reviewer_id=%s
    """, (*ids, post_id, reviewer_id))

    # 제출 플래그/시간
    cur.execute("""
        UPDATE reviewer_results
        SET submitted=1, submitted_at=%s
        WHERE post_id=%s AND reviewer_id=%s AND selected=1
    """, (datetime.now(), post_id, reviewer_id))

    current_app.mysql.connection.commit()
    cur.close()
    return jsonify({'ok': True, 'msg': '제출 완료! 크리에이터에게 전달되었습니다.'}), 200


# ----------------------------------------------------------------------
# 결과 페이지 (post_id) - 파일 시스템을 DB에 upsert 후 목록 표시
# ----------------------------------------------------------------------
@reviewer_bp.route('/result/<int:post_id>/<string:task_id>')
def result_page(post_id, task_id):
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))
    reviewer_id = session['user_id']

    # 1) task 폴더에서 mp4 목록 읽기
    out_dir = os.path.join(current_app.root_path, 'static', 'shorts_output', task_id)
    if os.path.isdir(out_dir):
        filenames = sorted([f for f in os.listdir(out_dir) if f.lower().endswith('.mp4')])
    else:
        filenames = []

    cur = current_app.mysql.connection.cursor(DictCursor)

    # 2) 없으면 reviewer_results에 upsert(INSERT if not exists)
    for fname in filenames:
        # 필요한 메타를 파일명에서 대충 파싱 (예: short_01_angry_None_6s_0.80.mp4)
        fname_rel = f"{task_id}/{fname}"
        emotion = None
        ts_str = None
        try:
            parts = fname.split('_')
            # short, 01, angry, None, 6s, 0.80.mp4
            if len(parts) >= 3:
                emotion = parts[2]
            if len(parts) >= 5:
                ts_str = parts[4].split('.')[0]  # "6s"
        except Exception:
            pass

        cur.execute("""
                SELECT id FROM reviewer_results
                WHERE reviewer_id=%s AND post_id=%s AND filename=%s
            """, (reviewer_id, post_id, fname_rel))
        row = cur.fetchone()
        if not row:
            cur.execute("""
                    INSERT INTO reviewer_results (reviewer_id, post_id, filename, emotion, timestamp)
                    VALUES (%s, %s, %s, %s, %s)
                """, (reviewer_id, post_id, fname, emotion, ts_str))
            current_app.mysql.connection.commit()

        # 3) 다시 조회해서 템플릿에 넘길 리스트 구성
    cur.execute("""
            SELECT id, filename, emotion, timestamp
            FROM reviewer_results
            WHERE reviewer_id=%s AND post_id=%s
            ORDER BY id ASC
        """, (reviewer_id, post_id))
    rows = cur.fetchall()
    cur.close()

    videos = [
        {
            "id": r["id"],
            "filename": r["filename"],
            "emotion": r.get("emotion"),
            "timestamp": r.get("timestamp"),
        }
        for r in rows
    ]

    return render_template('reviewer/result.html',
                           videos=videos,
                           task_id=task_id,
                           post_id=post_id)





IMAGE_BASE_URL = '/static/'

@reviewer_bp.route('/shop')
def shop():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cur = current_app.mysql.connection.cursor(DictCursor)

    # 코인 잔액 가져오기
    cur.execute("SELECT balance FROM reviewer_points WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    coins = row['balance'] if row else 0
    cur.close()

    # CSV 파일 읽기
    csv_path = os.path.join(current_app.root_path, 'static', 'data', 'GiftProduct.csv')
    products = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            products.append({
                'id': r['id'],
                'brand_name': r['brand_name'],
                'category': r['category_key'],
                'subcategory': r['subcategory_label'],
                'name': r['name'],
                'short': r['short_desc'],
                'badge': r['badge'],
                'star_price': int(r['star_price']) if r['star_price'] else 0,
                'cash_price': int(r['cash_price']) if r['cash_price'] else 0,
                # CSV에 있는 image_path를 그대로 static 경로로 변환
                'image_url': IMAGE_BASE_URL + r['image_path']
            })

    return render_template('reviewer/shop.html', coins=coins, products=products)

@reviewer_bp.route('/start_analysis/<int:post_id>', methods=['GET'])
def start_analysis_from_post(post_id):
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    # 1) post 조회
    cur = current_app.mysql.connection.cursor(DictCursor)
    cur.execute("SELECT * FROM posts WHERE id=%s AND is_deleted=FALSE", (post_id,))
    post = cur.fetchone()
    cur.close()

    if not post:
        return "해당 글을 찾을 수 없습니다.", 404

    # ⚠️ 여기를 실제 컬럼명으로 맞추세요.
    # 예: video_link / youtube_url / download_url 중 프로젝트에서 쓰는 컬럼
    youtube_url = post.get('video_link') or post.get('youtube_url') or post.get('download_url')
    if not youtube_url:
        # 영상 링크가 없다면 원래 폼으로 유도하거나 에러 처리
        return redirect(url_for('reviewer.emotion_form', post_id=post_id))

    youtube_id = extract_video_id(youtube_url)
    if not youtube_id:
        return "유효하지 않은 유튜브 링크입니다.", 400

    # 2) task_id 생성 및 저장 경로 준비
    task_id = str(uuid.uuid4())
    save_dir = os.path.join("reviewer", "emotion_uploads")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{task_id}.mp4")

    # 3) 유튜브 다운로드 (기존 /analyze_url 과 동일)
    try:
        ydl_opts = {
            'outtmpl': save_path,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
            'quiet': True,
            'merge_output_format': 'mp4'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        return f"유튜브 영상 다운로드 실패: {e}", 500

    # 4) 바로 분석 중 페이지로 이동
    return redirect(url_for('reviewer.analyzing',
                            task_id=task_id,
                            youtube_id=youtube_id,
                            post_id=post_id))
