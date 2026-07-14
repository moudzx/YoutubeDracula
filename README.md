# YouTube Dracula

Download YouTube videos and audio - pick quality, trim to a section, convert to MP3, or pull whole playlists as one file or a zip. Built with Flask + yt-dlp and ffmpeg.

<img width="1340" height="637" alt="wejha" src="https://github.com/user-attachments/assets/6e0b930d-df51-4560-9986-148c7af4b0de" />

<img width="1333" height="635" alt="vid" src="https://github.com/user-attachments/assets/c77f299e-071d-471a-a5f3-c81579e7642a" />

<img width="1327" height="631" alt="audio" src="https://github.com/user-attachments/assets/3da98950-7450-4046-a481-2f08d99d43aa" />

<img width="1325" height="636" alt="VIDcomb" src="https://github.com/user-attachments/assets/aadb6819-c6df-431f-b0a9-f87a5eeb48d2" />

<img width="1323" height="642" alt="VIDZip" src="https://github.com/user-attachments/assets/f8b13fd8-60ba-4eab-80c8-887a58639be0" />

<img width="1337" height="641" alt="audio-comb" src="https://github.com/user-attachments/assets/da609a00-ba9a-469f-a65d-74f0e2c27dd3" />

<img width="1336" height="640" alt="audio-zip" src="https://github.com/user-attachments/assets/f2ab65af-e9e9-4940-8d99-2bf56052ffd0" />


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
