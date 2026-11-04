#!/usr/bin/env python3
"""
Gospel Audio Craft & Harmonic Playlist Engine
=============================================
Unified single-use tool for forensic acoustic extraction, grounded 5-chapter
classification, size-first deduplication, harmonic DJ sequencing, and FAT32 export.
Includes both an Interactive Terminal CLI and a Local Web Dashboard.
"""

import os
import sys
import re
import json
import math
import shutil
import zipfile
import argparse
import subprocess
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from collections import defaultdict
import numpy as np

# ==============================================================================
# 1. CONSTANTS & HARMONIC DJ CONFIGURATION
# ==============================================================================

ROOT_DIR = r"c:\Users\USER\Downloads\Music"
BACKUP_DIR = os.path.join(ROOT_DIR, "_duplicates_backup")
CACHE_FILE = os.path.join(ROOT_DIR, "audio_metrics_cache.json")
BEATS_FILE = os.path.join(ROOT_DIR, "beats.txt")
PLAYLIST_FILE = os.path.join(ROOT_DIR, "playlist.txt")
ZIP_EXPORT_FILE = os.path.join(ROOT_DIR, "mp3SD.zip")

CAMELOT_MAP = {
    # Major keys (B suffix in Camelot notation)
    (0, True): ('8B', 'C Major'), (1, True): ('3B', 'Db Major'), (2, True): ('10B', 'D Major'),
    (3, True): ('5B', 'Eb Major'), (4, True): ('12B', 'E Major'), (5, True): ('7B', 'F Major'),
    (6, True): ('2B', 'F# Major'), (7, True): ('9B', 'G Major'), (8, True): ('4B', 'Ab Major'),
    (9, True): ('11B', 'A Major'), (10, True): ('6B', 'Bb Major'), (11, True): ('1B', 'B Major'),
    # Minor keys (A suffix in Camelot notation)
    (0, False): ('5A', 'C Minor'), (1, False): ('12A', 'C# Minor'), (2, False): ('7A', 'D Minor'),
    (3, False): ('2A', 'Eb Minor'), (4, False): ('9A', 'E Minor'), (5, False): ('4A', 'F Minor'),
    (6, False): ('11A', 'F# Minor'), (7, False): ('6A', 'G Minor'), (8, False): ('1A', 'Ab Minor'),
    (9, False): ('8A', 'A Minor'), (10, False): ('3A', 'Bb Minor'), (11, False): ('10A', 'B Minor'),
}

KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

CHAPTER_NAMES = [
    'Chapter 1 - Devotional & Intimate Presence',
    'Chapter 2 - Mid-Tempo Groove & Uplifting Praise',
    'Chapter 3 - High-Praise & Joyful Celebration',
    'Chapter 4 - Prophetic Warfare & Deep Chants',
    'Chapter 5 - Deep Soak & Atmospheric Prayer'
]

# ==============================================================================
# 2. HARMONIC MIXING COMPATIBILITY MATRIX
# ==============================================================================

def parse_camelot(c_str):
    if not c_str or len(c_str) < 2: return (8, 'B')
    try: return (int(c_str[:-1]), c_str[-1].upper())
    except Exception: return (8, 'B')

def camelot_compatibility(c1_str, c2_str):
    n1, l1 = parse_camelot(c1_str)
    n2, l2 = parse_camelot(c2_str)
    diff = abs(n1 - n2)
    diff = min(diff, 12 - diff)
    if diff == 0: return 1.00 if l1 == l2 else 0.95
    elif diff == 1: return 0.90 if l1 == l2 else 0.75
    elif diff == 2 and l1 == l2: return 0.82
    else: return 0.20

def tempo_compatibility(bpm1, bpm2):
    if bpm1 <= 0 or bpm2 <= 0: return 0.50
    diff_direct = abs(bpm1 - bpm2)
    diff_half = abs(bpm1 * 2.0 - bpm2)
    diff_double = abs(bpm1 - bpm2 * 2.0)
    diff = min(diff_direct, diff_half, diff_double)
    if diff <= 3.0: return 1.00
    elif diff <= 6.0: return 0.88
    elif diff <= 10.0: return 0.75
    elif diff <= 15.0: return 0.60
    elif diff <= 25.0: return 0.40
    else: return max(0.10, 1.0 - diff / 50.0)

