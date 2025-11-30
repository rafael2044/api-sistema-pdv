import asyncio
from app.database import SessionLocal, engine, Base
from app.models import User, Product, StockMovement, StockMovementType
from app.auth import get_password_hash

async def init_db():
    # 1. Cria as tabelas se não existirem
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Opcional: Limpa o banco para recomeçar
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        # 2. Criar Usuário Admin
        print("Criando usuário 'admin'...")
        admin_user = User(
            name="Administrador",
            username="admin",
            hashed_password=get_password_hash("123456"), # Senha simples para teste
            role="admin"
        )
        db.add(admin_user)

        # 3. Criar Produtos de Exemplo
        print("Criando produtos...")
        products = [
            Product(name="Coca-Cola 2L", price=10.00, cost_price=7.50, stock_quantity=50, category="Bebidas", barcode="7891000100"),
            Product(name="Arroz 5kg", price=25.90, cost_price=20.00, stock_quantity=100, category="Alimentos", barcode="7891000200"),
            Product(name="Cimento 50kg", price=35.00, cost_price=28.00, stock_quantity=30, category="Construção", barcode="7891000300"),
            Product(name="Chocolate", price=5.50, cost_price=3.00, stock_quantity=0, category="Doces", barcode="7891000400"), # Sem estoque para testar erro
        ]
        
        db.add_all(products)
        await db.commit()

        # 4. Adicionar Movimentação de Estoque Inicial (Opcional, mas boa prática)
        # Precisamos dos IDs gerados, então fazemos refresh ou query, 
        # mas aqui simplificaremos apenas registrando que o banco foi populado.
        
        print("Banco de dados populado com sucesso!")

if __name__ == "__main__":
    asyncio.run(init_db())