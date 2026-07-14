# YouTube Dracula — video/audio downloader with section trimming and playlist tools

Download YouTube videos and audio; pick quality, trim to a section, convert to MP3, or pull whole playlists as one file or a zip. Built with Flask + yt-dlp.

## Requirements

- Python 3.9+
- **ffmpeg** installed and on your system PATH (required for merging video+audio, trimming
  sections, and MP3 conversion)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: download from ffmpeg.org and add the `bin` folder to PATH

## Setup and run

```bash
cd tubely
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.
