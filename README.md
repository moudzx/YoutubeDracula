# YouTube Dracula

Download YouTube videos and audio - pick quality, trim to a section, convert to MP3, or pull whole playlists as one file or a zip. Built with Flask + yt-dlp and ffmpeg.

<img width="1530" height="1384" alt="interface" src="https://github.com/user-attachments/assets/2835afe9-78db-4e8e-b581-836e18ec5da6" />

<img width="679" height="628" alt="vid" src="https://github.com/user-attachments/assets/87c1f8be-e16b-4c16-9e71-99d844d3bb5e" />

<img width="676" height="636" alt="aud" src="https://github.com/user-attachments/assets/c1febafb-26c2-4954-9814-9f78223d4abc" />

<img width="657" height="636" alt="audZip" src="https://github.com/user-attachments/assets/c75943e3-5bd3-47f3-90cd-92c349e877ec" />

<img width="642" height="635" alt="audOne" src="https://github.com/user-attachments/assets/a875b01b-4f2d-4daa-af23-04b8a831bbdf" />

<img width="655" height="634" alt="vidOne" src="https://github.com/user-attachments/assets/c7c42620-0061-45a4-b20b-27210eb00e16" />


## Requirements to run locally

- Python 3.9+
- **ffmpeg** installed and on your system PATH (required for merging video+audio, trimming
  sections, and MP3 conversion)
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: download from ffmpeg.org and add the `bin` folder to PATH

 Setup and run

```bash
cd tubely
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.

In the terminal, you can monitor the downloading process in real-time

<img width="3070" height="1726" alt="process" src="https://github.com/user-attachments/assets/f2407fea-34ad-46db-a7cf-2d45e12bb9db" />


## Website

Or just use the website.

https://youtube-dracula.onrender.com/
