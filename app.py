from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from pathlib import Path
from functools import wraps
from werkzeug.utils import secure_filename
import sqlite3
import json
import re
import uuid

app = Flask(__name__)
app.secret_key = "troque-esta-chave-antes-de-publicar"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "catalogo.db"
UPLOAD_DIR = BASE_DIR / "static" / "img" / "produtos"

ADMIN_USUARIO = "grazi"
ADMIN_SENHA = "margarida2026"

EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}

def conectar():
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    return conexao

def criar_banco():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT NOT NULL,
                preco REAL NOT NULL,
                descricao TEXT NOT NULL,
                cor TEXT,
                tamanho TEXT,
                material TEXT,
                estoque INTEGER DEFAULT 0,
                selo TEXT,
                destaque INTEGER DEFAULT 0,
                imagens TEXT NOT NULL DEFAULT '[]',
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

        colunas = {
            linha["name"]
            for linha in con.execute("PRAGMA table_info(produtos)").fetchall()
        }

        novas_colunas = {
            "cor": "TEXT",
            "tamanho": "TEXT",
            "material": "TEXT",
            "estoque": "INTEGER DEFAULT 0",
            "selo": "TEXT",
            "destaque": "INTEGER DEFAULT 0",
            "imagens": "TEXT NOT NULL DEFAULT '[]'",
            "criado_em": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "atualizado_em": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        }

        for nome_coluna, definicao in novas_colunas.items():
            if nome_coluna not in colunas:
                try:
                    con.execute(
                        f"ALTER TABLE produtos ADD COLUMN {nome_coluna} {definicao}"
                    )
                except sqlite3.OperationalError:
                    pass

def login_obrigatorio(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            flash("Faça login para acessar o painel.", "erro")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper

def normalizar_telefone(valor):
    return re.sub(r"\D", "", valor or "")

def extensao_permitida(nome):
    return "." in nome and nome.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS

def salvar_imagens(arquivos):
    nomes_salvos = []

    for arquivo in arquivos:
        if not arquivo or not arquivo.filename:
            continue

        if not extensao_permitida(arquivo.filename):
            raise ValueError(
                "Use apenas imagens PNG, JPG, JPEG ou WEBP."
            )

        original = secure_filename(arquivo.filename)
        extensao = original.rsplit(".", 1)[1].lower()
        novo_nome = f"{uuid.uuid4().hex}.{extensao}"
        arquivo.save(UPLOAD_DIR / novo_nome)
        nomes_salvos.append(novo_nome)

    return nomes_salvos

def remover_imagem(nome):
    caminho = UPLOAD_DIR / nome
    if caminho.exists() and caminho.is_file():
        caminho.unlink()

def produto_para_dict(produto):
    dados = dict(produto)

    try:
        imagens = json.loads(dados.get("imagens") or "[]")
    except json.JSONDecodeError:
        imagens = []

    dados["imagens"] = [
        url_for("static", filename=f"img/produtos/{nome}")
        for nome in imagens
    ]
    return dados

@app.route("/")
def inicio():
    with conectar() as con:
        produtos = con.execute("""
            SELECT * FROM produtos
            ORDER BY destaque DESC, id DESC
        """).fetchall()

    return render_template("index.html", produtos=produtos)

@app.route("/api/produtos/<int:produto_id>")
def api_produto(produto_id):
    with conectar() as con:
        produto = con.execute(
            "SELECT * FROM produtos WHERE id = ?",
            (produto_id,)
        ).fetchone()

    if produto is None:
        return jsonify({"erro": "Produto não encontrado"}), 404

    return jsonify(produto_para_dict(produto))

@app.post("/cadastro")
def cadastro():
    nome = request.form.get("nome", "").strip()
    telefone = normalizar_telefone(request.form.get("telefone", ""))
    email = request.form.get("email", "").strip()

    if not nome or len(telefone) < 10:
        flash("Informe um nome e um WhatsApp válido.", "erro")
        return redirect(url_for("inicio") + "#ofertas")

    try:
        with conectar() as con:
            con.execute("""
                INSERT INTO contatos (nome, telefone, email)
                VALUES (?, ?, ?)
            """, (nome, telefone, email))

        flash("Cadastro realizado com sucesso!", "sucesso")

    except sqlite3.IntegrityError:
        flash("Este número de WhatsApp já está cadastrado.", "aviso")

    return redirect(url_for("inicio") + "#ofertas")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")

        if usuario == ADMIN_USUARIO and senha == ADMIN_SENHA:
            session["admin"] = True
            return redirect(url_for("admin"))

        flash("Usuário ou senha incorretos.", "erro")

    return render_template("login.html")

@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("inicio"))

@app.route("/admin")
@login_obrigatorio
def admin():
    with conectar() as con:
        produtos = con.execute(
            "SELECT * FROM produtos ORDER BY id DESC"
        ).fetchall()

        contatos = con.execute(
            "SELECT * FROM contatos ORDER BY id DESC"
        ).fetchall()

    return render_template(
        "admin.html",
        produtos=produtos,
        contatos=contatos
    )

