"""
DevSphere - Painel do desenvolvedor (INTEGRADO COM SQLITE)
Python + Flet (>= 1.0)

Tela que aparece depois de criar uma conta como DESENVOLVEDOR ou fazer login.
Todos os dados são carregados e salvos no banco SQLite via database.py.

Uso:
- Pelo main.py:  criarconta_desenvolvedor.dashboard(page, usuario, ao_sair=sair)
- Teste isolado: python criarconta_desenvolvedor.py
"""
import shutil
from datetime import datetime
from pathlib import Path
import flet as ft
import database as db

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------
MODO_TESTE = False  # True mostra o botão "Simular aprovação (teste)": o próprio dev se aprova. A aprovação real é feita no painel da empresa.
PASTA_UPLOADS = Path(__file__).parent / "uploads"
XP_POR_NIVEL = 1000
MAX_ATIVOS = 3
NOMES_NIVEL = ["Iniciante", "Júnior", "Pleno", "Sênior", "Especialista"]


def dashboard(page: ft.Page, usuario=None, ao_sair=None):
    usuario = usuario or {"nome": "Convidado", "email": "", "tipo": "desenvolvedor"}
    nome_inicial = usuario.get("nome") or "Desenvolvedor"

    page.title = "DevSphere | Dashboard"
    page.bgcolor = "#F7F6FC"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.min_width = 760
    page.window.min_height = 700

    # Cores
    PURPLE = "#6C3CE9"
    PURPLE_LIGHT = "#EEE8FF"
    TEXT = "#24213A"
    MUTED = "#77738D"
    BORDER = "#E9E6F2"
    WHITE = "#FFFFFF"
    GREEN = "#21A675"
    ORANGE = "#F19A38"
    BLUE = "#4385F5"
    RED = "#DC2626"
    GOLD = "#F5B301"

    CATEGORIAS = {
        "BACK-END": (PURPLE, ft.Icons.TERMINAL_ROUNDED),
        "FRONT-END": (BLUE, ft.Icons.WEB_ROUNDED),
        "FULL-STACK": (GREEN, ft.Icons.LAYERS_ROUNDED),
        "MOBILE": (ORANGE, ft.Icons.PHONE_ANDROID_ROUNDED),
        "DADOS": ("#D14C8B", ft.Icons.BAR_CHART_ROUNDED),
    }
    SITUACOES = {
        "andamento": ("EM ANDAMENTO", BLUE),
        "analise": ("EM ANÁLISE", ORANGE),
        "aceita": ("ACEITA", GREEN),
    }

    # ------------------------------------------------------------------
    # IDENTIFICADORES DO USUÁRIO
    # ------------------------------------------------------------------
    id_usuario = usuario.get("id_usuario")
    id_dev = usuario.get("id_dev")

    # ------------------------------------------------------------------
    # CARREGAMENTO INICIAL DO BANCO
    # ------------------------------------------------------------------
    perfil_db = db.buscar_perfil_dev(id_usuario)
    conta = {"xp": perfil_db.get("pontuacao", 0)}
    perfil = {
        "nome": perfil_db.get("nome", nome_inicial),
        "bio": perfil_db.get("bio", ""),
        "localizacao": perfil_db.get("localizacao", ""),
        "github": perfil_db.get("github", ""),
        "portfolio": perfil_db.get("portfolio", ""),
        "habilidades": perfil_db.get("habilidades", []) or [],
    }

    tarefas_db = db.buscar_tarefas_do_dev(id_dev)
    tarefas = []
    for t in tarefas_db:
        tarefas.append({
            "id": t["id"], "projeto": t, "titulo": t["titulo"],
            "empresa": t["empresa"], "categoria": t["categoria"],
            "valor": t["valor"], "xp": t["xp"], "prazo": t["prazo"],
            "progresso": t["progresso"], "status": t["status"],
            "entrega": t.get("entrega"),
        })

    catalogo = db.buscar_catalogo_projetos()
    seguindo = db.buscar_empresas_seguidas(id_dev)

    atividades_db = db.buscar_atividades_recentes(id_dev, limite=4)
    atividades = [
        (ft.Icons.CHECK_CIRCLE_ROUNDED, a["titulo"],
         f"{a['titulo']} · {a['empresa']}",
         a["data_aceite"] or "Hoje", "ACEITA", GREEN)
        for a in atividades_db
    ]

    mensagens: dict[str, list[dict]] = {}
    ultima_msg: dict[str, int] = {}
    empresas_db = db.buscar_empresas()
    for emp in empresas_db:
        nome_emp = emp["nome"]
        id_emp_usuario = emp.get("id_usuario")
        if id_emp_usuario:
            msgs = db.buscar_mensagens(id_usuario, id_emp_usuario)
            if msgs:
                mensagens[nome_emp] = [
                    {
                        "de": "dev" if m["direcao"] == "eu" else "empresa",
                        "texto": m["texto"],
                        "hora": m["hora"],
                    }
                    for m in msgs
                ]
                ultima_msg[nome_emp] = len(mensagens[nome_emp])

    ui = {
        "tela": "dashboard", "cat": "todas", "filtro_tarefa": "todas",
        "empresa": None, "busca": "", "empresa_chat": None,
        "rascunho": "", "seq": len(ultima_msg),
    }
    seletor = ft.FilePicker()
    page.services.append(seletor)

    # ------------------------------------------------------------------
    # AUXILIARES
    # ------------------------------------------------------------------
    def brl(v: float) -> str:
        return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def fmt(n: int) -> str:
        return f"{n:,}".replace(",", ".")

    def tamanho_legivel(n) -> str:
        if not n:
            return ""
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f} MB".replace(".", ",")
        return f"{max(1, round(n / 1000))} KB"

    def primeiro_nome() -> str:
        return (perfil["nome"].split() or ["Dev"])[0]

    def nivel_de(xp: int) -> int:
        return xp // XP_POR_NIVEL

    def nome_do_nivel(n: int) -> str:
        return NOMES_NIVEL[min(n, len(NOMES_NIVEL) - 1)]

    def com_opacidade(cor: str, op: float = 0.09) -> str:
        return ft.Colors.with_opacity(op, cor)

    def avisar(msg: str):
        page.show_dialog(ft.SnackBar(ft.Text(msg)))

    def registrar(icone, titulo: str, subtitulo: str, status: str, cor: str):
        atividades.insert(
            0, (icone, titulo, subtitulo, datetime.now().strftime("Hoje, %H:%M"), status, cor)
        )

    def tarefas_com(*status) -> list[dict]:
        return [t for t in tarefas if t["status"] in status]

    def ranking_completo() -> list[dict]:
        itens = db.buscar_ranking()
        for item in itens:
            item["eu"] = item["nome"] == perfil["nome"]
        itens.sort(key=lambda i: (-i["xp"], i["eu"]))
        for pos, item in enumerate(itens, start=1):
            item["pos"] = pos
        return itens

    def minha_posicao() -> int:
        return next((i["pos"] for i in ranking_completo() if i["eu"]), 0)

    # ------------------------------------------------------------------
    # PEÇAS VISUAIS
    # ------------------------------------------------------------------
    def avatar(texto: str, tamanho: int = 38) -> ft.CircleAvatar:
        ini = "".join(p[0] for p in texto.split()[:2]).upper()
        return ft.CircleAvatar(
            content=ft.Text(ini, color=WHITE, weight=ft.FontWeight.BOLD, size=max(10, tamanho // 3)),
            bgcolor="#8B5CF6", radius=tamanho / 2,
        )

    def selo(texto: str, cor: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(texto, color=cor, size=10, weight=ft.FontWeight.BOLD),
            bgcolor=com_opacidade(cor),
            padding=ft.Padding.symmetric(horizontal=9, vertical=5),
            border_radius=20,
        )

    def caixa(conteudo: ft.Control, **kw) -> ft.Container:
        return ft.Container(
            padding=kw.pop("padding", 18), bgcolor=WHITE,
            border=ft.Border.all(1, BORDER), border_radius=16,
            content=conteudo, **kw,
        )

    def botao_primario(texto: str, icone, on_click, ativo: bool = True) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=18, vertical=12),
            bgcolor=PURPLE if ativo else "#C9C4DE", border_radius=12,
            on_click=on_click,
            content=ft.Row(
                [ft.Icon(icone, color=WHITE, size=18),
                 ft.Text(texto, color=WHITE, size=13, weight=ft.FontWeight.W_600)],
                spacing=8, tight=True,
            ),
        )

    def link_acao(icone, texto: str, on_click, cor: str = PURPLE) -> ft.Container:
        return ft.Container(
            on_click=on_click,
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            content=ft.Row(
                [ft.Icon(icone, color=cor, size=15),
                 ft.Text(texto, color=cor, size=12, weight=ft.FontWeight.W_600)],
                spacing=5, tight=True,
            ),
        )

    def estrelas_fixas(nota: float, tamanho: int = 16) -> ft.Row:
        cheias = round(nota)
        return ft.Row(
            [ft.Icon(
                ft.Icons.STAR_ROUNDED if i <= cheias else ft.Icons.STAR_BORDER_ROUNDED,
                color=GOLD if i <= cheias else "#CFCBDD", size=tamanho,
            ) for i in range(1, 6)],
            spacing=1, tight=True,
        )

    def estado_vazio(icone, titulo: str, texto: str, acao: ft.Control | None = None) -> ft.Row:
        itens = [
            ft.Container(content=ft.Icon(icone, color=PURPLE, size=26),
                         bgcolor=PURPLE_LIGHT, padding=14, border_radius=30),
            ft.Text(titulo, color=TEXT, size=13, weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER),
            ft.Text(texto, color=MUTED, size=11, text_align=ft.TextAlign.CENTER),
        ]
        if acao:
            itens += [ft.Container(height=4), acao]
        return ft.Row([ft.Column(itens, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                 spacing=8, expand=True)])

    def cabecalho(titulo: str, subtitulo: str, extra: ft.Control | None = None) -> ft.Row:
        itens = [
            ft.Column(
                [ft.Text(titulo, size=26, color=TEXT, weight=ft.FontWeight.BOLD),
                 ft.Text(subtitulo, color=MUTED, size=13)],
                spacing=5, expand=True,
            )
        ]
        if extra:
            itens.append(extra)
        return ft.Row(itens, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def chip_filtro(rotulo: str, ativo: bool, on_click) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            border_radius=20,
            bgcolor=PURPLE if ativo else WHITE,
            border=ft.Border.all(1, PURPLE if ativo else BORDER),
            on_click=on_click,
            content=ft.Text(rotulo, size=12, weight=ft.FontWeight.W_600,
                            color=WHITE if ativo else MUTED),
        )

    def campo_texto(rotulo: str, **kw) -> ft.TextField:
        return ft.TextField(
            label=rotulo, border_radius=10, border_color=BORDER,
            focused_border_color=PURPLE, cursor_color=PURPLE,
            text_size=13, label_style=ft.TextStyle(color=MUTED), **kw,
        )

    def stat_card(icone, titulo: str, valor: str, nota: str, cor: str,
                  subindo: bool = False) -> ft.Container:
        return ft.Container(
            expand=True, padding=20, bgcolor=WHITE,
            border=ft.Border.all(1, BORDER), border_radius=18,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(content=ft.Icon(icone, color=cor, size=21),
                                         bgcolor=com_opacidade(cor), padding=11, border_radius=12),
                            ft.Container(expand=True),
                            ft.Icon(ft.Icons.TRENDING_UP if subindo else ft.Icons.TRENDING_FLAT,
                                    color=GREEN if subindo else MUTED, size=17),
                        ],
                    ),
                    ft.Text(titulo, color=MUTED, size=13),
                    ft.Text(valor, color=TEXT, size=27, weight=ft.FontWeight.BOLD),
                    ft.Text(nota, color=GREEN if subindo else MUTED, size=12,
                            weight=ft.FontWeight.W_500),
                ],
                spacing=9,
            ),
        )

    def project_card(name, company, category, progress, color, due, icon) -> ft.Container:
        return ft.Container(
            padding=18, bgcolor=WHITE, border=ft.Border.all(1, BORDER),
            border_radius=16,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(content=ft.Icon(icon, color=color, size=20),
                                         bgcolor=com_opacidade(color), padding=10, border_radius=11),
                            ft.Column(
                                [ft.Text(name, color=TEXT, weight=ft.FontWeight.BOLD, size=14),
                                 ft.Text(company, color=MUTED, size=12)],
                                spacing=3, expand=True,
                            ),
                            selo(category, color),
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        [ft.Text("Progresso", color=MUTED, size=12),
                         ft.Container(expand=True),
                         ft.Text(f"{int(progress * 100)}%", color=TEXT, size=12,
                                 weight=ft.FontWeight.BOLD)],
                    ),
                    ft.ProgressBar(value=progress, color=color, bgcolor="#F0EDF7",
                                   height=6, border_radius=8),
                    ft.Row(
                        [ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, color=MUTED, size=14),
                         ft.Text(f"Entrega: {due}", color=MUTED, size=11),
                         ft.Container(expand=True),
                         link_acao(ft.Icons.ARROW_FORWARD, "Ver tarefa",
                                   lambda e: mostrar("tarefas"))],
                        spacing=5,
                    ),
                ],
                spacing=13,
            ),
        )

    def activity_row(icon, title, subtitle, date, status, status_color) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=13),
            border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
            content=ft.Row(
                [
                    ft.Container(content=ft.Icon(icon, color=status_color, size=19),
                                 bgcolor=com_opacidade(status_color), padding=10, border_radius=11),
                    ft.Column(
                        [ft.Text(title, color=TEXT, size=13, weight=ft.FontWeight.W_600),
                         ft.Text(subtitle, color=MUTED, size=11)],
                        spacing=4, expand=True,
                    ),
                    ft.Column(
                        [selo(status, status_color),
                         ft.Text(date, color=MUTED, size=10)],
                        horizontal_alignment=ft.CrossAxisAlignment.END, spacing=7,
                    ),
                ],
                spacing=12,
            ),
        )

    def chip_arquivo(nome_arq: str, tamanho=None) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            bgcolor="#F7F6FC", border=ft.Border.all(1, BORDER), border_radius=10,
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED, color=MUTED, size=14),
                    ft.Text(f"{nome_arq}{' · ' + tamanho_legivel(tamanho) if tamanho else ''}",
                            color=TEXT, size=11),
                ],
                spacing=6, tight=True,
            ),
        )

    # ------------------------------------------------------------------
    # AÇÕES (INTEGRADAS COM O BANCO)
    # ------------------------------------------------------------------
    def pegar_projeto(p: dict):
        if len(tarefas_com("andamento")) >= MAX_ATIVOS:
            avisar(f"Você já tem {MAX_ATIVOS} projetos em andamento. "
                   f"Entregue ou desista de um para pegar outro.")
            return
        if not db.pegar_projeto(id_dev, p["id"]):
            avisar("Este projeto já foi pego por outro desenvolvedor.")
            return
        t = {
            "id": p["id"], "projeto": p, "titulo": p["titulo"],
            "empresa": p["empresa"], "categoria": p["categoria"],
            "valor": p["valor"], "xp": p["xp"], "prazo": p["prazo"],
            "progresso": 0, "status": "andamento", "entrega": None,
        }
        tarefas.insert(0, t)
        if p in catalogo:
            catalogo.remove(p)
        registrar(ft.Icons.ROCKET_LAUNCH_ROUNDED, "Projeto pego",
                  f"{p['titulo']} · {p['empresa']}", "EM ANDAMENTO", BLUE)
        mostrar("tarefas")
        avisar(f"Você pegou \"{p['titulo']}\". Atualize o progresso conforme avançar.")

    def atualizar_progresso(t: dict, valor: float):
        t["progresso"] = int(round(valor))
        db.atualizar_progresso(id_dev, t["id"], t["progresso"])
        mostrar()
        if t["progresso"] >= 100:
            avisar("Progresso em 100%! Agora é só enviar a entrega.")

    def abrir_desistencia(t: dict):
        def confirmar(ev):
            db.desistir_projeto(id_dev, t["id"])
            tarefas.remove(t)
            catalogo.insert(0, t["projeto"])
            registrar(ft.Icons.UNDO_ROUNDED, "Desistiu do projeto",
                      f"{t['titulo']} · {t['empresa']}", "CANCELADO", RED)
            page.pop_dialog()
            mostrar()
            avisar("Projeto devolvido: outro desenvolvedor poderá pegá-lo.")

        page.show_dialog(
            ft.AlertDialog(
                modal=True, bgcolor=WHITE,
                title=ft.Text("Desistir do projeto?", weight=ft.FontWeight.BOLD, color=TEXT),
                content=ft.Text(
                    f"\"{t['titulo']}\" volta para a lista de projetos e você perde o "
                    f"progresso feito ({t['progresso']}%).",
                    color=MUTED, size=13,
                ),
                actions=[
                    ft.TextButton(content=ft.Text("Cancelar", color=MUTED),
                                  on_click=lambda ev: page.pop_dialog()),
                    ft.Button(
                        content=ft.Text("Desistir", color=WHITE, weight=ft.FontWeight.W_600),
                        bgcolor=RED,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                        on_click=confirmar,
                    ),
                ],
            )
        )

    def guardar_arquivo(arquivo: dict, task_id: int):
        caminho = arquivo.get("caminho")
        if not caminho:
            return
        try:
            destino = PASTA_UPLOADS / "entregas" / f"task_{task_id}"
            destino.mkdir(parents=True, exist_ok=True)
            shutil.copy2(caminho, destino / arquivo["nome"])
        except OSError:
            pass

    async def escolher_arquivos() -> list[dict]:
        escolhidos = await seletor.pick_files(
            dialog_title="Anexar arquivos da entrega", allow_multiple=True
        )
        return [{"nome": f.name, "tamanho": f.size, "caminho": f.path}
                for f in (escolhidos or [])]

    def abrir_entrega(t: dict):
        anexos: list[dict] = []
        lista_anexos = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
        campo_nota = campo_texto("Observações para a empresa (opcional)",
                                 multiline=True, min_lines=3, max_lines=4)

        def desenhar_anexos():
            itens = []
            for i, a in enumerate(anexos):
                def remover(ev, idx=i):
                    anexos.pop(idx)
                    desenhar_anexos()
                    page.update()
                itens.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        bgcolor="#F7F6FC", border=ft.Border.all(1, BORDER), border_radius=10,
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED, color=MUTED, size=16),
                                ft.Text(a["nome"], size=12, color=TEXT, expand=True,
                                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(tamanho_legivel(a["tamanho"]), size=11, color=MUTED),
                                ft.Container(content=ft.Icon(ft.Icons.CLOSE_ROUNDED,
                                                             color=MUTED, size=16), on_click=remover),
                            ],
                            spacing=8,
                        ),
                    )
                )
            lista_anexos.controls = itens
            lista_anexos.height = 132 if len(itens) > 3 else None

        async def anexar(ev):
            anexos.extend(await escolher_arquivos())
            desenhar_anexos()
            page.update()

        def enviar(ev):
            for a in anexos:
                guardar_arquivo(a, t["id"])
            arquivos_entrega = [{"nome": a["nome"], "tamanho": a["tamanho"]} for a in anexos]
            nota = (campo_nota.value or "").strip()
            if not db.enviar_entrega(id_dev, t["id"], arquivos_entrega, nota):
                page.pop_dialog()
                avisar("Não foi possível enviar: esta tarefa não está em andamento.")
                return
            t["entrega"] = {"arquivos": arquivos_entrega, "nota": nota}
            t["status"] = "analise"
            t["progresso"] = 100
            registrar(ft.Icons.UPLOAD_ROUNDED, "Entrega enviada",
                      f"{t['titulo']} · {t['empresa']}", "EM ANÁLISE", ORANGE)
            page.pop_dialog()
            mostrar()
            avisar("Entrega enviada! Agora é aguardar a aprovação da empresa.")

        desenhar_anexos()
        page.show_dialog(
            ft.AlertDialog(
                modal=True, bgcolor=WHITE,
                title=ft.Text(f"Enviar entrega: {t['titulo']}",
                              weight=ft.FontWeight.BOLD, color=TEXT, size=18),
                content=ft.Container(
                    width=480,
                    content=ft.Column(
                        [
                            ft.Text("Anexe os arquivos do que você desenvolveu.", color=MUTED, size=13),
                            lista_anexos,
                            link_acao(ft.Icons.UPLOAD_FILE_ROUNDED, "Anexar arquivos", anexar),
                            campo_nota,
                        ],
                        spacing=14, tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    ),
                ),
                actions=[
                    ft.TextButton(content=ft.Text("Cancelar", color=MUTED),
                                  on_click=lambda ev: page.pop_dialog()),
                    ft.Button(
                        content=ft.Text("Enviar entrega", color=WHITE, weight=ft.FontWeight.W_600),
                        bgcolor=PURPLE,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                        on_click=enviar,
                    ),
                ],
            )
        )

    def simular_aprovacao(t: dict):
        def tratar(ev):
            try:
                resultado = db.aprovar_entrega(t["id"], id_dev)
            except (ValueError, PermissionError) as erro:
                avisar(f"Não foi possível aprovar: {erro}")
                return
            t["status"] = "aceita"
            conta["xp"] = resultado["pontuacao_total"]
            registrar(ft.Icons.CHECK_CIRCLE_ROUNDED, "Entrega aprovada",
                      f"{t['titulo']} · {t['empresa']}", "ACEITA", GREEN)
            mostrar()
            subiu = resultado["subiu_nivel"]
            avisar(
                f"Aprovada! +{resultado['xp_ganho']} XP. Você subiu para o nível "
                f"{nivel_de(conta['xp'])} ({nome_do_nivel(nivel_de(conta['xp']))})!"
                if subiu
                else f"Aprovada! +{resultado['xp_ganho']} XP."
            )
        return tratar

    def abrir_chat(nome_empresa: str, rascunho: str = ""):
        ui["empresa_chat"] = nome_empresa
        ui["rascunho"] = rascunho
        mostrar("mensagens")

    def ver_projetos_da_empresa(nome_empresa: str):
        ui["empresa"] = nome_empresa
        ui["cat"] = "todas"
        ui["busca"] = ""
        mostrar("projetos")

    def abrir_empresa(nome_empresa: str):
        ui["empresa_busca"] = nome_empresa
        mostrar("empresas")

    # ------------------------------------------------------------------
    # TELA: DASHBOARD
    # ------------------------------------------------------------------
    def view_dashboard() -> ft.Control:
        xp = conta["xp"]
        nivel = nivel_de(xp)
        progresso_nivel = (xp % XP_POR_NIVEL) / XP_POR_NIVEL
        pegas = len(tarefas)
        entregues = len(tarefas_com("analise", "aceita"))
        aprovadas = len(tarefas_com("aceita"))
        em_andamento = tarefas_com("andamento", "analise")
        novo = xp == 0 and pegas == 0

        def buscar(ev):
            ui["busca"] = (ev.control.value or "").strip()
            ui["empresa"] = None
            ui["cat"] = "todas"
            mostrar("projetos")

        cab = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Dashboard", size=26, color=TEXT, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"Bem-vindo, {primeiro_nome()}! Sua conta foi criada. "
                            "Aqui ficará o resumo das suas atividades."
                            if novo
                            else f"Bem-vindo de volta, {primeiro_nome()}! "
                                 "Aqui está seu resumo de atividades.",
                            color=MUTED, size=13,
                        ),
                    ],
                    spacing=5, expand=True,
                ),
                ft.TextField(
                    hint_text="Buscar projetos...",
                    hint_style=ft.TextStyle(color="#A29DB4"),
                    prefix_icon=ft.Icon(ft.Icons.SEARCH, color=MUTED, size=18),
                    border_radius=12, border_color=BORDER,
                    focused_border_color=PURPLE, bgcolor=WHITE, filled=True,
                    text_size=12, width=220,
                    content_padding=ft.Padding.symmetric(horizontal=10, vertical=10),
                    on_submit=buscar,
                ),
                ft.Container(
                    content=ft.Icon(ft.Icons.NOTIFICATIONS_NONE_ROUNDED, color=MUTED, size=21),
                    padding=11, bgcolor=WHITE, border=ft.Border.all(1, BORDER),
                    border_radius=12,
                    on_click=lambda e: avisar("Você não tem notificações novas."),
                ),
            ],
            spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        banner = ft.Container(
            padding=22, border_radius=18,
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                       colors=["#6C3CE9", "#4820A8"]),
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row(
                                [ft.Icon(ft.Icons.AUTO_AWESOME, color="#E0D3FF", size=18),
                                 ft.Text("SUA JORNADA DE DESENVOLVEDOR", color="#E0D3FF",
                                         size=10, weight=ft.FontWeight.BOLD)],
                                spacing=8,
                            ),
                            ft.Text("Sua jornada começa agora!" if novo else "Continue evoluindo!",
                                    color=WHITE, size=21, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Aceite seu primeiro projeto para ganhar seus primeiros pontos."
                                if novo
                                else f"Você já fez {entregues} entrega(s) na comunidade. "
                                     "Vamos para a próxima?",
                                color="#E1D8FF", size=12,
                            ),
                            ft.Container(height=5),
                            ft.Row(
                                [ft.Text(f"Próximo nível: {nivel + 1:02d}", color=WHITE,
                                         size=11, weight=ft.FontWeight.W_600),
                                 ft.Container(expand=True),
                                 ft.Text(f"{int(progresso_nivel * 100)}%", color=WHITE,
                                         size=11, weight=ft.FontWeight.BOLD)],
                            ),
                            ft.ProgressBar(value=progresso_nivel, color="#D8C8FF",
                                           bgcolor=ft.Colors.with_opacity(0.21, WHITE),
                                           height=7, border_radius=8),
                            ft.Text(f"{fmt(xp % XP_POR_NIVEL)} / {fmt(XP_POR_NIVEL)} "
                                    "XP para o próximo nível",
                                    color="#E1D8FF", size=10),
                        ],
                        spacing=9, expand=True,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.MILITARY_TECH_ROUNDED, color="#F9D976", size=42),
                                ft.Text(f"NÍVEL {nivel:02d}", color="#F9D976", size=11,
                                        weight=ft.FontWeight.BOLD),
                                ft.Text(nome_do_nivel(nivel), color=WHITE, size=10),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5,
                        ),
                        padding=ft.Padding.all(18),
                        bgcolor=ft.Colors.with_opacity(0.09, WHITE), border_radius=16,
                    ),
                ],
                spacing=20, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        taxa = f"{round(aprovadas * 100 / entregues)}% de aprovação" if entregues else "Sem entregas ainda"
        stats = ft.Row(
            [
                stat_card(ft.Icons.STAR_ROUNDED, "Pontuação total",
                          f"{fmt(xp)} XP",
                          f"Nível {nivel} · {nome_do_nivel(nivel)}" if xp else "Nenhum ponto ainda",
                          PURPLE, xp > 0),
                stat_card(ft.Icons.TASK_ALT_ROUNDED, "Tarefas aceitas",
                          str(pegas), f"{entregues} concluídas", GREEN, pegas > 0),
                stat_card(ft.Icons.FOLDER_SPECIAL_ROUNDED, "Projetos ativos",
                          f"{len(em_andamento):02d}",
                          "Em desenvolvimento" if em_andamento else "Nenhum em andamento",
                          BLUE, len(em_andamento) > 0),
                stat_card(ft.Icons.VERIFIED_ROUNDED, "Entregas aprovadas",
                          str(aprovadas), taxa, ORANGE, aprovadas > 0),
            ],
            spacing=14,
        )

        if em_andamento:
            projetos = ft.Column(
                [project_card(t["titulo"], t["empresa"], t["categoria"],
                              t["progresso"] / 100,
                              CATEGORIAS[t["categoria"]][0], t["prazo"],
                              CATEGORIAS[t["categoria"]][1])
                 for t in em_andamento],
                spacing=12,
            )
        else:
            projetos = caixa(
                estado_vazio(
                    ft.Icons.FOLDER_OPEN_ROUNDED,
                    "Nenhum projeto em andamento",
                    "Quando você aceitar um projeto, ele aparecerá aqui.",
                    botao_primario("Explorar projetos", ft.Icons.SEARCH,
                                   lambda e: mostrar("projetos")),
                ),
                padding=ft.Padding.symmetric(horizontal=18, vertical=34),
            )

        if atividades:
            ativ = caixa(ft.Column([activity_row(*a) for a in atividades[:4]], spacing=0),
                         padding=ft.Padding.symmetric(horizontal=16, vertical=4))
        else:
            ativ = caixa(
                estado_vazio(ft.Icons.HISTORY_ROUNDED, "Nenhuma atividade ainda",
                             "Suas entregas aceitas aparecerão aqui."),
                padding=ft.Padding.symmetric(horizontal=16, vertical=30),
            )

        dica = caixa(
            ft.Row(
                [
                    ft.Container(content=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE,
                                                 color=ORANGE, size=22),
                                 bgcolor="#FFF4E5", padding=10, border_radius=12),
                    ft.Column(
                        [ft.Text("Dica da comunidade", color=TEXT, size=12,
                                 weight=ft.FontWeight.BOLD),
                         ft.Text("Mantenha seu perfil atualizado para receber "
                                 "mais oportunidades.", color=MUTED, size=11)],
                        spacing=4, expand=True,
                    ),
                ],
                spacing=10,
            ),
            padding=16, on_click=lambda e: mostrar("perfil"),
        )

        return ft.Column(
            [
                cab, ft.Container(height=5), banner, stats,
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Row(
                                    [ft.Text("Projetos em andamento", color=TEXT,
                                             size=17, weight=ft.FontWeight.BOLD),
                                     ft.Container(expand=True),
                                     link_acao(ft.Icons.ARROW_FORWARD, "Ver todos",
                                               lambda e: mostrar("tarefas"))],
                                ),
                                projetos,
                            ],
                            spacing=14, expand=3,
                        ),
                        ft.Column(
                            [
                                ft.Row(
                                    [ft.Text("Atividades recentes", color=TEXT,
                                             size=17, weight=ft.FontWeight.BOLD),
                                     ft.Container(expand=True),
                                     ft.Icon(ft.Icons.HISTORY_ROUNDED, color=MUTED, size=18)],
                                ),
                                ativ, dica,
                            ],
                            spacing=14, expand=2,
                        ),
                    ],
                    spacing=18, vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=20, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # ------------------------------------------------------------------
    # TELA: PROJETOS
    # ------------------------------------------------------------------
    def projeto_card(p: dict) -> ft.Container:
        cor, icone = CATEGORIAS[p["categoria"]]
        corpo = [
            ft.Row(
                [
                    ft.Container(content=ft.Icon(icone, color=cor, size=20),
                                 bgcolor=com_opacidade(cor), padding=10, border_radius=11),
                    ft.Column(
                        [ft.Text(p["titulo"], color=TEXT, weight=ft.FontWeight.BOLD, size=14),
                         ft.Row(
                             [ft.Icon(ft.Icons.BUSINESS_ROUNDED, color=MUTED, size=13),
                              ft.Text(p["empresa"], color=MUTED, size=12)],
                             spacing=5,
                         )],
                        spacing=3, expand=True,
                    ),
                    selo(p["categoria"], cor),
                ],
                spacing=12,
            ),
            ft.Text(p["descricao"], color=MUTED, size=12),
            ft.Row(
                [
                    ft.Row([ft.Icon(ft.Icons.PAYMENTS_ROUNDED, color=GREEN, size=15),
                            ft.Text(brl(p["valor"]), color=TEXT, size=12,
                                    weight=ft.FontWeight.BOLD)],
                           spacing=5, tight=True),
                    ft.Row([ft.Icon(ft.Icons.BOLT_ROUNDED, color=PURPLE, size=15),
                            ft.Text(f"{p['xp']} XP", color=TEXT, size=12,
                                    weight=ft.FontWeight.BOLD)],
                           spacing=5, tight=True),
                    ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, color=MUTED, size=14),
                            ft.Text(f"Prazo: {p['prazo']}", color=MUTED, size=12)],
                           spacing=5, tight=True),
                ],
                spacing=18, wrap=True, run_spacing=6,
            ),
        ]
        if p.get("arquivos"):
            corpo.append(ft.Row(
                [chip_arquivo(a["nome"], a.get("tamanho")) for a in p["arquivos"]],
                wrap=True, spacing=8, run_spacing=8,
            ))
        corpo.append(
            ft.Row(
                [
                    link_acao(ft.Icons.BUSINESS_ROUNDED, "Ver empresa",
                              lambda e, n=p["empresa"]: abrir_empresa(n)),
                    link_acao(ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED, "Mensagem",
                              lambda e, pp=p: abrir_chat(
                                  pp["empresa"],
                                  f"Olá! Tenho uma dúvida sobre o projeto \"{pp['titulo']}\".")),
                    ft.Container(expand=True),
                    botao_primario("Pegar projeto", ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                   lambda e, pp=p: pegar_projeto(pp)),
                ],
            )
        )
        return ft.Container(
            padding=18, bgcolor=WHITE, border=ft.Border.all(1, BORDER),
            border_radius=16, content=ft.Column(corpo, spacing=12),
        )

    def view_projetos() -> ft.Control:
        lista_col = ft.Column(spacing=12)

        def desenhar_lista():
            termo = ui["busca"].lower()
            visiveis = [
                p for p in catalogo
                if (ui["cat"] == "todas" or p["categoria"] == ui["cat"])
                and (not ui["empresa"] or p["empresa"] == ui["empresa"])
                and (not termo
                     or termo in p["titulo"].lower()
                     or termo in p["empresa"].lower()
                     or termo in p["descricao"].lower())
            ]
            if visiveis:
                lista_col.controls = [projeto_card(p) for p in visiveis]
            else:
                lista_col.controls = [
                    caixa(
                        estado_vazio(ft.Icons.FOLDER_OPEN_ROUNDED,
                                     "Nenhum projeto encontrado",
                                     "Tente outra categoria ou outra busca."),
                        padding=ft.Padding.symmetric(horizontal=18, vertical=36),
                    )
                ]

        def ao_buscar(ev):
            ui["busca"] = (ev.control.value or "").strip()
            desenhar_lista()
            page.update()

        def definir_cat(valor: str):
            def tratar(ev):
                ui["cat"] = valor
                mostrar()
            return tratar

        def limpar_empresa(ev):
            ui["empresa"] = None
            mostrar()

        chips = [chip_filtro("Todos", ui["cat"] == "todas", definir_cat("todas"))]
        chips += [chip_filtro(c, ui["cat"] == c, definir_cat(c)) for c in CATEGORIAS]
        if ui["empresa"]:
            chips.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    border_radius=20, bgcolor=PURPLE_LIGHT,
                    border=ft.Border.all(1, PURPLE),
                    on_click=limpar_empresa,
                    content=ft.Row(
                        [ft.Text(f"Empresa: {ui['empresa']}", size=12, color=PURPLE,
                                 weight=ft.FontWeight.W_600),
                         ft.Icon(ft.Icons.CLOSE_ROUNDED, size=14, color=PURPLE)],
                        spacing=6, tight=True,
                    ),
                )
            )

        campo_busca = ft.TextField(
            hint_text="Buscar por título, empresa ou descrição...",
            hint_style=ft.TextStyle(color="#A29DB4"),
            prefix_icon=ft.Icon(ft.Icons.SEARCH, color=MUTED, size=18),
            value=ui["busca"], border_radius=12, border_color=BORDER,
            focused_border_color=PURPLE, bgcolor=WHITE, filled=True,
            text_size=13,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=10),
            on_change=ao_buscar,
        )

        desenhar_lista()
        ativos = len(tarefas_com("andamento"))
        info_limite = ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            bgcolor=PURPLE_LIGHT, border_radius=12,
            content=ft.Text(f"Em andamento: {ativos} de {MAX_ATIVOS}",
                            color=PURPLE, size=12, weight=ft.FontWeight.W_600),
        )

        return ft.Column(
            [
                cabecalho("Projetos",
                          "Escolha um projeto publicado pelas empresas para começar a ganhar XP.",
                          info_limite),
                campo_busca,
                ft.Row(chips, wrap=True, spacing=8, run_spacing=8),
                lista_col,
            ],
            spacing=18, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # ------------------------------------------------------------------
    # TELA: MINHAS TAREFAS
    # ------------------------------------------------------------------
    def tarefa_card(t: dict) -> ft.Container:
        link_msg = link_acao(
            ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED, "Mensagem",
            lambda e, tt=t: abrir_chat(tt["empresa"],
                                       f"Olá! Sobre o projeto \"{tt['titulo']}\": "),
        )
        cor, icone = CATEGORIAS[t["categoria"]]
        texto_sit, cor_sit = SITUACOES[t["status"]]
        corpo = [
            ft.Row(
                [
                    ft.Container(content=ft.Icon(icone, color=cor, size=20),
                                 bgcolor=com_opacidade(cor), padding=10, border_radius=11),
                    ft.Column(
                        [ft.Text(t["titulo"], color=TEXT, weight=ft.FontWeight.BOLD, size=14),
                         ft.Text(f"{t['empresa']}  ·  Prazo: {t['prazo']}  ·  "
                                 f"{brl(t['valor'])}  ·  {t['xp']} XP",
                                 color=MUTED, size=12)],
                        spacing=3, expand=True,
                    ),
                    selo(t["categoria"], cor), selo(texto_sit, cor_sit),
                ],
                spacing=10,
            ),
            ft.Row(
                [ft.Text("Progresso", color=MUTED, size=12),
                 ft.Container(expand=True),
                 ft.Text(f"{t['progresso']}%", color=TEXT, size=12,
                         weight=ft.FontWeight.BOLD)],
            ),
            ft.ProgressBar(value=t["progresso"] / 100,
                           color=GREEN if t["status"] == "aceita" else cor,
                           bgcolor="#F0EDF7", height=6, border_radius=8),
        ]
        if t["status"] == "andamento":
            corpo.append(
                ft.Row(
                    [
                        ft.Text("Atualizar progresso", color=MUTED, size=12),
                        ft.Slider(
                            min=0, max=100, divisions=20, value=t["progresso"],
                            label="{value}%", active_color=cor, expand=True,
                            on_change_end=lambda e, tt=t: atualizar_progresso(tt, e.control.value),
                        ),
                    ],
                    spacing=10,
                )
            )
        if t["entrega"] and t["entrega"]["arquivos"]:
            corpo.append(ft.Row(
                [chip_arquivo(a["nome"], a.get("tamanho"))
                 for a in t["entrega"]["arquivos"]],
                wrap=True, spacing=8, run_spacing=8,
            ))
        if t["status"] == "andamento":
            pronto = t["progresso"] >= 100
            corpo.append(
                ft.Row(
                    [
                        link_acao(ft.Icons.UNDO_ROUNDED, "Desistir",
                                  lambda e, tt=t: abrir_desistencia(tt), RED),
                        link_msg, ft.Container(expand=True),
                        ft.Text("" if pronto else "Chegue a 100% para entregar",
                                color=MUTED, size=11),
                        botao_primario(
                            "Enviar entrega", ft.Icons.UPLOAD_ROUNDED,
                            (lambda e, tt=t: abrir_entrega(tt)) if pronto
                            else (lambda e: avisar("Leve o progresso até 100% "
                                                   "para enviar a entrega.")),
                            ativo=pronto,
                        ),
                    ],
                    spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        elif t["status"] == "analise":
            corpo.append(ft.Row([
        ft.Icon(ft.Icons.HOURGLASS_TOP_ROUNDED, color=ORANGE, size=16),
        ft.Text("Aguardando a aprovação da empresa. Quando a empresa aprovar, você ganhará o XP.", color=ORANGE, size=12, weight=ft.FontWeight.W_500),
        ft.Container(expand=True), link_msg,
    ], spacing=6))
        else:
            corpo.append(
                ft.Row(
                    [
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=GREEN, size=16),
                        ft.Text(f"Aprovada pela empresa · +{t['xp']} XP",
                                color=GREEN, size=12, weight=ft.FontWeight.W_600),
                        ft.Container(expand=True), link_msg,
                    ],
                    spacing=6,
                )
            )
        return ft.Container(
            padding=18, bgcolor=WHITE, border=ft.Border.all(1, BORDER),
            border_radius=16, content=ft.Column(corpo, spacing=12),
        )

    def view_tarefas() -> ft.Control:
        filtro = ui["filtro_tarefa"]
        visiveis = tarefas if filtro == "todas" else tarefas_com(filtro)

        def definir(valor: str):
            def tratar(ev):
                ui["filtro_tarefa"] = valor
                mostrar()
            return tratar

        if visiveis:
            lista = ft.Column([tarefa_card(t) for t in visiveis], spacing=12)
        elif tarefas:
            lista = caixa(
                estado_vazio(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                             "Nenhuma tarefa nesta situação",
                             "Troque o filtro para ver as outras tarefas."),
                padding=ft.Padding.symmetric(horizontal=18, vertical=36),
            )
        else:
            lista = caixa(
                estado_vazio(
                    ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                    "Você ainda não pegou nenhum projeto",
                    "Escolha um projeto na aba Projetos.",
                    botao_primario("Ver projetos", ft.Icons.SEARCH,
                                   lambda e: mostrar("projetos")),
                ),
                padding=ft.Padding.symmetric(horizontal=18, vertical=40),
            )

        return ft.Column(
            [
                cabecalho("Minhas tarefas",
                          "Atualize o progresso, envie a entrega e acompanhe a aprovação."),
                ft.Row(
                    [
                        chip_filtro("Todas", filtro == "todas", definir("todas")),
                        chip_filtro("Em andamento", filtro == "andamento",
                                    definir("andamento")),
                        chip_filtro("Em análise", filtro == "analise", definir("analise")),
                        chip_filtro("Aceitas", filtro == "aceita", definir("aceita")),
                    ],
                    spacing=8, wrap=True,
                ),
                lista,
            ],
            spacing=18, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # ------------------------------------------------------------------
    # TELA: EMPRESAS
    # ------------------------------------------------------------------
    def view_empresas() -> ft.Control:
        grade = ft.Row(wrap=True, spacing=16, run_spacing=16,
                       vertical_alignment=ft.CrossAxisAlignment.START)
        filtro = {"texto": ui.pop("empresa_busca", "")}
        texto_seguindo = ft.Text("", color=PURPLE, size=12, weight=ft.FontWeight.W_600)

        def empresa_card(e: dict) -> ft.Container:
            abertos = len([p for p in catalogo if p["empresa"] == e["nome"]])
            ja_trabalhou = any(t["empresa"] == e["nome"] for t in tarefas)
            segue = e["nome"] in seguindo

            def alternar(ev, n=e["nome"]):
                if n in seguindo:
                    seguindo.remove(n)
                    db.deixar_seguir_empresa(id_dev, n)
                else:
                    seguindo.add(n)
                    db.seguir_empresa(id_dev, n)
                desenhar_grade()
                page.update()

            def botao_contorno(icone, texto, on_click, preenchido=False) -> ft.Container:
                return ft.Container(
                    expand=True,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=9),
                    border_radius=10, border=ft.Border.all(1, PURPLE),
                    bgcolor=PURPLE_LIGHT if preenchido else None,
                    on_click=on_click,
                    content=ft.Row(
                        [ft.Icon(icone, color=PURPLE, size=15),
                         ft.Text(texto, color=PURPLE, size=12, weight=ft.FontWeight.W_600)],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=6, tight=True,
                    ),
                )

            rodape = ft.Column(
                [
                    ft.Row(
                        [
                            botao_contorno(
                                ft.Icons.FAVORITE_ROUNDED if segue
                                else ft.Icons.FAVORITE_BORDER_ROUNDED,
                                "Seguindo" if segue else "Seguir",
                                alternar, preenchido=segue,
                            ),
                            botao_contorno(ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED,
                                           "Mensagem",
                                           lambda ev, n=e["nome"]: abrir_chat(n)),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            ft.Container(
                                expand=True,
                                padding=ft.Padding.symmetric(horizontal=14, vertical=11),
                                bgcolor=PURPLE, border_radius=12,
                                on_click=lambda ev, n=e["nome"]: ver_projetos_da_empresa(n),
                                content=ft.Row(
                                    [ft.Icon(ft.Icons.ARROW_FORWARD, color=WHITE, size=16),
                                     ft.Text("Ver projetos", color=WHITE, size=13,
                                             weight=ft.FontWeight.W_600)],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=8, tight=True,
                                ),
                            )
                        ]
                    ),
                ],
                spacing=8,
            )
            selos = [selo(f"{abertos} PROJETO(S) ABERTO(S)",
                          PURPLE if abertos else MUTED)]
            if ja_trabalhou:
                selos.append(selo("VOCÊ JÁ TRABALHOU AQUI", GREEN))
            return ft.Container(
                width=310, padding=18, bgcolor=WHITE,
                border=ft.Border.all(1, BORDER), border_radius=16,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                avatar(e["nome"], 44),
                                ft.Column(
                                    [ft.Text(e["nome"], color=TEXT, size=14,
                                             weight=ft.FontWeight.BOLD,
                                             max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                     ft.Text(f"{e.get('area', '')} · {e.get('cidade', '')}",
                                             color=MUTED, size=11,
                                             max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)],
                                    spacing=3, expand=True,
                                ),
                            ],
                            spacing=12,
                        ),
                        ft.Row(
                            [estrelas_fixas(e.get("nota", 5)),
                             ft.Text(f"{e.get('nota', 0):.1f}".replace(".", ","),
                                     color=TEXT, size=12, weight=ft.FontWeight.BOLD)],
                            spacing=6,
                        ),
                        ft.Text(e.get("descricao", ""), color=MUTED, size=12),
                        ft.Row(selos, wrap=True, spacing=6, run_spacing=6),
                        rodape,
                    ],
                    spacing=12,
                ),
            )

        def desenhar_grade():
            texto_seguindo.value = f"Seguindo: {len(seguindo)}"
            termo = filtro["texto"].lower()
            todas_empresas = db.buscar_empresas()
            itens = [
                e for e in todas_empresas
                if not termo or termo in e["nome"].lower() or termo in e.get("area", "").lower()
            ]
            grade.controls = [empresa_card(e) for e in itens] or [
                caixa(
                    estado_vazio(ft.Icons.BUSINESS_ROUNDED,
                                 "Nenhuma empresa encontrada",
                                 "Tente outro nome ou área."),
                    padding=ft.Padding.symmetric(horizontal=40, vertical=36),
                )
            ]

        def ao_buscar(ev):
            filtro["texto"] = (ev.control.value or "").strip()
            desenhar_grade()
            page.update()

        campo_busca = ft.TextField(
            hint_text="Buscar empresa por nome ou área...",
            hint_style=ft.TextStyle(color="#A29DB4"),
            prefix_icon=ft.Icon(ft.Icons.SEARCH, color=MUTED, size=18),
            value=filtro["texto"], border_radius=12, border_color=BORDER,
            focused_border_color=PURPLE, bgcolor=WHITE, filled=True,
            text_size=13,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=10),
            on_change=ao_buscar,
        )

        desenhar_grade()
        resumo = ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            bgcolor=PURPLE_LIGHT, border_radius=12,
            content=texto_seguindo,
        )
        return ft.Column(
            [cabecalho("Empresas",
                       "Conheça quem publica projetos na DevSphere e siga as suas favoritas.",
                       resumo),
             campo_busca, grade],
            spacing=18, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # ------------------------------------------------------------------
    # TELA: RANKING
    # ------------------------------------------------------------------
    def view_ranking() -> ft.Control:
        itens = ranking_completo()
        eu = next((i for i in itens if i["eu"]), None)
        if not eu:
            eu = {"nome": perfil["nome"], "xp": conta["xp"], "eu": True, "pos": len(itens) + 1}
            itens.append(eu)

        acima = next((i for i in itens if i["pos"] == eu["pos"] - 1), None)
        if acima:
            faltam = acima["xp"] - eu["xp"] + 1
            texto_meta = f"Faltam {fmt(faltam)} XP para ultrapassar {acima['nome']}."
        else:
            texto_meta = "Você lidera o ranking! Continue entregando para manter a posição."

        banner = ft.Container(
            padding=22, border_radius=18,
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                       colors=["#6C3CE9", "#4820A8"]),
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Column(
                            [ft.Text("SUA POSIÇÃO", color="#E0D3FF", size=10,
                                     weight=ft.FontWeight.BOLD),
                             ft.Text(f"#{eu['pos']}", color=WHITE, size=36,
                                     weight=ft.FontWeight.BOLD)],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2,
                        ),
                        padding=ft.Padding.symmetric(horizontal=24, vertical=14),
                        bgcolor=ft.Colors.with_opacity(0.12, WHITE), border_radius=16,
                    ),
                    ft.Column(
                        [
                            ft.Text(f"{fmt(eu['xp'])} XP  ·  Nível "
                                    f"{nivel_de(eu['xp'])} "
                                    f"({nome_do_nivel(nivel_de(eu['xp']))})",
                                    color=WHITE, size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{eu['pos']}º de {len(itens)} desenvolvedores",
                                    color="#E1D8FF", size=12),
                            ft.Text(texto_meta, color="#E1D8FF", size=12),
                        ],
                        spacing=6, expand=True,
                    ),
                ],
                spacing=20, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        medalhas = {1: GOLD, 2: "#A8A8B3", 3: "#C98A52"}

        def cartao_podio(i: dict) -> ft.Container:
            cor = medalhas[i["pos"]]
            return ft.Container(
                expand=True, padding=18, bgcolor=WHITE,
                border=ft.Border.all(2 if i["eu"] else 1,
                                     PURPLE if i["eu"] else BORDER),
                border_radius=16,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED, color=cor, size=30),
                        avatar(i["nome"], 46),
                        ft.Text(f"{i['nome']}{' (você)' if i['eu'] else ''}",
                                color=TEXT, size=13, weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER),
                        ft.Text(f"{fmt(i['xp'])} XP", color=PURPLE, size=13,
                                weight=ft.FontWeight.BOLD),
                        selo(f"{i['pos']}º LUGAR", cor),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8,
                ),
            )

        podio = ft.Row([cartao_podio(i) for i in itens[:3]], spacing=14)
        linhas = []
        for i in itens[3:]:
            linhas.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=12, vertical=11),
                    border_radius=12,
                    bgcolor=PURPLE_LIGHT if i["eu"] else None,
                    border=ft.Border.only(bottom=ft.BorderSide(1, BORDER))
                    if not i["eu"] else None,
                    content=ft.Row(
                        [
                            ft.Text(f"#{i['pos']}",
                                    color=PURPLE if i["eu"] else MUTED,
                                    size=13, weight=ft.FontWeight.BOLD, width=36),
                            avatar(i["nome"], 34),
                            ft.Column(
                                [ft.Text(f"{i['nome']}{' (você)' if i['eu'] else ''}",
                                         color=TEXT, size=13, weight=ft.FontWeight.W_600),
                                 ft.Text(f"Nível {nivel_de(i['xp'])} · "
                                         f"{nome_do_nivel(nivel_de(i['xp']))}",
                                         color=MUTED, size=11)],
                                spacing=2, expand=True,
                            ),
                            ft.Text(f"{fmt(i['xp'])} XP", color=TEXT, size=13,
                                    weight=ft.FontWeight.BOLD),
                        ],
                        spacing=12,
                    ),
                )
            )

        tabela = caixa(
            ft.Column(
                [ft.Text("Classificação geral", color=TEXT, size=16,
                         weight=ft.FontWeight.BOLD),
                 ft.Column(linhas, spacing=2)],
                spacing=12,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=18),
        ) if linhas else ft.Container()

        info = caixa(
            ft.Row(
                [
                    ft.Container(content=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE,
                                                 color=ORANGE, size=22),
                                 bgcolor="#FFF4E5", padding=10, border_radius=12),
                    ft.Column(
                        [ft.Text("Como subir no ranking", color=TEXT, size=12,
                                 weight=ft.FontWeight.BOLD),
                         ft.Text(f"Cada entrega aprovada pela empresa dá XP. "
                                 f"A cada {fmt(XP_POR_NIVEL)} XP você sobe de nível.",
                                 color=MUTED, size=11)],
                        spacing=4, expand=True,
                    ),
                ],
                spacing=10,
            ),
            padding=16,
        )
        return ft.Column(
            [cabecalho("Ranking",
                       "Veja como você se compara aos outros desenvolvedores da DevSphere."),
             banner, podio, tabela, info],
            spacing=20, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # ------------------------------------------------------------------
    # TELA: MEU PERFIL
    # ------------------------------------------------------------------
    def view_perfil() -> ft.Control:
        xp = conta["xp"]
        nivel = nivel_de(xp)
        rascunho_skills = list(perfil["habilidades"])
        linha_skills = ft.Row(wrap=True, spacing=8, run_spacing=8)
        campo_nome = campo_texto("Nome", value=perfil["nome"])
        campo_bio = campo_texto("Sobre você", value=perfil["bio"],
                                multiline=True, min_lines=3, max_lines=5)
        campo_local = campo_texto("Localização", value=perfil["localizacao"],
                                  prefix_icon=ft.Icon(ft.Icons.LOCATION_ON_OUTLINED,
                                                      color=MUTED, size=18))
        campo_github = campo_texto("GitHub", value=perfil["github"],
                                   prefix_icon=ft.Icon(ft.Icons.LINK_ROUNDED,
                                                       color=MUTED, size=18))
        campo_port = campo_texto("Portfólio", value=perfil["portfolio"],
                                 prefix_icon=ft.Icon(ft.Icons.PUBLIC_ROUNDED,
                                                     color=MUTED, size=18))
        campo_skill = campo_texto("Nova habilidade (ex.: Python)", expand=True)

        def desenhar_skills():
            chips = []
            for i, s in enumerate(rascunho_skills):
                def remover(ev, idx=i):
                    rascunho_skills.pop(idx)
                    desenhar_skills()
                    page.update()
                chips.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                        border_radius=20, bgcolor=PURPLE_LIGHT,
                        content=ft.Row(
                            [
                                ft.Text(s, color=PURPLE, size=12,
                                        weight=ft.FontWeight.W_600),
                                ft.Container(content=ft.Icon(ft.Icons.CLOSE_ROUNDED,
                                                             color=PURPLE, size=14),
                                             on_click=remover),
                            ],
                            spacing=6, tight=True,
                        ),
                    )
                )
            linha_skills.controls = chips or [
                ft.Text("Nenhuma habilidade adicionada ainda.", color=MUTED, size=12)
            ]

        async def adicionar_skill(ev=None):
            texto = (campo_skill.value or "").strip()
            if not texto:
                return
            if texto.lower() not in [s.lower() for s in rascunho_skills]:
                rascunho_skills.append(texto)
            campo_skill.value = ""
            desenhar_skills()
            page.update()
            await campo_skill.focus()

        campo_skill.on_submit = adicionar_skill

        def salvar(ev):
            novo_nome = (campo_nome.value or "").strip()
            if not novo_nome:
                campo_nome.error = "Informe seu nome."
                page.update()
                return
            campo_nome.error = None
            db.salvar_perfil_dev(
                id_usuario, novo_nome,
                (campo_bio.value or "").strip(),
                (campo_local.value or "").strip(),
                (campo_github.value or "").strip(),
                (campo_port.value or "").strip(),
                list(rascunho_skills),
            )
            perfil.update(
                nome=novo_nome,
                bio=(campo_bio.value or "").strip(),
                localizacao=(campo_local.value or "").strip(),
                github=(campo_github.value or "").strip(),
                portfolio=(campo_port.value or "").strip(),
                habilidades=list(rascunho_skills),
            )
            mostrar()
            avisar("Perfil atualizado!")

        desenhar_skills()
        entregues = len(tarefas_com("analise", "aceita"))
        aprovadas = len(tarefas_com("aceita"))
        perfil_completo = bool(perfil["bio"] and perfil["habilidades"])
        conquistas = [
            ("Primeiro projeto", "Pegue seu primeiro projeto",
             ft.Icons.ROCKET_LAUNCH_ROUNDED, len(tarefas) >= 1),
            ("Primeira entrega", "Envie sua primeira entrega",
             ft.Icons.UPLOAD_ROUNDED, entregues >= 1),
            ("Aprovado!", "Tenha uma entrega aprovada",
             ft.Icons.VERIFIED_ROUNDED, aprovadas >= 1),
            ("Nível 1", "Chegue a 1.000 XP",
             ft.Icons.MILITARY_TECH_ROUNDED, nivel >= 1),
            ("Top 5", "Entre nos 5 do ranking",
             ft.Icons.LEADERBOARD_ROUNDED, minha_posicao() <= 5),
            ("Perfil completo", "Preencha bio e habilidades",
             ft.Icons.PERSON_OUTLINE_ROUNDED, perfil_completo),
        ]

        def medalha(titulo, desc, icone, ok) -> ft.Container:
            cor = GOLD if ok else "#CFCBDD"
            return ft.Container(
                width=190, padding=14, bgcolor=WHITE,
                border=ft.Border.all(1, GOLD if ok else BORDER), border_radius=14,
                content=ft.Row(
                    [
                        ft.Container(content=ft.Icon(icone, color=cor, size=22),
                                     bgcolor=com_opacidade(cor, 0.14),
                                     padding=9, border_radius=11),
                        ft.Column(
                            [ft.Text(titulo, color=TEXT if ok else MUTED,
                                     size=12, weight=ft.FontWeight.BOLD),
                             ft.Text(desc, color=MUTED, size=10)],
                            spacing=3, expand=True,
                        ),
                    ],
                    spacing=10,
                ),
            )

        cartao_resumo = caixa(
            ft.Column(
                [
                    avatar(perfil["nome"], 84),
                    ft.Text(perfil["nome"], color=TEXT, size=18,
                            weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Text(usuario.get("email") or "Desenvolvedor",
                            color=MUTED, size=12),
                    selo(f"NÍVEL {nivel:02d} · {nome_do_nivel(nivel).upper()}", PURPLE),
                    ft.Divider(color=BORDER, height=12),
                    ft.Row([ft.Text("Pontuação", color=MUTED, size=12),
                            ft.Container(expand=True),
                            ft.Text(f"{fmt(xp)} XP", color=TEXT, size=12,
                                    weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Ranking", color=MUTED, size=12),
                            ft.Container(expand=True),
                            ft.Text(f"#{minha_posicao()}", color=TEXT, size=12,
                                    weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Tarefas pegas", color=MUTED, size=12),
                            ft.Container(expand=True),
                            ft.Text(str(len(tarefas)), color=TEXT, size=12,
                                    weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Entregas aprovadas", color=MUTED, size=12),
                            ft.Container(expand=True),
                            ft.Text(str(aprovadas), color=TEXT, size=12,
                                    weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Empresas seguidas", color=MUTED, size=12),
                            ft.Container(expand=True),
                            ft.Text(str(len(seguindo)), color=TEXT, size=12,
                                    weight=ft.FontWeight.BOLD)]),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10,
            ),
            padding=22, width=290,
        )

        formulario = caixa(
            ft.Column(
                [
                    ft.Text("Dados do perfil", color=TEXT, size=16,
                            weight=ft.FontWeight.BOLD),
                    campo_nome, campo_bio,
                    ft.Row([ft.Container(campo_local, expand=True)], spacing=12),
                    ft.Row([ft.Container(campo_github, expand=True),
                            ft.Container(campo_port, expand=True)], spacing=12),
                    ft.Text("Habilidades", color=MUTED, size=12,
                            weight=ft.FontWeight.W_600),
                    linha_skills,
                    ft.Row([campo_skill,
                            botao_primario("Adicionar", ft.Icons.ADD_ROUNDED,
                                           adicionar_skill)], spacing=10),
                    ft.Row([ft.Container(expand=True),
                            botao_primario("Salvar alterações",
                                           ft.Icons.SAVE_ROUNDED, salvar)]),
                ],
                spacing=14, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=22, expand=True,
        )

        return ft.Column(
            [
                cabecalho("Meu perfil",
                          "Mantenha seus dados atualizados para as empresas conhecerem seu trabalho."),
                ft.Row([cartao_resumo, formulario], spacing=18,
                       vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Text("Conquistas", color=TEXT, size=17, weight=ft.FontWeight.BOLD),
                ft.Row([medalha(*c) for c in conquistas],
                       wrap=True, spacing=12, run_spacing=12),
            ],
            spacing=20, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # ------------------------------------------------------------------
    # TELA: MENSAGENS
    # ------------------------------------------------------------------
    def bolha(m: dict) -> ft.Row:
        minha = m["de"] == "dev"
        largura = max(90, min(380, len(m["texto"]) * 7.2 + 34))
        return ft.Row(
            [
                ft.Container(
                    width=largura,
                    padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                    border_radius=14,
                    bgcolor=PURPLE if minha else "#F1EEF9",
                    content=ft.Column(
                        [
                            ft.Text(m["texto"], color=WHITE if minha else TEXT, size=13),
                            ft.Text(m["hora"], color="#D9CFFF" if minha else MUTED, size=10),
                        ],
                        spacing=4, horizontal_alignment=ft.CrossAxisAlignment.START,
                    ),
                )
            ],
            alignment=ft.MainAxisAlignment.END if minha else ft.MainAxisAlignment.START,
        )

    def view_mensagens() -> ft.Control:
        topo = cabecalho("Mensagens",
                         "Converse com as empresas que publicam projetos na DevSphere.")
        empresas_lista = db.buscar_empresas()
        nomes = [e["nome"] for e in empresas_lista]

        def ordem(n: str):
            return (-ultima_msg.get(n, 0), n)

        if ui["empresa_chat"] not in nomes:
            ui["empresa_chat"] = sorted(nomes, key=ordem)[0] if nomes else ""
        atual = ui["empresa_chat"]
        info = next((e for e in empresas_lista if e["nome"] == atual),
                    {"nome": atual, "area": "", "cidade": "", "nota": 0, "descricao": ""})
        rascunho = ui["rascunho"]
        ui["rascunho"] = ""
        altura = max(460, (page.height or 800) - 200)

        previas: dict[str, ft.Text] = {}
        lista_col = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

        def desenhar_lista(termo: str = ""):
            itens = []
            for n in sorted(nomes, key=ordem):
                if termo and termo.lower() not in n.lower():
                    continue
                emp = next((x for x in empresas_lista if x["nome"] == n), None)
                msgs = mensagens.get(n, [])
                previa = ft.Text(
                    msgs[-1]["texto"] if msgs else (emp["area"] if emp else ""),
                    color=MUTED, size=11, max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
                previas[n] = previa
                itens.append(
                    ft.Container(
                        padding=12, border_radius=12,
                        bgcolor=PURPLE_LIGHT if n == atual else None,
                        on_click=lambda ev, nn=n: abrir_chat(nn),
                        content=ft.Row(
                            [
                                avatar(n, 38),
                                ft.Column(
                                    [ft.Text(n, color=TEXT, size=13,
                                             weight=ft.FontWeight.W_600,
                                             max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                     previa],
                                    spacing=3, expand=True,
                                ),
                            ],
                            spacing=10,
                        ),
                    )
                )
            lista_col.controls = itens or [
                ft.Text("Nenhuma empresa encontrada.", color=MUTED, size=12)
            ]

        def ao_buscar_empresa(ev):
            desenhar_lista((ev.control.value or "").strip())
            page.update()

        desenhar_lista()
        lista = ft.Container(
            width=290, height=altura, padding=10, bgcolor=WHITE,
            border=ft.Border.all(1, BORDER), border_radius=16,
            content=ft.Column(
                [
                    ft.TextField(
                        hint_text="Buscar empresa...",
                        hint_style=ft.TextStyle(color="#A29DB4"),
                        prefix_icon=ft.Icon(ft.Icons.SEARCH, color=MUTED, size=18),
                        border_radius=12, border_color=BORDER,
                        focused_border_color=PURPLE, text_size=12,
                        content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                        on_change=ao_buscar_empresa,
                    ),
                    lista_col,
                ],
                spacing=8,
            ),
        )

        lista_msgs = ft.Column(spacing=8, expand=True,
                               scroll=ft.ScrollMode.AUTO, auto_scroll=True)

        def desenhar_msgs():
            msgs = mensagens.get(atual, [])
            lista_msgs.controls = [bolha(m) for m in msgs] or [
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=40),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(f"Envie a primeira mensagem para {atual}.",
                                    color=MUTED, size=12, text_align=ft.TextAlign.CENTER),
                )
            ]

        campo_msg = ft.TextField(
            hint_text="Escreva uma mensagem...",
            hint_style=ft.TextStyle(color="#A29DB4"),
            value=rascunho, border_radius=12, border_color=BORDER,
            focused_border_color=PURPLE, cursor_color=PURPLE,
            text_size=13, expand=True,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        )

        def usar_sugestao(texto: str):
            async def tratar(ev):
                campo_msg.value = texto
                page.update()
                await campo_msg.focus()
            return tratar

        sugestoes = [
            "Tenho uma dúvida sobre um projeto.",
            "Posso enviar uma proposta?",
            "Qual o prazo para resposta?",
        ]
        chips_rapidos = ft.Row(
            [chip_filtro(t, False, usar_sugestao(t)) for t in sugestoes],
            wrap=True, spacing=8, run_spacing=8,
            visible=not mensagens.get(atual),
        )

        async def enviar(ev):
            texto = (campo_msg.value or "").strip()
            if not texto:
                return
            id_dest = db.buscar_id_usuario_por_nome_empresa(atual)
            if id_dest:
                db.enviar_mensagem(id_usuario, id_dest, texto)
            ui["seq"] += 1
            ultima_msg[atual] = ui["seq"]
            mensagens.setdefault(atual, []).append({
                "de": "dev", "texto": texto,
                "hora": datetime.now().strftime("%H:%M"),
            })
            campo_msg.value = ""
            chips_rapidos.visible = False
            desenhar_msgs()
            if atual in previas:
                previas[atual].value = texto
            page.update()
            await campo_msg.focus()

        campo_msg.on_submit = enviar
        desenhar_msgs()

        abertos = len([p for p in catalogo if p["empresa"] == atual])
        painel = ft.Container(
            expand=True, height=altura, bgcolor=WHITE,
            border=ft.Border.all(1, BORDER), border_radius=16,
            content=ft.Column(
                [
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=18, vertical=14),
                        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
                        content=ft.Row(
                            [
                                avatar(atual, 40),
                                ft.Column(
                                    [ft.Text(atual, color=TEXT, size=14,
                                             weight=ft.FontWeight.BOLD),
                                     ft.Text(f"{info.get('area', '')} · "
                                             f"{abertos} projeto(s) aberto(s)",
                                             color=MUTED, size=11)],
                                    spacing=3, expand=True,
                                ),
                                link_acao(ft.Icons.FOLDER_OPEN_ROUNDED,
                                          "Ver projetos",
                                          lambda ev, n=atual: ver_projetos_da_empresa(n)),
                            ],
                            spacing=12,
                        ),
                    ),
                    ft.Container(expand=True,
                                 padding=ft.Padding.symmetric(horizontal=18, vertical=12),
                                 content=lista_msgs),
                    ft.Container(padding=ft.Padding.symmetric(horizontal=18),
                                 content=chips_rapidos),
                    ft.Container(
                        padding=ft.Padding.all(14),
                        border=ft.Border.only(top=ft.BorderSide(1, BORDER)),
                        content=ft.Row(
                            [
                                campo_msg,
                                ft.IconButton(
                                    icon=ft.Icons.SEND_ROUNDED,
                                    icon_color=WHITE, bgcolor=PURPLE,
                                    tooltip="Enviar", on_click=enviar,
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=12)),
                                ),
                            ],
                            spacing=10,
                        ),
                    ),
                ],
                spacing=0,
            ),
        )
        return ft.Column(
            [topo, ft.Row([lista, painel], spacing=16,
                          vertical_alignment=ft.CrossAxisAlignment.START)],
            spacing=18, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # ------------------------------------------------------------------
    # MENU LATERAL + NAVEGAÇÃO
    # ------------------------------------------------------------------
    NAV = [
        ("dashboard", ft.Icons.DASHBOARD_ROUNDED, "Dashboard"),
        ("projetos", ft.Icons.FOLDER_OPEN_ROUNDED, "Projetos"),
        ("tarefas", ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, "Minhas tarefas"),
        ("empresas", ft.Icons.BUSINESS_ROUNDED, "Empresas"),
        ("mensagens", ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED, "Mensagens"),
        ("ranking", ft.Icons.LEADERBOARD_ROUNDED, "Ranking"),
        ("perfil", ft.Icons.PERSON_OUTLINE_ROUNDED, "Meu perfil"),
    ]

    def item_menu(chave: str, icone, rotulo: str) -> ft.Container:
        selecionado = ui["tela"] == chave
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icone, size=20, color=WHITE if selecionado else "#B9B3D1"),
                    ft.Text(rotulo, size=14,
                            weight=ft.FontWeight.W_600 if selecionado else ft.FontWeight.NORMAL,
                            color=WHITE if selecionado else "#C9C4DE"),
                ],
                spacing=14,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=13),
            bgcolor="#5A2FC7" if selecionado else None,
            border_radius=12,
            margin=ft.Margin.only(bottom=5),
            on_click=lambda e: mostrar(chave),
        )

    def sair(e=None):
        if seletor in page.services:
            page.services.remove(seletor)
        if ao_sair:
            ao_sair()
        else:
            avisar("Abra pelo main.py para entrar e sair.")

    def conteudo_sidebar() -> ft.Control:
        iniciais = "".join(p[0] for p in perfil["nome"].split()[:2]).upper()
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(content=ft.Icon(ft.Icons.CODE_ROUNDED,
                                                     color=WHITE, size=24),
                                     bgcolor=PURPLE, padding=10, border_radius=13),
                        ft.Column(
                            [ft.Text("DevSphere", color=WHITE, size=20,
                                     weight=ft.FontWeight.BOLD),
                             ft.Text("DEV COMMUNITY", color="#A9A0C9", size=9,
                                     weight=ft.FontWeight.BOLD)],
                            spacing=2,
                        ),
                    ],
                    spacing=10,
                ),
                ft.Container(height=28),
                ft.Text("MENU PRINCIPAL", color="#8F84B8", size=10,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=8),
                *[item_menu(*n) for n in NAV],
                ft.Container(expand=True),
                ft.Container(
                    padding=15, bgcolor="#34245B", border_radius=14,
                    on_click=lambda e: mostrar("projetos"),
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED,
                                    color="#C7B4FF", size=25),
                            ft.Text("Suba de nível!", color=WHITE, size=13,
                                    weight=ft.FontWeight.BOLD),
                            ft.Text("Complete projetos e conquiste XP para evoluir.",
                                    color="#C4BBDD", size=11),
                            ft.Container(height=3),
                            ft.Text("Ver projetos  →", color="#D6C9FF", size=12,
                                    weight=ft.FontWeight.BOLD),
                        ],
                        spacing=8,
                    ),
                ),
                ft.Container(height=8),
                ft.Row(
                    [
                        ft.CircleAvatar(
                            content=ft.Text(iniciais, color=WHITE,
                                            weight=ft.FontWeight.BOLD),
                            bgcolor="#8B5CF6", radius=20,
                        ),
                        ft.Column(
                            [ft.Text(perfil["nome"], color=WHITE, size=12,
                                     weight=ft.FontWeight.BOLD,
                                     no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                             ft.Text("Desenvolvedor", color="#A9A0C9", size=10)],
                            spacing=3, expand=True,
                        ),
                        ft.IconButton(icon=ft.Icons.LOGOUT_ROUNDED, tooltip="Sair",
                                      icon_color="#A9A0C9", icon_size=18, on_click=sair),
                    ],
                    spacing=9,
                ),
            ],
            spacing=0, expand=True,
        )

    sidebar = ft.Container(width=245, bgcolor="#25164A",
                           padding=ft.Padding.symmetric(horizontal=18, vertical=24))
    area = ft.Container(expand=True, padding=ft.Padding.all(28))

    def construir():
        construtores = {
            "dashboard": view_dashboard, "projetos": view_projetos,
            "tarefas": view_tarefas, "empresas": view_empresas,
            "mensagens": view_mensagens, "ranking": view_ranking,
            "perfil": view_perfil,
        }
        sidebar.content = conteudo_sidebar()
        area.content = construtores[ui["tela"]]()

    def mostrar(tela: str | None = None):
        if tela:
            ui["tela"] = tela
        construir()
        page.update()

    def ao_redimensionar(e=None):
        if ui["tela"] == "mensagens":
            mostrar()

    page.on_resize = ao_redimensionar
    construir()
    page.add(
        ft.Row(
            [sidebar, area], spacing=0, expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )


if __name__ == "__main__":
    ft.run(dashboard)