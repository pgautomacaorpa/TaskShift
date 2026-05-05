import uuid
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

# IMPORTAÇÃO ATUALIZADA (Adicionamos o engine)
from core.database import SessionLocal, get_db, engine 
from core import models, schemas
from apscheduler.schedulers.background import BackgroundScheduler
from croniter import croniter

# =======================================================
# LINHA MÁGICA: Cria as tabelas que não existem no banco
# Como você apagou a TB_SCHEDULES, o Python vai recriá-la!
# =======================================================
models.Base.metadata.create_all(bind=engine)

# Cria a aplicação
app = FastAPI(
    title="TaskShift API",
    description="API de Orquestração de Robôs Python",
    version="1.0.0"
)

# Libera o acesso do frontend para a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# MOTOR DE AGENDAMENTO (BACKGROUND)
# ==========================================
scheduler = BackgroundScheduler()

def check_scheduled_tasks():
    """Função que roda a cada minuto para checar agendamentos (CRON ou HH:mm)"""
    db = SessionLocal()
    agora = datetime.now()
    agora_str = agora.strftime("%H:%M")
    
    # Busca todos os agendamentos ativos
    schedules = db.query(models.Schedule).filter(models.Schedule.is_active == True).all()
    
    for s in schedules:
        should_run = False
        
        # 1. Verifica pelo novo padrão Avançado (CRON)
        if s.cron_expression and croniter.is_valid(s.cron_expression):
            if croniter.match(s.cron_expression, agora):
                should_run = True
                
        # 2. Mantém compatibilidade com o modelo antigo simples (HH:mm)
        elif s.schedule_time == agora_str:
            should_run = True
            
        # Se for a hora certa, coloca na fila de execução!
        if should_run:
            print(f"[CRON] Disparando Robô {s.robot_id} na Máquina {s.machine_id} às {agora_str}")
            new_exec = models.Execution(
                execution_id=str(uuid.uuid4()),
                robot_id=s.robot_id,
                machine_id=s.machine_id,
                trigger_type="SCHEDULED",
                status="PENDING"
            )
            db.add(new_exec)
            
    db.commit()
    db.close()

# Inicia o motor quando a API ligar
@app.on_event("startup")
def startup_event():
    scheduler.add_job(check_scheduled_tasks, 'interval', minutes=1)
    scheduler.start()

# ==========================================
# ROTAS DE SAÚDE E INFRAESTRUTURA
# ==========================================
@app.get("/")
def read_root():
    return {"produto": "TaskShift", "status": "Online"}

@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Sucesso", "database": "Conectado ao TaskShift_DB perfeitamente!"}
    except Exception as e:
        return {"status": "Erro", "database": f"Falha na conexão: {str(e)}"}

@app.get("/api/v1/machines", response_model=List[schemas.MachineResponse], tags=["Infraestrutura"])
def list_machines(db: Session = Depends(get_db)):
    return db.query(models.Machine).filter(models.Machine.is_active == True).all()

@app.post("/api/v1/machines", response_model=schemas.MachineResponse, tags=["Infraestrutura"])
def create_machine(machine: schemas.MachineCreate, db: Session = Depends(get_db)):
    new_machine = models.Machine(
        machine_id=str(uuid.uuid4()),
        hostname=machine.hostname,
        ip_address=machine.ip_address,
        is_active=True
    )
    db.add(new_machine)
    db.commit()
    db.refresh(new_machine)
    return new_machine

# ==========================================
# ROTAS DE ROBÔS E PARÂMETROS
# ==========================================
@app.get("/api/v1/robots", response_model=List[schemas.RobotResponse], tags=["Robôs"])
def list_robots(db: Session = Depends(get_db)):
    return db.query(models.Robot).filter(models.Robot.is_active == True).all()

@app.post("/api/v1/robots", response_model=schemas.RobotResponse, tags=["Robôs"])
def create_robot(robot: schemas.RobotCreate, db: Session = Depends(get_db)):
    new_robot = models.Robot(
        robot_id=str(uuid.uuid4()),
        robot_name=robot.robot_name,
        script_path=robot.script_path,
        description=robot.description,
        is_active=True
    )
    db.add(new_robot)
    db.commit()
    db.refresh(new_robot)
    return new_robot

