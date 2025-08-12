# timestamp/routes.py
import os
import sys
import subprocess
from flask import Blueprint, request, redirect, url_for, render_template, send_file, current_app
from werkzeug.utils import safe_join

timestamp_bp = Blueprint('timestamp', __name__, url_prefix='/timestamp')

def _output_root():
    """앱 루트 기준의 결과 루트 경로: static/timestamp_output"""
    return os.path.join(current_app.root_path, 'static', 'timestamp_output')

def _list_task_dirs():
    """static/timestamp_output 하위의 task 폴더(video_id) 목록 반환"""
    root = _output_root()
    if not os.path.isdir(root):
        return []
    return [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]

def _get_latest_task_id():
    """가장 최근에 변경된 task 폴더 이름(video_id) 반환"""
    root = _output_root()
    task_dirs = _list_task_dirs()
    if not task_dirs:
        return None
    task_dirs.sort(key=lambda d: os.path.getmtime(os.path.join(root, d)), reverse=True)
    return task_dirs[0]

@timestamp_bp.route('/form')
def timestamp_form():
    return render_template('creator/timestamp/timestamp_form.html')

@timestamp_bp.route('/generate', methods=['POST'])
def shorts_comment():
    url = request.form.get('youtube_url', '').strip()
    if not url:
        return render_template('creator/timestamp/shorts_comment_result.html',
                               error='YouTube URL이 비었습니다.')

    # ▶ 스크립트 경로 (현재 파일 기준)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(base_dir, 'create_timestamp_shorts.py')
    if not os.path.exists(script):
        return render_template('creator/timestamp/shorts_comment_result.html',
                               error='create_timestamp_shorts.py를 찾을 수 없습니다.')

    # ▶ 결과 루트 보장
    os.makedirs(_output_root(), exist_ok=True)

    # ▶ 실행 전 폴더 목록 저장
    before_dirs = set(_list_task_dirs())

    # ▶ 스크립트 실행
    try:
        result = subprocess.run(
            [sys.executable, script, url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        print("=== create_timestamp_shorts.py stdout ===\n", result.stdout)
        print("=== create_timestamp_shorts.py stderr ===\n", result.stderr)
    except Exception as e:
        return render_template('creator/timestamp/shorts_comment_result.html',
                               error=f'스크립트 실행 실패: {e}')

    if result.returncode != 0:
        return render_template('creator/timestamp/shorts_comment_result.html',
                               error='숏폼 생성 스크립트가 오류로 종료되었습니다. 로그를 확인하세요.')

    # ▶ 실행 후 새로 생긴 task 폴더 찾기
    root = _output_root()
    after_dirs = set(_list_task_dirs())
    new_dirs = list(after_dirs - before_dirs)
    if new_dirs:
        new_dirs.sort(key=lambda d: os.path.getmtime(os.path.join(root, d)), reverse=True)
        task_id = new_dirs[0]
    else:
        task_id = _get_latest_task_id()

    if not task_id:
        return render_template('creator/timestamp/shorts_comment_result.html',
                               error='생성된 결과 폴더(task_id)를 찾지 못했습니다.')

    return redirect(url_for('timestamp.shorts_comment_result', task_id=task_id))

@timestamp_bp.route('/result/<task_id>')
def shorts_comment_result(task_id):
    root = _output_root()
    task_dir = os.path.join(root, task_id)
    if not os.path.isdir(task_dir):
        return render_template('creator/timestamp/shorts_comment_result.html',
                               error=f'결과 폴더가 존재하지 않습니다: {task_id}')

    # ▶ mp4 목록
    clips = sorted([f for f in os.listdir(task_dir) if f.lower().endswith('.mp4')])

    # ▶ 타임스탬프 파일 읽기
    timestamp_file = os.path.join(task_dir, 'timestamps.txt')
    timestamp_map = {}
    if os.path.exists(timestamp_file):
        with open(timestamp_file, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 예: short_01.mp4,00분 10초,00분 50초[,시작초,끝초...]
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    fname, start, end = parts[0], parts[1], parts[2]
                    timestamp_map[fname] = (start, end)

    videos_info = [{
        'filename': f,                   # 파일명만 (예: short_01.mp4)
        'relpath': f"{task_id}/{f}",    # 재생/다운로드용 상대경로
        'timestamps': timestamp_map.get(f, ())
    } for f in clips]

    return render_template('creator/timestamp/shorts_comment_result.html',
                           task_id=task_id,
                           videos_info=videos_info)

@timestamp_bp.route('/download/<task_id>/<filename>')
def download_file(task_id, filename):
    # 안전한 경로 결합
    root = _output_root()
    path = safe_join(root, task_id, filename)
    if not path or not os.path.exists(path):
        return ("File not found", 404)
    return send_file(path, as_attachment=True)
