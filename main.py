"""
DevSphere - arquivo principal
Python + Flet (>= 1.0)

Arquivos do projeto:
    main.py                       <- rode este (login/cadastro + liga as telas)
    entrar_desenvolvedor.py       <- dashboard do desenvolvedor (conta já existente)
    criarconta_desenvolvedor.py   <- dashboard zerado (conta de desenvolvedor recém-criada)
    criarconta_empresa.py         <- painel da empresa (tasks, mensagens, financeiro)

Fluxo:
    Login como desenvolvedor (e-mail/senha, GitHub ou Google) --> entrar_desenvolvedor
    Login como empresa                                        --> criarconta_empresa
    Cadastro como desenvolvedor                               --> criarconta_desenvolvedor
    Cadastro como empresa                                     --> criarconta_empresa

Instalação:   pip install -U flet
Execução:     python main.py
"""

import base64
import re

import flet as ft

from database import autenticar_usuario, registrar_usuario

import criarconta_desenvolvedor
import criarconta_empresa
import entrar_desenvolvedor

# ===========================================================================
# CORES
# ===========================================================================
# Roxo predominante
ROXO_NOITE = "#1A0B2E"
ROXO_PROFUNDO = "#2E1065"
ROXO_ESCURO = "#4C1D95"
ROXO = "#7C3AED"
ROXO_CLARO = "#A78BFA"
LAVANDA = "#F3EEFF"

# Neutros
BRANCO = "#FFFFFF"
TEXTO = "#1F1235"
TEXTO_SUAVE = "#6B5F85"
BORDA = "#D9CFF0"
BORDA_CARTAO = "#E8E0F7"

# Status
ERRO = "#DC2626"
VERDE = "#15803D"
VERDE_FUNDO = "#DCFCE7"
AMBAR = "#B45309"
AMBAR_FUNDO = "#FEF3C7"
VERMELHO = "#B91C1C"
VERMELHO_FUNDO = "#FEE2E2"


# ===========================================================================
# ÍCONES DO GITHUB E DO GOOGLE (SVG embutido, não precisa de arquivos)
# ===========================================================================
def _svg_base64(svg: str) -> str:
    return base64.b64encode(svg.encode()).decode()


ICONE_GITHUB = _svg_base64(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="#1F1235"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'
)

ICONE_GOOGLE = _svg_base64(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>'
)


# ===========================================================================
# DADOS (AINDA SEM BANCO DE DADOS)
# Quando o SQLite estiver pronto, é só trocar o corpo destas funções.
# Devem devolver {"nome", "email", "tipo"} ou levantar ValueError com a
# mensagem que será mostrada na tela.
# ===========================================================================
# Cadastro e autenticação reais via SQLite (database.py).


def autenticar_com_github() -> dict:
    raise ValueError("O login OAuth do GitHub ainda precisa ser configurado.")


def autenticar_com_google() -> dict:
    raise ValueError("O login OAuth do Google ainda precisa ser configurado.")


# ===========================================================================
# COMPONENTES VISUAIS COMPARTILHADOS
# ===========================================================================
def logo(cor_texto: str = BRANCO, tamanho: int = 30) -> ft.Row:
    """Esfera roxa + nome do app."""
    d = tamanho + 14
    return ft.Row(
        tight=True,
        spacing=12,
        controls=[
            ft.Container(
                width=d,
                height=d,
                border_radius=d / 2,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment.TOP_LEFT,
                    end=ft.Alignment.BOTTOM_RIGHT,
                    colors=[ROXO_CLARO, ROXO],
                ),
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.HUB, color=BRANCO, size=tamanho - 4),
            ),
            ft.Text("DevSphere", size=tamanho, weight=ft.FontWeight.W_800, color=cor_texto),
        ],
    )


def circulo_decorativo(tam: int, **posicao) -> ft.Container:
    """Círculo só com contorno, usado como detalhe nos painéis roxos."""
    return ft.Container(
        width=tam,
        height=tam,
        border_radius=tam / 2,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.10, BRANCO)),
        **posicao,
    )


