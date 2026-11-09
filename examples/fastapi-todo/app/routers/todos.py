from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import ApiKey, DbSession
from ..models import Todo
from ..schemas import TodoCreate, TodoOut, TodoUpdate
from ..services.notifications import send_reminder

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoOut])
async def list_todos(
    done: bool | None = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    db: Session = DbSession,
    key: str = ApiKey,
):
    stmt = select(Todo).where(Todo.owner_key == key).order_by(Todo.created_at.desc())
    if done is not None:
        stmt = stmt.where(Todo.done == done)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
async def create_todo(
    body: TodoCreate,
    background: BackgroundTasks,
    db: Session = DbSession,
    key: str = ApiKey,
):
    todo = Todo(owner_key=key, **body.model_dump())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    if todo.due_at and todo.remind_email:
        background.add_task(send_reminder, todo.remind_email, todo.title, todo.due_at)
    return todo


def _get_owned(db: Session, todo_id: int, key: str) -> Todo:
    todo = db.get(Todo, todo_id)
    if todo is None or todo.owner_key != key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "todo not found")
    return todo


@router.patch("/{todo_id}", response_model=TodoOut)
async def update_todo(todo_id: int, body: TodoUpdate, db: Session = DbSession, key: str = ApiKey):
    todo = _get_owned(db, todo_id, key)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: int, db: Session = DbSession, key: str = ApiKey):
    db.delete(_get_owned(db, todo_id, key))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
