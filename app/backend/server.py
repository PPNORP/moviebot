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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"

GENRES = {
    "Action": 28,
    "Comedy": 35,
    "Drama": 18,
    "Horror": 27,
    "Romance": 10749,
    "Sci-Fi": 878,
    "Thriller": 53,
    "Animation": 16,
    "Fantasy": 14
}

QUESTIONS = [
    {"key": "mood", "text": "วันนี้อยากได้ฟีลแบบไหน? (happy/chill/sad/hype/scary/romantic)"},
    {"key": "genre", "text": "อยากดูแนวไหน? (Action/Comedy/Drama/Horror/Romance/Sci-Fi/Thriller/Animation/Fantasy)"},
    {"key": "year", "text": "อยากได้หนังปีประมาณไหน? (เช่น 2015 หรือพิมพ์ any)"},
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
    answers: Dict[str, str]
    movies: List[Movie]

class ChatSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step: int = 0
    answers: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@api_router.get("/")
async def root():
    return {"message": "MovieBot API"}

@api_router.post("/chat", response_model=ChatResponse)
async def chat(msg: ChatMessage):
    user_msg = msg.message.strip()
    
    session = await db.chat_sessions.find_one({}, {"_id": 0})
    if not session:
        session = ChatSession().model_dump()
        session['timestamp'] = session['timestamp'].isoformat()
        await db.chat_sessions.insert_one(session)
    
    if isinstance(session.get('timestamp'), str):
        session['timestamp'] = datetime.fromisoformat(session['timestamp'])
    
    if user_msg.lower() in ["reset", "restart"]:
        await db.chat_sessions.delete_many({})
        new_session = ChatSession().model_dump()
        new_session['timestamp'] = new_session['timestamp'].isoformat()
        await db.chat_sessions.insert_one(new_session)
        return ChatResponse(reply="รีเซ็ตแล้ว พิมพ์ start เพื่อเริ่มใหม่", done=False)
    
    if user_msg.lower() == "start":
        session['step'] = 1
        session['answers'] = {}
        session['timestamp'] = datetime.now(timezone.utc).isoformat()
        await db.chat_sessions.update_one({}, {"$set": session}, upsert=True)
        return ChatResponse(reply=f"มาเริ่มกัน\n{QUESTIONS[0]['text']}", done=False)
    
    if session['step'] == 0:
        return ChatResponse(reply="พิมพ์ start ก่อนนะ 🎬", done=False)
    
    current_index = session['step'] - 1
    key = QUESTIONS[current_index]['key']
    session['answers'][key] = user_msg
    
    if session['step'] < len(QUESTIONS):
        session['step'] += 1
        await db.chat_sessions.update_one({}, {"$set": session}, upsert=True)
        next_q = QUESTIONS[session['step'] - 1]['text']
        return ChatResponse(reply=next_q, done=False)
    
    await db.chat_sessions.update_one({}, {"$set": session}, upsert=True)
    return ChatResponse(reply="ครบแล้ว กด Recommend ได้เลย 🍿", done=True)

@api_router.get("/recommend", response_model=RecommendResponse)
async def recommend():
    session = await db.chat_sessions.find_one({}, {"_id": 0})
    if not session or not session.get('answers'):
        raise HTTPException(status_code=400, detail="กรุณาตอบคำถามก่อน (พิมพ์ start)")
    
    answers = session['answers']
    
    if not TMDB_API_KEY:
        raise HTTPException(status_code=500, detail="ยังไม่ได้ตั้งค่า TMDB_API_KEY")
    
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "page": 1
    }
    
    g = answers.get("genre", "").strip()
    if g in GENRES:
        params["with_genres"] = GENRES[g]
    
    y = answers.get("year", "").strip().lower()
    if y.isdigit():
        params["primary_release_year"] = int(y)
    
    mood = answers.get("mood", "").strip().lower()
    if mood == "scary":
        params["with_genres"] = GENRES["Horror"]
    elif mood == "romantic":
        params["with_genres"] = GENRES["Romance"]
    elif mood == "happy":
        params["with_genres"] = GENRES["Comedy"]
    elif mood == "sad":
        params["with_genres"] = GENRES["Drama"]
    
    try:
        r = requests.get(f"{TMDB_BASE}/discover/movie", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TMDB API Error: {str(e)}")
    
    results = data.get("results", [])[:12]
    movies = []
    for m in results:
        movies.append(Movie(
            title=m.get("title"),
            year=(m.get("release_date") or "")[:4],
            rating=m.get("vote_average"),
            overview=m.get("overview"),
            poster=f"https://image.tmdb.org/t/p/w500{m.get('poster_path')}" if m.get("poster_path") else None
        ))
    
    return RecommendResponse(answers=answers, movies=movies)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()