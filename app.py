import os
import re
import uuid
import shutil
import threading
import time
from flask import Flask, request, jsonify, send_file, render_template, after_this_request

import yt_dlp

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Cookie config (needed when YouTube shows "Sign in to confirm you're not a bot") ---
# Set ONE of these environment variables before running the app:
#   YTDLP_COOKIES_FROM_BROWSER=chrome        (or firefox, edge, brave, safari, etc.)
#   YTDLP_COOKIES_FILE=/path/to/cookies.txt  (exported via a browser extension)
COOKIES_FROM_BROWSER = os.environ.get("YTDLP_COOKIES_FROM_BROWSER", "").strip()
COOKIES_FILE = os.environ.get("YTDLP_COOKIES_FILE", "").strip()

# Render (and similar platforms) mount "Secret Files" as read-only at /etc/secrets/...
# yt-dlp needs to be able to WRITE to the cookie jar (it refreshes cookies as it
# runs), so if our configured cookies file lives on a read-only mount, copy it to
# a writable location (/tmp) once at startup and use that copy instead.
if COOKIES_FILE and not os.access(os.path.dirname(COOKIES_FILE) or ".", os.W_OK):
    _writable_cookies = os.path.join("/tmp", os.path.basename(COOKIES_FILE) or "ytcookies.txt")
    try:
        shutil.copyfile(COOKIES_FILE, _writable_cookies)
        COOKIES_FILE = _writable_cookies
    except OSError:
        pass  # fall back to original path; will error clearly later if truly unreadable

# --- ffmpeg location (needed if ffmpeg/ffprobe aren't on your system PATH) ---
# Set this to the FOLDER containing ffmpeg.exe / ffprobe.exe, e.g. on Windows:
#   $env:TUBELY_FFMPEG_DIR = "C:\Users\10User\Downloads\ffmpeg-8.0-essentials_build\bin"
# Do this in the same terminal window before running `python app.py`.
FFMPEG_DIR = os.environ.get("TUBELY_FFMPEG_DIR", "").strip()
# What we hand to yt-dlp's `ffmpeg_location` option specifically.
FFMPEG_LOCATION = FFMPEG_DIR
if FFMPEG_DIR:
    # Prepend to PATH for this process so plain "ffmpeg"/"ffprobe" calls find it
    # (covers both yt-dlp's internal ffmpeg calls and our own subprocess calls).
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

    # yt-dlp's own ffmpeg_location resolution, when given a *directory*, builds
    # "<dir>/ffmpeg" with no extension - which doesn't exist on Windows (needs
    # ffmpeg.exe) and makes yt-dlp report ffmpeg as "not found" even though our
    # own subprocess calls (which rely on PATH + Windows' PATHEXT lookup) work
    # fine. Pointing it at the actual binary file avoids that bad code path.
    _exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    _candidate = os.path.join(FFMPEG_DIR, _exe_name)
    if os.path.exists(_candidate):
        FFMPEG_LOCATION = _candidate


def build_base_opts():
    """Common yt-dlp options, including cookie auth if configured."""
    opts = {"quiet": True, "no_warnings": True}
    if COOKIES_FROM_BROWSER:
        # yt-dlp expects a tuple: (browser, profile, keyring, container) - only browser is required
        opts["cookiesfrombrowser"] = (COOKIES_FROM_BROWSER,)
    elif COOKIES_FILE:
        opts["cookiefile"] = COOKIES_FILE
    if FFMPEG_LOCATION:
        opts["ffmpeg_location"] = FFMPEG_LOCATION
    return opts


# In-memory job store: job_id -> {status, progress, filepath, error, title}
JOBS = {}


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name.strip()[:150] or "video"


