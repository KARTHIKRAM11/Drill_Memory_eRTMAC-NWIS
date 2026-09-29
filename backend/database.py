"""
Database layer for NWIS.
Uses SQLite for the prototype. In production this would be PostGIS
(Postgres + spatial extension) for proper geospatial radius queries.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime

DATABASE_URL = "sqlite:///./nwis.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Well(Base):
    __tablename__ = "wells"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    field_name = Column(String)          # e.g. "Moran", "Lakwa"
    latitude = Column(Float)
    longitude = Column(Float)
    total_depth_m = Column(Float)
    spud_date = Column(String)
    status = Column(String)              # "producing", "abandoned", "drilling"
    formation_sequence = Column(Text)    # comma-separated formation tops, "Formation:Depth"

    events = relationship("DrillingEvent", back_populates="well", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="well", cascade="all, delete-orphan")


class DrillingEvent(Base):
    __tablename__ = "drilling_events"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    event_type = Column(String)          # mud_loss, kick, stuck_pipe, cementing_issue, torque_spike
    depth_m = Column(Float)
    formation = Column(String)
    severity = Column(String)            # low, medium, high
    description = Column(Text)
    mitigation = Column(Text)
    date = Column(String)

    well = relationship("Well", back_populates="events")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"))
    report_type = Column(String)         # WCR, DDR
    filename = Column(String)
    raw_text = Column(Text)
    extracted_json = Column(Text)        # structured extraction result, stored as JSON string
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    well = relationship("Well", back_populates="reports")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
