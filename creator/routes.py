# creator/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, abort, current_app, jsonify
from datetime import datetime
from MySQLdb.cursors import DictCursor
import os, glob

creator_bp = Blueprint('creator', __name__, url_prefix='/creator')


# 크리에이터 대시보드
@creator_bp.route('/dashboard')
def dashboard():
    if 'loggedin' not in session or session.get('role') != 'creator':
        return redirect(url_for('auth.login'))

    username = session.get('username')
    user_id = session.get('user_id')

    cursor = current_app.mysql.connection.cursor(DictCursor)
    cursor.execute("""
        SELECT * FROM posts 
        WHERE creator_id = %s AND is_deleted = FALSE
        ORDER BY id DESC
    """, (user_id,))
    posts = cursor.fetchall()
    cursor.close()

    return render_template('creator/dashboard.html', username=username, posts=posts)


# 감정 + 시선 분석 기반 숏폼 제작 페이지
@creator_bp.route('/emo_gaze_tool')
def emo_gaze_tool():
    if 'loggedin' not in session or session.get('role') != 'creator':
        return redirect(url_for('auth.login'))

    username = session.get('username')
    user_id = session.get('user_id')

    cursor = current_app.mysql.connection.cursor(DictCursor)
    cursor.execute("""
        SELECT * FROM posts 
        WHERE creator_id = %s AND is_deleted = FALSE
        ORDER BY id DESC
    """, (user_id,))
    posts = cursor.fetchall()
    cursor.close()

    return render_template('creator/emo_gaze_tool.html', username=username, posts=posts)


# 타임스탬프 기반 숏폼 제작 페이지
@creator_bp.route('/timestamp_tool')
def timestamp_tool():
    if 'loggedin' not in session or session.get('role') != 'creator':
        return redirect(url_for('auth.login'))

    return render_template('creator/timestamp_tool.html')


# 리뷰어 모집글 등록
@creator_bp.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'loggedin' not in session or session.get('role') != 'creator':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        video_link = request.form['video_link']
        creator_id = session['user_id']

        cursor = current_app.mysql.connection.cursor(DictCursor)
        cursor.execute("""
            INSERT INTO posts (creator_id, title, description, video_link) 
            VALUES (%s, %s, %s, %s)
        """, (creator_id, title, description, video_link))
        current_app.mysql.connection.commit()

        cursor.execute("SELECT LAST_INSERT_ID() AS id")
        post_id = cursor.fetchone()['id']
        cursor.close()

        return render_template('creator/create_complete.html', post_id=post_id)

    return render_template('creator/create_post.html')


# 모집글 상세 보기 (+ 하단 리뷰어 리스트 포함)
@creator_bp.route('/post/<int:post_id>', endpoint='view_post')
def view_post(post_id):
    if 'loggedin' not in session or session.get('role') != 'creator':
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    cursor = current_app.mysql.connection.cursor(DictCursor)

    # 글 정보
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()
    if not post:
        cursor.close()
        return "해당 글을 찾을 수 없습니다.", 404

    is_owner = (post['creator_id'] == user_id)

    # 소유자일 때만 리뷰어 리스트 조회
    reviewers = []
    if is_owner:
        cursor.execute("""
            SELECT 
              u.id   AS reviewer_id,
              u.name AS reviewer_name,
              u.email AS reviewer_email,
              MAX(CASE WHEN rr.submitted=1 THEN 1 ELSE 0 END) AS is_submitted,
              SUM(CASE WHEN rr.submitted=1 AND rr.selected=1 THEN 1 ELSE 0 END) AS submitted_count
            FROM reviewer_post rp
            JOIN users u ON u.id = rp.reviewer_id
            LEFT JOIN reviewer_results rr
              ON rr.post_id = rp.post_id AND rr.reviewer_id = rp.reviewer_id
            WHERE rp.post_id=%s
            GROUP BY u.id, u.name, u.email
            ORDER BY u.id ASC
        """, (post_id,))
        reviewers = cursor.fetchall()

    cursor.close()
    return render_template('creator/view_post.html',
                           post=post,
                           is_owner=is_owner,
                           reviewers=reviewers)


# 모집 상태 변경
@creator_bp.route('/toggle_recruiting/<int:post_id>', methods=['POST'])
def toggle_recruiting(post_id):
    if 'loggedin' not in session or session.get('role') != 'creator':
        return redirect(url_for('auth.login'))

    cursor = current_app.mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT is_recruiting FROM posts WHERE id = %s", (post_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return "해당 글을 찾을 수 없습니다.", 404

    new_status = 0 if bool(row['is_recruiting']) else 1
    cursor.execute("UPDATE posts SET is_recruiting = %s WHERE id = %s", (new_status, post_id))
    current_app.mysql.connection.commit()
    cursor.close()

    return redirect(url_for('creator.view_post', post_id=post_id))


# 모집글 수정
@creator_bp.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'loggedin' not in session or session.get('role') != 'creator':
        return redirect(url_for('auth.login'))

    cursor = current_app.mysql.connection.cursor(DictCursor)

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        video_link = request.form['video_link']
        cursor.execute("""
            UPDATE posts SET title = %s, description = %s, video_link = %s WHERE id = %s
        """, (title, description, video_link, post_id))
        current_app.mysql.connection.commit()
        cursor.close()

        return redirect(url_for('creator.view_post', post_id=post_id))

    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()
    cursor.close()

    if not post:
        return "해당 글을 찾을 수 없습니다.", 404

    return render_template('creator/edit_post.html', post=post)