@app.get("/api/v1/robots/{robot_id}/parameters", response_model=List[schemas.ParameterResponse], tags=["Parâmetros"])
def list_robot_parameters(robot_id: str, db: Session = Depends(get_db)):
    return db.query(models.Parameter).filter(models.Parameter.robot_id == robot_id).all()

@app.post("/api/v1/robots/{robot_id}/parameters", response_model=schemas.ParameterResponse, tags=["Parâmetros"])
def create_robot_parameter(robot_id: str, param: schemas.ParameterCreate, db: Session = Depends(get_db)):
    new_param = models.Parameter(
        parameter_id=str(uuid.uuid4()),
        robot_id=robot_id,
        param_key=param.param_key,
        param_value=param.param_value
    )
    db.add(new_param)
    db.commit()
    db.refresh(new_param)
    return new_param

@app.delete("/api/v1/parameters/{parameter_id}", tags=["Parâmetros"])
def delete_parameter(parameter_id: str, db: Session = Depends(get_db)):
    param = db.query(models.Parameter).filter(models.Parameter.parameter_id == parameter_id).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parâmetro não encontrado.")
    db.delete(param)
    db.commit()
    return {"message": "Parâmetro deletado com sucesso."}

# ==========================================
# ROTAS DE AGENDAMENTOS (SCHEDULES)
# ==========================================
@app.get("/api/v1/schedules", response_model=List[schemas.ScheduleResponse], tags=["Agendamentos"])
def list_schedules(db: Session = Depends(get_db)):
    return db.query(models.Schedule).all()

