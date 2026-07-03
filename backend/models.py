from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ListingScore(BaseModel):
    id: Optional[str] = None
    listing_id: str
    total_score: int
    income_score: int
    school_score: int
    transit_score: int
    price_score: int
    size_score: int
    lifestyle_score: int
    neighbourhood_income: int
    school_rating: float
    transit_min: int
    scored_at: Optional[datetime] = None


class Listing(BaseModel):
    id: str
    address: str
    neighbourhood: Optional[str] = None
    city: str = "Toronto"
    price: int
    beds: Optional[int] = None
    baths: Optional[int] = None
    sqft: Optional[int] = None
    listing_type: Optional[str] = None
    listed_date: Optional[date] = None
    realtor_url: Optional[str] = None
    img_url: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    listing_scores: Optional[list[ListingScore]] = []


class Neighbourhood(BaseModel):
    id: int
    name: str
    avg_income: Optional[int] = None
    school_rating: Optional[float] = None
    transit_min_union: Optional[int] = None
    lifestyle_score: Optional[int] = None
    keywords: Optional[list[str]] = []


class AlertLog(BaseModel):
    id: Optional[str] = None
    listing_id: str
    score: int
    channel: str = "email"
    sent_at: Optional[datetime] = None