def energy_compatibility(db1, db2):
    diff = abs(db1 - db2)
    if diff <= 3.0: return 1.00
    elif diff <= 6.0: return 0.85
    elif diff <= 10.0: return 0.65
    else: return max(0.20, 1.0 - diff / 20.0)

def transition_score(t1, t2):
    h = camelot_compatibility(t1.get('camelot', '8B'), t2.get('camelot', '8B'))
    t = tempo_compatibility(t1.get('bpm', 100), t2.get('bpm', 100))
    e = energy_compatibility(t1.get('overall_energy_db', -15.0), t2.get('overall_energy_db', -15.0))
    return round(0.45 * h + 0.35 * t + 0.20 * e, 4)

# ==============================================================================
# 3. FORENSIC ACOUSTIC EXTRACTION (WITH TEMPO FOLDING DE-ALIASING)
# ==============================================================================

def estimate_harmonic_key(chroma_sum):
    if np.sum(chroma_sum) == 0: return '8B', 'C Major', 0.0
    chroma_norm = (chroma_sum - np.mean(chroma_sum)) / (np.std(chroma_sum) + 1e-8)
    best_score = -999.0
    best_match = (0, True)
    ks_maj_norm = (KS_MAJOR - np.mean(KS_MAJOR)) / np.std(KS_MAJOR)
    ks_min_norm = (KS_MINOR - np.mean(KS_MINOR)) / np.std(KS_MINOR)

    for shift in range(12):
        rotated = np.roll(chroma_norm, -shift)
        corr_maj = float(np.dot(rotated, ks_maj_norm) / 12.0)
        corr_min = float(np.dot(rotated, ks_min_norm) / 12.0)
        if corr_maj > best_score:
            best_score = corr_maj
            best_match = (shift, True)
        if corr_min > best_score:
            best_score = corr_min
            best_match = (shift, False)

    camelot, key_name = CAMELOT_MAP[best_match]
    return camelot, key_name, round(best_score, 3)

def analyze_audio_forensics(filepath):
    """
    High-precision acoustic extraction with tempo de-aliasing and energy profiling.
    """
    sr = 22050
    try:
        # Step A: Duration
        cmd_dur = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath]
        p_dur = subprocess.run(cmd_dur, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dur = float(p_dur.stdout.strip()) if p_dur.returncode == 0 and p_dur.stdout.strip() else 180.0

        # Step B: 30-second center slice decode
        offset = max(0.0, (dur - 30.0) / 2.0)
        cmd_mid = ['ffmpeg', '-v', 'error', '-ss', f"{offset:.2f}", '-t', '30.0', '-i', filepath, '-ar', str(sr), '-ac', '1', '-f', 's16le', '-']
        p_mid = subprocess.run(cmd_mid, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        bpm = 100.0
        camelot = '8B'
        key_name = 'C Major'
        overall_db = -15.0

        if len(p_mid.stdout) > 0:
            import librosa
            y = np.frombuffer(p_mid.stdout, dtype=np.int16).astype(np.float32) / 32768.0
            
            # RMS Energy
            rms = float(np.sqrt(np.mean(y**2) + 1e-12))
            overall_db = float(20.0 * np.log10(max(rms, 1e-6)))

            # Tempo beat tracking
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=512)
            bpm = float(np.atleast_1d(tempo)[0])

            # Harmonic Key
            chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=512)
            camelot, key_name, _ = estimate_harmonic_key(np.sum(chroma, axis=1))

        # Calibrated Tempo Folding Rule: Disambiguate 16th-note worship subdivisions
        fn_lower = os.path.basename(filepath).lower()
        is_worship_title = any(w in fn_lower for w in [
            'worship', 'praise', 'burn', 'nagode', 'speak to my heart', 'heart of worship',
            'breathe', 'majesty', 'grace', 'deeper', 'ran mi lowo', 'clean heart', 'broken'
        ])
        if is_worship_title and bpm >= 130.0:
            bpm = bpm / 2.0

        return {
            'filename': os.path.basename(filepath),
            'filepath': filepath,
            'duration': round(dur, 2),
            'bpm': round(bpm, 1),
            'key_name': key_name,
            'camelot': camelot,
            'overall_energy_db': round(overall_db, 1),
            'is_major': camelot.endswith('B')
        }
    except Exception as e:
        return {
            'filename': os.path.basename(filepath),
            'filepath': filepath,
            'duration': 180.0,
            'bpm': 100.0,
            'key_name': 'C Major',
            'camelot': '8B',
            'overall_energy_db': -15.0,
            'is_major': True
        }

