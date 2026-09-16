from sqlalchemy import Column, String, DateTime, Enum, Float, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.core.database import Base

class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    FINANCIER = "FINANCIER"
    REVIEWER = "REVIEWER"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.FINANCIER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Applicant(Base):
    __tablename__ = "applicants"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    applicant_type = Column(String, nullable=False)
    mobile = Column(String, nullable=False)
    email = Column(String, nullable=False)
    business_name = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    business_vintage = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    applications = relationship("LoanApplication", back_populates="applicant")

class LoanApplication(Base):
    __tablename__ = "loan_applications"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    applicant_id = Column(String, ForeignKey("applicants.id"), nullable=False)
    loan_type = Column(String, nullable=False)
    requested_amount = Column(Float, nullable=False)
    proposed_interest_rate = Column(Float, nullable=False)
    proposed_tenure = Column(Integer, nullable=False)
    purpose = Column(String, nullable=True)
    status = Column(String, default="DRAFT", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    applicant = relationship("Applicant", back_populates="applications")
    documents = relationship("Document", back_populates="application")

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, ForeignKey("loan_applications.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    processing_status = Column(String, default="UPLOADED", nullable=False)
    extracted_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("LoanApplication", back_populates="documents")
