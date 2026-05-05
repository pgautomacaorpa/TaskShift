import os
import time
import requests
import subprocess
import psutil

# ==========================================
# CONFIGURAÇÕES DO WORKER
# ==========================================
API_URL = "http://127.0.0.1:8000/api/v1"

# IMPORTANTE: Cole aqui o ID da máquina que aparece lá no seu Dashboard (aba Setup)!
MACHINE_ID = "ef1f014f-ceb8-4762-bc1d-fd3d9bcfa592"

def get_robot_path(robot_id):
    """Busca o caminho do script (.py) na API baseado no ID do robô"""
    try:
        resp = requests.get(f"{API_URL}/robots")
        if resp.status_code == 200:
            robos = resp.json()
            for r in robos:
                if r["robot_id"] == robot_id:
                    return r["script_path"]
    except Exception as e:
        print(f"[!] Erro ao buscar dados do robô: {e}")
    return None

def kill_process_tree(pid):
    """Mata o processo principal e qualquer sub-janela (ex: Chrome, Excel) que ele tenha aberto"""
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass

def run_worker():
    print(f"==================================================")
    print(f"🤖 TaskShift Worker Agent iniciado!")
    print(f"📡 Conectado ao Orquestrador: {API_URL}")
    print(f"💻 ID desta Máquina: {MACHINE_ID}")
    print(f"==================================================\n")
    
    while True:
        try:
            # 1. Pergunta para a API se tem alguma tarefa para esta máquina
            resp = requests.get(f"{API_URL}/executions/next/{MACHINE_ID}")
            
            if resp.status_code == 200:
                task = resp.json()
                exec_id = task["execution_id"]
                robot_id = task["robot_id"]
                
                script_path = get_robot_path(robot_id)
                if not script_path:
                    requests.put(f"{API_URL}/executions/{exec_id}/status", json={"status": "FAILED", "error_log": "Caminho do script não encontrado no banco de dados."})
                    continue

                print(f"[*] Nova Tarefa Recebida! ID: {exec_id[:8]} | Executando: {script_path}")
                
                # 2. INJEÇÃO DE DEPENDÊNCIA (O Pulo do Gato para o SDK)
                # Copiamos as variáveis do Windows e injetamos as nossas escondidas
                env = os.environ.copy()
                env["TASKSHIFT_API_URL"] = API_URL
                env["TASKSHIFT_EXECUTION_ID"] = exec_id
                env["TASKSHIFT_ROBOT_ID"] = robot_id

                # 3. Dispara o robô
                proc = subprocess.Popen(
                    ["python", script_path],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Avisa a API que o robô começou a rodar e salva o PID no banco
                requests.put(f"{API_URL}/executions/{exec_id}/status", json={"status": "RUNNING", "pid": proc.pid})
                
                # 4. MONITORAMENTO E GRACEFUL STOP
                killed_by_worker = False
                
                while proc.poll() is None:
                    time.sleep(3) # Checa a API a cada 3 segundos
                    try:
                        status_check = requests.get(f"{API_URL}/executions/{exec_id}")
                        if status_check.status_code == 200:
                            current_status = status_check.json().get("status")
                            
                            # Se o usuário apertou STOP no painel Web
                            if current_status == "STOPPED":
                                print(f"[!] Sinal de STOP recebido do painel. Aguardando SDK finalizar com segurança...")
                                try:
                                    # Dá 10 segundos de cortesia para o robô se desligar sozinho
                                    proc.wait(timeout=10)
                                except subprocess.TimeoutExpired:
                                    print(f"[!] O Robô recusou-se a parar. Forçando encerramento (Kill)...")
                                    kill_process_tree(proc.pid)
                                    killed_by_worker = True
                                break
                    except Exception:
                        pass
                
                # 5. REDE DE SEGURANÇA (Se o processo morreu e não foi o usuário que parou)
                if not killed_by_worker:
                    exit_code = proc.poll()
                    stdout, stderr = proc.communicate()
                    
                    # Verificamos como ficou o status na API. 
                    # Se o SDK funcionou perfeitamente, o SDK já terá alterado o status para COMPLETED ou FAILED.
                    # Mas se o status ainda for RUNNING, significa que o Python explodiu (Syntax Error, falta de RAM) antes do SDK conseguir avisar.
                    final_check = requests.get(f"{API_URL}/executions/{exec_id}").json()
                    
                    if final_check.get("status") == "RUNNING":
                        # O Worker salva o dia! Avisa que deu erro e manda os logs do terminal.
                        error_msg = stderr[-1500:] if stderr else "Erro fatal desconhecido. O processo Python encerrou inesperadamente."
                        print(f"[X] Robô explodiu. Worker salvando erro fatal.")
                        requests.put(f"{API_URL}/executions/{exec_id}/status", json={"status": "FAILED", "error_log": error_msg})
                    else:
                        print(f"[*] Execução finalizada! Status Final: {final_check.get('status')}")

            else:
                # Se não tem tarefa, dorme por 5 segundos para não sobrecarregar a API
                time.sleep(5)
                
        except requests.exceptions.ConnectionError:
            print("[!] Orquestrador offline. Tentando reconectar em 10 segundos...")
            time.sleep(10)
        except Exception as e:
            print(f"[!] Erro inesperado no Worker: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    run_worker()