def hhmmss_to_seconds(t: str):
    """Accept 'SS', 'MM:SS', or 'HH:MM:SS' -> float seconds. Returns None if empty."""
    if t is None:
        return None
    t = t.strip()
    if t == "":
        return None
    parts = t.split(":")
    parts = [float(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


# Audio formats offered for playlist "one combined file" and "separate audio files" modes
AUDIO_FORMAT_CODECS = {
    "mp3": "mp3",
    "m4a": "m4a",
    "wav": "wav",
    "opus": "opus",
}

# Video quality presets offered for playlist "separate video files" mode
VIDEO_QUALITY_FORMATS = {
    "best": "bestvideo+bestaudio/best",
    "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
}


def audio_postprocessor(fmt):
    codec = AUDIO_FORMAT_CODECS.get(fmt, "mp3")
    pp = {"key": "FFmpegExtractAudio", "preferredcodec": codec}
    if codec == "mp3":
        pp["preferredquality"] = "192"
    return pp


def _ffprobe_streams(path):
    """Return (audio_stream_dict_or_None, video_stream_dict_or_None) via ffprobe, or (None, None) on failure."""
    import subprocess
    import json as _json
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", path],
            capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL,
        )
        if proc.returncode != 0:
            return None, None
        streams = _json.loads(proc.stdout).get("streams", [])
    except Exception:
        return None, None
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    return audio, video


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def info():
    """Fetch video metadata and available formats for a given URL, or playlist track list."""
    data = request.get_json(force=True)
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Cheap first pass: extract_flat avoids fetching full metadata for every
    # playlist entry, so we can tell quickly whether this is a playlist.
    flat_opts = build_base_opts()
    flat_opts["extract_flat"] = "in_playlist"

    try:
        with yt_dlp.YoutubeDL(flat_opts) as ydl:
            flat_result = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": f"Could not fetch video info: {str(e)}"}), 400

    if "entries" in flat_result and flat_result.get("_type") in (None, "playlist"):
        entries = [e for e in flat_result["entries"] if e]
        if not entries:
            return jsonify({"error": "No videos found in this playlist"}), 400

        tracks = []
        for e in entries:
            tracks.append({
                "title": e.get("title") or "Untitled track",
                "duration": e.get("duration"),
                "url": e.get("url") or e.get("webpage_url") or e.get("id"),
            })

        return jsonify({
            "is_playlist": True,
            "playlist_title": flat_result.get("title") or "Playlist",
            "count": len(tracks),
            "tracks": tracks,
        })

    # Not a playlist -> full extraction for real format list
    ydl_opts = build_base_opts()
    ydl_opts["skip_download"] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": f"Could not fetch video info: {str(e)}"}), 400

    if "entries" in result:
        entries = list(result["entries"])
        if not entries:
            return jsonify({"error": "No videos found at this URL"}), 400
        result = entries[0]

    formats = []
    for f in result.get("formats", []):
        # Skip formats with no useful download url or storyboard/image formats
        if f.get("vcodec") == "none" and f.get("acodec") == "none":
            continue
        if f.get("format_note") == "storyboard":
            continue

        is_audio_only = f.get("vcodec") == "none"
        is_video_only = f.get("acodec") == "none"

        height = f.get("height")
        abr = f.get("abr")
        filesize = f.get("filesize") or f.get("filesize_approx")

        label_bits = []
        if is_audio_only:
            label_bits.append("Audio only")
            if abr:
                label_bits.append(f"{round(abr)}kbps")
            ext = f.get("ext", "m4a")
        elif is_video_only:
            label_bits.append(f"{height}p" if height else "Video")
            ext = f.get("ext", "mp4")
        else:
            label_bits.append(f"{height}p" if height else "Video+Audio")
            ext = f.get("ext", "mp4")

        if f.get("fps") and not is_audio_only:
            label_bits.append(f"{f['fps']}fps")

        size_mb = round(filesize / (1024 * 1024), 1) if filesize else None

        formats.append({
            "format_id": f["format_id"],
            "ext": ext,
            "label": " · ".join(label_bits),
            "is_audio_only": is_audio_only,
            "is_video_only": is_video_only,
            "height": height or 0,
            "abr": abr or 0,
            "filesize_mb": size_mb,
        })

    # Sort: combined video+audio (best first), then video-only, then audio-only
    def sort_key(f):
        return (
            0 if not f["is_audio_only"] and not f["is_video_only"] else (1 if f["is_video_only"] else 2),
            -f["height"],
            -f["abr"],
        )

    formats.sort(key=sort_key)

    return jsonify({
        "title": result.get("title"),
        "duration": result.get("duration"),
        "thumbnail": result.get("thumbnail"),
        "uploader": result.get("uploader"),
        "formats": formats,
    })


def _run_download(job_id, url, format_id, is_audio_only, start, end, want_mp3):
    job = JOBS[job_id]
    outtmpl = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    def progress_hook(d):
        if d["status"] == "downloading":
            pct = d.get("_percent_str", "0%").strip()
            job["progress"] = pct
        elif d["status"] == "finished":
            job["progress"] = "processing"

    ydl_opts = build_base_opts()
    ydl_opts.update({
        "outtmpl": outtmpl,
        "progress_hooks": [progress_hook],
        "noplaylist": True,
    })

    # Section download (yt-dlp native trimming via ffmpeg, no full download needed for most sites)
    if start is not None or end is not None:
        start_s = start or 0
        end_s = end  # None means "to the end"
        if end_s is not None:
            section = f"*{start_s}-{end_s}"
        else:
            section = f"*{start_s}-inf"
        ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(start_s, end_s if end_s else float("inf"))])
        ydl_opts["force_keyframes_at_cuts"] = True

    if is_audio_only:
        ydl_opts["format"] = format_id if format_id else "bestaudio/best"
        if want_mp3:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
    else:
        # Combine chosen video format with best audio if the chosen format has no audio
        ydl_opts["format"] = f"{format_id}+bestaudio/best" if format_id else "best"
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if is_audio_only and want_mp3:
                base, _ = os.path.splitext(filename)
                filename = base + ".mp3"
            elif not is_audio_only:
                base, _ = os.path.splitext(filename)
                candidate = base + ".mp4"
                if os.path.exists(candidate):
                    filename = candidate

        job["status"] = "done"
        job["filepath"] = filename
        job["title"] = info.get("title", "video")
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