# ===========================================================================
# TELA DE LOGIN / CADASTRO
# ===========================================================================
LARGURA_MINIMA_PAINEL = 900  # abaixo disso o painel roxo da esquerda some
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Cores do "editor de código" decorativo
COD_PALAVRA = "#C4B5FD"
COD_FUNCAO = "#7DD3FC"
COD_TEXTO = "#E9E3F7"
COD_STRING = "#86EFAC"
COD_COMENT = "#8B7FB0"


# ---------------------------------------------------------------------------
# Painel decorativo da esquerda
# ---------------------------------------------------------------------------
def linha_codigo(*partes, recuo: int = 0) -> ft.Text:
    """Uma linha do editor decorativo. Cada parte é (texto, cor)."""
    return ft.Text(
        spans=[
            ft.TextSpan("    " * recuo),
            *[ft.TextSpan(t, style=ft.TextStyle(color=c)) for t, c in partes],
        ],
        font_family="Courier New",
        size=13,
        color=COD_TEXTO,
    )


def janela_de_codigo() -> ft.Container:
    bolinha = lambda cor: ft.Container(width=11, height=11, border_radius=6, bgcolor=cor)
    return ft.Container(
        bgcolor=ROXO_NOITE,
        border_radius=14,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.18, BRANCO)),
        padding=ft.Padding.all(18),
        content=ft.Column(
            spacing=6,
            tight=True,
            controls=[
                ft.Row(spacing=7, controls=[bolinha("#F87171"), bolinha("#FBBF24"), bolinha("#4ADE80")]),
                ft.Container(height=8),
                linha_codigo(("# conectando talentos e projetos", COD_COMENT)),
                linha_codigo(("class ", COD_PALAVRA), ("DevSphere", COD_FUNCAO), (":", COD_TEXTO)),
                linha_codigo(("def ", COD_PALAVRA), ("conectar", COD_FUNCAO), ("(dev, empresa):", COD_TEXTO), recuo=1),
                linha_codigo(("if ", COD_PALAVRA), ("dev.skills & empresa.vaga:", COD_TEXTO), recuo=2),
                linha_codigo(("return ", COD_PALAVRA), ('"match!"', COD_STRING), recuo=3),
            ],
        ),
    )


def etiqueta_tecnologia(icone, texto: str) -> ft.Container:
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
        border_radius=20,
        bgcolor=ft.Colors.with_opacity(0.12, BRANCO),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.2, BRANCO)),
        content=ft.Row(
            tight=True,
            spacing=6,
            controls=[
                ft.Icon(icone, size=15, color=ROXO_CLARO),
                ft.Text(texto, size=12, color=BRANCO),
            ],
        ),
    )


def painel_lateral() -> ft.Container:
    conteudo = ft.Container(
        padding=ft.Padding.all(48),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=26,
            controls=[
                logo(),
                ft.Text(
                    "Onde desenvolvedores\ne empresas se encontram.",
                    size=30,
                    weight=ft.FontWeight.W_700,
                    color=BRANCO,
                ),
                ft.Text(
                    "Mostre seus projetos, descubra talentos e construa a próxima grande solução.",
                    size=15,
                    color=ROXO_CLARO,
                ),
                janela_de_codigo(),
                ft.Row(
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        etiqueta_tecnologia(ft.Icons.TERMINAL, "Python"),
                        etiqueta_tecnologia(ft.Icons.DATA_OBJECT, "APIs"),
                        etiqueta_tecnologia(ft.Icons.MERGE_TYPE, "Git"),
                        etiqueta_tecnologia(ft.Icons.BUG_REPORT_OUTLINED, "Debug"),
                    ],
                ),
            ],
        ),
    )
    return ft.Container(
        expand=5,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=[ROXO_NOITE, ROXO_PROFUNDO, ROXO_ESCURO],
        ),
        content=ft.Stack(
            controls=[
                circulo_decorativo(420, right=-140, top=-120),
                circulo_decorativo(260, right=-60, top=-40),
                circulo_decorativo(360, left=-150, bottom=-150),
                conteudo,
            ]
        ),
    )