# 모집글 삭제(소프트 딜리트)
@creator_bp.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'loggedin' not in session or session.get('role') != 'creator':
        return redirect(url_for('auth.login'))

    cursor = current_app.mysql.connection.cursor()
    cursor.execute("UPDATE posts SET is_deleted = TRUE WHERE id = %s", (post_id,))
    current_app.mysql.connection.commit()
    cursor.close()

    return redirect(url_for('creator.dashboard'))








# 선택된 숏폼 보기
@creator_bp.route('/review_result/<int:post_id>/<int:reviewer_id>')
def review_result(post_id, reviewer_id):
    if 'loggedin' not in session or session.get('role') != 'creator':
        return redirect(url_for('auth.login'))
    user_id = session['user_id']

    cur = current_app.mysql.connection.cursor(DictCursor)
    cur.execute("SELECT creator_id, title FROM posts WHERE id=%s", (post_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)
    if row['creator_id'] != user_id:
        cur.close()
        return redirect(url_for('creator.dashboard'))

    post_title = row['title']

    cur.execute("""
        SELECT id, filename
        FROM reviewer_results
        WHERE post_id=%s AND reviewer_id=%s AND submitted=1 AND selected=1
        ORDER BY id ASC
    """, (post_id, reviewer_id))
    clips = cur.fetchall()
    cur.close()

    base_dir = os.path.join(current_app.root_path, 'static', 'shorts_output')
    for clip in clips:
        fname = clip.get('filename') or ''
        # 이미 "task_id/파일명" 형태면 패스
        if '/' in fname:
            continue
        # 폴더 없이 저장된 경우: shorts_output/*/파일명 을 찾아서 폴더명 붙이기
        matches = glob.glob(os.path.join(base_dir, '*', fname))
        if matches:
            task_folder = os.path.basename(os.path.dirname(matches[0]))
            clip['filename'] = f"{task_folder}/{fname}"

    return render_template('creator/review_result.html',
                           post_id=post_id,
                           post_title=post_title,
                           reviewer_id=reviewer_id,
                           clips=clips)


# ★ 별점 저장 (Creator가 Reviewer에게) - JSON 응답
@creator_bp.route('/rate', methods=['POST'])
@creator_bp.post('/rate')
def rate_reviewer():
    if 'loggedin' not in session or session.get('role') != 'creator':
        return jsonify({"ok": False, "msg": "로그인이 필요합니다."}), 401

    creator_id = session['user_id']
    try:
        post_id     = int(request.form.get('post_id', 0))
        reviewer_id = int(request.form.get('reviewer_id', 0))
        rating      = int(request.form.get('rating', 0))
    except ValueError:
        return jsonify({"ok": False, "msg": "잘못된 파라미터입니다."}), 400

    comment = (request.form.get('comment') or '').strip()

    if rating < 1 or rating > 5:
        return jsonify({"ok": False, "msg": "별점은 1~5 사이여야 합니다."}), 400

    cur = current_app.mysql.connection.cursor(DictCursor)

    # 글 소유자 확인
    cur.execute("SELECT creator_id FROM posts WHERE id=%s", (post_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({"ok": False, "msg": "해당 글을 찾을 수 없습니다."}), 404
    if row['creator_id'] != creator_id:
        cur.close()
        return jsonify({"ok": False, "msg": "권한이 없습니다."}), 403

    # 기존 평점 여부
    cur.execute("""
        SELECT id, rating FROM reviewer_ratings
        WHERE post_id=%s AND reviewer_id=%s AND creator_id=%s
    """, (post_id, reviewer_id, creator_id))
    existing = cur.fetchone()

    reward_delta = 0  # 새로 생성될 때만 포인트 지급
    if existing:
        cur.execute("""
            UPDATE reviewer_ratings
               SET rating=%s, comment=%s, updated_at=NOW()
             WHERE id=%s
        """, (rating, comment, existing['id']))
    else:
        cur.execute("""
            INSERT INTO reviewer_ratings (post_id, reviewer_id, creator_id, rating, comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (post_id, reviewer_id, creator_id, rating, comment))
        reward_delta = rating * 10

        # reviewer_points upsert
        cur.execute("SELECT user_id FROM reviewer_points WHERE user_id=%s", (reviewer_id,))
        if cur.fetchone():
            cur.execute("""
                UPDATE reviewer_points
                   SET balance = balance + %s, updated_at = NOW()
                 WHERE user_id=%s
            """, (reward_delta, reviewer_id))
        else:
            cur.execute("""
                INSERT INTO reviewer_points (user_id, balance, updated_at)
                VALUES (%s, %s, NOW())
            """, (reviewer_id, reward_delta))

        cur.execute("""
            INSERT INTO point_transactions (user_id, delta, reason, post_id)
            VALUES (%s, %s, 'rating_reward', %s)
        """, (reviewer_id, reward_delta, post_id))

    current_app.mysql.connection.commit()
    cur.close()

    return jsonify({"ok": True, "msg": "별점이 저장되었습니다.", "reward_delta": reward_delta}), 200
