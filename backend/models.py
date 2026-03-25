from pydantic import BaseModel, Field
from typing import List

class Experience(BaseModel):
    company: str
    role: str
    points: List[str]


class Project(BaseModel):
    name: str
    points: List[str]

class Research(BaseModel):
    name: str
    points: List[str]

class Profile(BaseModel):
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    research: List[Research] = Field(default_factory=list)