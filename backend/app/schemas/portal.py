from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Channel = Literal["agent", "broker"]


class PortalAccept(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class PortalLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PortalToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PortalInvite(BaseModel):
    invite_url: str
    expires_at: datetime
    email_status: str
    email_detail: str


class PortalStatus(BaseModel):
    invited: bool
    active: bool
    invite_expires_at: datetime | None
    activated_at: datetime | None
    last_login_at: datetime | None


class StageStep(BaseModel):
    key: str
    label: str
    state: Literal["done", "current", "todo"]


class PortalAgent(BaseModel):
    name: str
    email: str


class PortalAppointment(BaseModel):
    starts_at: datetime
    ends_at: datetime
    kind: str
    address: str | None


class PortalOffer(BaseModel):
    address: str | None
    amount: float
    counter_amount: float | None
    status: str
    updated_at: datetime | None


class PortalOverview(BaseModel):
    first_name: str
    last_name: str
    email: str | None
    agent: PortalAgent | None
    stage: str | None
    stage_label: str
    stage_description: str
    paused: bool
    steps: list[StageStep]
    appointments: list[PortalAppointment]
    offers: list[PortalOffer]
    unread: dict[str, int]


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class PortalMessageIn(MessageIn):
    channel: Channel


class MessageRead(BaseModel):
    id: int
    channel: str
    sender: str
    sender_name: str
    body: str
    created_at: datetime
    read_at: datetime | None


class Conversation(BaseModel):
    client_id: int
    client_name: str
    channel: str
    agent_name: str | None
    last_body: str
    last_sender: str
    last_at: datetime
    unread: int
