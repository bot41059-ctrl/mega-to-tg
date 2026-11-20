# 📘 Google Colab Pe Bot Kaise Chalayein (Complete Step-by-Step Guide)

Yeh guide aapko step-by-step batati hai ki kaise aap is **MEGA to Telegram Sequential Bot** ko Google Colab pe bilkul free me run kar sakte hain.

---

## 🛠 Step 1: Zaroori Cheezein (Prerequisites)

Bot run karne ke liye aapke paas yeh 3 cheezein honi chahiye:

### 1. Telegram Bot Token:
1. Telegram open karein aur search karein: [@BotFather](https://t.me/BotFather)
2. Send karein `/newbot` aur apna bot name aur username choose karein.
3. BotFather aapko ek `BOT_TOKEN` dega (jaise `123456789:ABCdefGh...`). Use copy kar lein.

### 2. Telegram API ID & API Hash:
1. Apne browser me open karein: [https://my.telegram.org](https://my.telegram.org)
2. Apna Telegram phone number daal kar login karein.
3. **API development tools** par click karein.
4. Koi bhi app title aur short name dekar create karein.
5. Aapko `App api_id` (number) aur `App api_hash` (string) mil jayega. Use note kar lein.

### 3. Telegram Channel Setup:
1. Ek Telegram Channel banayein (ya existing channel use karein).
2. Channel ke **Settings > Administrators > Add Administrator** me jaakar apne naye bot ko Admin banayein.
3. Bot ko **"Post Messages"** permission zaroor allow karein.
4. Channel ka Username (jaise `@MyChannel`) ya Channel ID (jaise `-1001234567890`) note kar lein.

---

## 🚀 Step 2: Google Colab Setup (2 Aasan Tareeqe)

### Tareeqa A: Colab Notebook Upload Karke (Sabse Aasan)
1. Browser me open karein: [Google Colab](https://colab.research.google.com/)
2. **File > Upload Notebook** par click karein.
3. Is folder me maujood **`Mega_to_Telegram_Colab.ipynb`** file ko select karke upload kar dein.
4. Colab ke left sidebar me **Folder (Files)** icon par click karein aur `megadl` folder aur `requirements.txt` ko drag & drop karke upload kar dein (ya GitHub repo clone kar lein).

### Tareeqa B: Direct GitHub Repo Se (Recommended)
Colab ke pehle cell me bas yeh run karein:
```bash
!git clone <YOUR_GITHUB_REPO_LINK> .
```

---

## ⚙️ Step 3: Notebook Cells Run Karein

Notebook me 4 simple cells hain:

1. **Step 1: Install Dependencies**
   - Play button click karein. Yeh FFmpeg, Megatools aur Python libraries install karega.
2. **Step 2: Bot Configuration**
   - Apni `BOT_TOKEN`, `API_ID`, `API_HASH`, aur `CHANNEL_ID` form fields me daalein.
   - Play button click karein. Configuration automatically `.env` file me save ho jayegi.
3. **Step 3: Anti-Disconnection Keep-Alive (Optional)**
   - Yeh cell Colab ko background me disconnect hone se bachata hai.
4. **Step 4: Start the Bot**
   - Play button click karein. Terminal me aayega:
     `🤖 Bot Started Successfully as @YourBotUsername`

---

## 🎬 Step 4: Bot Ko Use Kaise Karein

1. Telegram me apne Bot ke chat me jayein aur `/start` send karein.
2. Ab koi bhi **MEGA Folder Link** (jaise `https://mega.nz/folder/xxxx#yyyy`) bot ko send karein.
3. Bot turant:
   - Folder ke saare subfolders aur video files ko scan karega.
   - Aapko ek **Hierarchy Tree Report** dikhayega:
     ```
     📁 MEGA Folder Scan Completed!
     🏷 Main Folder: Web Series
     📂 Total Subfolders: 4
     🎬 Total Videos Found: 12
     💾 Total Videos Size: 8.50 GB
     ```
4. **🚀 Upload All Videos to Channel** button par click karein!
5. Bot ek-ek video download karega:
   - Video 1 download -> Channel pe upload with Thumbnail & Duration -> Colab disk se file delete!
   - Video 2 download -> Channel pe upload -> Delete!
   - Is tarah Colab ki storage kabhi full nahi hogi aur aap 100GB+ ka data bhi aasaani se transfer kar payenge!

---

## 🛠 Commands Reference

| Command | Kaam |
| :--- | :--- |
| `/start` | Bot ko start karein aur status dekhein |
| `/setchannel <id>` | Target channel set ya change karein (e.g. `/setchannel @MyChannel`) |
| `/channel` | Current target channel check karein |
| `/cancel` | Chal rahe download ya upload task ko turant stop karein |
| `/status` | Colab ki Free Disk Space aur RAM usage check karein |
| `/help` | Detailed instructions dekhein |
