import uuid
from datetime import datetime
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import SessionLocal, get_db
from core import models, schemas
from apscheduler.schedulers.background import BackgroundScheduler

# Cria a aplicação
app = FastAPI(
    title="TaskShift API",
    description="API de Orquestração de Robôs Python",
    version="1.0.0"
)

# Criamos o motor de agendamento
scheduler = BackgroundScheduler()

# Função que o motor vai rodar a cada 1 minuto
def check_scheduled_tasks():
    db = SessionLocal()
    agora = datetime.now().strftime("%H:%M")
    print(f"[*] Verificando agendamentos para o horário: {agora}")
    
    # Busca agendamentos ativos para este minuto exato
    schedules = db.query(models.Schedule).filter(
        models.Schedule.schedule_time == agora,
        models.Schedule.is_active == True
    ).all()
    
    for s in schedules:
        # Coloca o robô na fila (igual o botão Play faz)
        new_exec = models.Execution(
            execution_id=str(uuid.uuid4()),
            robot_id=s.robot_id,
            machine_id=s.machine_id,
            trigger_type="SCHEDULED",
            status="PENDING"
        )
        db.add(new_exec)
        print(f"[!] Agendamento disparado: Robô {s.robot_id} na máquina {s.machine_id}")
    
    db.commit()
    db.close()

# Inicia o motor quando a API ligar
@app.on_event("startup")
def startup_event():
    scheduler.add_job(check_scheduled_tasks, 'interval', minutes=1)
    scheduler.start()

# Rotas de CRUD para Agendamentos (Adicione ao final do main.py)
@app.get("/api/v1/schedules", response_model=List[schemas.ScheduleResponse], tags=["Agendamentos"])
def list_schedules(db: Session = Depends(get_db)):
    return db.query(models.Schedule).all()

@app.post("/api/v1/schedules", response_model=schemas.ScheduleResponse, tags=["Agendamentos"])
def create_schedule(sch: schemas.ScheduleCreate, db: Session = Depends(get_db)):
    new_sch = models.Schedule(
        schedule_id=str(uuid.uuid4()),
        robot_id=sch.robot_id,
        machine_id=sch.machine_id,
        schedule_time=sch.schedule_time
    )
    db.add(new_sch)
    db.commit()
    db.refresh(new_sch)
    return new_sch

# Libera o acesso do frontend para a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# ==========================================
# ROTAS DE NEGÓCIO - TASKSHIFT
# ==========================================

@app.get("/api/v1/machines", response_model=List[schemas.MachineResponse], tags=["Infraestrutura"])
def list_machines(db: Session = Depends(get_db)):
    return db.query(models.Machine).filter(models.Machine.is_active == True).all()

@app.get("/api/v1/robots", response_model=List[schemas.RobotResponse], tags=["Robôs"])
def list_robots(db: Session = Depends(get_db)):
    return db.query(models.Robot).filter(models.Robot.is_active == True).all()

@app.post("/api/v1/machines", response_model=schemas.MachineResponse, tags=["Infraestrutura"])
def create_machine(machine: schemas.MachineCreate, db: Session = Depends(get_db)):
    new_machine = models.Machine(
        machine_id=str(uuid.uuid4()),
        hostname=machine.hostname,
        ip_address=machine.ip_address
    )
    db.add(new_machine)
    db.commit()
    db.refresh(new_machine)
    return new_machine

@app.post("/api/v1/robots", response_model=schemas.RobotResponse, tags=["Robôs"])
def create_robot(robot: schemas.RobotCreate, db: Session = Depends(get_db)):
    new_robot = models.Robot(
        robot_id=str(uuid.uuid4()),
        robot_name=robot.robot_name,
        script_path=robot.script_path,
        description=robot.description
    )
    db.add(new_robot)
    db.commit()
    db.refresh(new_robot)
    return new_robot

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

# ==========================================
# ROTAS DO AGENTE (WORKER)
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


# ==========================================
# ROTAS DO DASHBOARD (FRONTEND)
# ==========================================

@app.get("/api/v1/executions/queue", response_model=List[schemas.ExecutionResponse], tags=["Execução e Fila"])
def get_execution_queue(db: Session = Depends(get_db)):
    queue = db.query(models.Execution).filter(
        models.Execution.status.in_(["PENDING", "RUNNING"])
    ).order_by(models.Execution.created_at.desc()).all()
    return queue

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
    return {"message": "Sinal de interrupção enviado com sucesso.", "status": "STOPPED"}


@app.get("/api/v1/executions/{execution_id}", response_model=schemas.ExecutionResponse, tags=["Worker"])
def get_execution_status(execution_id: str, db: Session = Depends(get_db)):
    execution = db.query(models.Execution).filter(models.Execution.execution_id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return execution


# ==========================================
# ROTAS DE PARÂMETROS (CONFIGURAÇÃO)
# ==========================================

@app.get("/api/v1/robots/{robot_id}/parameters", response_model=List[schemas.ParameterResponse], tags=["Parâmetros"])
def list_robot_parameters(robot_id: str, db: Session = Depends(get_db)):
    parameters = db.query(models.Parameter).filter(models.Parameter.robot_id == robot_id).all()
    return parameters

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