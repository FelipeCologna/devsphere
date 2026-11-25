"""Camada SQLite do DevSphere - versão completa com aprovação de entregas (revisada)."""
import hashlib
import hmac
import json
import os
import re
import sqlite3
import warnings
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "devsphere.db"
XP_POR_NIVEL = 1000
REAIS_POR_XP = 10  # regra do catálogo: 1 XP a cada R$ 10 da task (R$ 4.500 -> 450 XP)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SCHEMA = r'''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT NOT NULL,
    email         TEXT NOT NULL COLLATE NOCASE UNIQUE,
    senha_hash    TEXT NOT NULL,
    tipo_usuario  TEXT NOT NULL CHECK(tipo_usuario IN ('desenvolvedor','empresa')),
    data_cadastro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS desenvolvedores (
    id_dev      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario  INTEGER NOT NULL UNIQUE,
    descricao   TEXT DEFAULT '',
    nivel       INTEGER NOT NULL DEFAULT 0,
    github      TEXT DEFAULT '',
    portfolio   TEXT DEFAULT '',
    pontuacao   INTEGER NOT NULL DEFAULT 0,
    bio         TEXT DEFAULT '',
    localizacao TEXT DEFAULT '',
    habilidades TEXT DEFAULT '[]',
    FOREIGN KEY(id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS empresas (
    id_empresa   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario   INTEGER NOT NULL UNIQUE,
    nome_empresa TEXT NOT NULL,
    descricao    TEXT DEFAULT '',
    site         TEXT DEFAULT '',
    area         TEXT DEFAULT '',
    cidade       TEXT DEFAULT '',
    nota         REAL DEFAULT 5.0,
    FOREIGN KEY(id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tecnologias (
    id_tecnologia INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS desenvolvedor_tecnologias (
    id_dev             INTEGER NOT NULL,
    id_tecnologia      INTEGER NOT NULL,
    nivel_conhecimento TEXT DEFAULT 'iniciante',
    PRIMARY KEY(id_dev, id_tecnologia),
    FOREIGN KEY(id_dev) REFERENCES desenvolvedores(id_dev) ON DELETE CASCADE,
    FOREIGN KEY(id_tecnologia) REFERENCES tecnologias(id_tecnologia) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tarefas (
    id_tarefa      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_empresa     INTEGER NOT NULL,
    titulo         TEXT NOT NULL,
    descricao      TEXT DEFAULT '',
    valor          REAL DEFAULT 0,
    prazo          TEXT,
    nivel_exigido  INTEGER DEFAULT 0,
    status         TEXT DEFAULT 'aberta',      -- aberta | pega | concluida
    categoria      TEXT DEFAULT 'BACK-END',
    xp             INTEGER DEFAULT 0,
    arquivos       TEXT DEFAULT '[]',
    pago           INTEGER DEFAULT 0,
    pago_em        TEXT,
    FOREIGN KEY(id_empresa) REFERENCES empresas(id_empresa) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS propostas (
    id_proposta      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_tarefa        INTEGER NOT NULL,
    id_dev           INTEGER NOT NULL,
    valor_proposto   REAL DEFAULT 0,
    prazo_proposto   TEXT,
    mensagem         TEXT DEFAULT '',
    status           TEXT DEFAULT 'andamento', -- andamento | analise | aceita
    progresso        INTEGER DEFAULT 0,
    entrega_arquivos TEXT DEFAULT '[]',
    entrega_nota     TEXT DEFAULT '',
    data_entrega     TEXT,
    data_aceite      TEXT,
    FOREIGN KEY(id_tarefa) REFERENCES tarefas(id_tarefa) ON DELETE CASCADE,
    FOREIGN KEY(id_dev) REFERENCES desenvolvedores(id_dev) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projetos (
    id_projeto    INTEGER PRIMARY KEY AUTOINCREMENT,
    id_proposta   INTEGER NOT NULL UNIQUE,
    data_inicio   TEXT,
    data_entrega  TEXT,
    status        TEXT DEFAULT 'em_andamento',
    link_entrega  TEXT DEFAULT '',
    FOREIGN KEY(id_proposta) REFERENCES propostas(id_proposta) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS desafios (
    id_desafio  INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo      TEXT NOT NULL,
    descricao   TEXT DEFAULT '',
    tecnologia  TEXT DEFAULT '',
    dificuldade TEXT DEFAULT 'iniciante',
    pontuacao   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS avaliacoes (
    id_avaliacao   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_projeto     INTEGER,
    id_empresa     INTEGER,
    id_dev         INTEGER NOT NULL,
    nota           REAL CHECK(nota>=0 AND nota<=5),
    comentario     TEXT DEFAULT '',
    data_avaliacao TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(id_projeto) REFERENCES projetos(id_projeto) ON DELETE CASCADE,
    FOREIGN KEY(id_empresa) REFERENCES empresas(id_empresa) ON DELETE CASCADE,
    FOREIGN KEY(id_dev) REFERENCES desenvolvedores(id_dev) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dev_desafios (
    id_dev_desafio   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_dev           INTEGER NOT NULL,
    id_desafio       INTEGER NOT NULL,
    pontuacao_obtida INTEGER DEFAULT 0,
    status           TEXT DEFAULT 'iniciado',
    data_realizacao  TEXT,
    UNIQUE(id_dev, id_desafio),
    FOREIGN KEY(id_dev) REFERENCES desenvolvedores(id_dev) ON DELETE CASCADE,
    FOREIGN KEY(id_desafio) REFERENCES desafios(id_desafio) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mensagens (
    id_mensagem             INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario_remetente    INTEGER NOT NULL,
    id_usuario_destinatario INTEGER NOT NULL,
    texto                   TEXT NOT NULL,
    data_envio              TEXT DEFAULT CURRENT_TIMESTAMP,
    lida                    INTEGER DEFAULT 0,
    FOREIGN KEY(id_usuario_remetente) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY(id_usuario_destinatario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS empresas_seguidas (
    id_dev     INTEGER NOT NULL,
    id_empresa INTEGER NOT NULL,
    PRIMARY KEY(id_dev, id_empresa),
    FOREIGN KEY(id_dev) REFERENCES desenvolvedores(id_dev) ON DELETE CASCADE,
    FOREIGN KEY(id_empresa) REFERENCES empresas(id_empresa) ON DELETE CASCADE
);
'''

# Colunas que bancos antigos (criados por versões anteriores) podem não ter.
COLUNAS_NOVAS = [
    ("desenvolvedores", "bio", "TEXT DEFAULT ''"),
    ("desenvolvedores", "localizacao", "TEXT DEFAULT ''"),
    ("desenvolvedores", "habilidades", "TEXT DEFAULT '[]'"),
    ("empresas", "area", "TEXT DEFAULT ''"),
    ("empresas", "cidade", "TEXT DEFAULT ''"),
    ("empresas", "nota", "REAL DEFAULT 5.0"),
    ("tarefas", "categoria", "TEXT DEFAULT 'BACK-END'"),
    ("tarefas", "xp", "INTEGER DEFAULT 0"),
    ("tarefas", "arquivos", "TEXT DEFAULT '[]'"),
    ("tarefas", "pago", "INTEGER DEFAULT 0"),
    ("tarefas", "pago_em", "TEXT"),
    ("propostas", "progresso", "INTEGER DEFAULT 0"),
    ("propostas", "entrega_arquivos", "TEXT DEFAULT '[]'"),
    ("propostas", "entrega_nota", "TEXT DEFAULT ''"),
    ("propostas", "data_entrega", "TEXT"),
    ("propostas", "data_aceite", "TEXT"),
    ("avaliacoes", "id_empresa", "INTEGER"),
]


# ============================ CONEXÃO / MIGRAÇÃO ============================
@contextmanager
def conectar():
    """Abre a conexão, faz commit no sucesso, rollback no erro e SEMPRE fecha."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inicializar_banco():
    with conectar() as conn:
        conn.executescript(SCHEMA)


def _coluna_existe(conn, tabela, coluna):
    return any(r["name"] == coluna for r in conn.execute(f"PRAGMA table_info({tabela})").fetchall())


def _adicionar_coluna(conn, tabela, coluna, definicao):
    if not _coluna_existe(conn, tabela, coluna):
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def migrar_schema():
    with conectar() as conn:
        for tabela, coluna, definicao in COLUNAS_NOVAS:
            _adicionar_coluna(conn, tabela, coluna, definicao)

        conn.execute("UPDATE propostas SET status='andamento' WHERE status='pendente'")

        # Reparo (roda uma única vez, pois zera a condição xp=0): tasks já APROVADAS com xp=0 não
        # creditaram nada ao dev. Define o XP da task e credita agora ao dev que teve a entrega aceita.
        for r in conn.execute("""SELECT t.id_tarefa, t.valor, p.id_dev
                                 FROM tarefas t JOIN propostas p ON p.id_tarefa = t.id_tarefa
                                 WHERE t.status='concluida' AND p.status='aceita'
                                   AND (t.xp IS NULL OR t.xp = 0) AND t.valor > 0""").fetchall():
            xp = xp_sugerido(r["valor"])
            conn.execute("UPDATE tarefas SET xp=? WHERE id_tarefa=?", (xp, r["id_tarefa"]))
            conn.execute("UPDATE desenvolvedores SET pontuacao = pontuacao + ?, "
                         "nivel = (pontuacao + ?) / ? WHERE id_dev=?", (xp, xp, XP_POR_NIVEL, r["id_dev"]))

        # Tasks criadas pelo painel da empresa antes da correção ficaram com xp=0 e, por isso,
        # a aprovação não creditava XP ao desenvolvedor. Corrige as que ainda não foram concluídas.
        conn.execute("""UPDATE tarefas
                        SET xp = MAX(10, CAST(valor / ? AS INTEGER))
                        WHERE (xp IS NULL OR xp = 0) AND valor > 0 AND status != 'concluida'""",
                     (REAIS_POR_XP,))

        # Uma avaliação por par (empresa, dev). Remove duplicatas antigas antes de criar o índice,
        # senão o CREATE UNIQUE INDEX falharia. Linhas legadas sem id_empresa são preservadas.
        conn.execute('''DELETE FROM avaliacoes
                        WHERE id_empresa IS NOT NULL
                          AND id_avaliacao NOT IN (
                              SELECT MAX(id_avaliacao) FROM avaliacoes
                              WHERE id_empresa IS NOT NULL GROUP BY id_empresa, id_dev)''')
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_avaliacoes_empresa_dev ON avaliacoes(id_empresa, id_dev)")

        # Uma proposta ativa por tarefa.
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_propostas_tarefa_unico ON propostas(id_tarefa)")
        except sqlite3.IntegrityError:
            warnings.warn("Existem propostas duplicadas para a mesma tarefa; índice único não foi criado. "
                          "Remova as duplicatas em 'propostas'.")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_propostas_dev ON propostas(id_dev, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tarefas_empresa ON tarefas(id_empresa, status)")


# ============================ UTILITÁRIOS ============================
def xp_sugerido(valor):
    """XP padrão de uma task a partir do valor (mínimo de 10 XP quando há valor)."""
    try:
        valor = float(valor or 0)
    except (TypeError, ValueError):
        return 0
    return max(10, int(valor // REAIS_POR_XP)) if valor > 0 else 0


def _json_lista(valor):
    """Converte JSON em lista sem quebrar se o conteúdo estiver corrompido."""
    try:
        r = json.loads(valor or "[]")
        return r if isinstance(r, list) else []
    except (TypeError, ValueError):
        return []


def _hash_senha(senha):
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt, 310_000).hex()
    return f"pbkdf2_sha256$310000${salt.hex()}${h}"


def _verificar_senha(senha, armazenado):
    try:
        alg, it, sh, hh = armazenado.split("$")
        if alg != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sh), int(it)).hex()
        return hmac.compare_digest(calc, hh)
    except (ValueError, TypeError):
        return False


# ============================ CONTAS ============================
def registrar_usuario(nome, email, senha, tipo):
    nome, email, tipo = nome.strip(), email.strip().lower(), tipo.strip().lower()
    if not nome:
        raise ValueError("Informe o nome.")
    if not EMAIL_RE.match(email):
        raise ValueError("E-mail inválido.")
    if tipo not in ("desenvolvedor", "empresa"):
        raise ValueError("Tipo de conta inválido.")
    if len(senha) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    try:
        with conectar() as conn:
            cur = conn.execute(
                "INSERT INTO usuarios(nome,email,senha_hash,tipo_usuario) VALUES(?,?,?,?)",
                (nome, email, _hash_senha(senha), tipo))
            uid = cur.lastrowid
            if tipo == "desenvolvedor":
                cur = conn.execute("INSERT INTO desenvolvedores(id_usuario) VALUES(?)", (uid,))
                return {"id_usuario": uid, "id_dev": cur.lastrowid, "nome": nome, "email": email, "tipo": tipo}
            cur = conn.execute("INSERT INTO empresas(id_usuario,nome_empresa) VALUES(?,?)", (uid, nome))
            return {"id_usuario": uid, "id_empresa": cur.lastrowid, "nome": nome, "email": email, "tipo": tipo}
    except sqlite3.IntegrityError as exc:
        if "usuarios.email" in str(exc):
            raise ValueError("Este e-mail já está cadastrado.") from None
        raise ValueError("Não foi possível criar a conta.") from exc


def autenticar_usuario(email, senha):
    with conectar() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE email=?", (email.strip().lower(),)).fetchone()
        if not row or not _verificar_senha(senha, row["senha_hash"]):
            raise ValueError("E-mail ou senha incorretos.")
        usuario = {"id_usuario": row["id_usuario"], "nome": row["nome"],
                   "email": row["email"], "tipo": row["tipo_usuario"]}
        if usuario["tipo"] == "desenvolvedor":
            p = conn.execute("SELECT id_dev,nivel,pontuacao,github,portfolio,descricao,bio,localizacao,habilidades "
                             "FROM desenvolvedores WHERE id_usuario=?", (row["id_usuario"],)).fetchone()
        else:
            p = conn.execute("SELECT id_empresa,nome_empresa,descricao,site,area,cidade,nota "
                             "FROM empresas WHERE id_usuario=?", (row["id_usuario"],)).fetchone()
        if p:
            usuario.update(dict(p))
        return usuario


# ============================ DEV ============================
def buscar_catalogo_projetos():
    with conectar() as conn:
        rows = conn.execute('''
            SELECT t.id_tarefa AS id, t.titulo, t.descricao, t.categoria, t.valor, t.xp, t.prazo,
                   t.arquivos, e.nome_empresa AS empresa
            FROM tarefas t JOIN empresas e ON e.id_empresa = t.id_empresa
            WHERE t.status='aberta' ORDER BY t.id_tarefa DESC''').fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["arquivos"] = _json_lista(d["arquivos"])
            out.append(d)
        return out


def buscar_tarefas_do_dev(id_dev):
    with conectar() as conn:
        rows = conn.execute('''
            SELECT t.id_tarefa AS id, t.titulo, t.descricao, t.categoria, t.valor, t.xp, t.prazo,
                   e.nome_empresa AS empresa, p.progresso, p.status, p.entrega_arquivos, p.entrega_nota
            FROM propostas p
            JOIN tarefas t ON t.id_tarefa = p.id_tarefa
            JOIN empresas e ON e.id_empresa = t.id_empresa
            WHERE p.id_dev=? AND p.status IN ('andamento','analise','aceita')
            ORDER BY p.status, t.id_tarefa DESC''', (id_dev,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            ar = _json_lista(d.pop("entrega_arquivos"))
            no = d.pop("entrega_nota") or ""
            d["entrega"] = {"arquivos": ar, "nota": no} if (ar or no) else None
            out.append(d)
        return out


def pegar_projeto(id_dev, id_tarefa):
    """Reserva a tarefa para o dev. A reserva é atômica: só uma pessoa consegue pegar."""
    with conectar() as conn:
        cur = conn.execute("UPDATE tarefas SET status='pega' WHERE id_tarefa=? AND status='aberta'", (id_tarefa,))
        if cur.rowcount == 0:
            return False
        try:
            conn.execute("INSERT INTO propostas(id_tarefa,id_dev,valor_proposto,progresso,status) "
                         "VALUES(?,?,0,0,'andamento')", (id_tarefa, id_dev))
        except sqlite3.IntegrityError:
            conn.rollback()  # desfaz também o status='pega'
            return False
        return True


def atualizar_progresso(id_dev, id_tarefa, progresso):
    progresso = max(0, min(100, int(progresso)))
    with conectar() as conn:
        cur = conn.execute("UPDATE propostas SET progresso=? WHERE id_dev=? AND id_tarefa=? AND status='andamento'",
                           (progresso, id_dev, id_tarefa))
        return cur.rowcount > 0


def enviar_entrega(id_dev, id_tarefa, arquivos, nota):
    """Dev envia a entrega: proposta vai para 'analise'. Retorna False se não havia projeto em andamento."""
    with conectar() as conn:
        cur = conn.execute('''UPDATE propostas
                              SET progresso=100, status='analise', entrega_arquivos=?, entrega_nota=?,
                                  data_entrega=CURRENT_TIMESTAMP
                              WHERE id_dev=? AND id_tarefa=? AND status='andamento' ''',
                           (json.dumps(arquivos or [], ensure_ascii=False), nota or "", id_dev, id_tarefa))
        return cur.rowcount > 0


def desistir_projeto(id_dev, id_tarefa):
    """Só é possível desistir enquanto o projeto está 'andamento'."""
    with conectar() as conn:
        cur = conn.execute("DELETE FROM propostas WHERE id_dev=? AND id_tarefa=? AND status='andamento'",
                           (id_dev, id_tarefa))
        if cur.rowcount == 0:
            return False
        conn.execute("UPDATE tarefas SET status='aberta' WHERE id_tarefa=? AND status='pega'", (id_tarefa,))
        return True


def _obter_entrega_em_analise(conn, id_tarefa, id_dev, id_empresa=None):
    """Retorna a entrega em análise ou levanta um erro explicando exatamente o que está errado."""
    row = conn.execute('''
        SELECT p.id_proposta, p.status AS status_proposta, t.xp, t.id_empresa, d.pontuacao
        FROM propostas p
        JOIN tarefas t ON t.id_tarefa = p.id_tarefa
        JOIN desenvolvedores d ON d.id_dev = p.id_dev
        WHERE p.id_tarefa=? AND p.id_dev=?''', (id_tarefa, id_dev)).fetchone()
    if not row:
        raise ValueError(f"Não existe proposta da tarefa {id_tarefa} para o dev {id_dev}. "
                         "Confira se está passando id_dev (e não id_usuario) e o id correto da tarefa.")
    if id_empresa is not None and row["id_empresa"] != id_empresa:
        raise PermissionError("Esta tarefa pertence a outra empresa.")
    if row["status_proposta"] != "analise":
        raise ValueError(f"A entrega não está em análise (status atual: '{row['status_proposta']}'). "
                         "O desenvolvedor precisa enviar a entrega antes.")
    return row


def aprovar_entrega(id_tarefa, id_dev, id_empresa=None):
    """Aprova a entrega, conclui a tarefa e credita o XP. Levanta erro claro se algo estiver errado."""
    with conectar() as conn:
        row = _obter_entrega_em_analise(conn, id_tarefa, id_dev, id_empresa)
        xp = row["xp"] or 0
        antes = row["pontuacao"] or 0
        depois = antes + xp
        nivel_antes, nivel_depois = antes // XP_POR_NIVEL, depois // XP_POR_NIVEL
        conn.execute("UPDATE propostas SET status='aceita', data_aceite=CURRENT_TIMESTAMP WHERE id_proposta=?",
                     (row["id_proposta"],))
        conn.execute("UPDATE tarefas SET status='concluida' WHERE id_tarefa=?", (id_tarefa,))
        conn.execute("UPDATE desenvolvedores SET pontuacao=?, nivel=? WHERE id_dev=?",
                     (depois, nivel_depois, id_dev))
        return {"xp_ganho": xp, "pontuacao_total": depois, "nivel": nivel_depois,
                "subiu_nivel": nivel_depois > nivel_antes}


def buscar_perfil_dev(id_usuario):
    with conectar() as conn:
        row = conn.execute('''
            SELECT d.id_dev, u.nome, u.email, d.bio, d.localizacao, d.github, d.portfolio,
                   d.habilidades, d.pontuacao
            FROM desenvolvedores d JOIN usuarios u ON u.id_usuario = d.id_usuario
            WHERE d.id_usuario=?''', (id_usuario,)).fetchone()
        if not row:
            return {}
        d = dict(row)
        d["habilidades"] = _json_lista(d["habilidades"])
        return d


def salvar_perfil_dev(id_usuario, nome, bio, localizacao, github, portfolio, habilidades):
    with conectar() as conn:
        conn.execute("UPDATE usuarios SET nome=? WHERE id_usuario=?", (nome, id_usuario))
        conn.execute("UPDATE desenvolvedores SET bio=?, descricao=?, localizacao=?, github=?, portfolio=?, "
                     "habilidades=? WHERE id_usuario=?",
                     (bio, bio, localizacao, github, portfolio,
                      json.dumps(habilidades or [], ensure_ascii=False), id_usuario))


def buscar_ranking():
    with conectar() as conn:
        return [dict(r) for r in conn.execute('''
            SELECT u.nome, d.pontuacao AS xp
            FROM desenvolvedores d JOIN usuarios u ON u.id_usuario = d.id_usuario
            ORDER BY d.pontuacao DESC, u.nome ASC''').fetchall()]


def buscar_empresas():
    with conectar() as conn:
        return [dict(r) for r in conn.execute('''
            SELECT id_empresa, id_usuario, nome_empresa AS nome, area, cidade, nota, descricao
            FROM empresas ORDER BY nome_empresa ASC''').fetchall()]


def buscar_empresas_seguidas(id_dev):
    with conectar() as conn:
        return {r["nome"] for r in conn.execute('''
            SELECT e.nome_empresa AS nome
            FROM empresas_seguidas es JOIN empresas e ON e.id_empresa = es.id_empresa
            WHERE es.id_dev=?''', (id_dev,)).fetchall()}


def seguir_empresa(id_dev, nome_empresa):
    with conectar() as conn:
        emp = conn.execute("SELECT id_empresa FROM empresas WHERE nome_empresa=?", (nome_empresa,)).fetchone()
        if emp:
            conn.execute("INSERT OR IGNORE INTO empresas_seguidas(id_dev,id_empresa) VALUES(?,?)",
                         (id_dev, emp["id_empresa"]))


def deixar_seguir_empresa(id_dev, nome_empresa):
    with conectar() as conn:
        conn.execute("DELETE FROM empresas_seguidas WHERE id_dev=? AND "
                     "id_empresa=(SELECT id_empresa FROM empresas WHERE nome_empresa=?)", (id_dev, nome_empresa))


def buscar_mensagens(id_usuario_remetente, id_usuario_destinatario):
    with conectar() as conn:
        return [dict(r) for r in conn.execute('''
            SELECT m.texto, m.data_envio AS hora,
                   CASE WHEN m.id_usuario_remetente=? THEN 'eu' ELSE 'outro' END AS direcao
            FROM mensagens m
            WHERE (m.id_usuario_remetente=? AND m.id_usuario_destinatario=?)
               OR (m.id_usuario_remetente=? AND m.id_usuario_destinatario=?)
            ORDER BY m.data_envio ASC, m.id_mensagem ASC''',
            (id_usuario_remetente, id_usuario_remetente, id_usuario_destinatario,
             id_usuario_destinatario, id_usuario_remetente)).fetchall()]


def enviar_mensagem(id_usuario_remetente, id_usuario_destinatario, texto):
    texto = (texto or "").strip()
    if not texto:
        return
    with conectar() as conn:
        conn.execute("INSERT INTO mensagens(id_usuario_remetente,id_usuario_destinatario,texto) VALUES(?,?,?)",
                     (id_usuario_remetente, id_usuario_destinatario, texto))


def buscar_id_usuario_por_nome_empresa(nome_empresa):
    with conectar() as conn:
        r = conn.execute("SELECT id_usuario FROM empresas WHERE nome_empresa=?", (nome_empresa,)).fetchone()
        return r["id_usuario"] if r else None


def buscar_id_usuario_por_nome_dev(nome_dev):
    with conectar() as conn:
        r = conn.execute("SELECT u.id_usuario FROM usuarios u "
                         "JOIN desenvolvedores d ON d.id_usuario=u.id_usuario WHERE u.nome=?", (nome_dev,)).fetchone()
        return r["id_usuario"] if r else None


def buscar_id_dev_por_nome_dev(nome_dev):
    with conectar() as conn:
        r = conn.execute("SELECT d.id_dev FROM desenvolvedores d "
                         "JOIN usuarios u ON u.id_usuario=d.id_usuario WHERE u.nome=?", (nome_dev,)).fetchone()
        return r["id_dev"] if r else None


def buscar_atividades_recentes(id_dev, limite=4):
    with conectar() as conn:
        return [dict(r) for r in conn.execute('''
            SELECT t.titulo, e.nome_empresa AS empresa, t.xp, p.data_aceite
            FROM propostas p
            JOIN tarefas t ON t.id_tarefa = p.id_tarefa
            JOIN empresas e ON e.id_empresa = t.id_empresa
            WHERE p.id_dev=? AND p.status='aceita'
            ORDER BY p.data_aceite DESC LIMIT ?''', (id_dev, limite)).fetchall()]


# ============================ EMPRESA ============================
def publicar_task(id_empresa, titulo, descricao, categoria, valor, xp, prazo, arquivos):
    titulo = (titulo or "").strip()
    if not titulo:
        raise ValueError("Informe o título da task.")
    if (valor or 0) < 0 or (xp or 0) < 0:
        raise ValueError("Valor e XP não podem ser negativos.")
    if not xp:
        xp = xp_sugerido(valor)  # nunca grava task sem XP: a aprovação precisa creditar algo
    with conectar() as conn:
        cur = conn.execute('''INSERT INTO tarefas(id_empresa,titulo,descricao,categoria,valor,xp,prazo,arquivos,status)
                              VALUES(?,?,?,?,?,?,?,?,'aberta')''',
                           (id_empresa, titulo, descricao, categoria, valor or 0, xp or 0, prazo,
                            json.dumps(arquivos or [], ensure_ascii=False)))
        return cur.lastrowid


def adicionar_arquivos_task(id_tarefa, novos_arquivos, id_empresa=None):
    """Acrescenta arquivos à task já publicada e grava no banco. Retorna a lista final de arquivos."""
    with conectar() as conn:
        sql = "SELECT arquivos FROM tarefas WHERE id_tarefa=?"
        params = [id_tarefa]
        if id_empresa is not None:
            sql += " AND id_empresa=?"
            params.append(id_empresa)
        row = conn.execute(sql, params).fetchone()
        if not row:
            raise ValueError("Task não encontrada para esta empresa.")
        arquivos = _json_lista(row["arquivos"]) + list(novos_arquivos or [])
        conn.execute("UPDATE tarefas SET arquivos=? WHERE id_tarefa=?",
                     (json.dumps(arquivos, ensure_ascii=False), id_tarefa))
        return arquivos


def buscar_tasks_da_empresa(id_empresa):
    with conectar() as conn:
        rows = conn.execute('''
            SELECT t.id_tarefa AS id, t.titulo, t.descricao, t.categoria, t.valor, t.xp, t.prazo, t.arquivos,
                   t.status, t.pago, t.pago_em, u.nome AS dev, p.id_dev, p.status AS status_proposta,
                   p.progresso, p.entrega_arquivos, p.entrega_nota
            FROM tarefas t
            LEFT JOIN propostas p ON p.id_tarefa = t.id_tarefa
            LEFT JOIN desenvolvedores d ON d.id_dev = p.id_dev
            LEFT JOIN usuarios u ON u.id_usuario = d.id_usuario
            WHERE t.id_empresa=? ORDER BY t.id_tarefa DESC''', (id_empresa,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["arquivos"] = _json_lista(d["arquivos"])
            d["entrega_arquivos"] = _json_lista(d["entrega_arquivos"])
            d["pago"] = bool(d["pago"])
            out.append(d)
        return out


def buscar_entregas_pendentes(id_empresa):
    with conectar() as conn:
        rows = conn.execute('''
            SELECT t.id_tarefa AS id, t.titulo, t.categoria, t.valor, t.xp, t.prazo, u.nome AS dev, p.id_dev,
                   p.entrega_arquivos, p.entrega_nota, p.data_entrega, p.data_aceite
            FROM propostas p
            JOIN tarefas t ON t.id_tarefa = p.id_tarefa
            JOIN desenvolvedores d ON d.id_dev = p.id_dev
            JOIN usuarios u ON u.id_usuario = d.id_usuario
            WHERE t.id_empresa=? AND p.status='analise'
            ORDER BY p.data_entrega DESC, t.id_tarefa DESC''', (id_empresa,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["entrega_arquivos"] = _json_lista(d["entrega_arquivos"])
            out.append(d)
        return out


def aprovar_entrega_empresa(id_tarefa, id_dev, id_empresa=None):
    """Passe id_empresa para garantir que só o dono da task consiga aprovar."""
    return aprovar_entrega(id_tarefa, id_dev, id_empresa)


def recusar_entrega_empresa(id_tarefa, id_dev, id_empresa=None):
    """Devolve a entrega ao dev (volta para 'andamento' com progresso 0)."""
    with conectar() as conn:
        row = _obter_entrega_em_analise(conn, id_tarefa, id_dev, id_empresa)
        conn.execute("UPDATE propostas SET status='andamento', progresso=0, entrega_arquivos='[]', "
                     "entrega_nota='', data_entrega=NULL WHERE id_proposta=?", (row["id_proposta"],))
        return True


def registrar_pagamento(id_tarefa, id_empresa=None):
    """Só registra pagamento de task já concluída (entrega aprovada). Retorna True se registrou."""
    sql = "UPDATE tarefas SET pago=1, pago_em=CURRENT_TIMESTAMP WHERE id_tarefa=? AND status='concluida' AND pago=0"
    params = [id_tarefa]
    if id_empresa is not None:
        sql += " AND id_empresa=?"
        params.append(id_empresa)
    with conectar() as conn:
        return conn.execute(sql, params).rowcount > 0


def buscar_devs_da_empresa(id_empresa):
    with conectar() as conn:
        return [dict(r) for r in conn.execute('''
            SELECT u.nome AS dev, COUNT(*) AS total, AVG(p.progresso) AS progresso_medio
            FROM propostas p
            JOIN tarefas t ON t.id_tarefa = p.id_tarefa
            JOIN desenvolvedores d ON d.id_dev = p.id_dev
            JOIN usuarios u ON u.id_usuario = d.id_usuario
            WHERE t.id_empresa=? AND p.status IN ('andamento','analise','aceita')
            GROUP BY u.nome''', (id_empresa,)).fetchall()]


def buscar_avaliacao(id_empresa, id_dev):
    with conectar() as conn:
        r = conn.execute("SELECT nota, comentario FROM avaliacoes WHERE id_empresa=? AND id_dev=?",
                         (id_empresa, id_dev)).fetchone()
        return dict(r) if r else None


def salvar_avaliacao(id_empresa, id_dev, nota, comentario):
    nota = float(nota)
    if not 0 <= nota <= 5:
        raise ValueError("A nota deve estar entre 0 e 5.")
    with conectar() as conn:
        # Depende do índice único idx_avaliacoes_empresa_dev (criado em migrar_schema).
        conn.execute('''INSERT INTO avaliacoes(id_empresa,id_dev,nota,comentario) VALUES(?,?,?,?)
                        ON CONFLICT(id_empresa,id_dev) DO UPDATE SET
                            nota=excluded.nota, comentario=excluded.comentario,
                            data_avaliacao=CURRENT_TIMESTAMP''',
                     (id_empresa, id_dev, nota, comentario or ""))


# ============================ SEED ============================
def popular_dados_iniciais():
    with conectar() as conn:
        if conn.execute("SELECT COUNT(*) AS n FROM empresas").fetchone()["n"] > 0:
            return
        empresas_seed = [
            ("TechNova Solutions", "Fintech", "São Paulo, SP", 4.8, "Soluções financeiras digitais."),
            ("Inova Commerce", "E-commerce", "Curitiba, PR", 4.6, "Plataforma de vendas online."),
            ("CodeWave", "Software house", "Belo Horizonte, MG", 4.9, "Desenvolvimento sob medida."),
            ("DataViva", "Dados e BI", "Recife, PE", 4.5, "Análise de dados e BI."),
            ("Entrega Rápida", "Logística", "Campinas, SP", 4.3, "Gestão de entregas e rotas."),
            ("NovaSoft", "Sistemas de gestão", "Porto Alegre, RS", 4.4, "Sistemas ERP e automação."),
        ]
        senha_hash = _hash_senha("senha_ficticia_123")  # calculado uma vez só (PBKDF2 é lento)
        for nome, area, cidade, nota, desc in empresas_seed:
            dominio = re.sub(r"\W", "", nome.lower())
            email = f"contato@{dominio}.com"
            cur = conn.execute("INSERT INTO usuarios(nome,email,senha_hash,tipo_usuario) VALUES(?,?,?,?)",
                               (nome, email, senha_hash, "empresa"))
            conn.execute("INSERT INTO empresas(id_usuario,nome_empresa,area,cidade,nota,descricao) "
                         "VALUES(?,?,?,?,?,?)", (cur.lastrowid, nome, area, cidade, nota, desc))
        ids = {r["nome_empresa"]: r["id_empresa"]
               for r in conn.execute("SELECT id_empresa,nome_empresa FROM empresas").fetchall()}
        catalogo_seed = [
            ("API de gestão financeira", "TechNova Solutions", "BACK-END", "Endpoints REST para lançamentos.",
             4500.0, 450, "20/12/2026", [{"nome": "especificacao_api.pdf", "tamanho": 820000}]),
            ("Dashboard de vendas", "Inova Commerce", "FRONT-END", "Painel com gráficos de vendas.",
             3200.0, 320, "22/12/2026", [{"nome": "layout_figma.pdf", "tamanho": 1480000}]),
            ("Sistema de autenticação", "CodeWave", "FULL-STACK", "Login, cadastro e recuperação de senha.",
             2800.0, 280, "15/12/2026", []),
            ("App de entregas", "Entrega Rápida", "MOBILE", "App para acompanhar rotas.",
             6800.0, 680, "15/01/2027", [{"nome": "wireframes.pdf", "tamanho": 1480000}]),
            ("Painel de relatórios", "DataViva", "DADOS", "Relatórios automáticos.",
             3000.0, 300, "10/01/2027", [{"nome": "base_exemplo.csv", "tamanho": 120000}]),
            ("Migração do cadastro", "NovaSoft", "BACK-END", "Migrar cadastro legado.",
             2400.0, 240, "05/12/2026", []),
            ("Landing page do produto", "Inova Commerce", "FRONT-END", "Página com formulário e SEO.",
             1800.0, 180, "28/11/2026", [{"nome": "identidade_visual.zip", "tamanho": 5900000}]),
            ("Integração gateway de pagamento", "TechNova Solutions", "BACK-END", "Cartão e Pix com conciliação.",
             3900.0, 390, "18/01/2027", [{"nome": "documentacao_gateway.pdf", "tamanho": 640000}]),
        ]
        for titulo, empresa, categoria, descricao, valor, xp, prazo, arquivos in catalogo_seed:
            conn.execute("INSERT INTO tarefas(id_empresa,titulo,descricao,categoria,valor,xp,prazo,arquivos) "
                         "VALUES(?,?,?,?,?,?,?,?)",
                         (ids[empresa], titulo, descricao, categoria, valor, xp, prazo,
                          json.dumps(arquivos, ensure_ascii=False)))


def preparar_banco():
    inicializar_banco()
    migrar_schema()
    popular_dados_iniciais()


preparar_banco()