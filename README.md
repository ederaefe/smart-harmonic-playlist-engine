# Gospel Harmonic Playlist Engine

Unified single-use tool for forensic acoustic extraction, grounded 5-chapter classification, size-first deduplication, harmonic DJ sequencing, and FAT32 SD archive export.

Includes both an Interactive Terminal CLI and a Local Web Dashboard.

---

## Overview

Portable MP3 players and Bluetooth speakers with MicroSD card readers (JieLi AC690X, BuildWin, Actions chipsets) struggle with scrambled file order, bloated ID3 artwork header crashes, and abrupt tempo/key jumps.

The Gospel Harmonic Playlist Engine solves these problems by providing:
1. Grounded 5-Chapter Mood Arc: Sequences continuous worship journeys from intimate acoustic devotion to celebratory high praise, prophetic warfare, and deep soaking prayer.
2. Forensic Acoustic Telemetry: Short-Time Fourier Transform (STFT) chromagram key detection, Krumhansl-Schmuckler harmonic correlation mapped to the Camelot Wheel (1A-12B), dynamic RMS energy profiling, and tempo folding de-aliasing.
3. Maximum-Weight Hamiltonian DJ Sequencing: Solves optimal track-to-track transitions using greedy nearest neighbor search and 2-Opt local search refinement.
4. Size-First Deduplication: Identifies duplicate tracks across different bitrate and naming variants, retaining the largest byte-size copy.
5. Microcontroller-Safe FAT32 Packaging: Exports sequentially numbered files in uncompressed ZIP_STORED format (`mp3SD.zip`) for instant extraction and physical FAT directory table alignment.

---

## The 5-Chapter Listening Experience

The library of 284 tracks is structured into 277 continuous music selections across 5 distinct chapters, plus an isolated Review & Interludes section:

| Chapter | Track Range | Track Count | Target Energy & Acoustic Character |
| :--- | :--- | :--- | :--- |
| Chapter 1: Devotional Warm-Up & Intimate Presence | 001 - 124 | 124 tracks | 68-84 true BPM, acoustic guitars, warm piano pads, reverent dynamics (-18 to -11 dBFS). |
| Chapter 2: Mid-Tempo Groove & Uplifting Praise | 125 - 186 | 62 tracks | 92-118 BPM, syncopated Afro-gospel rhythms, upbeat faith declarations. |
| Chapter 3: High-Praise & Joyful Celebration | 187 - 224 | 38 tracks | 118-144+ BPM, peak loudness (-12.5 dBFS), celebratory dance and praise anthems. |
| Chapter 4: Prophetic Warfare & Deep Chants | 225 - 252 | 28 tracks | 120-140 BPM cadence, 71.4% minor modality, driving marching drums and warfare intercession. |
| Chapter 5: Deep Soak, Atmospheric Prayer & Reflection | 253 - 277 | 25 tracks | <72 BPM ambient pads, extended duration (>7 min), contemplative soaking peace. |
| Review & Interludes | REVIEW_* | 8 tracks | Spoken teachings, voice notes, ceremonial anthems, and duplicate audio versions held outside mix. |

---

## Calibrated Forensic Patterns & Mathematical Rules

Analysis of the 284-track catalog revealed key mathematical signatures incorporated into `engine.py`:

1. Tempo Folding De-Aliasing Rule:
   Naive onset detectors mistake 16th-note drum shakers and acoustic guitar strums for double tempo (e.g. 143.6 BPM instead of 71.8 BPM). When titles contain devotional markers and raw BPM is >= 130 BPM, the engine applies a 0.5x tempo-folding factor to preserve the true downbeat pulse.

2. Duration Boundary Rule:
   Commercial radio praise and groove songs (Chapters 2 and 3) have an average duration of 3.4-3.5 minutes. In contrast, live spontaneous warfare chants (Chapter 4) and prayer soaking ministrations (Chapter 5) jump to an average duration of 8.0-8.9 minutes (reaching up to 23.4 minutes).

3. Harmonic Modality Rule:
   Warfare chants (Chapter 4) are predominantly Minor modality (71.4% Minor: Ab Minor, D Minor, F# Minor). High praise and Afro-gospel grooves (Chapters 2 and 3) favor Major modality (55-60% Major) with bright spectral distribution.

4. Loudness Compression Ceiling:
   Chapter 3 operates at peak loudness (-12.5 dBFS mean). Chapters 1 and 5 preserve wide dynamic headroom (-14 to -24 dBFS) with extended natural reverb decay tails (>0.45s).

---

## Getting Started

### Prerequisites

- Python 3.8 or newer
- Standard libraries: `os`, `sys`, `re`, `json`, `math`, `shutil`, `zipfile`, `argparse`, `http.server`, `urllib`
- Optional scientific libraries: `numpy`, `librosa` (for deep STFT chromagram analysis)
- Optional external tools: `ffmpeg` and `ffprobe` (for center-slice audio decoding)

### Usage

The unified engine can be operated in two modes:

#### 1. Interactive Terminal CLI
```bash
python engine.py
```
Provides an interactive menu for:
- [1] Run Deep Forensic Analysis & Grounded Classification
- [2] Deduplicate Library (Keep Highest File Size)
- [3] Reorganize & Sequence Continuous 5-Chapter Journey
- [4] Export FAT32 ZIP Archive for SD Microcontrollers (mp3SD.zip)
- [5] Launch Interactive Web Dashboard & Audio Streamer
- [6] Exit

#### 2. Local Web Dashboard
```bash
python engine.py --web
```
Launches an embedded HTTP server on `http://localhost:8080` featuring:
- Real-time catalog summary statistics by chapter.
- Full-text search by title, artist, or keyword.
- Chapter filtering dropdown.
- In-browser HTML5 audio player streaming local MP3 bitstreams directly.

#### 3. Command-Line Flags
- Execute size-first deduplication:
  ```bash
  python engine.py --dedup
  ```
- Export uncompressed FAT32 ZIP archive:
  ```bash
  python engine.py --export-zip
  ```
- Launch web dashboard on a custom port:
  ```bash
  python engine.py --web --port 9000
  ```

---

## File Structure

```
Music/
├── engine.py                     # Unified single-use CLI and Web dashboard engine
├── beats.txt                     # Grounded forensic manifest (BPM, Key, Camelot, Energy)
├── documentation.md              # Technical reference and empirical calibration log
├── README.md                     # Project overview and user guide
├── mp3SD.zip                     # Sequential FAT32 archive for SD microcontrollers
├── _duplicates_backup/           # Master catalog organized into 5 chapters + Review
│   ├── Chapter 1 - Devotional & Intimate Presence/     # 124 tracks (001 - 124)
│   ├── Chapter 2 - Mid-Tempo Groove & Uplifting Praise/ # 62 tracks (125 - 186)
│   ├── Chapter 3 - High-Praise & Joyful Celebration/   # 38 tracks (187 - 224)
│   ├── Chapter 4 - Prophetic Warfare & Deep Chants/    # 28 tracks (225 - 252)
│   ├── Chapter 5 - Deep Soak & Atmospheric Prayer/     # 25 tracks (253 - 277)
│   └── Review & Interludes/                            # 8 tracks (QC / Interludes)
```

---

## License

MIT License. Free to use, adapt, and share for audio library curation, speaker firmware optimization, and personal music collections.
