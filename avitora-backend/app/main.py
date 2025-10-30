from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import os

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security configuration
SECRET_KEY = secrets.token_urlsafe(32)  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# In-memory user storage (replace with database in production)
users_db: Dict[str, Dict[str, Any]] = {}

# Models
class UserSignup(BaseModel):
    email: EmailStr
    display_name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class User(BaseModel):
    id: str
    email: str
    display_name: str

class AnalyzePayload(BaseModel):
    text: str

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = users_db.get(user_id)
    if user is None:
        raise credentials_exception

    return User(
        id=user["id"],
        email=user["email"],
        display_name=user["display_name"]
    )

# Health endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# Authentication endpoints
@app.post("/auth/signup", response_model=Token)
def signup(user_data: UserSignup):
    # Check if user already exists
    for user in users_db.values():
        if user["email"] == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    # Create new user
    user_id = secrets.token_urlsafe(16)
    hashed_password = get_password_hash(user_data.password)

    users_db[user_id] = {
        "id": user_id,
        "email": user_data.email,
        "display_name": user_data.display_name,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow().isoformat()
    }

    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token)

@app.post("/auth/login", response_model=Token)
def login(user_data: UserLogin):
    # Find user by email
    user = None
    for u in users_db.values():
        if u["email"] == user_data.email:
            user = u
            break

    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token)

@app.post("/auth/logout")
def logout():
    # Client-side token removal
    return {"message": "Logged out successfully"}

@app.get("/users/me", response_model=User)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Analysis endpoint - proxy to main BetValue Finder system
@app.post("/analyze_paste")
async def analyze_paste(body: AnalyzePayload) -> Dict[str, Any]:
    """
    Proxy analysis requests to the main BetValue Finder system.

    For local development: http://localhost:8002/analyze_paste
    For production: Point to main system deployed on Railway
    """
    import httpx

    # Configuration: Main system URL
    # TODO: Set via environment variable for production
    MAIN_SYSTEM_URL = os.getenv("MAIN_SYSTEM_URL", "http://localhost:8002")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{MAIN_SYSTEM_URL}/analyze_paste",
                json={"text": body.text}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Main system error: {e.response.text}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to main system: {str(e)}"
        )

@app.get("/games/today")
def games_today():
    # TODO: Replace with actual implementation
    return {"mlb": [], "npb": [], "soccer": [], "nba": []}
