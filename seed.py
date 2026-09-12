import sys
import os

# Adiciona a raiz do projeto ao path para importar os módulos locais
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.database import SessionLocal
from src.api.models.user import User
from src.api.services.auth_service import hash_password

def seed_users():
    db = SessionLocal()
    try:
        # Verifica se o usuário admin já existe
        admin_email = "admin@oraculo.com"
        existing_user = db.query(User).filter(User.email == admin_email).first()
        
        if existing_user:
            print(f"✅ O usuário {admin_email} já existe no banco de dados.")
        else:
            # Cria o usuário admin
            hashed_pwd = hash_password("admin123")
            admin_user = User(email=admin_email, hashed_password=hashed_pwd)
            db.add(admin_user)
            db.commit()
            print(f"🚀 Usuário {admin_email} criado com sucesso! (Senha: admin123)")
    except Exception as e:
        print(f"❌ Erro ao popular banco de dados: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Executando seeder de usuários...")
    seed_users()
