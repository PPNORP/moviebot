from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone
import requests
import re
from fastapi.responses import JSONResponse

@app.get("/")
def root():
    return JSONResponse({"ok": True, "message": "MovieBot backend is running", "docs": "/docs"})


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI()
api_router = APIRouter(prefix="/api")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"

# TMDB Genre IDs
GENRES = {
    "Action": 28,
    "Comedy": 35,
    "Drama": 18,
    "Horror": 27,
    "Romance": 10749,
    "Sci-Fi": 878,
    "Thriller": 53,
    "Animation": 16,
    "Fantasy": 14,
    "Mystery": 9648,
    "Adventure": 12,
    "Family": 10751,
    "Crime": 80
}

DNA_TYPES = ["dark", "healing", "fantasy", "motivation"]

# “DNA หนัง” 7 ข้อ (A/B/C/D -> 4 สาย)
QUESTIONS = [
    {
        "key": "q1_weather",
        "text": "🎬 DNA หนัง (1/7)\nสภาพอากาศในหนังแบบไหนที่ทำให้คุณอยากนั่งดูจนจบ?\n"
                "A) ฝนตกหนัก มืดครึ้ม หรือพายุเข้า (Dark)\n"
                "B) แดดอ่อนๆ ยามเช้า หรือฟ้าหลังฝน (Healing)\n"
                "C) ท้องฟ้าที่เต็มไปด้วยดาว หรือแสงเหนือ (Fantasy)\n"
                "D) แสงแดดจ้าตอนกลางวัน สดใส มีพลัง (Motivation)\n"
                "ตอบ A/B/C/D:",
        "map": {"A":"dark","B":"healing","C":"fantasy","D":"motivation"}
    },
    {
        "key": "q2_feeling",
        "text": "🎬 DNA หนัง (2/7)\nคุณมักจะเปิดดูหนังเมื่อรู้สึกอย่างไร?\n"
                "A) อยากจมดิ่งกับอารมณ์/หาคำตอบให้ชีวิต (Dark)\n"
                "B) เหนื่อย อยากได้อะไรปลอบใจ (Healing)\n"
                "C) เบื่อโลกความจริง อยากวาร์ปไปที่อื่น (Fantasy)\n"
                "D) ท้อ อยากได้แรงบันดาลใจให้ฮึด (Motivation)\n"
                "ตอบ A/B/C/D:",
        "map": {"A":"dark","B":"healing","C":"fantasy","D":"motivation"}
    },
    {
        "key": "q3_pacing",
        "text": "🎬 DNA หนัง (3/7)\nจังหวะ (Pacing) แบบไหนที่ไม่ทำให้คุณกด Skip?\n"
                "A) ค่อยๆ กดดัน เน้นความเงียบ/สายตา (Dark)\n"
                "B) เรื่อยๆ เรียบง่าย เหมือนชีวิตจริง (Healing)\n"
                "C) รวดเร็ว ตื่นเต้น ว้าวตลอด (Fantasy)\n"
                "D) หนักแน่น มั่นคง มีช่วงปลุกใจ (Motivation)\n"
                "ตอบ A/B/C/D:",
        "map": {"A":"dark","B":"healing","C":"fantasy","D":"motivation"}
    },
    {
        "key": "q4_place",
        "text": "🎬 DNA หนัง (4/7)\nถ้าเลือกสถานที่หลักในเรื่องได้ คุณอยากให้เกิดที่ไหน?\n"
                "A) เมืองใหญ่ วุ่นวาย เต็มไปด้วยความลับ (Dark)\n"
                "B) บ้านไม้ชนบท/คาเฟ่เล็กๆ (Healing)\n"
                "C) ดินแดนเวทมนตร์/ยานอวกาศ (Fantasy)\n"
                "D) สนามกีฬา/ออฟฟิศ/ที่ฝึกฝนตัวเอง (Motivation)\n"
                "ตอบ A/B/C/D:",
        "map": {"A":"dark","B":"healing","C":"fantasy","D":"motivation"}
    },
    {
        "key": "q5_soundtrack",
        "text": "🎬 DNA หนัง (5/7)\nเพลงประกอบแบบไหนที่ติดหูคุณที่สุด?\n"
                "A) เปียโนเศร้าๆ / บีทลึกลับ (Dark)\n"
                "B) Acoustic ฟังสบาย / เสียงธรรมชาติ (Healing)\n"
                "C) ออร์เคสตร้าอลังการ (Fantasy)\n"
                "D) จังหวะคึกคัก ปลุกใจ (Motivation)\n"
                "ตอบ A/B/C/D:",
        "map": {"A":"dark","B":"healing","C":"fantasy","D":"motivation"}
    },
    {
        "key": "q6_cry",
        "text": "🎬 DNA หนัง (6/7)\nเวลาเห็นตัวละครร้องไห้ คุณอยากให้เขาร้องเพราะอะไร?\n"
                "A) ความจริงโหดร้าย/บาดแผลในใจ (Dark)\n"
                "B) ซาบซึ้งในความสัมพันธ์ (Healing)\n"
                "C) ลาจากโลก/สิ่งที่รัก (Fantasy)\n"
                "D) ตื้นตันหลังฝ่าฟันอุปสรรคสำเร็จ (Motivation)\n"
                "ตอบ A/B/C/D:",
        "map": {"A":"dark","B":"healing","C":"fantasy","D":"motivation"}
    },
    {
        "key": "q7_quote",
        "text": "🎬 DNA หนัง (7/7)\nข้อคิดแบบไหนที่คุณมักเซฟเก็บไว้หลังดูจบ?\n"
                "A) “โลกนี้ไม่ได้สวยงามอย่างที่คิด” (Dark)\n"
                "B) “ใจดีกับตัวเองบ้างก็ได้นะ” (Healing)\n"
                "C) “จินตนาการสำคัญกว่าความรู้” (Fantasy)\n"
                "D) “ความพยายามไม่เคยทำร้ายใคร” (Motivation)\n"
                "ตอบ A/B/C/D:",
        "map": {"A":"dark","B":"healing","C":"fantasy","D":"motivation"}
    },
]

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    reply: str
    done: bool

