from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import ClientType, FinancingStatus


class IntakeCreate(BaseModel):
    """What a client fills in on the public “Find a home” form."""
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    client_type: ClientType = ClientType.buyer
    preferred_city: str | None = Field(default=None, max_length=100)
    preferred_state: str | None = Field(default="Illinois", max_length=50)
    budget_min: float | None = Field(default=None, ge=0, le=50_000_000)
    budget_max: float | None = Field(default=None, ge=0, le=50_000_000)
    min_bedrooms: int | None = Field(default=None, ge=0, le=10)
    min_bathrooms: float | None = Field(default=None, ge=0, le=10)
    financing_status: FinancingStatus = FinancingStatus.unknown
    purchase_timeline_months: int | None = Field(default=None, ge=0, le=36)
    notes: str | None = Field(default=None, max_length=1000)
    consent: bool = Field(description="The client agrees to be contacted about their request")
    # Left empty by people; bots that fill every field get a polite reply and nothing is saved.
    website: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def sensible(self):
        if not self.consent:
            raise ValueError("Please tick the box so an agent may contact you.")
        if self.budget_min is not None and self.budget_max is not None and self.budget_min > self.budget_max:
            raise ValueError("The lowest budget can’t be more than the highest.")
        return self


class IntakeReply(BaseModel):
    message: str
