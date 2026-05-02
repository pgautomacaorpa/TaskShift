import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base



# Carrega as variáveis do arquivo .env
load_dotenv()

SERVER = os.getenv("DB_SERVER")
DATABASE = os.getenv("DB_NAME")
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")

# Monta a string de conexão. 
# Se tiver usuário e senha, usa autenticação SQL. Senão, usa Autenticação do Windows.
if USER and PASSWORD:
    CONNECTION_STRING = f"mssql+pyodbc://{USER}:{PASSWORD}@{SERVER}/{DATABASE}?driver=ODBC+Driver+17+for+SQL+Server"
else:
    CONNECTION_STRING = f"mssql+pyodbc://@{SERVER}/{DATABASE}?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes"

# Cria o motor de conexão
engine = create_engine(CONNECTION_STRING, echo=False)

# Prepara a fábrica de sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Função geradora que a nossa API vai usar para injetar o banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Cria a classe base para os nossos modelos
Base = declarative_base()