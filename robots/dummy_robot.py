import time
import sys

print("--- INICIANDO DUMMY ROBOT ---")
print("Simulando abertura de sistema de faturamento...")
time.sleep(2)

total_itens = 10
for i in range(1, total_itens + 1):
    print(f"[*] Processando fatura {i} de {total_itens}...")
    time.sleep(5) # Pausa de 3 segundos por item

print("--- PROCESSAMENTO CONCLUÍDO COM SUCESSO ---")
sys.exit(0) # Retorna 0 para avisar o Windows e o Agente que deu tudo certo