@app.post("/api/v1/schedules", response_model=schemas.ScheduleResponse, tags=["Agendamentos"])
def create_schedule(sch: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    new_sch = models.Schedule(
        schedule_id=str(uuid.uuid4()),
        robot_id=sch.robot_id,
        machine_id=sch.machine_id,
        schedule_time=sch.schedule_time,
        cron_expression=sch.cron_expression,
        is_active=True
    )
    db.add(new_sch)
    db.commit()
    db.refresh(new_sch)
    return new_sch

@app.put("/api/v1/schedules/{schedule_id}/toggle", response_model=schemas.ScheduleResponse, tags=["Agendamentos"])
def toggle_schedule(schedule_id: str, db: Session = Depends(get_db)):
    schedule = db.query(models.Schedule).filter(models.Schedule.schedule_id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    
    schedule.is_active = not schedule.is_active # Inverte de Ativo para Pausado e vice-versa
    db.commit()
    db.refresh(schedule)
    return schedule

@app.delete("/api/v1/schedules/{schedule_id}", tags=["Agendamentos"])
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)):
    schedule = db.query(models.Schedule).filter(models.Schedule.schedule_id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    db.delete(schedule)
    db.commit()
    return {"message": "Agendamento deletado com sucesso."}

# ==========================================
# ROTAS DE EXECUÇÃO E FILA (QUEUE & PLAY)
# ==========================================
@app.get("/api/v1/executions/queue", response_model=List[schemas.ExecutionResponse], tags=["Execução e Fila"])
def get_execution_queue(db: Session = Depends(get_db)):
    return db.query(models.Execution).filter(
        models.Execution.status.in_(["PENDING", "RUNNING"])
    ).order_by(models.Execution.created_at.desc()).all()

@app.post("/api/v1/executions/play", response_model=schemas.ExecutionResponse, tags=["Execução e Fila"])
def play_robot(execution: schemas.ExecutionCreate, db: Session = Depends(get_db)):
    new_execution = models.Execution(
        execution_id=str(uuid.uuid4()),
        robot_id=execution.robot_id,
        machine_id=execution.machine_id,
        trigger_type="MANUAL",
        status="PENDING"
    )
    db.add(new_execution)
    db.commit()
    db.refresh(new_execution)
    return new_execution

@app.post("/api/v1/executions/{execution_id}/stop", tags=["Execução e Fila"])
def stop_execution(execution_id: str, db: Session = Depends(get_db)):
    execution = db.query(models.Execution).filter(models.Execution.execution_id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    
    if execution.status in ["COMPLETED", "FAILED", "STOPPED"]:
        raise HTTPException(status_code=400, detail="Esta execução já foi finalizada.")
        
    execution.status = "STOPPED"
    execution.end_time = datetime.now()
    db.commit()
    db.refresh(execution)
    return {"message": "Sinal de interrupção enviado.", "status": "STOPPED"}

# ==========================================
# ROTAS DO WORKER (AGENTES LOCAIS)
# ==========================================
@app.get("/api/v1/executions/next/{machine_id}", response_model=schemas.ExecutionResponse, tags=["Worker"])
def get_next_execution(machine_id: str, db: Session = Depends(get_db)):
    next_task = db.query(models.Execution).filter(
        models.Execution.machine_id == machine_id,
        models.Execution.status == "PENDING"
    ).order_by(models.Execution.created_at.asc()).first()
    
    if not next_task:
        raise HTTPException(status_code=404, detail="Nenhuma tarefa na fila para esta máquina.")
    return next_task

@app.put("/api/v1/executions/{execution_id}/status", response_model=schemas.ExecutionResponse, tags=["Worker"])
def update_execution_status(execution_id: str, update_data: schemas.ExecutionUpdate, db: Session = Depends(get_db)):
    execution = db.query(models.Execution).filter(models.Execution.execution_id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    
    execution.status = update_data.status
    if update_data.pid:
        execution.pid = update_data.pid
    if update_data.error_log:
        execution.error_log = update_data.error_log
        
    if update_data.status == "RUNNING" and not execution.start_time:
        execution.start_time = datetime.now()
        
    if update_data.status in ["COMPLETED", "FAILED", "STOPPED"]:
        execution.end_time = datetime.now()
        execution.processed_success = update_data.processed_success
        execution.processed_errors = update_data.processed_errors

    db.commit()
    db.refresh(execution)
    return execution

@app.get("/api/v1/executions/{execution_id}", response_model=schemas.ExecutionResponse, tags=["Worker"])
def get_execution_status(execution_id: str, db: Session = Depends(get_db)):
    execution = db.query(models.Execution).filter(models.Execution.execution_id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return execution

# ==========================================
# ROTAS DO COFRE DE CREDENCIAIS (VAULT)
# ==========================================
@app.get("/api/v1/credentials", response_model=List[schemas.CredentialResponse], tags=["Cofre"])
def list_credentials(db: Session = Depends(get_db)):
    """Lista todas as credenciais (sem expor as senhas)."""
    return db.query(models.Credential).all()

@app.post("/api/v1/credentials", response_model=schemas.CredentialResponse, tags=["Cofre"])
def create_credential(cred: schemas.CredentialCreate, db: Session = Depends(get_db)):
    """Salva uma nova credencial no cofre."""
    # Verifica se já existe uma credencial com esse nome
    if db.query(models.Credential).filter(models.Credential.credential_name == cred.credential_name).first():
        raise HTTPException(status_code=400, detail="Já existe uma credencial com este nome.")
        
    new_cred = models.Credential(
        credential_id=str(uuid.uuid4()),
        credential_name=cred.credential_name,
        username=cred.username,
        password_secret=cred.password_secret
    )
    db.add(new_cred)
    db.commit()
    db.refresh(new_cred)
    return new_cred

@app.delete("/api/v1/credentials/{credential_id}", tags=["Cofre"])
def delete_credential(credential_id: str, db: Session = Depends(get_db)):
    """Remove uma credencial do cofre."""
    cred = db.query(models.Credential).filter(models.Credential.credential_id == credential_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credencial não encontrada.")
    db.delete(cred)
    db.commit()
    return {"message": "Credencial removida com sucesso."}