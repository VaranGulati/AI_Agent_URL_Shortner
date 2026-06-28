import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from typing_extensions import TypedDict
import json

Base = declarative_base()

class Run(Base):
    __tablename__ = 'runs'
    id = Column(String, primary_key=True)
    status = Column(String, default="RUNNING")
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    scenario = Column(String)
    stages = relationship("Stage", back_populates="run")

class Stage(Base):
    __tablename__ = 'stages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey('runs.id'))
    stage_name = Column(String)
    status = Column(String, default="PENDING")
    input_state = Column(JSON, default=dict)
    output_artifacts = Column(JSON, default=dict)
    retry_count = Column(Integer, default=0)
    decisions_rationale = Column(Text, nullable=True)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    requires_human_approval = Column(Boolean, default=False)
    
    run = relationship("Run", back_populates="stages")

class TaskItem(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    stage_id = Column(Integer, ForeignKey('stages.id'))
    description = Column(Text)
    status = Column(String, default="PENDING")
    code_diff = Column(Text, nullable=True)

class Approval(Base):
    __tablename__ = 'approvals'
    id = Column(Integer, primary_key=True, autoincrement=True)
    stage_id = Column(Integer, ForeignKey('stages.id'))
    human_decision = Column(String) # APPROVE, REJECT, RETRY
    comments = Column(Text, nullable=True)

# Database Setup Helper
def init_db(db_path: str = "sqlite:///runs/state.sqlite"):
    import os
    os.makedirs(os.path.dirname(db_path.replace("sqlite:///", "")), exist_ok=True)
    engine = create_engine(db_path)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

# LangGraph TypedDict State
class GraphState(TypedDict):
    run_id: str
    scenario: str
    requirements: str
    architecture: Dict[str, Any]
    tasks: List[Dict[str, Any]]
    implementation_code: Dict[str, str] # filename -> code
    tests_code: Dict[str, str]
    docs: Dict[str, str]
    errors: List[str]
    gate_feedback: str
    retry_count: int
    current_stage: str
    db_path: str