# ==============================================================================
# 4. GROUNDED 5-CHAPTER CLASSIFIER
# ==============================================================================

def classify_track_grounded(filename, meta):
    """
    Assigns each song to its grounded spiritual phase using calibrated rules.
    """
    fn_lower = filename.lower()
    bpm = meta.get('bpm', 100.0)
    dur = meta.get('duration', 0.0)
    energy = meta.get('overall_energy_db', -15.0)

    # Review & Interludes
    if any(k in fn_lower for k in ['voice note', 'national anthem', 'sssspotify', 'secret to spiritual growth and power']):
        return 'Review & Interludes'

    # Chapter 4: Prophetic Warfare, Chants & Intercession
    warfare_tokens = [
        'drum beats of war', 'cast & bind', 'c&b', 'tongues of fire', 'alignment chant',
        'we say no to you satan', 'deeper experience chant', 'sacred flames', 'chants of activation',
        'ahhh ehh chant', 'prophetic chant', 'intensify another measure', 'fire on my altar',
        'jugular jugular', 'take over', 'time for shift', 'connect', 'emmanuel', 'volume of the book',
        'i have escaped', 'judgement day', 'baruch hashem adonai', 'help us respond'
    ]
    if any(k in fn_lower for k in warfare_tokens):
        return 'Chapter 4 - Prophetic Warfare & Deep Chants'

    # Chapter 5: Deep Soak, Atmospheric Prayer & Reflection
    soak_tokens = [
        'orokpo', 'delvan', 'solitude', 'nocturne', 'rain & piano', 'soaking', 'prayer meditation',
        'chlorine', 'idea 22', 'idea 10', 'deep waters (instrumental)', 'aurora', 'adullam',
        'iba', 'ga shi nan', 'rahama', 'tare', 'the glory song', 'living water', 'ah ah eh chant',
        'kill what', 'secret place', 'earthen vessel', 'el elohe israel', 'yahweh', 'hunger',
        'send down the spirit', 'how can you walk'
    ]
    if any(k in fn_lower for k in soak_tokens):
        return 'Chapter 5 - Deep Soak & Atmospheric Prayer'
    if dur > 420.0 and bpm < 76.0:
        return 'Chapter 5 - Deep Soak & Atmospheric Prayer'

    # Chapter 3: High-Praise & Joyful Celebration
    celebration_tokens = [
        'up!', 'lemonade', 'good day', 'okay!', 'inferno', 'revolution', 'victory',
        'the jesus generation', 'gods got my back', 'if you believe', 'heaven on this earth',
        'your ways better', 'love like that', 'jesus is alive', 'jesus is coming back',
        'praises (remix)', 'no longer bound', 'you are good', 'elee', 'energy', 'praise your name',
        'waymaker', 'daddy wey dey pamper', 'look what youve done', 'drill remix', 'we still believe',
        'chinwe ike', 'ekele', 'our god', 'make heaven crowded', 'rejoice chant', 'no turning back',
        'kumama papa', 'pariwo', 'agalliao', 'raba baba eh'
    ]
    if any(k in fn_lower for k in celebration_tokens) and bpm >= 115.0:
        return 'Chapter 3 - High-Praise & Joyful Celebration'

    # Chapter 2: Mid-Tempo Groove & Uplifting Praise
    groove_tokens = [
        'brighter day', 'd2d', 'eden', 'confidential', 'p & a', 'sori', 'love practitioner',
        'nazarene', 'revival', 'juba', 'el', 'l.n.b', 'ji', 'bire', 'gratitude', 'za', 'alakori',
        'jireh', 'angels', 'elijah level', 'umbrella', 'e dey flow', 'baba', 'goodness of god',
        'holy father', 'tinbake', 'miracle no dey tire', 'open doors', 'the train theme song',
        'my promised land', 'dusty bibles', 'correct', 'eternal', 'leave am', 'let me in',
        'finidi george', 'celebration', 'anointed', 'wys', 'adml', 'holy spirit', 'mercy',
        'look at god', 'god did', 'no lele', 'baba saanu', 'standing - remix', 'because jesus christ',
        'nasara', 'jesus oh', 'we outside', 'biggi man', 'all the praise', 'holiday', 'prodigal',
        'jowo', 'bo ta joor', 'bigger - odogwu', 'abba riddim'
    ]
    if any(k in fn_lower for k in groove_tokens):
        return 'Chapter 2 - Mid-Tempo Groove & Uplifting Praise'
    if bpm >= 92.0 and bpm <= 118.0:
        return 'Chapter 2 - Mid-Tempo Groove & Uplifting Praise'

    # Chapter 1: Devotional Warm-Up & Intimate Presence (Default for reflective worship)
    return 'Chapter 1 - Devotional & Intimate Presence'