# ---------------------------------------------------------------------------
# Tela
# ---------------------------------------------------------------------------
def tela_login(page: ft.Page, ao_entrar, ao_cadastrar=None) -> ft.Control:
    """Monta a tela.

    `ao_entrar(usuario)`    -> chamado quando o LOGIN dá certo (e-mail/senha, GitHub ou Google).
    `ao_cadastrar(usuario)` -> chamado quando uma conta (desenvolvedor ou empresa) é criada.
                               Sem esse callback, o cadastro volta para a aba Entrar.
    """
    estado = {"modo": "login", "tipo": None}

    # Campos criados uma vez e reaproveitados ao trocar entre Entrar/Criar conta
    def campo(rotulo, icone, **kw) -> ft.TextField:
        return ft.TextField(
            label=rotulo,
            prefix_icon=ft.Icon(icone, color=TEXTO_SUAVE, size=20),
            border_radius=10,
            border_color=BORDA,
            focused_border_color=ROXO,
            cursor_color=ROXO,
            label_style=ft.TextStyle(color=TEXTO_SUAVE),
            text_style=ft.TextStyle(color=TEXTO),
            on_submit=lambda e: enviar(),
            **kw,
        )

    campo_nome = campo("Nome", ft.Icons.PERSON_OUTLINE)
    campo_email = campo("E-mail", ft.Icons.EMAIL_OUTLINED, keyboard_type=ft.KeyboardType.EMAIL)
    campo_senha = campo("Senha", ft.Icons.LOCK_OUTLINE, password=True, can_reveal_password=True)
    texto_erro = ft.Text("", color=ERRO, size=13, visible=False)

    # -- ações ---------------------------------------------------------------
    def mostrar_erro(msg: str, erro: bool = True):
        """Mostra uma mensagem acima do botão (vermelha = erro, verde = sucesso)."""
        texto_erro.value = msg
        texto_erro.color = ERRO if erro else VERDE
        texto_erro.visible = bool(msg)
        page.update()

    def conta_criada():
        """Sem tela para abrir depois do cadastro: volta para o login."""
        estado["modo"] = "login"
        estado["tipo"] = None
        campo_nome.value = ""
        campo_senha.value = ""
        for c in (campo_nome, campo_email, campo_senha):
            c.error = None
        desenhar_formulario()
        mostrar_erro("Conta criada com sucesso! Entre com seu e-mail e senha.", erro=False)

    def trocar_modo(modo: str):
        estado["modo"] = modo
        for c in (campo_nome, campo_email, campo_senha):
            c.error = None
        texto_erro.visible = False
        desenhar_formulario()

    def escolher_tipo(tipo: str):
        estado["tipo"] = tipo
        texto_erro.visible = False
        desenhar_formulario()

    def enviar():
        nome = (campo_nome.value or "").strip()
        email = (campo_email.value or "").strip()
        senha = campo_senha.value or ""
        criando = estado["modo"] == "cadastro"

        for c in (campo_nome, campo_email, campo_senha):
            c.error = None

        problema = False
        if criando and not nome:
            campo_nome.error = "Informe seu nome."
            problema = True
        if not EMAIL_REGEX.match(email):
            campo_email.error = "Informe um e-mail válido."
            problema = True
        if not senha:
            campo_senha.error = "Informe a senha."
            problema = True
        elif criando and len(senha) < 8:
            campo_senha.error = "Use pelo menos 8 caracteres."
            problema = True
        if criando and not estado["tipo"]:
            texto_erro.value = "Escolha se você é desenvolvedor ou empresa."
            texto_erro.color = ERRO
            texto_erro.visible = True
            problema = True
        if problema:
            page.update()
            return

        try:
            if criando:
                usuario = registrar_usuario(nome, email, senha, estado["tipo"])
            else:
                usuario = autenticar_usuario(email, senha)
        except ValueError as erro:
            mostrar_erro(str(erro))
            return

        if not criando:
            ao_entrar(usuario)
        elif ao_cadastrar:
            ao_cadastrar(usuario)
        else:
            conta_criada()

    def entrar_social(funcao):
        try:
            usuario = funcao()
        except ValueError as erro:
            mostrar_erro(str(erro))
            return
        ao_entrar(usuario)

    # -- widgets do formulário -----------------------------------------------
    def aba(rotulo: str, modo: str) -> ft.Container:
        ativa = estado["modo"] == modo
        return ft.Container(
            expand=True,
            padding=ft.Padding.symmetric(vertical=11),
            border_radius=9,
            alignment=ft.Alignment.CENTER,
            bgcolor=BRANCO if ativa else None,
            shadow=(
                ft.BoxShadow(blur_radius=6, color=ft.Colors.with_opacity(0.15, ROXO), offset=ft.Offset(0, 2))
                if ativa
                else None
            ),
            on_click=lambda e: trocar_modo(modo),
            content=ft.Text(rotulo, weight=ft.FontWeight.W_600, color=ROXO if ativa else TEXTO_SUAVE),
        )

    def cartao_tipo(valor: str, icone, titulo: str, descricao: str) -> ft.Container:
        marcado = estado["tipo"] == valor
        return ft.Container(
            expand=True,
            padding=ft.Padding.all(14),
            border_radius=12,
            border=ft.Border.all(2 if marcado else 1, ROXO if marcado else BORDA),
            bgcolor=LAVANDA if marcado else BRANCO,
            on_click=lambda e: escolher_tipo(valor),
            content=ft.Column(
                spacing=4,
                tight=True,
                controls=[
                    ft.Icon(icone, color=ROXO if marcado else TEXTO_SUAVE, size=26),
                    ft.Text(titulo, weight=ft.FontWeight.W_700, color=TEXTO),
                    ft.Text(descricao, size=12, color=TEXTO_SUAVE),
                ],
            ),
        )

    def botao_principal(texto: str) -> ft.Button:
        return ft.Button(
            content=ft.Text(texto, size=16, weight=ft.FontWeight.W_600, color=BRANCO),
            height=50,
            bgcolor=ROXO,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=lambda e: enviar(),
        )

    def botao_social(icone: str, texto: str, funcao) -> ft.OutlinedButton:
        return ft.OutlinedButton(
            expand=True,
            height=48,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                side=ft.BorderSide(1, BORDA),
                padding=ft.Padding.symmetric(horizontal=6),
            ),
            on_click=lambda e: entrar_social(funcao),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Image(src=icone, width=20, height=20),
                    ft.Text(texto, size=13, color=TEXTO, weight=ft.FontWeight.W_600),
                ],
            ),
        )

    divisor_ou = ft.Row(
        spacing=12,
        controls=[
            ft.Divider(color=BORDA, height=1, expand=True),
            ft.Text("ou", color=TEXTO_SUAVE, size=13),
            ft.Divider(color=BORDA, height=1, expand=True),
        ],
    )

    marca_compacta = ft.Container(
        visible=False,
        content=logo(cor_texto=ROXO_PROFUNDO, tamanho=26),
        margin=ft.Margin.only(bottom=8),
    )

    area_formulario = ft.Column(
        spacing=16,
        tight=True,
        width=420,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    def desenhar_formulario():
        login = estado["modo"] == "login"
        itens = [
            marca_compacta,
            ft.Text(
                "Bem-vindo de volta" if login else "Crie sua conta",
                size=28,
                weight=ft.FontWeight.W_800,
                color=TEXTO,
            ),
            ft.Text(
                "Entre para continuar na DevSphere." if login else "Leva menos de um minuto para começar.",
                size=14,
                color=TEXTO_SUAVE,
            ),
            ft.Container(
                bgcolor=LAVANDA,
                border_radius=12,
                padding=ft.Padding.all(4),
                content=ft.Row(spacing=4, controls=[aba("Entrar", "login"), aba("Criar conta", "cadastro")]),
            ),
        ]
        if not login:
            itens.append(campo_nome)
        itens += [campo_email, campo_senha]

        if not login:
            itens += [
                ft.Text("Eu sou", size=13, weight=ft.FontWeight.W_600, color=TEXTO),
                ft.Row(
                    spacing=12,
                    controls=[
                        cartao_tipo("desenvolvedor", ft.Icons.CODE, "Desenvolvedor", "Quero mostrar meu trabalho"),
                        cartao_tipo("empresa", ft.Icons.BUSINESS_CENTER_OUTLINED, "Empresa", "Quero encontrar talentos"),
                    ],
                ),
            ]

        itens.append(texto_erro)
        itens.append(botao_principal("Entrar" if login else "Criar conta"))

        if login:
            itens += [
                divisor_ou,
                ft.Row(
                    spacing=12,
                    controls=[
                        botao_social(ICONE_GITHUB, "GitHub", autenticar_com_github),
                        botao_social(ICONE_GOOGLE, "Google", autenticar_com_google),
                    ],
                ),
            ]
        area_formulario.controls = itens

    desenhar_formulario()

    # -- composição ------------------------------------------------------------
    painel = painel_lateral()
    lado_formulario = ft.Container(
        expand=4,
        bgcolor=BRANCO,
        padding=ft.Padding.symmetric(horizontal=24, vertical=24),
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[area_formulario],
        ),
    )

    def ajustar_layout(e=None, atualizar: bool = True):
        largo = (page.width or 1200) >= LARGURA_MINIMA_PAINEL
        painel.visible = largo
        marca_compacta.visible = not largo
        area_formulario.width = 420 if largo else max(260, min(420, (page.width or 420) - 48))
        if atualizar:
            page.update()

    page.on_resize = ajustar_layout
    ajustar_layout(atualizar=False)

    return ft.Row(
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[painel, lado_formulario],
    )


