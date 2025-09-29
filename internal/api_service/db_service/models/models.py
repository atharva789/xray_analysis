from datetime import datetime
import sqlalchemy.dialects.postgresql as pg
from typing import Optional, List
from datetime import datetime, date
from sqlmodel import Field, SQLModel, Relationship


class Accounts(SQLModel, table=True):
  aid: Optional[int] = Field(default=None, primary_key=True)
  username: str = Field(index=True, unique=True, nullable=False, max_length=100)
  email: str = Field(index=True, unique=True, nullable=False, max_length=100)
  fname: str = Field(nullable=False, max_length=100)
  lname: str = Field(nullable=False, max_length=100)
  pswrd_hash: bytes = Field(nullable=False)  # BYTEA -> bytes
  dob: date = Field(nullable=False)
  created_at: datetime = Field(default_factory=datetime.utcnow)

  patient: Optional["Patients"] = Relationship(back_populates="account")


class Patients(SQLModel, table=True):
  aid: int = Field(primary_key=True, foreign_key="accounts.aid")
  mrn: int = Field(unique=True, nullable=False)

  account: Accounts = Relationship(back_populates="patient")
  dicoms: List["PatientDicoms"] = Relationship(back_populates="patient")
  files: List["PatientFiles"] = Relationship(back_populates="patient")


class FileRecords(SQLModel, table=True):
  file_id: Optional[int] = Field(default=None, primary_key=True)
  filetype: str = Field(nullable=False, max_length=50)  # check constraint needs manual enforcement
  object_key: str = Field(nullable=False, max_length=255)

  dicoms: List["DICOMFiles"] = Relationship(back_populates="file")
  patients: List["PatientFiles"] = Relationship(back_populates="file")


class PatientStats(SQLModel, table=True):
  stat_id: Optional[int] = Field(default=None, primary_key=True)
  agaston_score: Optional[int] = None

  dicoms: List["Dicoms"] = Relationship(back_populates="stat")


class Dicoms(SQLModel, table=True):
  dicom_id: Optional[int] = Field(default=None, primary_key=True)
  dicom_name: str = Field(nullable=False, max_length=100)
  stat_id: Optional[int] = Field(default=None, foreign_key="patientstats.stat_id")
  created_at: datetime = Field(default_factory=datetime.utcnow)

  stat: Optional[PatientStats] = Relationship(back_populates="dicoms")
  files: List["DICOMFiles"] = Relationship(back_populates="dicom")
  patients: List["PatientDicoms"] = Relationship(back_populates="dicom")


class DICOMFiles(SQLModel, table=True):
  dicom_id: int = Field(foreign_key="dicoms.dicom_id", primary_key=True)
  file_id: int = Field(foreign_key="filerecords.file_id", primary_key=True)

  dicom: Dicoms = Relationship(back_populates="files")
  file: FileRecords = Relationship(back_populates="dicoms")


class PatientDicoms(SQLModel, table=True):
  patient_id: int = Field(foreign_key="patients.aid", primary_key=True)
  dicom_id: int = Field(foreign_key="dicoms.dicom_id", primary_key=True)

  patient: Patients = Relationship(back_populates="dicoms")
  dicom: Dicoms = Relationship(back_populates="patients")


class PatientFiles(SQLModel, table=True):
  file_id: int = Field(foreign_key="filerecords.file_id", primary_key=True)
  aid: int = Field(foreign_key="patients.aid", primary_key=True)

  file: FileRecords = Relationship(back_populates="patients")
  patient: Patients = Relationship(back_populates="files")
