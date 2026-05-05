import os
import time
import requests
import subprocess
import psutil
import sys

# ==========================================
# CONFIGURAÇÕES DO WORKER
# ==========================================
API_URL = "http://127.0.0.1:8000/api/v1"

# ⚠️ COLE O ID DA SUA MÁQUINA AQUI (Copie do painel web)
MACHINE_ID = "481d92ca-0d11-42b0-8000-60668d15f890"

def verificar_maquina():
    """Valida se o ID da máquina está correto e ajuda o usuário a encontrar o certo"""
    try:
        resp = requests.get(f"{API_URL}/machines")
        if resp.status_code == 200:
            maquinas = resp.json()
            minha_maquina = next((m for m in maquinas if m["machine_id"] == MACHINE_ID), None)
            
            if not minha_maquina:
                print("\n" + "="*65)
                print("❌ ERRO FATAL: MACHINE_ID INCORRETO!")
                print(f"O ID '{MACHINE_ID}' não existe no seu Control Room.")
                print("-" * 65)
                print("Máquinas ativas que você pode usar (Copie o ID abaixo):")
                if not maquinas:
                    print(" -> (Nenhuma máquina cadastrada. Vá no painel e cadastre!)")
                for m in maquinas:
                    print(f" -> MÁQUINA: {m['hostname']} | ID: {m['machine_id']}")
                print("="*65 + "\n")
                sys.exit(1) # Para o worker imediatamente
            
            return minha_maquina["hostname"]
    except requests.exceptions.ConnectionError:
        print("[!] Erro: Não foi possível conectar à API. A API está ligada?")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Erro ao verificar máquina: {e}")
        sys.exit(1)

def get_robot_path(robot_id):
    """Busca o caminho do script (.py) na API baseado no ID do robô"""
    try:
        resp = requests.get(f"{API_URL}/robots")
        if resp.status_code == 200:
            robos = resp.json()
            for r in robos:
                if r["robot_id"] == robot_id:
                    return r["script_path"]
    except:
        pass
    return None

def kill_process_tree(pid):
    """Mata o processo principal e qualquer sub-janela (ex: Chrome, Excel)"""
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass

def run_worker():
    # 1. Faz a checagem inteligente de ID antes de iniciar
    hostname = verificar_maquina()
    
    print(f"==================================================")
    print(f"🤖 TaskShift Worker Agent iniciado!")
    print(f"📡 Orquestrador: {API_URL}")
    print(f"💻 Máquina Autenticada: {hostname}")
    print(f"==================================================\n")
    
    while True:
        try:
            # 2. Pergunta para a API se tem alguma tarefa para esta máquina
            resp = requests.get(f"{API_URL}/executions/next/{MACHINE_ID}")
            
            if resp.status_code == 200:
                task = resp.json()
                exec_id = task["execution_id"]
                robot_id = task["robot_id"]
                
                script_path = get_robot_path(robot_id)
                
                # Prevenção: O arquivo .py existe na pasta?
                if not script_path or not os.path.exists(script_path):
                    error_msg = f"Arquivo do robô não encontrado no diretório: {script_path}"
                    print(f"[X] {error_msg}")
                    requests.put(f"{API_URL}/executions/{exec_id}/status", json={"status": "FAILED", "error_log": error_msg})
                    continue

                print(f"[*] Nova Tarefa Recebida! Executando: {script_path}")
                
                # 3. INJEÇÃO DE DEPENDÊNCIA (Preparando o terreno para o SDK!)
                env = os.environ.copy()
                env["TASKSHIFT_API_URL"] = API_URL
                env["TASKSHIFT_EXECUTION_ID"] = exec_id
                env["TASKSHIFT_ROBOT_ID"] = robot_id

                # Dispara o robô usando o próprio interpretador Python atual
                proc = subprocess.Popen([sys.executable, script_path], env=env)
                
                requests.put(f"{API_URL}/executions/{exec_id}/status", json={"status": "RUNNING", "pid": proc.pid})
                
                killed_by_worker = False
                
                # 4. MONITORAMENTO E GRACEFUL STOP
                while proc.poll() is None:
                    time.sleep(3)
                    try:
                        status_check = requests.get(f"{API_URL}/executions/{exec_id}")
                        if status_check.status_code == 200:
                            if status_check.json().get("status") == "STOPPED":
                                print(f"[!] Sinal de STOP recebido. Abortando processo à força...")
                                kill_process_tree(proc.pid)
                                killed_by_worker = True
                                break
                    except:
                        pass
                
                # 5. REDE DE SEGURANÇA (Se o robô crashar de repente)
                if not killed_by_worker:
                    exit_code = proc.poll()
                    final_check = requests.get(f"{API_URL}/executions/{exec_id}").json()
                    
                    if final_check.get("status") == "RUNNING":
                        # O robô explodiu antes do SDK conseguir avisar a API
                        print(f"[X] Robô encerrou inesperadamente (Crash). Código: {exit_code}")
                        requests.put(f"{API_URL}/executions/{exec_id}/status", json={"status": "FAILED", "error_log": f"Processo Python encerrou com código de erro {exit_code}. Verifique a sintaxe do script."})
                    else:
                        print(f"[*] Execução finalizada! Status: {final_check.get('status')}\n")

            else:
                time.sleep(3) # Nenhuma tarefa, dorme 3 segundos
                
        except requests.exceptions.ConnectionError:
            print("[!] Orquestrador offline. Tentando reconectar...")
            time.sleep(10)
        except Exception as e:
            print(f"[!] Erro inesperado no Worker: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    run_worker()