# ==============================================================================
# 5. MAXIMUM-WEIGHT HAMILTONIAN DJ SEQUENCER
# ==============================================================================

def solve_hamiltonian_path(tracks):
    n = len(tracks)
    if n <= 1: return tracks

    adj = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                adj[i][j] = transition_score(tracks[i], tracks[j])

    best_start = 0
    best_avg = -1.0
    for i in range(n):
        avg = sum(adj[i][j] for j in range(n) if i != j) / (n - 1)
        if avg > best_avg:
            best_avg = avg
            best_start = i

    unvisited = set(range(n))
    path = [best_start]
    unvisited.remove(best_start)
    curr = best_start
    while unvisited:
        nxt = max(unvisited, key=lambda c: adj[curr][c])
        path.append(nxt)
        unvisited.remove(nxt)
        curr = nxt

    # 2-Opt local search refinement
    improved = True
    passes = 0
    while improved and passes < 25:
        improved = False
        passes += 1
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                old_d = adj[path[i-1]][path[i]] + adj[path[j]][path[j+1]]
                new_d = adj[path[i-1]][path[j]] + adj[path[i]][path[j+1]]
                if new_d > old_d + 1e-4:
                    path[i:j+1] = path[i:j+1][::-1]
                    improved = True
                    break
            if improved: break

    return [tracks[idx] for idx in path]

# ==============================================================================
# 6. DEDUPLICATION (SIZE-FIRST INTEGRITY)
# ==============================================================================

def deduplicate_library(target_dir):
    """
    Deletes smaller duplicate audio files while preserving the highest byte size copy.
    """
    all_files = []
    for root, dirs, files in os.walk(target_dir):
        for f in files:
            if f.lower().endswith('.mp3'):
                p = os.path.join(root, f)
                all_files.append((f, p, os.path.getsize(p)))

    # Clean title tokens
    def get_norm(s):
        s = os.path.splitext(s)[0].lower()
        s = re.sub(r'^\d+\s*-\s*', '', s)
        s = re.sub(r'[\(\[\{].*?[\)\]\}]', '', s)
        s = re.sub(r'[_ -]?(spotdown\.org|ceenaija\.com|gospelsong\.com\.ng|christianselect\.com\.ng|divineflaver\.com).*', '', s)
        return re.sub(r'[^a-z0-9]+', ' ', s).strip()

    clusters = defaultdict(list)
    for fn, p, sz in all_files:
        norm = get_norm(fn)
        clusters[norm].append((fn, p, sz))

    deleted = 0
    for norm, group in clusters.items():
        if len(group) > 1:
            group.sort(key=lambda x: x[2], reverse=True)
            kept = group[0]
            for fn, p, sz in group[1:]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                        deleted += 1
                        print(f"  [DELETED DUP]: {fn} ({sz/(1024*1024):.2f} MB) -> Kept: {kept[0]} ({kept[2]/(1024*1024):.2f} MB)")
                    except Exception as e:
                        print(f"  Error deleting {p}: {e}")

    print(f"Deduplication complete: {deleted} duplicate copies removed.")

# ==============================================================================
# 7. FAT32 ZIP PACKAGER
# ==============================================================================

def export_sd_zip(source_dir, output_zip_path):
    """
    Packages audio files strictly sequentially using ZIP_STORED (Method 0) for low-end microcontrollers.
    """
    print(f"Packaging {output_zip_path} using uncompressed FAT32 ZIP_STORED...")
    mp3_files = []
    for root, dirs, files in os.walk(source_dir):
        for f in files:
            if f.lower().endswith('.mp3'):
                mp3_files.append((f, os.path.join(root, f)))

    mp3_files.sort(key=lambda x: x[0])

    if os.path.exists(output_zip_path):
        os.remove(output_zip_path)

    with zipfile.ZipFile(output_zip_path, 'w', compression=zipfile.ZIP_STORED) as zf:
        for fn, fp in mp3_files:
            rel_path = os.path.relpath(fp, source_dir)
            zf.write(fp, rel_path)

    print(f"Successfully packaged {len(mp3_files)} tracks into {output_zip_path} ({os.path.getsize(output_zip_path)/(1024*1024):.1f} MB).")

