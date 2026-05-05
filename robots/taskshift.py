import os
import requests

class BusinessException(Exception):
    """Exceção personalizada para erros de regra de negócio (não crasha o robô)."""
    pass

class TaskShiftBot:
    def __init__(self):
        """Inicializa o robô lendo as variáveis injetadas pelo Worker."""
        self.api_url = os.getenv("TASKSHIFT_API_URL")
        self.execution_id = os.getenv("TASKSHIFT_EXECUTION_ID")
        self.robot_id = os.getenv("TASKSHIFT_ROBOT_ID")
        
        # Se as variáveis não existirem, o robô está sendo rodado solto (em dev/teste)
        self.is_local_dev = not all([self.api_url, self.execution_id, self.robot_id])
        
        if self.is_local_dev:
            self.log("⚠️ AVISO: Variáveis do TaskShift não encontradas. Rodando em Modo de Desenvolvimento Local.", "WARN")
        else:
            self.log(f"✅ Conectado ao TaskShift Control Room. Execução: {self.execution_id[:8]}")

    def log(self, message: str, level: str = "INFO"):
        """Imprime logs de forma padronizada. O Worker captura isso no terminal."""
        print(f"[{level}] {message}")

    def get_parameter(self, param_key: str):
        """Busca um parâmetro do robô na API."""
        if self.is_local_dev:
            self.log(f"Modo Dev: Retornando mock para o parâmetro '{param_key}'", "DEBUG")
            return "VALOR_DE_TESTE_LOCAL"
            
        try:
            resp = requests.get(f"{self.api_url}/robots/{self.robot_id}/parameters")
            if resp.status_code == 200:
                params = resp.json()
                for p in params:
                    if p["param_key"] == param_key:
                        return p["param_value"]
            self.log(f"Parâmetro '{param_key}' não encontrado no Control Room.", "WARN")
            return None
        except Exception as e:
            self.log(f"Erro ao buscar parâmetro: {e}", "ERROR")
            return None

    def get_credential(self, credential_name: str):
        """Busca uma credencial segura no Vault da API."""
        if self.is_local_dev:
            self.log(f"Modo Dev: Retornando mock para a credencial '{credential_name}'", "DEBUG")
            return {"username": "teste", "password_secret": "123456"}
            
        try:
            # Em um cenário real, teríamos uma rota específica para buscar 1 credencial com a senha
            # Aqui estamos adaptando para o nosso MVP
            resp = requests.get(f"{self.api_url}/credentials")
            if resp.status_code == 200:
                creds = resp.json()
                for c in creds:
                    if c["credential_name"] == credential_name:
                        # NOTA: Nossa API atual mascara a senha. Para produção, 
                        # seria necessário um endpoint que retorne a senha descriptografada para o robô.
                        return c
            self.log(f"Credencial '{credential_name}' não encontrada.", "WARN")
            return None
        except Exception as e:
            self.log(f"Erro ao buscar credencial: {e}", "ERROR")
            return None

    def set_progress(self, processed_success: int, expected_items: int = 0):
        """Atualiza a barra de progresso no Dashboard."""
        if self.is_local_dev: return
        try:
            payload = {
                "status": "RUNNING",
                "processed_success": processed_success,
                "expected_items": expected_items
            }
            requests.put(f"{self.api_url}/executions/{self.execution_id}/status", json=payload)
        except Exception as e:
            self.log(f"Erro ao atualizar progresso: {e}", "ERROR")

    def should_stop(self) -> bool:
        """Verifica se o usuário apertou o botão Stop no Dashboard."""
        if self.is_local_dev: return False
        try:
            resp = requests.get(f"{self.api_url}/executions/{self.execution_id}")
            if resp.status_code == 200:
                if resp.json().get("status") == "STOPPED":
                    return True
        except:
            pass
        return False

    def finish(self, status: str = "COMPLETED", error_log: str = None, success_count: int = 0, error_count: int = 0):
        """Avisa o Orquestrador que o robô terminou (com sucesso ou erro fatal)."""
        if self.is_local_dev:
            self.log(f"🏁 Fim da execução local. Status Final: {status}", "INFO")
            return
            
        try:
            payload = {
                "status": status,
                "error_log": error_log,
                "processed_success": success_count,
                "processed_errors": error_count
            }
            requests.put(f"{self.api_url}/executions/{self.execution_id}/status", json=payload)
            self.log(f"Status atualizado para {status} no Control Room.")
        except Exception as e:
            self.log(f"Erro ao finalizar execução no Orquestrador: {e}", "ERROR")