class Movie(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str
    year: Optional[str] = None
    rating: Optional[float] = None
    overview: Optional[str] = None
    poster: Optional[str] = None

class RecommendResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dna: str
    scores: Dict[str, int]
    answers: Dict[str, str]
    movies: List[Movie]

class ChatSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step: int = 0  # 0=ยังไม่ start, 1..len(QUESTIONS)=กำลังตอบข้อ step, len+1=จบ
    answers: Dict[str, str] = Field(default_factory=dict)
    scores: Dict[str, int] = Field(default_factory=lambda: {k: 0 for k in DNA_TYPES})
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

def _normalize_choice(text: str) -> Optional[str]:
    """
    รับคำตอบแบบ A/B/C/D หรือพิมพ์เต็ม ๆ ก็ได้ (ไทย/อังกฤษ)
    คืนค่า 'A'/'B'/'C'/'D' ถ้าจับได้ ไม่งั้น None
    """
    t = text.strip().upper()

    # ถ้าพิมพ์เป็นตัวอักษรตรง ๆ
    if t in ["A", "B", "C", "D"]:
        return t

    # ถ้าพิมพ์เช่น "a)" "A." "ตอบ A" "ข้อ A"
    m = re.search(r"\b([ABCD])\b", t)
    if m:
        return m.group(1)

    # fallback จากคำในวงเล็บ
    # dark/healing/fantasy/motivation -> map เป็น A/B/C/D ตามข้อ
    if "DARK" in t or "มืด" in t or "ลึกลับ" in t:
        return "A"
    if "HEAL" in t or "ปลอบ" in t or "สบาย" in t or "อบอุ่น" in t:
        return "B"
    if "FANT" in t or "เวท" in t or "อวกาศ" in t or "จินตนาการ" in t:
        return "C"
    if "MOTIV" in t or "แรงบันดาลใจ" in t or "ฮึด" in t or "ปลุกใจ" in t:
        return "D"

    return None

def _dna_winner(scores: Dict[str, int]) -> str:
    # ถ้าเสมอ ให้เรียงตาม priority นี้ (ปรับได้)
    priority = ["fantasy", "motivation", "healing", "dark"]
    best = max(scores.values())
    tied = [k for k, v in scores.items() if v == best]
    for p in priority:
        if p in tied:
            return p
    return tied[0]

def _tmdb_params_from_dna(dna: str) -> Dict:
    """
    map DNA -> TMDB discover params
    """
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "page": 1,
    }

    # แนวทาง: ใส่หลาย genre ได้โดย comma-separated
    if dna == "dark":
        # ดาร์ค/ลึกลับ/กดดัน
        params["with_genres"] = f"{GENRES['Thriller']},{GENRES['Mystery']},{GENRES['Crime']}"
        params["sort_by"] = "vote_average.desc"
        params["vote_count.gte"] = 200
    elif dna == "healing":
        # อบอุ่น/ฟีลกู๊ด/ปลอบใจ
        params["with_genres"] = f"{GENRES['Drama']},{GENRES['Romance']},{GENRES['Comedy']}"
        params["sort_by"] = "popularity.desc"
        params["vote_count.gte"] = 100
    elif dna == "fantasy":
        # แฟนตาซี/ผจญภัย/ไซไฟ
        params["with_genres"] = f"{GENRES['Fantasy']},{GENRES['Adventure']},{GENRES['Sci-Fi']},{GENRES['Animation']}"
        params["sort_by"] = "popularity.desc"
        params["vote_count.gte"] = 100
    elif dna == "motivation":
        # แรงบันดาลใจ/ฮึด/เส้นทางชีวิต (ทำได้ดีด้วย drama + action + family)
        params["with_genres"] = f"{GENRES['Drama']},{GENRES['Action']},{GENRES['Family']}"
        params["sort_by"] = "vote_average.desc"
        params["vote_count.gte"] = 150

    return params

