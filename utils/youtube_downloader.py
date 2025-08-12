# utils/youtube_downloader.py
import os
import yt_dlp

def download_youtube_video(url, save_dir, filename_prefix):
    os.makedirs(save_dir, exist_ok=True)
    output_path = os.path.join(save_dir, f"{filename_prefix}.mp4")

    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    print(f"[DOWNLOADED] {output_path}")
    return output_path