def _run_playlist_stitch(job_id, url, playlist_title, audio_format):
    """Download every track as audio, then concatenate into one file in the chosen format."""
    job = JOBS[job_id]
    work_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(work_dir, exist_ok=True)
    job["current_track"] = 0
    job["total_tracks"] = 0

    def progress_hook(d):
        if d["status"] == "downloading":
            idx = d.get("info_dict", {}).get("playlist_index") or job["current_track"]
            job["current_track"] = idx
            pct = d.get("_percent_str", "0%").strip()
            job["progress"] = pct
        elif d["status"] == "finished":
            job["progress"] = "processing"

    outtmpl = os.path.join(work_dir, "%(playlist_index)03d - %(title)s.%(ext)s")
    ext = audio_format

    ydl_opts = build_base_opts()
    ydl_opts.update({
        "outtmpl": outtmpl,
        "progress_hooks": [progress_hook],
        "format": "bestaudio/best",
        "postprocessors": [audio_postprocessor(audio_format)],
        "ignoreerrors": True,  # skip unavailable tracks instead of failing the whole playlist
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)

        entries = [e for e in (result.get("entries") or []) if e]
        job["total_tracks"] = len(entries) or job["current_track"]

        track_files = sorted(
            f for f in os.listdir(work_dir) if f.lower().endswith(f".{ext}")
        )
        track_paths = [os.path.join(work_dir, f) for f in track_files]

        if not track_paths:
            raise RuntimeError("No tracks could be downloaded from this playlist.")

        job["progress"] = "stitching"

        # Tracks were downloaded from different source videos, so sample rate
        # / channel layout / codec often differ just enough that a plain
        # stream-copy concat fails, forcing a full re-encode of the whole
        # concatenated file at the end - a slow, single serial job.
        # Instead, normalize each (short) track to identical params up front,
        # in parallel across CPU cores, so the final concat is always a fast
        # stream copy.
        import subprocess
        import concurrent.futures

        reencode_codec = {"mp3": "libmp3lame", "m4a": "aac", "wav": "pcm_s16le", "opus": "libopus"}.get(ext, "libmp3lame")
        target_codec_names = {
            "libmp3lame": "mp3", "aac": "aac", "pcm_s16le": "pcm_s16le", "libopus": "opus",
        }
        target_codec_name = target_codec_names.get(reencode_codec, reencode_codec)

        max_workers = os.cpu_count() or 1
        # Each parallel worker gets 1 ffmpeg thread, so total threads in use
        # stays at core count instead of every worker fighting for all cores
        # (oversubscription that makes parallel re-encoding slower, not faster).
        threads_per_job = 1

        def normalize_track(path):
            audio_stream, _ = _ffprobe_streams(path)
            if (
                audio_stream is not None
                and audio_stream.get("codec_name") == target_codec_name
                and int(audio_stream.get("sample_rate") or 0) == 44100
                and int(audio_stream.get("channels") or 0) == 2
            ):
                return  # already matches target format, no re-encode needed

            tmp_path = path + ".norm." + ext
            cmd = ["ffmpeg", "-y", "-i", path, "-threads", str(threads_per_job),
                   "-ar", "44100", "-ac", "2", "-c:a", reencode_codec]
            if ext != "wav":
                cmd += ["-b:a", "192k"]
            cmd.append(tmp_path)
            t0 = time.time()
            print(f"[job {job_id}] normalize start: {os.path.basename(path)}", flush=True)
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                       stdin=subprocess.DEVNULL, timeout=300)
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"ffmpeg timed out normalizing {os.path.basename(path)} after 300s")
            print(f"[job {job_id}] normalize done: {os.path.basename(path)} in {time.time()-t0:.1f}s", flush=True)
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg failed to normalize track: {proc.stderr[-500:]}")
            os.replace(tmp_path, path)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            list(pool.map(normalize_track, track_paths))

        concat_list_path = os.path.join(work_dir, "concat_list.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for p in track_paths:
                escaped = p.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        final_filename = f"{job_id}_stitched.{ext}"
        final_path = os.path.join(DOWNLOAD_DIR, final_filename)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            final_path,
        ]
        t0 = time.time()
        print(f"[job {job_id}] concat start ({len(track_paths)} tracks)", flush=True)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                   stdin=subprocess.DEVNULL, timeout=300)
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg timed out concatenating tracks after 300s")
        print(f"[job {job_id}] concat done in {time.time()-t0:.1f}s", flush=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed to stitch tracks: {proc.stderr[-500:]}")

        job["status"] = "done"
        job["filepath"] = final_path
        job["title"] = playlist_title or "playlist"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _run_playlist_stitch_video(job_id, url, playlist_title, quality):
    """Download every track as video, then concatenate into one MP4 file, in order."""
    job = JOBS[job_id]
    work_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(work_dir, exist_ok=True)
    job["current_track"] = 0
    job["total_tracks"] = 0

    def progress_hook(d):
        if d["status"] == "downloading":
            idx = d.get("info_dict", {}).get("playlist_index") or job["current_track"]
            job["current_track"] = idx
            pct = d.get("_percent_str", "0%").strip()
            job["progress"] = pct
        elif d["status"] == "finished":
            job["progress"] = "processing"

    outtmpl = os.path.join(work_dir, "%(playlist_index)03d - %(title)s.%(ext)s")

    ydl_opts = build_base_opts()
    ydl_opts.update({
        "outtmpl": outtmpl,
        "progress_hooks": [progress_hook],
        "format": VIDEO_QUALITY_FORMATS.get(quality, VIDEO_QUALITY_FORMATS["best"]),
        "merge_output_format": "mp4",
        "ignoreerrors": True,  # skip unavailable tracks instead of failing the whole playlist
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)

        entries = [e for e in (result.get("entries") or []) if e]
        job["total_tracks"] = len(entries) or job["current_track"]

        track_files = sorted(
            f for f in os.listdir(work_dir) if f.lower().endswith(".mp4")
        )
        track_paths = [os.path.join(work_dir, f) for f in track_files]

        if not track_paths:
            raise RuntimeError("No tracks could be downloaded from this playlist.")

        job["progress"] = "stitching"

        # Tracks came from different source videos, so resolution/codec/fps
        # often mismatch and a plain stream-copy concat fails. Rather than
        # re-encoding the whole concatenated video as one slow serial job at
        # the end, normalize each (much shorter) track to one consistent
        # format up front, in parallel across CPU cores, so the final concat
        # is always a fast stream copy.
        import subprocess
        import concurrent.futures

        target_height = {"best": 1080, "1080": 1080, "720": 720, "480": 480}.get(quality, 1080)

        def _already_matches(path):
            audio_stream, video_stream = _ffprobe_streams(path)
            if video_stream is None:
                return False
            if video_stream.get("codec_name") != "h264":
                return False
            if int(video_stream.get("height") or 0) != target_height:
                return False
            fr = video_stream.get("r_frame_rate") or "0/1"
            try:
                num, den = fr.split("/")
                fps = float(num) / float(den) if float(den) else 0
            except Exception:
                fps = 0
            if round(fps) != 30:
                return False
            if audio_stream is None:
                return False
            if audio_stream.get("codec_name") != "aac":
                return False
            if int(audio_stream.get("sample_rate") or 0) != 44100:
                return False
            return True

        max_workers = os.cpu_count() or 1
        # Each parallel worker gets 1 ffmpeg thread, so total threads in use
        # stays at core count instead of every worker fighting for all cores
        # (oversubscription that makes parallel re-encoding slower, not faster).
        threads_per_job = 1

        def normalize_track(path):
            if _already_matches(path):
                return  # already matches target format, no re-encode needed

            tmp_path = path + ".norm.mp4"
            cmd = [
                "ffmpeg", "-y", "-i", path, "-threads", str(threads_per_job),
                "-vf", f"scale=-2:{target_height}:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2,fps=30",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                tmp_path,
            ]
            t0 = time.time()
            print(f"[job {job_id}] normalize start: {os.path.basename(path)}", flush=True)
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                       stdin=subprocess.DEVNULL, timeout=300)
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"ffmpeg timed out normalizing {os.path.basename(path)} after 300s")
            print(f"[job {job_id}] normalize done: {os.path.basename(path)} in {time.time()-t0:.1f}s", flush=True)
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg failed to normalize track: {proc.stderr[-500:]}")
            os.replace(tmp_path, path)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            list(pool.map(normalize_track, track_paths))

        concat_list_path = os.path.join(work_dir, "concat_list.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for p in track_paths:
                escaped = p.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        final_filename = f"{job_id}_stitched.mp4"
        final_path = os.path.join(DOWNLOAD_DIR, final_filename)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            final_path,
        ]
        t0 = time.time()
        print(f"[job {job_id}] concat start ({len(track_paths)} tracks)", flush=True)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                   stdin=subprocess.DEVNULL, timeout=300)
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg timed out concatenating tracks after 300s")
        print(f"[job {job_id}] concat done in {time.time()-t0:.1f}s", flush=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed to stitch tracks: {proc.stderr[-500:]}")

        job["status"] = "done"
        job["filepath"] = final_path
        job["title"] = playlist_title or "playlist"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _zip_directory(work_dir, final_path):
    import zipfile
    # Audio/video files are already compressed, so ZIP_DEFLATED wastes huge
    # amounts of CPU trying (and failing) to shrink them further. Store them
    # uncompressed instead - this is dramatically faster with no size penalty.
    with zipfile.ZipFile(final_path, "w", zipfile.ZIP_STORED) as zf:
        for fname in sorted(os.listdir(work_dir)):
            fpath = os.path.join(work_dir, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, arcname=fname)


def _run_playlist_separate(job_id, url, playlist_title, mode, fmt_or_quality):
    """Download every track as separate files (audio or video) and zip them up."""
    job = JOBS[job_id]
    work_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(work_dir, exist_ok=True)
    job["current_track"] = 0
    job["total_tracks"] = 0

    def progress_hook(d):
        if d["status"] == "downloading":
            idx = d.get("info_dict", {}).get("playlist_index") or job["current_track"]
            job["current_track"] = idx
            pct = d.get("_percent_str", "0%").strip()
            job["progress"] = pct
        elif d["status"] == "finished":
            job["progress"] = "processing"

    outtmpl = os.path.join(work_dir, "%(playlist_index)03d - %(title)s.%(ext)s")

    ydl_opts = build_base_opts()
    ydl_opts.update({
        "outtmpl": outtmpl,
        "progress_hooks": [progress_hook],
        "ignoreerrors": True,
    })

    if mode == "separate_audio":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [audio_postprocessor(fmt_or_quality)]
    else:  # separate_video
        ydl_opts["format"] = VIDEO_QUALITY_FORMATS.get(fmt_or_quality, VIDEO_QUALITY_FORMATS["best"])
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)

        entries = [e for e in (result.get("entries") or []) if e]
        job["total_tracks"] = len(entries) or job["current_track"]

        files_present = [f for f in os.listdir(work_dir) if os.path.isfile(os.path.join(work_dir, f))]
        if not files_present:
            raise RuntimeError("No tracks could be downloaded from this playlist.")

        job["progress"] = "zipping"

        final_filename = f"{job_id}_tracks.zip"
        final_path = os.path.join(DOWNLOAD_DIR, final_filename)
        _zip_directory(work_dir, final_path)

        job["status"] = "done"
        job["filepath"] = final_path
        job["title"] = playlist_title or "playlist"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@app.route("/api/download_playlist", methods=["POST"])
