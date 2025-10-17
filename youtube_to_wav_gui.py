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
import subprocess

from audio_analyzer import analyze_audio_full 

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

progress_bar = None
status_label = None
analyze_toggle_var = None
download_directory = ""
download_dir_label = None
output_format_var = None 

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
        output_format = output_format_var.get()
        
        temp_audio_file_ext = 'wav'

        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'output')
            safe_title = sanitize_filename(title)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(tmpdir, f'audio_temp.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': temp_audio_file_ext,
                'preferredquality': '0',
            }],
            'ffmpeg_location': ffmpeg_path,
            'ffprobe_location': ffprobe_path,
            'progress_hooks': [progress_hook],
            'quiet': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        wav_file_temp = os.path.join(tmpdir, f"audio_temp.{temp_audio_file_ext}")
        
        if os.path.exists(wav_file_temp):
            analyzed_title_part = ""
            if analyze_toggle_var.get():
                status_label.config(text="BPMとキーを解析中...")
                bpm, key = analyze_audio_full(wav_file_temp) 

                if bpm is not None and key is not None:
                    analyzed_title_part = f" - {bpm}BPM {key}"
                else:
                    messagebox.showwarning("解析失敗", "BPMとキーの解析に失敗しました。タイトルのみで保存します。")
            
            final_ext = ".wav" if output_format == "WAV" else ".mp3"
            output_filename = f"{safe_title}{analyzed_title_part}{final_ext}"
            final_output_path = os.path.join(download_directory, output_filename)
            
            counter = 1
            base_name, ext = os.path.splitext(final_output_path)
            while os.path.exists(final_output_path):
                final_output_path = f"{base_name} ({counter}){ext}"
                counter += 1

            status_label.config(text=f"最終エンコード ({output_format}) 中...")

            if output_format == "WAV":
                shutil.copy(wav_file_temp, final_output_path)
            elif output_format == "MP3":
                
                status_label.config(text=f"最終エンコード ({output_format}) 中... (FFmpeg)")

                try:
                    subprocess.run([
                        ffmpeg_path,
                        '-i', wav_file_temp,
                        '-b:a', '320k', # 320kbps
                        '-y',
                        final_output_path
                    ], 
                    check=True, 
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW) 
                except subprocess.CalledProcessError as e:
                    messagebox.showerror("FFmpegエラー", f"MP3変換に失敗しました。\n{e.stderr.decode()}")
                    raise Exception("MP3変換失敗")

            messagebox.showinfo("成功", f"ダウンロード完了！\n{final_output_path} を確認してください。")
        else:
            messagebox.showerror("エラー", "一時ファイルの作成に失敗しました。")
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

def paste_url():
    """クリップボードのテキストをURL入力欄に貼り付ける"""
    try:
        clipboard_content = root.clipboard_get()
        url_entry.delete(0, tk.END)
        url_entry.insert(0, clipboard_content)
    except tk.TclError:
        messagebox.showwarning("エラー", "クリップボードにテキストがありません。")

def open_instagram_link(event):
    """Instagramのリンクをブラウザで開く"""
    webbrowser.open_new("https://instagram.com/suzuya_ins")

root = tk.Tk()
root.title("WavTube mp3+")
root.geometry("550x380")
root.resizable(False, False)

try:
    icon_path = resource_path("icon.png")
    photo = tk.PhotoImage(file=icon_path)
    root.iconphoto(False, photo)
except Exception as e:
    print(f"アイコンの読み込みに失敗しました: {e}")

style = ttk.Style(root)
style.theme_use("clam")

style.configure('TLabel', font=('Helvetica', 10))
style.configure('TButton', font=('Helvetica', 10, 'bold'), padding=5)
style.configure('TEntry', font=('Helvetica', 10))
style.configure('TCheckbutton', font=('Helvetica', 10))
style.configure('TRadiobutton', font=('Helvetica', 10))
style.configure('TProgressbar', thickness=15)

main_frame = ttk.Frame(root, padding="20 15 20 15")
main_frame.pack(fill=tk.BOTH, expand=True)

ttk.Label(main_frame, text="YouTubeのURLを入力:").pack(pady=(0, 5), anchor=tk.W)

url_input_frame = ttk.Frame(main_frame)
url_input_frame.pack(pady=(0, 15), fill=tk.X, expand=True)

url_entry = ttk.Entry(url_input_frame, width=50)
url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

ttk.Button(url_input_frame, text="貼り付け", command=paste_url).pack(side=tk.LEFT, ipadx=5)

download_path_frame = ttk.Frame(main_frame)
download_path_frame.pack(pady=(0, 10), fill=tk.X, anchor=tk.W)

download_dir_label = ttk.Label(download_path_frame, text="保存先: (設定中...)")
download_dir_label.pack(side=tk.LEFT, padx=(0, 10))

ttk.Button(download_path_frame, text="変更", command=select_download_directory).pack(side=tk.LEFT)

output_format_var = tk.StringVar(value="WAV")

output_format_frame = ttk.Frame(main_frame)
output_format_frame.pack(pady=(5, 15), anchor=tk.W)

ttk.Label(output_format_frame, text="出力形式:").pack(side=tk.LEFT, padx=(0, 10))

ttk.Radiobutton(output_format_frame, text="WAV (ロスレス)", variable=output_format_var, value="WAV").pack(side=tk.LEFT, padx=(0, 15))
ttk.Radiobutton(output_format_frame, text="MP3 (320kbps)", variable=output_format_var, value="MP3").pack(side=tk.LEFT)

analyze_toggle_var = tk.BooleanVar(value=False) 
ttk.Checkbutton(main_frame, text="BPMとキーを解析してファイル名に追加", variable=analyze_toggle_var).pack(pady=(0, 15), anchor=tk.W)

ttk.Button(main_frame, text="ダウンロード開始", command=start_download, style='Accent.TButton').pack(pady=(0, 15), fill=tk.X)

progress_bar = ttk.Progressbar(main_frame, length=400, mode='determinate')
progress_bar.pack(pady=(0, 5), fill=tk.X)

status_label = ttk.Label(main_frame, text="待機中")
status_label.pack(pady=(0, 15))

contact_frame = ttk.Frame(root, padding="10 0 10 10")
contact_frame.pack(fill=tk.X, side=tk.BOTTOM)

ttk.Label(contact_frame, text="お問い合わせは : ").pack(side=tk.LEFT)

instagram_link_label = ttk.Label(contact_frame, text="@suzuya_ins (Instgram)", foreground="blue", cursor="hand2")
instagram_link_label.pack(side=tk.LEFT)
instagram_link_label.bind("<Button-1>", open_instagram_link)

ttk.Label(contact_frame, text=" まで").pack(side=tk.LEFT)

set_initial_download_directory()

root.mainloop()