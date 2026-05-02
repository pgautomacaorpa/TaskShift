import time
import requests
import subprocess
import sys
import psutil # Importação necessária para gerenciar a árvore de processos do Windows

# Configurações do Worker
API_URL = "http://127.0.0.1:8000/api/v1"
MACHINE_ID = "16F0D1EC-87CE-412A-9D6E-286B3E73362D" # Seu ID real

def poll_and_execute():
    print(f"[*] TaskShift Worker Iniciado.")
    print(f"[*] Monitorando a fila para a máquina: {MACHINE_ID}\n")
    
    while True:
        try:
            # 1. Pergunta para a API se tem robô na fila para esta máquina
            response = requests.get(f"{API_URL}/executions/next/{MACHINE_ID}")
            
            if response.status_code == 200:
                task = response.json()
                execution_id = task["execution_id"]
                
                print(f">>> Nova tarefa recebida! Execution ID: {execution_id}")
                
                # Para este teste, vamos forçar o caminho do nosso dummy robot.
                script_path = "robots/dummy_robot.py"
                
                # 2. Inicia o robô
                print(f"[*] Iniciando robô: {script_path}")
                process = subprocess.Popen([sys.executable, script_path])
                
                # 3. Avisa a API que começou a rodar e envia o PID
                requests.put(f"{API_URL}/executions/{execution_id}/status", json={
                    "status": "RUNNING",
                    "pid": process.pid
                })
                print(f"[*] API atualizada: Status RUNNING (PID: {process.pid})")
                
                # Variável de controle para sabermos se o processo foi morto de propósito
                was_stopped = False
                
                # 4. LOOP DE MONITORAMENTO (O Segredo do STOP)
                while process.poll() is None:
                    time.sleep(3) # Checa a cada 3 segundos
                    
                    try:
                        # Pergunta para a API se o status mudou para STOPPED
                        check_resp = requests.get(f"{API_URL}/executions/{execution_id}")
                        if check_resp.status_code == 200:
                            current_status = check_resp.json().get("status")
                            
                            if current_status == "STOPPED":
                                print("\n[!] ALERTA: Sinal de STOP recebido da API!")
                                print("[!] Forçando o encerramento do processo no Windows...")
                                
                                # Mata a árvore de processos (O processo principal e as janelas que ele abriu)
                                try:
                                    parent = psutil.Process(process.pid)
                                    for child in parent.children(recursive=True):
                                        child.terminate()
                                    parent.terminate()
                                except psutil.NoSuchProcess:
                                    pass
                                
                                print("[*] Processo interrompido com sucesso.\n")
                                was_stopped = True
                                break # Sai do loop de espera
                    except Exception as e:
                        print(f"Erro ao checar status: {e}")
                
                # 5. Só atualiza para COMPLETED ou FAILED se a execução seguiu seu fluxo natural
                if not was_stopped:
                    process.wait() # Garante que o processo terminou totalmente
                    
                    # Verifica como o robô terminou (0 = Sucesso, Outros = Erro)
                    if process.returncode == 0:
                        print("[*] Robô finalizou com sucesso. Atualizando API...\n")
                        requests.put(f"{API_URL}/executions/{execution_id}/status", json={
                            "status": "COMPLETED",
                            "processed_success": 5 # Valor fixo para o dummy
                        })
                    else:
                        print(f"[X] Robô falhou (Exit Code {process.returncode}). Atualizando API...\n")
                        requests.put(f"{API_URL}/executions/{execution_id}/status", json={
                            "status": "FAILED",
                            "error_log": f"Processo terminou com código de erro {process.returncode}"
                        })
                
            elif response.status_code == 404:
                # Se não tem tarefa, apenas dorme silenciosamente por 5 segundos e tenta de novo
                time.sleep(5)
            else:
                print(f"[X] Resposta inesperada da API: HTTP {response.status_code}")
                time.sleep(5)
                
        except requests.exceptions.ConnectionError:
            print("[X] Não foi possível conectar ao TaskShift API. Tentando novamente em 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"[X] Erro inesperado no Worker: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    poll_and_execute()