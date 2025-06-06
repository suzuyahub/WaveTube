import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from yt_dlp import YoutubeDL
import tempfile
import re
import shutil
import webbrowser

from audio_analyzer import analyze_audio_full # 後で作成するファイルからインポート

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Global variables
progress_bar = None
status_label = None
analyze_toggle_var = None
download_directory = ""
download_dir_label = None

def set_initial_download_directory():
    global download_directory
    default_download_path = os.path.expanduser('~/Downloads')
    if not os.path.exists(default_download_path):
        default_download_path = os.path.expanduser('~')
    download_directory = default_download_path
    if download_dir_label:
        download_dir_label.config(text=f"保存先: {download_directory}")

def select_download_directory():
    global download_directory
    new_directory = filedialog.askdirectory(
        parent=root,
        initialdir=download_directory,
        title="ダウンロードフォルダを選択"
    )
    if new_directory:
        download_directory = new_directory
        download_dir_label.config(text=f"保存先: {download_directory}")

def progress_hook(d):
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        downloaded = d.get('downloaded_bytes', 0)
        if total_bytes and progress_bar:
            percent = downloaded / total_bytes * 100
            progress_bar['value'] = percent
            status_label.config(text=f"ダウンロード中... {percent:.1f}%")
    elif d['status'] == 'finished':
        status_label.config(text="変換中...")

def download_audio(url):
    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp()
        ffmpeg_path = resource_path("ffmpeg.exe")
        ffprobe_path = resource_path("ffprobe.exe")

        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'output')
            safe_title = sanitize_filename(title)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(tmpdir, 'audio.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '0',
            }],
            'ffmpeg_location': ffmpeg_path,
            'ffprobe_location': ffprobe_path,
            'progress_hooks': [progress_hook],
            'quiet': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        wav_file_temp = os.path.join(tmpdir, "audio.wav")
        if os.path.exists(wav_file_temp):
            output_filename = f"{safe_title}.wav"

            if analyze_toggle_var.get():
                status_label.config(text="BPMとキーを解析中...")
                bpm, key = analyze_audio_full(wav_file_temp) 

                if bpm is not None and key is not None:
                    output_filename = f"{safe_title} - {bpm}BPM {key}.wav"
                else:
                    messagebox.showwarning("解析失敗", "BPMとキーの解析に失敗しました。タイトルのみで保存します。")
            else:
                status_label.config(text="WAV変換中...")

            final_output_path = os.path.join(download_directory, output_filename)
            
            counter = 1
            base_name, ext = os.path.splitext(final_output_path)
            while os.path.exists(final_output_path):
                final_output_path = f"{base_name} ({counter}){ext}"
                counter += 1

            shutil.copy(wav_file_temp, final_output_path)
            messagebox.showinfo("成功", f"ダウンロード完了！\n{final_output_path} を確認してください。")
        else:
            messagebox.showerror("エラー", "変換に失敗しました。")
    except Exception as e:
        messagebox.showerror("エラー", str(e))
    finally:
        status_label.config(text="完了")
        progress_bar['value'] = 0
        if tmpdir and os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)

def start_download():
    url = url_entry.get()
    if not url.strip():
        messagebox.showwarning("入力エラー", "YouTubeのURLを入力してください。")
        return
    
    status_label.config(text="変換中...")
    progress_bar['value'] = 0
    
    threading.Thread(target=download_audio, args=(url,), daemon=True).start()

def open_twitter_link(event):
    webbrowser.open_new("https://x.com/suzuya_twi")

# --- GUI Setup ---
root = tk.Tk()
root.title("WavTube")
root.geometry("550x320")
root.resizable(False, False)

# アイコンファイルを読み込む
try:
    icon_path = resource_path("icon.png")
    photo = tk.PhotoImage(file=icon_path)
    root.iconphoto(False, photo)
except Exception as e:
    print(f"アイコンの読み込みに失敗しました: {e}")

# Apply a style
style = ttk.Style(root)
style.theme_use("clam")

# Configure some styles for better appearance
style.configure('TLabel', font=('Helvetica', 10))
style.configure('TButton', font=('Helvetica', 10, 'bold'), padding=5)
style.configure('TEntry', font=('Helvetica', 10))
style.configure('TCheckbutton', font=('Helvetica', 10))
style.configure('TProgressbar', thickness=15)

# Main content frame for consistent padding
main_frame = ttk.Frame(root, padding="20 15 20 15")
main_frame.pack(fill=tk.BOTH, expand=True)

# URL input
ttk.Label(main_frame, text="YouTubeのURLを入力:").pack(pady=(0, 5), anchor=tk.W)
url_entry = ttk.Entry(main_frame, width=60)
url_entry.pack(pady=(0, 15), fill=tk.X, expand=True)

# Download directory frame
download_path_frame = ttk.Frame(main_frame)
download_path_frame.pack(pady=(0, 10), fill=tk.X, anchor=tk.W)

download_dir_label = ttk.Label(download_path_frame, text="保存先: (設定中...)")
download_dir_label.pack(side=tk.LEFT, padx=(0, 10))

ttk.Button(download_path_frame, text="変更", command=select_download_directory).pack(side=tk.LEFT)

# Analysis checkbox
analyze_toggle_var = tk.BooleanVar(value=True)
ttk.Checkbutton(main_frame, text="BPMとキーを解析してファイル名に追加", variable=analyze_toggle_var).pack(pady=(0, 15), anchor=tk.W)

# Download button
ttk.Button(main_frame, text="ダウンロード開始", command=start_download, style='Accent.TButton').pack(pady=(0, 15), fill=tk.X)

# Progress bar
progress_bar = ttk.Progressbar(main_frame, length=400, mode='determinate')
progress_bar.pack(pady=(0, 5), fill=tk.X)

# Status label
status_label = ttk.Label(main_frame, text="待機中")
status_label.pack(pady=(0, 15))

# Contact information
contact_frame = ttk.Frame(root, padding="10 0 10 10")
contact_frame.pack(fill=tk.X, side=tk.BOTTOM)

ttk.Label(contact_frame, text="お問い合わせは : ").pack(side=tk.LEFT)

twitter_link_label = ttk.Label(contact_frame, text="@suzuya_twi (X)", foreground="blue", cursor="hand2")
twitter_link_label.pack(side=tk.LEFT)
twitter_link_label.bind("<Button-1>", open_twitter_link)

ttk.Label(contact_frame, text=" まで").pack(side=tk.LEFT)

set_initial_download_directory()

root.mainloop()