# YouTube Dracula

Downloading content from YouTube is often a frustrating, multi-step process. Users typically need separate tools to download a video, another to convert it to MP3, and a third if they only want a specific clip or an entire playlist. This fragmentation wastes time and creates a confusing experience, especially for non-technical users. YoutubeDracula solves this by consolidating all these tasks into one streamlined tool, eliminating the need to juggle multiple websites or command-line utilities.

YoutubeDracula provides a simple, web-based interface where users can paste a YouTube link and choose their desired action in just a few clicks. First, it can download videos in your chosen quality. Second, it can extract and convert audio to MP3 format. Third, it allows you to trim a video to a specific section, saving only the part you need. Finally, it can process entire playlists, offering the option to download each video individually or combine them into a single file or a convenient ZIP archive.

## Website

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

Then open **http://localhost:5000** in your browser to run locally, deployment is still under construction [https://youtube-dracula.onrender.com/]

In the terminal, you can monitor the downloading process in real-time

<img width="3070" height="1726" alt="process" src="https://github.com/user-attachments/assets/f2407fea-34ad-46db-a7cf-2d45e12bb9db" />
