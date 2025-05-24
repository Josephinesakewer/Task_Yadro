from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import chardet

with open('requirements.txt', 'rb') as f:
    raw_data = f.read()
    result = chardet.detect(raw_data)
    print(result)

from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg2://daguser:dagpass@postgres/dagdb?client_encoding=utf8")




# Database setup

DATABASE_URL = "postgresql+psycopg2://daguser:dagpass@postgres/dagdb?client_encoding=utf8"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "options": "-c client_encoding=utf8"
    },
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    edges_from = relationship("Edge", foreign_keys="Edge.source_id")
    edges_to = relationship("Edge", foreign_keys="Edge.target_id")

class Edge(Base):
    __tablename__ = "edges"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("nodes.id"))
    target_id = Column(Integer, ForeignKey("nodes.id"))

Base.metadata.create_all(bind=engine)

# Schemas
class NodeCreate(BaseModel):
    name: str

class EdgeCreate(BaseModel):
    source: str
    target: str

class GraphResponse(BaseModel):
    nodes: list[str]
    edges: list[tuple[str, str]]

# App setup
app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions
def check_cycle(db: Session, source_id: int, target_id: int):
    visited = set()
    stack = [target_id]

    while stack:
        current = stack.pop()
        if current == source_id:
            raise HTTPException(status_code=400, detail="Edge creates cycle")
        visited.add(current)
        for edge in db.query(Edge).filter(Edge.target_id == current).all():
            if edge.source_id not in visited:
                stack.append(edge.source_id)

# API Endpoints
@app.post("/nodes")
def create_node(node: NodeCreate, db: Session = Depends(get_db)):
    if db.query(Node).filter(Node.name == node.name).first():
        raise HTTPException(status_code=400, detail="Node already exists")
    db.add(Node(name=node.name))
    db.commit()
    return {"message": "Node created"}

@app.post("/edges")
def create_edge(edge: EdgeCreate, db: Session = Depends(get_db)):
    source = db.query(Node).filter(Node.name == edge.source).first()
    target = db.query(Node).filter(Node.name == edge.target).first()

    if not source or not target:
        raise HTTPException(status_code=404, detail="Node not found")

    check_cycle(db, source.id, target.id)

    db.add(Edge(source_id=source.id, target_id=target.id))
    db.commit()
    return {"message": "Edge created"}

@app.get("/graph", response_model=GraphResponse)
def get_graph(db: Session = Depends(get_db)):
    nodes = [n.name for n in db.query(Node).all()]
    edges = [
        (db.get(Node, e.source_id).name, db.get(Node, e.target_id).name)
        for e in db.query(Edge).all()
    ]
    return {"nodes": nodes, "edges": edges}
import chardet