@api_router.get("/")
async def root():
    return {"message": "MovieBot API"}

@api_router.post("/chat", response_model=ChatResponse)
async def chat(msg: ChatMessage):
    user_msg = msg.message.strip()

    session = await db.chat_sessions.find_one({}, {"_id": 0})
    if not session:
        session = ChatSession().model_dump()
        session["timestamp"] = session["timestamp"].isoformat()
        await db.chat_sessions.insert_one(session)

    # reset
    if user_msg.lower() in ["reset", "restart"]:
        await db.chat_sessions.delete_many({})
        new_session = ChatSession().model_dump()
        new_session["timestamp"] = new_session["timestamp"].isoformat()
        await db.chat_sessions.insert_one(new_session)
        return ChatResponse(reply="รีเซ็ตแล้ว ✅ พิมพ์ start เพื่อเริ่มใหม่", done=False)

    # start
    if user_msg.lower() == "start":
        session["step"] = 1
        session["answers"] = {}
        session["scores"] = {k: 0 for k in DNA_TYPES}
        session["timestamp"] = datetime.now(timezone.utc).isoformat()
        await db.chat_sessions.update_one({}, {"$set": session}, upsert=True)
        return ChatResponse(reply=f"มาเริ่มกัน 🔍\n{QUESTIONS[0]['text']}", done=False)

    # ยังไม่ start
    if session.get("step", 0) == 0:
        return ChatResponse(reply="พิมพ์ start ก่อนนะ 🎬 (หรือพิมพ์ reset ถ้าค้าง)", done=False)

    # ตอนนี้กำลังตอบข้อไหน
    step = int(session["step"])
    current_index = step - 1

    if current_index < 0 or current_index >= len(QUESTIONS):
        # จบแล้วแต่ยังพิมพ์มา
        return ChatResponse(reply="ครบแล้ว กด Recommend ได้เลย 🍿 (พิมพ์ reset ถ้าจะทำใหม่)", done=True)

    q = QUESTIONS[current_index]
    choice = _normalize_choice(user_msg)

    if not choice:
        return ChatResponse(
            reply="ตอบเป็น A/B/C/D ได้เลยนะ 🙂\n" + q["text"],
            done=False
        )

    # เก็บคำตอบ + อัปเดตคะแนน
    session["answers"][q["key"]] = choice
    dna_pick = q["map"][choice]
    session["scores"][dna_pick] = int(session["scores"].get(dna_pick, 0)) + 1

    # ไปข้อถัดไป หรือจบ
    if step < len(QUESTIONS):
        session["step"] = step + 1
        await db.chat_sessions.update_one({}, {"$set": session}, upsert=True)
        next_q = QUESTIONS[session["step"] - 1]["text"]
        return ChatResponse(reply=next_q, done=False)

    # จบ
    session["step"] = len(QUESTIONS) + 1
    await db.chat_sessions.update_one({}, {"$set": session}, upsert=True)

    winner = _dna_winner(session["scores"])
    label = {
        "dark": "Dark 🖤",
        "healing": "Healing 🌿",
        "fantasy": "Fantasy ✨",
        "motivation": "Motivation 🔥",
    }[winner]

    return ChatResponse(
        reply=f"ครบแล้ว ✅ DNA ของคุณคือ: {label}\nกด Recommend ได้เลย 🍿",
        done=True
    )

@api_router.get("/recommend", response_model=RecommendResponse)
async def recommend():
    session = await db.chat_sessions.find_one({}, {"_id": 0})
    if not session or not session.get("answers"):
        raise HTTPException(status_code=400, detail="กรุณาพิมพ์ start แล้วตอบคำถามก่อน")

    if not TMDB_API_KEY:
        raise HTTPException(status_code=500, detail="ยังไม่ได้ตั้งค่า TMDB_API_KEY ใน .env")

    scores = session.get("scores") or {k: 0 for k in DNA_TYPES}
    dna = _dna_winner(scores)

    params = _tmdb_params_from_dna(dna)

    try:
        r = requests.get(f"{TMDB_BASE}/discover/movie", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TMDB API Error: {str(e)}")

    results = (data.get("results") or [])[:12]
    movies: List[Movie] = []
    for m in results:
        movies.append(Movie(
            title=m.get("title") or "-",
            year=(m.get("release_date") or "")[:4] or None,
            rating=m.get("vote_average"),
            overview=m.get("overview"),
            poster=f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}" if m.get("poster_path") else None
        ))

    return RecommendResponse(
        dna=dna,
        scores=scores,
        answers=session.get("answers") or {},
        movies=movies
    )

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
