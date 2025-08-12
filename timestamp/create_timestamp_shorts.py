# timestamp/create_timestamp_shorts.py
import os, re, sys, subprocess, time
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from collections import Counter
import yt_dlp

YOUTUBE_API_KEY = 'AIzaSyBirO4FkbsDGxAn7DIG5muexbDTkY-wLVk'  # 보안상 환경변수 권장

# === 경로 설정 (프로젝트 루트 기준 고정) ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))

OUTPUT_ROOT = os.path.join(ROOT_DIR, 'static', 'timestamp_output')  # 결과 루트
UPLOAD_DIR  = os.path.join(ROOT_DIR, 'timestamp_uploads')           # 원본 저장
os.makedirs(OUTPUT_ROOT, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

def extract_video_id(url):
    parsed = urlparse(url)
    if 'youtube.com' in parsed.netloc:
        return parse_qs(parsed.query).get('v', [None])[0]
    elif 'youtu.be' in parsed.netloc:
        return parsed.path.lstrip('/')
    return None

def extract_timestamps(text):
    pattern = r'\b(?:[0-5]?\d:)?[0-5]?\d:[0-5]\d\b'
    return re.findall(pattern, text)

def timestamp_to_seconds(ts):
    parts = list(map(int, ts.split(":")))
    return parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0]*3600 + parts[1]*60 + parts[2]

def seconds_to_hms(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f"{h}시간 {m}분 {s}초" if h > 0 else f"{m}분 {s}초"

def fetch_comments(video_id):
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    comments, token = [], None
    while True:
        req = youtube.commentThreads().list(part='snippet', videoId=video_id, maxResults=100, pageToken=token)
        res = req.execute()
        for item in res.get('items', []):
            comments.append(item['snippet']['topLevelComment']['snippet']['textDisplay'])
        token = res.get('nextPageToken')
        if not token: break
    return comments

def group_timestamps(timestamps, threshold=5):
    if not timestamps: return []
    timestamps.sort()
    grouped, current = [], [timestamps[0]]
    for ts in timestamps[1:]:
        if ts - current[-1] <= threshold:
            current.append(ts)
        else:
            grouped.append(current)
            current = [ts]
    grouped.append(current)
    return grouped

def download_full_video(url, video_id):
    """원본 전체 영상을 timestamp_uploads/{video_id}.mp4 로 저장"""
    output_file = os.path.join(UPLOAD_DIR, f'{video_id}.mp4')
    if os.path.exists(output_file):
        os.remove(output_file)
    ydl_opts = {
        'outtmpl': output_file,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    time.sleep(1)
    if not os.path.exists(output_file) or os.path.getsize(output_file) < 1_000_000:
        raise RuntimeError('다운로드 실패 또는 파일 크기가 비정상적으로 작습니다.')
    return os.path.abspath(output_file)

def create_clips(video_path, timestamps, video_id):
    """결과를 static/timestamp_output/{video_id}/ 에 저장"""
    video_out_dir = os.path.join(OUTPUT_ROOT, video_id)
    os.makedirs(video_out_dir, exist_ok=True)

    timestamp_log = []
    for idx, sec in enumerate(timestamps):
        start, duration = max(sec - 20, 0), 40  # 기존 로직 유지(20초 앞, 40초 길이)
        clip_path = os.path.join(video_out_dir, f'short_{idx+1}.mp4')
        result = subprocess.run([
            'ffmpeg', '-ss', str(start), '-i', video_path,
            '-t', str(duration), '-c:v', 'libx264', '-c:a', 'aac',
            '-y', clip_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

        if result.returncode != 0 or not os.path.exists(clip_path) or os.path.getsize(clip_path) < 200_000:
            if os.path.exists(clip_path):
                os.remove(clip_path)
            continue

        end = start + duration
        timestamp_log.append((f'short_{idx+1}.mp4', seconds_to_hms(start), seconds_to_hms(end), start, end))

    with open(os.path.join(video_out_dir, 'timestamps.txt'), 'w', encoding='utf-8') as f:
        for name, start_hms, end_hms, s, e in timestamp_log:
            # 파일명, 시작(HMS), 종료(HMS), 시작초, 종료초
            f.write(f"{name},{start_hms},{end_hms},{s},{e}\n")

def main():
    if len(sys.argv) < 2:
        print("❌ YouTube URL을 입력해주세요.")
        return
    url = sys.argv[1]
    vid = extract_video_id(url)
    if not vid:
        print("❌ 잘못된 URL입니다.")
        return

    comments = fetch_comments(vid)
    times = [timestamp_to_seconds(t) for c in comments for t in extract_timestamps(c)]
    if not times:
        print("❌ 타임스탬프 없음")
        return

    counter = Counter(times)
    grouped = group_timestamps(sorted(counter))  # 빈도 사전의 key(초)만 정렬
    rep_times = [max(g, key=lambda x: counter[x]) for g in grouped]
    top5 = sorted(rep_times, key=lambda x: counter[x], reverse=True)[:5]

    video_path = download_full_video(url, vid)
    create_clips(video_path, top5, vid)

if __name__ == '__main__':
    main()