@app.route("/admin/produtos/novo", methods=["GET", "POST"])
@login_obrigatorio
def novo_produto():
    if request.method == "POST":
        try:
            nome = request.form.get("nome", "").strip()
            categoria = request.form.get("categoria", "").strip()
            preco = float(
                request.form.get("preco", "0").replace(",", ".")
            )
            descricao = request.form.get("descricao", "").strip()
            cor = request.form.get("cor", "").strip()
            tamanho = request.form.get("tamanho", "").strip()
            material = request.form.get("material", "").strip()
            estoque = int(request.form.get("estoque", "0"))
            selo = request.form.get("selo", "").strip()
            destaque = 1 if request.form.get("destaque") else 0

            imagens = salvar_imagens(
                request.files.getlist("imagens")
            )

            if not nome or not categoria or not descricao:
                raise ValueError("Preencha nome, categoria e descrição.")

            if not imagens:
                raise ValueError("Adicione pelo menos uma imagem.")

            with conectar() as con:
                con.execute("""
                    INSERT INTO produtos (
                        nome, categoria, preco, descricao, cor,
                        tamanho, material, estoque, selo,
                        destaque, imagens
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nome, categoria, preco, descricao, cor,
                    tamanho, material, estoque, selo,
                    destaque,
                    json.dumps(imagens, ensure_ascii=False)
                ))

            flash("Produto cadastrado com sucesso!", "sucesso")
            return redirect(url_for("admin"))

        except (ValueError, TypeError) as erro:
            flash(str(erro), "erro")

    return render_template(
        "produto_form.html",
        produto=None,
        imagens=[]
    )

@app.route(
    "/admin/produtos/<int:produto_id>/editar",
    methods=["GET", "POST"]
)
@login_obrigatorio
def editar_produto(produto_id):
    with conectar() as con:
        produto = con.execute(
            "SELECT * FROM produtos WHERE id = ?",
            (produto_id,)
        ).fetchone()

    if produto is None:
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("admin"))

    try:
        imagens_atuais = json.loads(produto["imagens"] or "[]")
    except json.JSONDecodeError:
        imagens_atuais = []

    if request.method == "POST":
        try:
            nome = request.form.get("nome", "").strip()
            categoria = request.form.get("categoria", "").strip()
            preco = float(
                request.form.get("preco", "0").replace(",", ".")
            )
            descricao = request.form.get("descricao", "").strip()
            cor = request.form.get("cor", "").strip()
            tamanho = request.form.get("tamanho", "").strip()
            material = request.form.get("material", "").strip()
            estoque = int(request.form.get("estoque", "0"))
            selo = request.form.get("selo", "").strip()
            destaque = 1 if request.form.get("destaque") else 0

            remover = request.form.getlist("remover_imagens")
            imagens_restantes = [
                nome_img
                for nome_img in imagens_atuais
                if nome_img not in remover
            ]

            novas_imagens = salvar_imagens(
                request.files.getlist("imagens")
            )

            imagens_finais = imagens_restantes + novas_imagens

            if not imagens_finais:
                raise ValueError("O produto precisa ter pelo menos uma imagem.")

            with conectar() as con:
                con.execute("""
                    UPDATE produtos
                    SET nome = ?, categoria = ?, preco = ?,
                        descricao = ?, cor = ?, tamanho = ?,
                        material = ?, estoque = ?, selo = ?,
                        destaque = ?, imagens = ?,
                        atualizado_em = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    nome, categoria, preco, descricao, cor,
                    tamanho, material, estoque, selo,
                    destaque,
                    json.dumps(imagens_finais, ensure_ascii=False),
                    produto_id
                ))

            for nome_img in remover:
                remover_imagem(nome_img)

            flash("Produto atualizado com sucesso!", "sucesso")
            return redirect(url_for("admin"))

        except (ValueError, TypeError) as erro:
            flash(str(erro), "erro")

    return render_template(
        "produto_form.html",
        produto=produto,
        imagens=imagens_atuais
    )

@app.post("/admin/produtos/<int:produto_id>/excluir")
@login_obrigatorio
def excluir_produto(produto_id):
    with conectar() as con:
        produto = con.execute(
            "SELECT imagens FROM produtos WHERE id = ?",
            (produto_id,)
        ).fetchone()

        if produto is None:
            flash("Produto não encontrado.", "erro")
            return redirect(url_for("admin"))

        try:
            imagens = json.loads(produto["imagens"] or "[]")
        except json.JSONDecodeError:
            imagens = []

        con.execute(
            "DELETE FROM produtos WHERE id = ?",
            (produto_id,)
        )

    for nome_img in imagens:
        remover_imagem(nome_img)

    flash("Produto excluído com sucesso.", "sucesso")
    return redirect(url_for("admin"))

criar_banco()

if __name__ == "__main__":
    app.run(debug=True)
