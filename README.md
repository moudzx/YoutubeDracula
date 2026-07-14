# YouTube Dracula

Download YouTube videos and audio - pick quality, trim to a section, convert to MP3, or pull whole playlists as one file or a zip. Built with Flask + yt-dlp and ffmpeg.

<img width="676" height="635" alt="UI" src="https://github.com/user-attachments/assets/381c107b-e219-44c2-b453-e5842fb965e1" />

<img width="679" height="628" alt="vid" src="https://github.com/user-attachments/assets/87c1f8be-e16b-4c16-9e71-99d844d3bb5e" />

<img width="676" height="636" alt="aud" src="https://github.com/user-attachments/assets/c1febafb-26c2-4954-9814-9f78223d4abc" />

<img width="657" height="636" alt="audZip" src="https://github.com/user-attachments/assets/c75943e3-5bd3-47f3-90cd-92c349e877ec" />

<img width="642" height="635" alt="audOne" src="https://github.com/user-attachments/assets/a875b01b-4f2d-4daa-af23-04b8a831bbdf" />

<img width="655" height="634" alt="vidOne" src="https://github.com/user-attachments/assets/c7c42620-0061-45a4-b20b-27210eb00e16" />


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
