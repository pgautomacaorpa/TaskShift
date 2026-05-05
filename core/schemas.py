from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- SCHEMAS PARA MÁQUINAS ---
class MachineCreate(BaseModel):
    hostname: str
    ip_address: Optional[str] = None

class MachineResponse(BaseModel):
    machine_id: str
    hostname: str
    ip_address: Optional[str] = None
    status: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

# --- SCHEMAS PARA ROBÔS ---
class RobotCreate(BaseModel):
    robot_name: str
    script_path: str
    description: Optional[str] = None

class RobotResponse(BaseModel):
    robot_id: str
    robot_name: str
    script_path: str
    description: Optional[str] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

# --- SCHEMAS PARA EXECUÇÃO E FILA ---
class ExecutionCreate(BaseModel):
    robot_id: str
    machine_id: str

class ExecutionResponse(BaseModel):
    execution_id: str
    robot_id: str
    machine_id: str
    trigger_type: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    expected_items: Optional[int] = 0
    processed_success: Optional[int] = 0
    processed_errors: Optional[int] = 0
    error_log: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
# --- SCHEMA PARA O AGENTE ATUALIZAR O STATUS ---
class ExecutionUpdate(BaseModel):
    status: str
    pid: Optional[int] = None
    error_log: Optional[str] = None
    processed_success: Optional[int] = 0
    processed_errors: Optional[int] = 0

# --- SCHEMAS PARA PARÂMETROS ---
class ParameterCreate(BaseModel):
    param_key: str
    param_value: str

class ParameterResponse(BaseModel):
    parameter_id: str
    robot_id: str
    param_key: str
    param_value: str
    
    model_config = ConfigDict(from_attributes=True)

class ScheduleCreate(BaseModel):
    robot_id: str
    machine_id: str
    schedule_time: str # Ex: "08:30"
    cron_expression: Optional[str] = None

class ScheduleResponse(BaseModel):
    schedule_id: str
    robot_id: str
    machine_id: str
    schedule_time: Optional[str] = None
    cron_expression: Optional[str] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

# --- SCHEMAS PARA O COFRE DE CREDENCIAIS ---
class CredentialCreate(BaseModel):
    credential_name: str
    username: Optional[str] = None
    password_secret: str

class CredentialResponse(BaseModel):
    credential_id: str
    credential_name: str
    username: Optional[str] = None
    # NOTA DE SEGURANÇA: Nunca retornamos o password_secret na resposta da API para o Dashboard!
    model_config = ConfigDict(from_attributes=True)