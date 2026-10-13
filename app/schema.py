from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class ConfidenceScores(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    invoice_number: float = Field(default=0.0, ge=0.0, le=1.0)
    invoice_date: float = Field(default=0.0, ge=0.0, le=1.0)
    due_date: float = Field(default=0.0, ge=0.0, le=1.0)
    subtotal: float = Field(default=0.0, ge=0.0, le=1.0)
    tax: float = Field(default=0.0, ge=0.0, le=1.0)
    total: float = Field(default=0.0, ge=0.0, le=1.0)
    currency: float = Field(default=0.0, ge=0.0, le=1.0)
    vendor: float = Field(default=0.0, ge=0.0, le=1.0)

class ExtractionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    vendor: Optional[str] = None
    confidence: ConfidenceScores = Field(default_factory=ConfidenceScores)
    warnings: List[str] = Field(default_factory=list)
