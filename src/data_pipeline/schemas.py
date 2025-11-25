"""定义外部 API (football-data.org) 的数据结构。"""
from pydantic import BaseModel
from typing import List, Optional

class ExternalArea(BaseModel):
    name: str
    code: str

class ExternalSeason(BaseModel):
    id: int
    startDate: str
    endDate: str

class ExternalTeam(BaseModel):
    id: int
    name: str
    shortName: Optional[str] = None
    tla: Optional[str] = None # e.g. 'MUN'

class ExternalScoreFullTime(BaseModel):
    home: Optional[int] = None
    away: Optional[int] = None

class ExternalScore(BaseModel):
    winner: Optional[str] = None
    duration: str
    fullTime: ExternalScoreFullTime

class ExternalMatch(BaseModel):
    id: int
    utcDate: str
    status: str
    matchday: Optional[int] = None
    homeTeam: ExternalTeam
    awayTeam: ExternalTeam
    score: ExternalScore

class ExternalApiResponse(BaseModel):
    matches: List[ExternalMatch]