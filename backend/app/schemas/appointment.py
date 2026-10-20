from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import AppointmentStatus, AppointmentType


class AppointmentCreate(BaseModel):
    client_id: int
    property_id: int | None = None
    appointment_type: AppointmentType = AppointmentType.viewing
    starts_at: datetime
    ends_at: datetime
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def sensible_times(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("The appointment has to end after it starts.")
        if (self.ends_at - self.starts_at).total_seconds() > 8 * 3600:
            raise ValueError("Appointments can be at most 8 hours long.")
        return self


class AppointmentUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    property_id: int | None = None
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentStatusChange(BaseModel):
    status: AppointmentStatus
    outcome: str | None = Field(default=None, max_length=2000, description="Feedback after a viewing")


class AppointmentRead(BaseModel):
    id: int
    agent_id: int
    client_id: int
    client_name: str
    lead_id: int | None
    property_id: int | None
    property_address: str | None
    appointment_type: AppointmentType
    status: AppointmentStatus
    starts_at: datetime
    ends_at: datetime
    notes: str | None
    outcome: str | None
