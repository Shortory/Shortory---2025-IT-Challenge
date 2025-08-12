# result_routes.py
# 결과/진행률 관련 라우트

from flask import Blueprint, render_template, jsonify, session, redirect, url_for, current_app, request
import os
from reviewer.services.result_service import get_progress, is_analysis_completed, get_result_clips
from MySQLdb.cursors import DictCursor


# ✅ 이 파일에서는 result_bp만 사용 (reviewer_bp 선언/사용 금지)
result_bp = Blueprint('result', __name__, url_prefix='/reviewer')


# 1) 분석 종료 직후 대기 페이지
@result_bp.route('/waiting_analysis/<int:post_id>/<string:task_id>')
def waiting_analysis(post_id, task_id):
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))
    return render_template('reviewer/waiting_analysis.html',
                           post_id=post_id, task_id=task_id)


# 2) 진행률 폴링
@result_bp.route('/progress/<task_id>')
def progress(task_id):
    return jsonify({"progress": get_progress(task_id)})


# 3) 완료 여부 폴링 (done.flag 확인)
@result_bp.route('/check_analysis_status/<task_id>')
def check_analysis_status(task_id):
    # ✅ Flask 루트 디렉토리 (.flaskroot) 탐색
    cur = os.path.abspath(os.path.dirname(__file__))
    root_dir = None
    while cur != os.path.dirname(cur):
        if '.flaskroot' in os.listdir(cur):
            root_dir = cur
            break
        cur = os.path.dirname(cur)

    if not root_dir:
        return jsonify({'status': 'error', 'message': 'Flask 루트(.flaskroot) 못 찾음'})

    done_flag_path = os.path.join(root_dir, 'static', 'shorts_output', task_id, 'done.flag')
    print(f"[CHECK] done.flag 경로 확인: {done_flag_path}")

    if os.path.exists(done_flag_path):
        print(f"[CHECK] 완료된 분석 결과 확인됨: {done_flag_path}")
        return jsonify({'status': 'completed'})

    print(f"[CHECK] 진행 중...: {done_flag_path} 존재하지 않음")
    return jsonify({'status': 'processing'})


# 4) 결과 페이지
#    👉 analyzing.html / waiting_analysis.html 에서 이 경로로 이동합니다:
#    /reviewer/result/<post_id>/<task_id>
@result_bp.route('/result/<int:post_id>/<string:task_id>')
def result(post_id, task_id):
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    # 파일 기반으로 생성된 mp4 수집 (필요시 DB 연동은 reviewer/routes.py에서 처리)
    # get_result_clips(task_id)는 static/shorts_output/<task_id>/ 안의 mp4를 읽어 리스트 반환하도록 구현되어 있어야 함
    videos = get_result_clips(task_id)

    # (선택) 경과 시간 표시는 나중에 실제 값으로 교체
    elapsed_time = "2분 30초"

    return render_template("reviewer/result.html",
                           post_id=post_id,
                           task_id=task_id,
                           videos=videos,
                           elapsed_time=elapsed_time)


# 5) 보관함 저장
@result_bp.route('/save_clip', methods=['POST'])
def save_clip():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return jsonify({"status": "unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    # 프론트가 어떤 키로 보내든 흡수
    short_name = data.get('filename') or data.get('file') or data.get('name')
    emotion    = data.get('emotion')      # 없어도 OK
    timestamp  = data.get('timestamp')    # 없어도 OK

    # post_id / task_id 최대한 보완: body → query → session → referrer
    post_id = data.get('post_id') or request.args.get('post_id', type=int) or session.get('current_post_id')
    task_id = data.get('task_id') or session.get('current_task_id')
    if (not post_id or not task_id) and request.referrer:
        try:
            from urllib.parse import urlparse
            seg = urlparse(request.referrer).path.strip('/').split('/')
            # /reviewer/result/<post_id>/<task_id>
            if len(seg) >= 4 and seg[0] == 'reviewer' and seg[1] == 'result':
                if not post_id:
                    post_id = int(seg[2])
                if not task_id:
                    task_id = seg[3]
        except Exception:
            pass

    if not short_name:
        return jsonify({"status": "error", "message": "filename 누락"}), 400
    if not post_id:
        return jsonify({"status": "error", "message": "post_id 누락"}), 400

    # 저장용 파일키 만들기: "taskid/파일명" (이미 경로 포함이면 그대로)
    stored_filename = short_name if '/' in short_name else (f"{task_id}/{short_name}" if task_id else None)

    reviewer_id = session.get('user_id')
    cur = current_app.mysql.connection.cursor()

    # task_id를 못 구했으면 DB에서 suffix 매칭으로 복원 시도
    if not stored_filename:
        cur.execute("""
            SELECT filename FROM reviewer_results
            WHERE reviewer_id=%s AND post_id=%s AND filename LIKE %s
            ORDER BY id DESC LIMIT 1
        """, (reviewer_id, post_id, f"%/{short_name}"))
        row = cur.fetchone()
        if row:
            stored_filename = row[0]

    if not stored_filename:
        cur.close()
        return jsonify({"status": "error", "message": "task_id를 알 수 없어 저장 경로를 만들 수 없습니다."}), 400

    # 중복 저장 방지
    cur.execute("""
        SELECT id FROM saved_clips
        WHERE reviewer_id=%s AND post_id=%s AND filename=%s
    """, (reviewer_id, post_id, stored_filename))
    if cur.fetchone():
        cur.close()
        return jsonify({"status": "ok", "message": "이미 저장됨"}), 200

    # 저장
    cur.execute("""
        INSERT INTO saved_clips (reviewer_id, post_id, filename, emotion, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    """, (reviewer_id, post_id, stored_filename, emotion, timestamp))
    current_app.mysql.connection.commit()
    cur.close()

    return jsonify({"status": "success"})


# 6) 보관함 보기
@result_bp.route('/categories_view')
def categories_view():
    if 'loggedin' not in session or session.get('role') != 'reviewer':
        return redirect(url_for('auth.login'))

    reviewer_id = session.get('user_id')
    cur = current_app.mysql.connection.cursor(DictCursor)
    cur.execute("""
        SELECT filename, emotion, timestamp, saved_at
        FROM saved_clips
        WHERE reviewer_id=%s
        ORDER BY saved_at DESC
    """, (reviewer_id,))
    rows = cur.fetchall()
    cur.close()

    clips = []
    base_dir = os.path.join(current_app.root_path, 'static', 'shorts_output')
    for r in rows:
        stored = r['filename'] or ""      # 예: "<task_id>/short_01_....mp4" 또는 "short_01_..."
        # task_id/파일명 보정: task_id 없는 경우는 건너뜀(경로 확정 불가)
        if '/' not in stored:
            continue
        abs_path = os.path.join(base_dir, stored)
        if not os.path.isfile(abs_path):
            continue

        video_url = url_for('static', filename=f"shorts_output/{stored}")
        # 캐시 무효화(메타데이터 갱신)
        if r['saved_at']:
            video_url += f"?v={int(r['saved_at'].timestamp())}"

        clips.append({
            "video_url": video_url,
            "emotion": r.get("emotion"),
            "timestamp": r.get("timestamp"),
            "saved_at": r.get("saved_at"),
        })

    return render_template("reviewer/categories_view.html", clips=clips)
