from datetime import date
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base

app = FastAPI()

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./athletes.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class DBAthlete(Base):
    __tablename__ = "athletes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    
    achievements = relationship("DBAchievement", back_populates="athlete", cascade="all, delete")

class DBAchievement(Base):
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String, nullable=False)
    result = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    athlete_id = Column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    
    athlete = relationship("DBAthlete", back_populates="achievements")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class AthleteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)

class AthleteCreate(AthleteBase):
    pass

class AthleteResponse(AthleteBase):
    id: int
    
    class Config:
        from_attributes = True

class AchievementBase(BaseModel):
    sport: str = Field(..., min_length=1, max_length=100)
    result: str = Field(..., min_length=1, max_length=100)
    date: date
    athlete_id: int

class AchievementCreate(AchievementBase):
    pass

class AchievementResponse(AchievementBase):
    id: int
    
    class Config:
        from_attributes = True

# Helper functions
def get_athlete_or_404(db: Session, athlete_id: int):
    athlete = db.query(DBAthlete).filter(DBAthlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Athlete not found")
    return athlete

def get_achievement_or_404(db: Session, achievement_id: int):
    achievement = db.query(DBAchievement).filter(DBAchievement.id == achievement_id).first()
    if not achievement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    return achievement

# API endpoints
@app.get("/athletes", response_model=List[AthleteResponse])
def get_athletes(db: Session = Depends(get_db)):
    return db.query(DBAthlete).all()

@app.post("/athletes", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
def create_athlete(athlete: AthleteCreate, db: Session = Depends(get_db)):
    db_athlete = DBAthlete(**athlete.model_dump())
    db.add(db_athlete)
    db.commit()
    db.refresh(db_athlete)
    return db_athlete

@app.get("/athletes/{athlete_id}/achievements", response_model=List[AchievementResponse])
def get_athlete_achievements(athlete_id: int, db: Session = Depends(get_db)):
    athlete = get_athlete_or_404(db, athlete_id)
    return athlete.achievements

@app.delete("/athletes/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_athlete(athlete_id: int, db: Session = Depends(get_db)):
    athlete = get_athlete_or_404(db, athlete_id)
    db.delete(athlete)
    db.commit()
    return None

@app.get("/achievements", response_model=List[AchievementResponse])
def get_achievements(athlete_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(DBAchievement)
    if athlete_id is not None:
        query = query.filter(DBAchievement.athlete_id == athlete_id)
    return query.all()

@app.post("/achievements", response_model=AchievementResponse, status_code=status.HTTP_201_CREATED)
def create_achievement(achievement: AchievementCreate, db: Session = Depends(get_db)):
    get_athlete_or_404(db, achievement.athlete_id)
    db_achievement = DBAchievement(**achievement.model_dump())
    db.add(db_achievement)
    db.commit()
    db.refresh(db_achievement)
    return db_achievement

@app.delete("/achievements/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_achievement(achievement_id: int, db: Session = Depends(get_db)):
    achievement = get_achievement_or_404(db, achievement_id)
    db.delete(achievement)
    db.commit()
    return None