# ===========================================================================
# APP
# ===========================================================================
def main(page: ft.Page):
    page.theme = ft.Theme(color_scheme_seed=ROXO)

    def configurar_pagina_do_login():
        """A tela do dashboard altera o título, a cor de fundo e o tamanho mínimo da
        janela. Ao voltar para o login, restauramos tudo."""
        page.title = "DevSphere"
        page.bgcolor = BRANCO
        page.padding = 0
        page.spacing = 0
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 1280
        page.window.height = 800
        page.window.min_width = 380
        page.window.min_height = 600

    def ir_para_login():
        page.on_resize = None
        page.controls.clear()
        configurar_pagina_do_login()
        page.add(tela_login(page, ao_entrar=ir_para_painel, ao_cadastrar=ir_para_conta_nova))
        page.update()

    def ir_para_conta_nova(usuario: dict):
        """Chamado quando uma conta é criada: abre a tela inicial do tipo de conta."""
        page.on_resize = None
        page.controls.clear()
        if usuario.get("tipo") == "empresa":
            criarconta_empresa.dashboard(page, usuario, ao_sair=ir_para_login)
        else:
            criarconta_desenvolvedor.dashboard(page, usuario, ao_sair=ir_para_login)
        page.update()

    def ir_para_painel(usuario: dict):
        """Chamado quando o login dá certo."""
        page.on_resize = None
        page.controls.clear()
        if usuario.get("tipo") == "empresa":
            criarconta_empresa.dashboard(page, usuario, ao_sair=ir_para_login)
        else:
            entrar_desenvolvedor.dashboard(page, usuario, ao_sair=ir_para_login)
        page.update()

    ir_para_login()


if __name__ == "__main__":
    ft.run(main)