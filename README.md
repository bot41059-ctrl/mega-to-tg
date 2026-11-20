<p align="center">
  <img src="assests/logo.png" width="180" height="180" alt="Mega to Telegram Bot Logo" />
  <br>
  <h1>🚀 Mega.nz to Telegram Sequential Bot</h1>
  <p><b>Recursive Folder Scanner & Sequential Video Uploader for Telegram Channels</b></p>
  <p><i>Specially optimized for Google Colab, VPS, and local environments with Zero-Disk Overflow protection.</i></p>
</p>

---

## 🌟 Key Highlights

- 🔍 **Deep Recursive Scanner:** Traverses MEGA public folders to arbitrary depths, automatically discovering all nested subfolders and video files.
- 🌳 **Interactive Directory Tree:** Presents a beautiful ASCII tree report summarizing folder hierarchy, video counts, and size breakdowns before transfer starts.
- ⚡ **Sequential Transfer Engine:** Downloads **one video at a time**, extracts metadata/thumbnail, uploads to Telegram, and **immediately deletes the local copy from disk**!
- 💾 **Google Colab Friendly:** Eliminates "Disk Full / Out of Memory" crashes on Google Colab by keeping disk usage minimal at all times.
- 🎬 **Rich Video Streaming:** Generates video thumbnails, duration, dimensions, and custom captions with `supports_streaming=True`.
- 🔪 **Smart File Splitting:** Automatically splits video files larger than Telegram's 2GB limit into parts and uploads them sequentially.
- 📢 **Direct Channel Uploading:** Upload directly to any Telegram Channel (or private chat) with real-time speed, percentage, and ETA progress bars.
- 🛑 **Graceful Cancellation:** Cancel tasks anytime via `/cancel` command or inline button with automatic temporary file cleanup.

---

## 📸 How It Works

```
1. Send MEGA Folder URL  ===>  2. Deep Scan & Tree Map  ===>  3. Sequential Processing Loop
                               [📁 Main Folder]              ┌── 1. Download Video 1
                               ├── 📁 Season 1 (10 vids)     ├── 2. Extract Thumb & Meta
                               └── 📁 Season 2 (12 vids)     ├── 3. Upload to Channel
                                                             └── 4. Delete Local File (Disk Free!)
                                                             └── Repeat for Video 2, 3...
```

---

## 🚀 Quick Start on Google Colab

The easiest way to run the bot is with Google Colab:

1. Open **[Google Colab](https://colab.research.google.com/)**.
2. Upload the provided **[`Mega_to_Telegram_Colab.ipynb`](Mega_to_Telegram_Colab.ipynb)** notebook.
3. Fill your Telegram credentials (`BOT_TOKEN`, `API_ID`, `API_HASH`, `CHANNEL_ID`) in the form.
4. Run the cells and start sending MEGA links to your bot!

👉 Detailed Hindi/English guide available in **[COLAB_GUIDE.md](COLAB_GUIDE.md)**.

---

## 💻 Local / VPS Setup

### 1. Clone the repository
```bash
git clone https://github.com/partiallywritten/Mega.nz-Bot.git
cd Mega.nz-Bot
```

### 2. Install dependencies
Make sure `ffmpeg` is installed on your operating system:
- **Ubuntu/Debian:** `sudo apt-get install -y ffmpeg megatools`
- **Windows:** Download FFmpeg from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add to PATH.

Install Python libraries:
```bash
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -U -r requirements.txt
```

### 3. Configure `.env`
Copy `.env.sample` to `.env`:
```bash
cp .env.sample .env
```
Edit `.env` with your values:
```ini
APP_ID=12345678
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token_from_botfather
CHANNEL_ID=-1001234567890
AUTH_USERS=*
```

### 4. Run the Bot
```bash
python -m megadl
```

---

## 🛠 Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Displays welcome message, bot status, and target channel |
| `/setchannel <channel>` | Sets target channel (e.g. `/setchannel @MyChannel` or `-1001234567890`) |
| `/channel` | Shows current configured channel |
| `/status` | Displays system RAM usage, free disk storage, and active tasks |
| `/cancel` | Cancels any active downloading/uploading process |
| `/help` | Detailed instructions and usage guide |

---

## 📁 Project Structure

```
mega-to-tg/
├── megadl/
│   ├── helpers/
│   │   ├── crypt.py            # MEGA key decryption & AES-CTR streaming
│   │   ├── cypher.py           # Enhanced Pyrogram client & task tracking
│   │   ├── files.py            # File utilities & splitters
│   │   ├── pyros.py            # Visual progress bars & throttle handlers
│   │   ├── sysfncs.py          # Process execution & subprocess helpers
│   │   └── video_processor.py  # FFmpeg thumbnail & metadata extractor
│   ├── lib/
│   │   ├── mega_scanner.py     # Recursive folder scanner & tree generator
│   │   ├── mega_downloader.py  # Chunked AES-CTR direct MEGA downloader
│   │   ├── megatools.py        # Megatools fallback wrapper
│   │   └── splitter.py         # 2GB+ file splitter
│   ├── modules/
│   │   ├── callbacks.py        # Inline button handlers & cancellation
│   │   ├── generals.py         # /start, /help, /setchannel, /status
│   │   └── mega_dl.py          # Core scanning & sequential processing loop
│   ├── __init__.py
│   └── __main__.py
├── Mega_to_Telegram_Colab.ipynb # Ready-to-run Google Colab Notebook
├── COLAB_GUIDE.md               # Step-by-step Hindi/English Colab Guide
├── .env.sample                  # Configuration template
├── requirements.txt             # Python dependencies
└── README.md                    # Documentation
```

---

## ⚖️ License & Disclaimer

This project is licensed under the GNU General Public License v3.0.  
This tool is intended for personal backups and data migration. Please respect copyright laws and Mega's terms of service.
