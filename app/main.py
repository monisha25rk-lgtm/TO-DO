from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Task
from .schemas import TaskCreate, TaskResponse, TaskUpdate

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Task Manager API", lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db)
):
    task = Task(title=data.title.strip())

    if not task.title:
        raise HTTPException(status_code=422, detail="Title is required")

    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@app.get("/api/tasks", response_model=list[TaskResponse])
def get_tasks(db: Session = Depends(get_db)):
    return db.scalars(
        select(Task).order_by(Task.id.desc())
    ).all()

@app.patch("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db)
):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task.completed = data.completed
    db.commit()
    db.refresh(task)
    return task

@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return Response(status_code=204)