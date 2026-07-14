import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "catalogo.db"

# Produtos iniciais usados somente quando o banco estiver vazio.
PRODUTOS_INICIAIS = [
    ("Edredom Blend Comfort Plush", "Cama", 249.90, "Edredom dupla face em tons rosé, toque macio e visual acolhedor.", "edredom-rosa", "Rosé e xadrez", "Solteiro, Casal, Queen e King", "Microfibra premium", 12, "Destaque"),
    ("Edredom Floral Elegance", "Cama", 279.90, "Modelo floral elegante com acabamento macio e enchimento confortável.", "edredom-floral", "Cinza floral", "Casal, Queen e King", "Microfibra", 8, "Novo"),
    ("Edredom Urban Cinza", "Cama", 269.90, "Estampa moderna em cinza com toque sofisticado para o quarto.", "edredom-cinza", "Cinza e branco", "Casal e Queen", "Microfibra", 9, "Mais vendido"),
    ("Colcha Azul Marinho Premium", "Cama", 159.90, "Colcha elegante em azul marinho, com textura e acabamento refinado.", "colcha-azul", "Azul marinho", "Casal e Queen", "Algodão e poliéster", 10, "Coleção"),
    ("Travesseiro Liberty 180 Fios", "Cama", 89.90, "Travesseiro macio com enchimento de fibra siliconada e toque suave.", "travesseiro-liberty", "Branco", "50 x 70 cm", "Percal 180 fios", 15, "Oferta"),
    ("Jogo Infantil Pirata", "Infantil", 139.90, "Jogo infantil divertido com tema de pirata e tecido confortável.", "jogo-infantil", "Azul", "Solteiro", "Microfibra", 7, "Novo"),
    ("Toalha de Banho Premium Terracota", "Banho", 79.90, "Toalha felpuda e absorvente em tom terracota.", "toalhas-coloridas", "Terracota", "Banho", "Algodão", 18, "Destaque"),
    ("Toalha Azul Marinho Bordada", "Banho", 84.90, "Toalha azul marinho com detalhe bordado e acabamento sofisticado.", "toalhas-listradas", "Azul marinho", "Banho", "Algodão", 10, "Mais vendido"),
    ("Toalha de Mesa Floral", "Mesa", 169.90, "Toalha de mesa decorativa com estampa floral delicada.", "toalha-mesa", "Branco e azul", "4, 6 e 8 lugares", "Algodão", 9, "Destaque"),
    ("Kit Panos de Prato Morango", "Cozinha", 59.90, "Kit bordado com tema de morangos, delicado e funcional.", "panos-de-prato", "Branco e vermelho", "3 peças", "Algodão", 20, "Mais vendido"),
]

GALERIAS = {
    "edredom-rosa": ["edredom-rosa.jpg", "edredom-rosa-detalhe-1.jpg", "edredom-rosa-detalhe-2.jpg", "edredom-rosa-detalhe-3.jpg"],
    "edredom-floral": ["edredom-floral.jpg", "edredom-floral-detalhe-1.jpg", "edredom-floral-detalhe-2.jpg", "edredom-floral-detalhe-3.jpg"],
    "edredom-cinza": ["edredom-cinza.jpg", "edredom-cinza-detalhe-1.jpg", "edredom-cinza-detalhe-2.jpg", "edredom-cinza-detalhe-3.jpg"],
    "colcha-azul": ["colcha-azul.jpg", "colcha-azul-detalhe-1.jpg", "colcha-azul-detalhe-2.jpg", "colcha-azul-detalhe-3.jpg"],
    "travesseiro-liberty": ["travesseiro-liberty.jpg", "travesseiro-liberty-detalhe-1.jpg", "travesseiro-liberty-detalhe-2.jpg", "travesseiro-liberty-detalhe-3.jpg"],
    "jogo-infantil": ["jogo-infantil.jpg", "jogo-infantil-detalhe-1.jpg", "jogo-infantil-detalhe-2.jpg", "jogo-infantil-detalhe-3.jpg"],
    "toalhas-coloridas": ["toalhas-coloridas.jpg", "toalhas-coloridas-detalhe-1.jpg", "toalhas-coloridas-detalhe-2.jpg", "toalhas-coloridas-detalhe-3.jpg"],
    "toalhas-listradas": ["toalhas-listradas.jpg", "toalhas-listradas-detalhe-1.jpg", "toalhas-listradas-detalhe-2.jpg", "toalhas-listradas-detalhe-3.jpg"],
    "toalha-mesa": ["toalha-mesa.jpg", "toalha-mesa-detalhe-1.jpg", "toalha-mesa-detalhe-2.jpg", "toalha-mesa-detalhe-3.jpg"],
    "panos-de-prato": ["panos-de-prato.jpg", "panos-de-prato-detalhe-1.jpg", "panos-de-prato-detalhe-2.jpg", "panos-de-prato-detalhe-3.jpg"],
}

def conectar():
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao

def criar_estrutura():
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT NOT NULL,
                preco REAL NOT NULL,
                descricao TEXT NOT NULL,
                slug_imagem TEXT NOT NULL,
                cor TEXT,
                tamanho TEXT,
                material TEXT,
                estoque INTEGER DEFAULT 0,
                selo TEXT,
                imagens TEXT NOT NULL,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS contatos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL UNIQUE,
                email TEXT,
                criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

def atualizar_colunas_antigas():
    """Adiciona colunas novas sem apagar os dados existentes."""
    with conectar() as con:
        colunas = {linha["name"] for linha in con.execute("PRAGMA table_info(produtos)").fetchall()}
        if "criado_em" not in colunas:
            con.execute("ALTER TABLE produtos ADD COLUMN criado_em DATETIME")
        if "atualizado_em" not in colunas:
            con.execute("ALTER TABLE produtos ADD COLUMN atualizado_em DATETIME")

def inserir_produtos_iniciais_somente_se_vazio():
    with conectar() as con:
        total = con.execute("SELECT COUNT(*) AS total FROM produtos").fetchone()["total"]
        if total > 0:
            print(f"Banco preservado: {total} produto(s) já cadastrado(s).")
            return

        for produto in PRODUTOS_INICIAIS:
            nome, categoria, preco, descricao, slug, cor, tamanho, material, estoque, selo = produto
            imagens = GALERIAS.get(slug, [slug + ".jpg"])
            con.execute("""
                INSERT INTO produtos
                (nome, categoria, preco, descricao, slug_imagem, cor, tamanho,
                 material, estoque, selo, imagens)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nome, categoria, preco, descricao, slug, cor, tamanho,
                material, estoque, selo, json.dumps(imagens, ensure_ascii=False)
            ))
        print("Produtos iniciais inseridos com sucesso.")

def preparar_banco():
    criar_estrutura()
    atualizar_colunas_antigas()
    inserir_produtos_iniciais_somente_se_vazio()
    print("Banco de dados verificado sem apagar produtos ou clientes.")

if __name__ == "__main__":
    preparar_banco()