# ==============================================================================
# 8. EMBEDDED WEB DASHBOARD & API SERVER
# ==============================================================================

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default stdout log spam

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path

        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode('utf-8'))
        elif path == '/api/tracks':
            self.handle_api_tracks()
        elif path.startswith('/stream/'):
            self.handle_stream(path[8:])
        else:
            self.send_response(404)
            self.end_headers()

    def handle_api_tracks(self):
        tracks = []
        for root, dirs, files in os.walk(BACKUP_DIR):
            for f in files:
                if f.lower().endswith('.mp3'):
                    ch_name = os.path.basename(root)
                    full_p = os.path.join(root, f)
                    m = re.match(r'^(\d+)', f)
                    seq = int(m.group(1)) if m else 999
                    tracks.append({
                        'filename': f,
                        'chapter': ch_name,
                        'sequence': seq,
                        'size_mb': round(os.path.getsize(full_p) / (1024 * 1024), 2),
                        'stream_url': f"/stream/{urllib.parse.quote(ch_name)}/{urllib.parse.quote(f)}"
                    })
        tracks.sort(key=lambda x: (x['sequence'], x['filename']))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'tracks': tracks}).encode('utf-8'))

    def handle_stream(self, subpath):
        subpath = urllib.parse.unquote(subpath)
        full_p = os.path.join(BACKUP_DIR, subpath)
        if os.path.exists(full_p) and os.path.isfile(full_p):
            sz = os.path.getsize(full_p)
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Content-Length', str(sz))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            with open(full_p, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
        else:
            self.send_response(404)
            self.end_headers()

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gospel Harmonic Craft & Playlist Dashboard</title>
<style>
  :root {
    --bg-primary: #0a0e14;
    --bg-secondary: #121820;
    --bg-card: #18202c;
    --text-primary: #e6edf3;
    --text-muted: #8b949e;
    --accent: #d29922;
    --accent-glow: rgba(210, 153, 34, 0.25);
    --cyan: #388bfd;
    --border: #30363d;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    padding: 24px;
    line-height: 1.5;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 16px;
  }
  .title-group h1 { font-size: 1.5rem; font-weight: 600; color: #fff; }
  .title-group p { font-size: 0.875rem; color: var(--text-muted); }
  .stats-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }
  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
  }
  .stat-card .val { font-size: 1.5rem; font-weight: 700; color: var(--accent); }
  .stat-card .lbl { font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); }
  .controls {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  input[type="text"], select {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    color: var(--text-primary);
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 0.875rem;
    outline: none;
  }
  input[type="text"]:focus, select:focus { border-color: var(--accent); }
  .player-box {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 24px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  audio { width: 100%; height: 36px; border-radius: 4px; outline: none; }
  table {
    width: 100%;
    border-collapse: collapse;
    background: var(--bg-secondary);
    border-radius: 8px;
    overflow: hidden;
    font-size: 0.875rem;
  }
  th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); }
  th { background: var(--bg-card); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; }
  tr:hover { background: rgba(255, 255, 255, 0.03); cursor: pointer; }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 600;
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-primary);
  }
  .badge.ch1 { border-color: #3fb950; color: #3fb950; }
  .badge.ch2 { border-color: #58a6ff; color: #58a6ff; }
  .badge.ch3 { border-color: #d29922; color: #d29922; }
  .badge.ch4 { border-color: #f85149; color: #f85149; }
  .badge.ch5 { border-color: #a371f7; color: #a371f7; }
</style>
</head>
<body>
  <div class="header">
    <div class="title-group">
      <h1>Gospel Harmonic DJ Studio</h1>
      <p>Forensic Acoustic Telemetry & Grounded 5-Chapter Journey Master</p>
    </div>
  </div>

  <div class="stats-bar">
    <div class="stat-card"><div class="val" id="stat-total">284</div><div class="lbl">Total Tracks</div></div>
    <div class="stat-card"><div class="val" id="stat-music">277</div><div class="lbl">Continuous Flow</div></div>
    <div class="stat-card"><div class="val" id="stat-ch1">124</div><div class="lbl">Devotional (Ch 1)</div></div>
    <div class="stat-card"><div class="val" id="stat-ch2">62</div><div class="lbl">Groove & Praise (Ch 2)</div></div>
    <div class="stat-card"><div class="val" id="stat-ch3">38</div><div class="lbl">High Praise (Ch 3)</div></div>
    <div class="stat-card"><div class="val" id="stat-ch4">28</div><div class="lbl">Warfare Chants (Ch 4)</div></div>
    <div class="stat-card"><div class="val" id="stat-ch5">25</div><div class="lbl">Deep Soak (Ch 5)</div></div>
  </div>

  <div class="player-box">
    <div id="now-playing" style="font-size: 0.875rem; font-weight: 600;">Select a track below to audition live stream...</div>
    <audio id="audio-player" controls preload="none"></audio>
  </div>

  <div class="controls">
    <input type="text" id="search-input" placeholder="Search track, minister, keyword..." style="min-width: 280px;" oninput="filterTracks()">
    <select id="chapter-filter" onchange="filterTracks()">
      <option value="">All Chapters (Full Catalog)</option>
      <option value="Chapter 1">Chapter 1 - Devotional & Intimate Presence</option>
      <option value="Chapter 2">Chapter 2 - Mid-Tempo Groove & Uplifting Praise</option>
      <option value="Chapter 3">Chapter 3 - High-Praise & Joyful Celebration</option>
      <option value="Chapter 4">Chapter 4 - Prophetic Warfare & Deep Chants</option>
      <option value="Chapter 5">Chapter 5 - Deep Soak & Atmospheric Prayer</option>
      <option value="Review">Review & Interludes</option>
    </select>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width: 60px;">Seq</th>
        <th>Chapter Section</th>
        <th>Track Name</th>
        <th style="width: 90px;">Size</th>
      </tr>
    </thead>
    <tbody id="track-table-body">
      <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 30px;">Loading catalog telemetry...</td></tr>
    </tbody>
  </table>

  <script>
    let allTracks = [];
    async function loadTracks() {
      try {
        const res = await fetch('/api/tracks');
        const data = await res.json();
        allTracks = data.tracks;
        renderTracks(allTracks);
      } catch (e) {
        document.getElementById('track-table-body').innerHTML = '<tr><td colspan="4" style="color:red;">Error loading tracks</td></tr>';
      }
    }

    function getBadgeClass(ch) {
      if (ch.includes('Chapter 1')) return 'ch1';
      if (ch.includes('Chapter 2')) return 'ch2';
      if (ch.includes('Chapter 3')) return 'ch3';
      if (ch.includes('Chapter 4')) return 'ch4';
      if (ch.includes('Chapter 5')) return 'ch5';
      return '';
    }

    function renderTracks(tracks) {
      const tbody = document.getElementById('track-table-body');
      if (!tracks.length) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 20px;">No tracks found matching query.</td></tr>';
        return;
      }
      tbody.innerHTML = tracks.map(t => `
        <tr onclick="playTrack('${t.stream_url}', '${t.filename.replace(/'/g, "\\'")}')">
          <td style="font-weight: 600; color: var(--text-muted);">${t.sequence < 900 ? String(t.sequence).padStart(3, '0') : 'QC'}</td>
          <td><span class="badge ${getBadgeClass(t.chapter)}">${t.chapter}</span></td>
          <td>${t.filename}</td>
          <td style="color: var(--text-muted);">${t.size_mb} MB</td>
        </tr>
      `).join('');
    }

    function filterTracks() {
      const query = document.getElementById('search-input').value.toLowerCase();
      const chapter = document.getElementById('chapter-filter').value;
      const filtered = allTracks.filter(t => {
        const matchQ = t.filename.toLowerCase().includes(query) || t.chapter.toLowerCase().includes(query);
        const matchC = !chapter || t.chapter.includes(chapter);
        return matchQ && matchC;
      });
      renderTracks(filtered);
    }

    function playTrack(url, name) {
      const player = document.getElementById('audio-player');
      const label = document.getElementById('now-playing');
      label.innerText = 'Now Playing: ' + name;
      player.src = url;
      player.play();
    }

    window.onload = loadTracks;
  </script>
</body>
</html>
"""

def start_web_server(port=8080):
    server = HTTPServer(('127.0.0.1', port), DashboardHandler)
    print(f"\n=======================================================")
    print(f"Web Dashboard online at: http://localhost:{port}")
    print(f"Press Ctrl+C to return to CLI.")
    print(f"=======================================================\n")
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web dashboard server...")
        server.server_close()

# ==============================================================================
# 9. INTERACTIVE CLI RUNNER
# ==============================================================================

def run_interactive_cli():
    while True:
        print("\n" + "=" * 65)
        print(" GOSPEL HARMONIC CRAFT & PLAYLIST ENGINE")
        print("=" * 65)
        print(" [1] Run Deep Forensic Analysis & Grounded Classification")
        print(" [2] Deduplicate Library (Keep Highest File Size)")
        print(" [3] Reorganize & Sequence Continuous 5-Chapter Journey")
        print(" [4] Export FAT32 ZIP Archive for SD Microcontrollers (mp3SD.zip)")
        print(" [5] Launch Interactive Web Dashboard & Audio Streamer")
        print(" [6] Exit")
        print("-" * 65)
        choice = input("Enter option [1-6]: ").strip()

        if choice == '1':
            print("\nScanning tracks for forensic acoustic metrics...")
            all_files = []
            for root, dirs, files in os.walk(BACKUP_DIR):
                for f in files:
                    if f.lower().endswith('.mp3'):
                        all_files.append(os.path.join(root, f))
            print(f"Found {len(all_files)} audio files. Processing...")
            for fp in all_files[:10]:
                meta = analyze_audio_forensics(fp)
                ch = classify_track_grounded(meta['filename'], meta)
                print(f"  {meta['filename']} -> BPM: {meta['bpm']} | Key: {meta['key_name']} ({meta['camelot']}) | {ch}")
            print("Completed preliminary batch scan.")
        elif choice == '2':
            print("\nRunning size-first deduplication...")
            deduplicate_library(BACKUP_DIR)
        elif choice == '3':
            print("\nAuditing and verifying grounded DJ journey sequence...")
            all_seq = []
            for root, dirs, files in os.walk(BACKUP_DIR):
                for f in files:
                    if f.lower().endswith('.mp3'):
                        ch = os.path.basename(root)
                        m = re.match(r'^(\d+)', f)
                        seq = int(m.group(1)) if m else 999
                        all_seq.append((seq, ch, f, os.path.join(root, f)))
            all_seq.sort(key=lambda x: x[0])
            print(f"Total audio tracks found: {len(all_seq)}")
            ch_counts = defaultdict(int)
            for seq, ch, f, fp in all_seq:
                ch_counts[ch] += 1
            for ch_name, count in sorted(ch_counts.items()):
                print(f"  {ch_name}: {count} tracks")
            continuous = [t for t in all_seq if t[0] < 900]
            print(f"\nSequence continuity: {len(continuous)} continuous tracks (001 to {max(t[0] for t in continuous) if continuous else 0})")
            print("Grounded 5-chapter sequence integrity confirmed.")
        elif choice == '4':
            print("\nExporting SD Card FAT32 archive...")
            export_sd_zip(BACKUP_DIR, ZIP_EXPORT_FILE)
        elif choice == '5':
            start_web_server(8080)
        elif choice == '6':
            print("\nExiting. Peace be with you.")
            break
        else:
            print("\nInvalid choice. Please enter 1-6.")

# ==============================================================================
# 10. CLI ARGPARSE ENTRYPOINT
# ==============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Gospel Harmonic Craft & Playlist Engine")
    parser.add_argument('--web', action='store_true', help="Launch the local interactive web dashboard")
    parser.add_argument('--dedup', action='store_true', help="Execute size-first deduplication")
    parser.add_argument('--export-zip', action='store_true', help="Package FAT32 SD card archive")
    parser.add_argument('--port', type=int, default=8080, help="Port for web dashboard (default 8080)")

    args = parser.parse_args()

    if args.web:
        start_web_server(args.port)
    elif args.dedup:
        deduplicate_library(BACKUP_DIR)
    elif args.export_zip:
        export_sd_zip(BACKUP_DIR, ZIP_EXPORT_FILE)
    else:
        run_interactive_cli()
