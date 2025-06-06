import numpy as np
import librosa
import soundfile as sf # librosa.loadが内部でsfを使うため、明示的にインポートすると良い

def _get_key_templates():
    """Krumhansl-Schmuckler Key Templates (正規化済み)."""
    major_template = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_template = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    
    return librosa.util.normalize(major_template, norm=1), librosa.util.normalize(minor_template, norm=1)

def detect_key_from_chroma(y, sr):
    """オーディオのクロマ特徴量とKrumhansl-Schmucklerテンプレートに基づいてキーを検出します。
    長調と短調のどちらかのキーを返します。
    """
    # ハーモニック成分を抽出して、非調性的なノイズの影響を減らす
    y_harmonic = librosa.effects.harmonic(y)
    
    # CQTベースのクロマ特徴量 (よりロバスト)
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    chroma_mean = librosa.util.normalize(chroma_mean, norm=1)

    major_template, minor_template = _get_key_templates()
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    major_scores = []
    minor_scores = []
    for i in range(12):
        rotated_chroma = np.roll(chroma_mean, -i) # 各キーポジションにクロマを回転
        major_scores.append(np.dot(rotated_chroma, major_template))
        minor_scores.append(np.dot(rotated_chroma, minor_template))

    best_major_idx = np.argmax(major_scores)
    best_minor_idx = np.argmax(minor_scores)

    # 長調と短調の最も高いスコアを比較し、より良いフィットを選ぶ
    if major_scores[best_major_idx] >= minor_scores[best_minor_idx]:
        return f"{keys[best_major_idx]} Maj", major_scores[best_major_idx]
    else:
        return f"{keys[best_minor_idx]} Min", minor_scores[best_minor_idx]

def analyze_audio_full(audio_path):
    """
    指定されたオーディオファイルのBPMとキーを検出します。
    現時点では、BPMはLibrosa、キーはKrumhansl-Schmucklerテンプレートに基づいています。
    将来的に、複数のキー検出アルゴリズムを統合して精度を向上させることができます。
    """
    try:
        y, sr = librosa.load(audio_path, sr=None) # sr=Noneで元のサンプリングレートを維持

        # --- BPM検出 ---
        # Librosaのbeat_trackは、音楽のテンポを推定します。
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = int(round(tempo[0])) # 小数点以下を四捨五入して整数に
        
        detected_key, confidence_score = detect_key_from_chroma(y, sr)

        return bpm, detected_key

    except Exception as e:
        # ここでのエラーは呼び出し元で処理されることを想定
        print(f"オーディオ解析中にエラーが発生しました: {e}")
        return None, None

if __name__ == '__main__':
    # このファイルを単独で実行して、キー検出のテストを行うためのコード

    sr_test = 22050
    duration = 5 # seconds
    
    # C Majorスケールの簡単なテストオーディオを作成
    t = np.linspace(0, duration, int(sr_test * duration), endpoint=False)
    notes_c_major = [librosa.note_to_hz('C4'), librosa.note_to_hz('D4'), librosa.note_to_hz('E4'),
                     librosa.note_to_hz('F4'), librosa.note_to_hz('G4'), librosa.note_to_hz('A4'),
                     librosa.note_to_hz('B4'), librosa.note_to_hz('C5')]
    y_c_major = np.array([])
    for note_freq in notes_c_major:
        # 短いサイン波のセグメントを追加
        segment = 0.5 * np.sin(2 * np.pi * note_freq * t[:int(sr_test * 0.5)])
        y_c_major = np.concatenate((y_c_major, segment))
    
    test_c_major_path = 'test_c_major.wav'
    sf.write(test_c_major_path, y_c_major, sr_test)

    print("--- C Major スケールのテスト ---")
    bpm, key = analyze_audio_full(test_c_major_path)
    print(f"検出されたBPM: {bpm}, 検出されたキー: {key}") # 期待値: C Maj に近い結果

    # テストファイルを削除
    import os
    if os.path.exists(test_c_major_path):
        os.remove(test_c_major_path)

    # 別の例: A Minor (簡易的)
    notes_a_minor = [librosa.note_to_hz('A4'), librosa.note_to_hz('B4'), librosa.note_to_hz('C5'),
                     librosa.note_to_hz('D5'), librosa.note_to_hz('E5'), librosa.note_to_hz('F5'),
                     librosa.note_to_hz('G5'), librosa.note_to_hz('A5')]
    y_a_minor = np.array([])
    for note_freq in notes_a_minor:
        segment = 0.5 * np.sin(2 * np.pi * note_freq * t[:int(sr_test * 0.5)])
        y_a_minor = np.concatenate((y_a_minor, segment))
    
    test_a_minor_path = 'test_a_minor.wav'
    sf.write(test_a_minor_path, y_a_minor, sr_test)

    print("\n--- A Minor スケールのテスト ---")
    bpm, key = analyze_audio_full(test_a_minor_path)
    print(f"検出されたBPM: {bpm}, 検出されたキー: {key}") # 期待値: A Min に近い結果

    if os.path.exists(test_a_minor_path):
        os.remove(test_a_minor_path)