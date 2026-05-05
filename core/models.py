from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from core.database import Base
from typing import Optional, List


class Machine(Base):
    __tablename__ = "TB_MACHINES"

    machine_id = Column(String(36), primary_key=True)
    hostname = Column(String(100), nullable=False)
    ip_address = Column(String(50))
    status = Column(String(20), default="OFFLINE")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

class Robot(Base):
    __tablename__ = "TB_ROBOTS"

    robot_id = Column(String(36), primary_key=True)
    robot_name = Column(String(200), nullable=False)
    script_path = Column(String(500), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

class Execution(Base):
    __tablename__ = "INDICADORES_RPA"

    execution_id = Column(String(36), primary_key=True)
    robot_id = Column(String(36), ForeignKey("TB_ROBOTS.robot_id"))
    machine_id = Column(String(36), ForeignKey("TB_MACHINES.machine_id"))
    pid = Column(Integer, nullable=True)
    trigger_type = Column(String(50), nullable=False)
    execution_date = Column(DateTime, default=func.now())
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    expected_items = Column(Integer, default=0)
    processed_success = Column(Integer, default=0)
    processed_errors = Column(Integer, default=0)
    status = Column(String(50), nullable=False)
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Parameter(Base):
    __tablename__ = "TB_PARAMETERS"

    parameter_id = Column(String(36), primary_key=True)
    robot_id = Column(String(36), ForeignKey("TB_ROBOTS.robot_id"))
    param_key = Column(String(100), nullable=False)
    param_value = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Schedule(Base):
    __tablename__ = "TB_SCHEDULES"

    schedule_id = Column(String(36), primary_key=True)
    robot_id = Column(String(36), ForeignKey("TB_ROBOTS.robot_id"))
    machine_id = Column(String(36), ForeignKey("TB_MACHINES.machine_id"))
    schedule_time = Column(String(5), nullable=True) # Guardaremos como "HH:mm"
    cron_expression = Column(String(100), nullable=True) # O novo formato avançado
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class Credential(Base):
    __tablename__ = "TB_CREDENTIALS"

    credential_id = Column(String(36), primary_key=True)
    credential_name = Column(String(100), unique=True, nullable=False) # Ex: "sap_login_financeiro"
    username = Column(String(100), nullable=True)
    password_secret = Column(String(500), nullable=False) # Em produção usaríamos criptografia aqui
    created_at = Column(DateTime, default=func.now())
