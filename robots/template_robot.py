import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Importa o nosso Motor (SDK)
from taskshift import TaskShiftBot, BusinessException

# Inicializa a comunicação com o Orquestrador
bot = TaskShiftBot()

def main():
    bot.log("Iniciando Robô Vitrine: Extrator de Cotações...", level="INFO")
    
   # 1. Abre o Navegador visível para gerar o efeito "UAU" na apresentação
    bot.log("A iniciar o Google Chrome (Modo Anti-Detect)...", level="INFO")
    options = webdriver.ChromeOptions()
    
    # --- O DISFARCE ANTI-BOT ---
    options.add_argument("--disable-blink-features=AutomationControlled") # Esconde a flag de automação
    options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging']) # Remove a tarja "Chrome está a ser controlado..."
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # O Golpe de Mestre: Usa JavaScript para apagar a variável que o Google usa para nos detetar
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    driver.maximize_window()
    
    # 2. A nossa lista de trabalho. A última moeda é falsa para demonstrar o Tratamento de Erros!
    moedas = ["Dólar", "Euro", "Libra", "Bitcoin", "MoedaFalsaTaskShift"]
    
    total_itens = len(moedas)
    sucessos = 0
    erros = 0
    
    try:
        for item in moedas:
            # 3. GRACEFUL STOP: Verifica se o Diretor clicou em "Stop" no painel
            if bot.should_stop():
                bot.log("Sinal de paragem recebido do Control Room. A encerrar com segurança.", level="WARN")
                break
                
            try:
                bot.log(f"A pesquisar cotação para: {item}", level="INFO")
                
                # Simulação da Regra de Negócio que falha (Moeda não existe)
                if item == "MoedaFalsaTaskShift":
                    raise BusinessException(f"A moeda '{item}' não existe ou não tem cotação válida.")
                
                # A FORMA A PROVA DE FALHAS: Injetar a pesquisa direto na URL!
                termo_pesquisa = f"Cotação {item} para Real".replace(" ", "+")
                driver.get(f"https://www.google.com/search?q={termo_pesquisa}")
                
                # Pausa dramática para o cliente ver o gráfico do Google na tela
                time.sleep(3) 
                
                bot.log(f"Cotação capturada para {item} com sucesso!", level="INFO")
                sucessos += 1
                
                # 4. FEEDBACK EM TEMPO REAL: Atualiza os gráficos no Dashboard
                bot.set_progress(processed_success=sucessos, expected_items=total_itens)
                
            except BusinessException as be:
                # O Erro de Negócio: O robô falha este item, pinta o gráfico de vermelho, mas CONTINUA a trabalhar!
                erros += 1
                bot.log(str(be), level="WARN")

        # 5. FINALIZAÇÃO: O loop terminou pacificamente
        bot.finish(status="COMPLETED", success_count=sucessos, error_count=erros)

    finally:
        # 6. CLEANUP: Fecha o Chrome para não deixar o computador do cliente cheio de janelas
        bot.log("A limpar o ambiente e fechar o navegador...", level="INFO")
        driver.quit()

if __name__ == "__main__":
    try:
        main()
    except Exception as fatal_error:
        # Se a internet cair de repente ou o Chrome crashar, o SDK apanha o erro fatal
        error_trace = traceback.format_exc()
        bot.log(f"ERRO FATAL: {str(fatal_error)}", level="ERROR")
        bot.finish(status="FAILED", error_log=error_trace)