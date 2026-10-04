from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine("sqlite:///secrets.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


class SecretIncident(Base):
    __tablename__ = "secret_incidents"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    secret_content = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ScanRecord(Base):
    __tablename__ = "scan_records"

    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String, nullable=True)
    repo = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    findings_count = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    repo = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    line = Column(Integer, nullable=True, default=0)
    masked_snippet = Column(String, nullable=True)
    commit = Column(String, nullable=True)
    author = Column(String, nullable=True)
    status = Column(String, nullable=False, default="New")
    rule_id = Column(String, nullable=True)
    rule_severity = Column(String, nullable=True)
    rule_description = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Rule(Base):
    __tablename__ = "rules"

    id = Column(String, primary_key=True, index=True)
    pattern = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="Medium")
    description = Column(String, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, nullable=True)
    channel = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Pending")
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


Base.metadata.create_all(engine)
