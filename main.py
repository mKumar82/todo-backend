from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlmodel import SQLModel, Field, Session, create_engine, select
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt

# CONFIG
SECRET_KEY = "123456"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI(title="Todo App Backend")
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add here 👇
@app.get("/health")
def health_check():
    return {"status": "ok"}



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow Expo mobile
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sqlite_file_name = "todo.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})

# MODELS
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    full_name: Optional[str] = None
    hashed_password: str

class Todo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    title: str
    description: Optional[str] = None
    completed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Pydantic schemas
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TodoRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool
    created_at: datetime

# UTIL
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(session: Session, email: str):
    statement = select(User).where(User.email == email)
    result = session.exec(statement).first()
    return result

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(session, email=email)
    if user is None:
        raise credentials_exception
    return user

# STARTUP
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# AUTH ENDPOINTS
@app.post("/auth/signup", response_model=Token)
def signup(user_in: UserCreate, session: Session = Depends(get_session)):
    print("PASSWORD RECEIVED:", user_in.password, type(user_in.password))
    existing = get_user_by_email(session, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=user_in.email, full_name=user_in.full_name or "", hashed_password=get_password_hash(user_in.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# @app.post("/auth/login", response_model=Token)
# def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
#     user = get_user_by_email(session, form_data.username)
#     if not user or not verify_password(form_data.password, user.hashed_password):
#         raise HTTPException(status_code=400, detail="Incorrect username or password")
#     access_token = create_access_token({"sub": user.email})
#     return {"access_token": access_token, "token_type": "bearer"}

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/login", response_model=Token)
def login(data: LoginRequest, session: Session = Depends(get_session)):
    user = get_user_by_email(session, data.email)
    print("LOGIN ATTEMPT:", data.email, data.password)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# PROFILE
@app.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "full_name": current_user.full_name}

# TODOS
@app.get("/todos", response_model=List[TodoRead])
def list_todos(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    statement = select(Todo).where(Todo.user_id == current_user.id).order_by(Todo.created_at.desc())
    todos = session.exec(statement).all()
    return todos

@app.post("/todos", response_model=TodoRead)
def create_todo(payload: TodoCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    todo = Todo(user_id=current_user.id, title=payload.title, description=payload.description)
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo

@app.patch("/todos/{todo_id}", response_model=TodoRead)
def update_todo(todo_id: int, payload: TodoCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    todo = session.get(Todo, todo_id)
    if not todo or todo.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
    todo.title = payload.title
    todo.description = payload.description
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo

@app.post("/todos/{todo_id}/toggle", response_model=TodoRead)
def toggle_todo(todo_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    todo = session.get(Todo, todo_id)
    if not todo or todo.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
    todo.completed = not todo.completed
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    todo = session.get(Todo, todo_id)
    if not todo or todo.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(todo)
    session.commit()
    return {"ok": True}

