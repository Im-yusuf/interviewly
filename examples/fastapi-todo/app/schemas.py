from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_at: datetime | None = None
    remind_email: str | None = None


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    done: bool | None = None
    due_at: datetime | None = None


class TodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    done: bool
    due_at: datetime | None
    created_at: datetime
