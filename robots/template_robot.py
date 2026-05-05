import time
import traceback

# Importa o nosso Motor (SDK) que acabamos de criar
from taskshift import TaskShiftBot, BusinessException

# 1. Inicializa a comunicação com o Orquestrador (Puxa variáveis invisíveis injetadas pelo Worker)
bot = TaskShiftBot()

def main():
    bot.log("Iniciando processamento do robô...", level="INFO")
    
    # 2. SETUP: Busca de Parâmetros e Credenciais do Painel Web (Exemplos)
    # pasta_input = bot.get_parameter("pasta_input")
    # credencial_sap = bot.get_credential("SAP_PROD_LOGIN")
    # bot.log(f"A pasta de input configurada é: {pasta_input}")
    
    # Simulando uma extração de dados (ex: lendo linhas de um Excel, e-mails de uma caixa)
    itens_para_processar = ["Fatura 01", "Fatura 02", "Fatura 03", "Fatura 04", "Fatura 05"]
    
    total_itens = len(itens_para_processar)
    sucessos = 0
    erros = 0
    
    for item in itens_para_processar:
        # 3. GRACEFUL STOP: A cada item, o robô checa se você apertou o botão Stop lá no painel!
        if bot.should_stop():
            bot.log("Sinal de parada recebido do Control Room. Encerrando o loop com segurança.", level="WARN")
            break
            
        try:
            bot.log(f"Processando item: {item}", level="INFO")
            
            # =================================================================
            # SUA LÓGICA DE NEGÓCIO VEM AQUI! (Selenium, PyAutoGUI, Pandas...)
            # =================================================================
            time.sleep(2) # Simulando o robô digitando e clicando...
            
            # Simulando uma Regra de Negócio que falha (Ex: O cliente da Fatura 03 não existe no sistema)
            if item == "Fatura 03":
                raise BusinessException(f"O item '{item}' está com dados inválidos. Pulando para o próximo.")
            
            # Se a automação passou direto pelo IF e chegou aqui, deu certo!
            sucessos += 1
            
            # 4. FEEDBACK EM TEMPO REAL: Atualiza a barra de progresso no seu navegador
            bot.set_progress(processed_success=sucessos, expected_items=total_itens)
            
        except BusinessException as be:
            # Tratamento de Exceção de Negócio: Avisa que deu erro, mas NÃO crasha o robô!
            erros += 1
            bot.log(str(be), level="WARN")

    # 5. FINALIZAÇÃO: Avisa o orquestrador que o loop terminou pacificamente
    bot.finish(status="COMPLETED", success_count=sucessos, error_count=erros)


if __name__ == "__main__":
    try:
        main()
    
    except Exception as fatal_error:
        # 6. TRATAMENTO DE ERRO FATAL: O robô explodiu (Ex: Sistema SAP caiu, Sem Internet, Chrome não abriu)
        error_trace = traceback.format_exc()
        bot.log(f"ERRO FATAL: {str(fatal_error)}", level="ERROR")
        bot.finish(status="FAILED", error_log=error_trace) # Salva o rastro de sangue no banco de dados!
        
    finally:
        # 7. CLEANUP (LIMPEZA FINAL): Executado independentemente de sucesso ou falha fatal
        bot.log("Limpando ambiente (fechando navegadores, apagando arquivos temporários)...", level="INFO")
        
        # Exemplo de comandos que os devs vão usar aqui:
        # os.system("taskkill /F /IM chrome.exe /T > nul 2>&1")
        # os.system("taskkill /F /IM excel.exe /T > nul 2>&1")
        pass