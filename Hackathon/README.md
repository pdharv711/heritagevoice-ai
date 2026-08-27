# HeritageVoice AI - Multilingual Smart Tour Guide

Interactive AI narrative guide with camera monument recognition and native regional audio synthesis, designed for the **OMNIKON National Hackathon 2026**.

Developed by Team **Tech Sparker** (Parmar Dhruvil, Patel Dharv).

---

## Features
1. **Live Camera Monument Recognition**: Users can capture a live photo of a monument or upload an image. Google Gemini 1.5 Flash Vision identifies the structure.
2. **Multilingual Story Synthesis**: Narrates the monument history in 10+ languages (English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, French, Spanish) utilizing natural-sounding browser TTS.
3. **Factual Grounding (RAG)**: Uses a structured monument database of historical facts to prevent AI hallucinations.
4. **Interactive Two-way Q&A**: Users can type or use browser-native speech recognition to ask follow-up questions about the monument.

---

## Tech Stack
- **Frontend**: Next.js 14, React, Tailwind CSS, Lucide icons, Web Speech API (TTS & Speech Recognition)
- **Backend API**: Python FastAPI, Uvicorn, Pillow, Pydantic
- **AI Engine**: Google Gemini 1.5 Flash API (google-generativeai)

---

## Directory Structure
```
/ (workspace root)
├── backend/
│   ├── main.py              # FastAPI application server
│   ├── database.py          # Monument catalog (Taj Mahal, Red Fort, Sun Temple, etc.)
│   ├── config.py            # Configuration & environment loader
│   ├── requirements.txt     # Python packages
│   └── create_test_images.py# Script to generate colored mock images
├── frontend/
│   ├── package.json         # Node.js dependencies
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx     # Mobile-first dashboard layout
│   │   │   ├── layout.tsx   # Styling & metadata config
│   │   │   └── globals.css  # Tailwind configurations
│   │   └── components/
│   │       ├── CameraFeed.tsx      # HTML5 video capture & file fallback
│   │       ├── LanguageSelector.tsx # Multilingual option list
│   │       └── ChatWindow.tsx      # Q&A conversation & Speech TTS
│   └── tailwind.config.ts
├── test_images/             # Generated test images for demo mode
└── run_all.bat              # Double-click launcher for Windows
```

---

## Quick Start (Windows)

### 1. Configure the Gemini API Key
Rename/copy `backend/.env.example` to `backend/.env` and replace `YOUR_GEMINI_API_KEY_HERE` with your actual Google AI Studio API key.
*(If no API key is provided, the project runs in **Demo Mode**, utilizing size check mapping for the `test_images/` to mock monument detection and answer questions).*

### 2. Launch the Application
Simply double-click the **`run_all.bat`** file in the root folder.
This will:
- Open a Command Prompt running the FastAPI backend on `http://127.0.0.1:8000`.
- Open a second Command Prompt running the Next.js frontend on `http://localhost:3000`.
- Copy configuration defaults if not already present.

Open your browser and navigate to **`http://localhost:3000`** to view the app!

---

## Testing Monument Recognition in Demo Mode
If you are running in **Demo Mode** (without a Gemini API Key), we have pre-generated solid-color test images in the `test_images/` directory. Uploading them maps to respective monuments in the catalog:
- `taj_mahal_test.jpg` -> Taj Mahal
- `red_fort_test.jpg` -> Red Fort
- `sun_temple_test.jpg` -> Konark Sun Temple
- `hampi_test.jpg` -> Virupaksha Temple (Hampi)
- `qutub_minar_test.jpg` -> Qutub Minar