def download_playlist():
    data = request.get_json(force=True)
    url = (data or {}).get("url", "").strip()
    playlist_title = (data or {}).get("playlist_title", "playlist")
    mode = (data or {}).get("mode", "stitch")  # stitch | stitch_video | separate_audio | separate_video
    fmt = (data or {}).get("format", "mp3")

    if not url:
        return jsonify({"error": "No URL provided"}), 400
    if mode not in ("stitch", "stitch_video", "separate_audio", "separate_video"):
        return jsonify({"error": "Invalid mode"}), 400

    job_id = uuid.uuid4().hex
    JOBS[job_id] = {
        "status": "downloading",
        "progress": "0%",
        "filepath": None,
        "error": None,
        "current_track": 0,
        "total_tracks": 0,
    }

    if mode == "stitch":
        target = _run_playlist_stitch
        args = (job_id, url, playlist_title, fmt)
    elif mode == "stitch_video":
        target = _run_playlist_stitch_video
        args = (job_id, url, playlist_title, fmt)
    else:
        target = _run_playlist_separate
        args = (job_id, url, playlist_title, mode, fmt)

    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/download", methods=["POST"])
def download():
    data = request.get_json(force=True)
    url = (data or {}).get("url", "").strip()
    format_id = (data or {}).get("format_id")
    is_audio_only = bool((data or {}).get("is_audio_only"))
    want_mp3 = bool((data or {}).get("convert_mp3"))
    start = hhmmss_to_seconds((data or {}).get("start_time"))
    end = hhmmss_to_seconds((data or {}).get("end_time"))

    if not url:
        return jsonify({"error": "No URL provided"}), 400
    if end is not None and start is not None and end <= start:
        return jsonify({"error": "End time must be after start time"}), 400

    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "downloading", "progress": "0%", "filepath": None, "error": None}

    thread = threading.Thread(
        target=_run_download,
        args=(job_id, url, format_id, is_audio_only, start, end, want_mp3),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Unknown job"}), 404
    print(f"[job {job_id}] status={job['status']} progress={job.get('progress')} "
          f"track={job.get('current_track')}/{job.get('total_tracks')}", flush=True)
    if job["status"] == "error" and job.get("error"):
        print(f"[job {job_id}] ERROR DETAIL: {job['error']}", flush=True)
    return jsonify({
        "status": job["status"],
        "progress": job.get("progress"),
        "error": job.get("error"),
        "current_track": job.get("current_track"),
        "total_tracks": job.get("total_tracks"),
    })


@app.route("/api/file/<job_id>")
def get_file(job_id):
    job = JOBS.get(job_id)
    if not job or job["status"] != "done" or not job["filepath"] or not os.path.exists(job["filepath"]):
        return jsonify({"error": "File not ready"}), 404

    filepath = job["filepath"]
    title = sanitize_filename(job.get("title", "video"))
    ext = os.path.splitext(filepath)[1]
    download_name = f"{title}{ext}"

    @after_this_request
    def cleanup(response):
        def delayed_cleanup():
            time.sleep(30)
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass
            JOBS.pop(job_id, None)
        threading.Thread(target=delayed_cleanup, daemon=True).start()
        return response

    return send_file(filepath, as_attachment=True, download_name=download_name)


import shutil as _shutil
for _exe in ("ffmpeg", "ffprobe"):
    if _shutil.which(_exe) is None:
        print(f"WARNING: '{_exe}' was not found. Playlist stitching/zipping and MP3 "
              f"conversion will fail until it's available. Set TUBELY_FFMPEG_DIR to the "
              f"folder containing {_exe}.exe (or add it to PATH) and restart.", flush=True)
    else:
        print(f"OK: '{_exe}' found at {_shutil.which(_exe)}", flush=True)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
