"""DevSphere - Painel da empresa (INTEGRADO COM SQLITE)."""
import shutil
from datetime import date, datetime
from pathlib import Path
import flet as ft
import database as db

PASTA_UPLOADS = Path(__file__).parent / "uploads"


def dashboard(page: ft.Page, usuario=None, ao_sair=None):
    usuario = usuario or {"nome": "Empresa", "email": "", "tipo": "empresa"}
    nome = usuario.get("nome") or "Empresa"
    iniciais_empresa = " ".join(p[0] for p in nome.split()[:2]).upper()

    page.title = "DevSphere | Painel da empresa"
    page.bgcolor = "#F7F6FC"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.min_width = 900
    page.window.min_height = 620

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

    id_usuario = usuario.get("id_usuario")
    id_empresa = usuario.get("id_empresa")

    # Carregar tasks do banco (função reutilizável: a tela é recarregada a cada mudança)
    tasks = []

    def carregar_tasks():
        tasks[:] = [{
            "id": t["id"], "titulo": t["titulo"], "descricao": t["descricao"],
            "categoria": t["categoria"], "valor": t["valor"], "xp": t.get("xp") or 0,
            "prazo": t["prazo"], "arquivos": t.get("arquivos", []), "dev": t.get("dev"),
            "id_dev": t.get("id_dev"),
            "progresso": t.get("progresso") or 0,   # LEFT JOIN: task sem dev vem com None
            "status": t.get("status"), "status_proposta": t.get("status_proposta"),
            "pago": t.get("pago", False), "pago_em": t.get("pago_em"),
        } for t in db.buscar_tasks_da_empresa(id_empresa)]

    carregar_tasks()

    def id_dev_do_nome(nm):
        """Prefere o id_dev que já está na task (nomes de devs podem se repetir)."""
        return next((t["id_dev"] for t in tasks if t["dev"] == nm and t["id_dev"]), None) \
            or db.buscar_id_dev_por_nome_dev(nm)

    # Carregar mensagens
    mensagens: dict[str, list[dict]] = {}
    devs_db = db.buscar_devs_da_empresa(id_empresa)
    for dd in devs_db:
        du = db.buscar_id_usuario_por_nome_dev(dd["dev"])
        if du:
            msgs = db.buscar_mensagens(id_usuario, du)
            if msgs:
                mensagens[dd["dev"]] = [
                    {"de": "empresa" if m["direcao"] == "eu" else "dev",
                     "texto": m["texto"], "hora": m["hora"]} for m in msgs
                ]

    # Carregar avaliações
    avaliacoes: dict[str, dict] = {}
    for dd in devs_db:
        ddev = id_dev_do_nome(dd["dev"])
        if ddev:
            av = db.buscar_avaliacao(id_empresa, ddev)
            if av:
                avaliacoes[dd["dev"]] = {"nota": av["nota"], "comentario": av["comentario"]}

    ui = {"tela": "dashboard", "dev": None, "filtro": "todas",
          "prox_id": max([t["id"] for t in tasks] + [0]) + 1}
    seletor = ft.FilePicker()
    page.services.append(seletor)

    # ---------- AUXILIARES ----------
    def brl(v): return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    def tamanho_legivel(n):
        if not n: return ""
        return f"{n/1_000_000:.1f} MB".replace(".", ",") if n >= 1_000_000 else f"{max(1, round(n/1000))} KB"
    def situacao(t):
        if t["dev"] is None: return "aberta"
        if t.get("status") == "concluida" or t.get("status_proposta") == "aceita": return "concluida"
        if t.get("status_proposta") == "analise": return "analise"   # entregue, esperando a sua aprovação
        return "andamento"
    SITUACOES = {"aberta": ("AGUARDANDO DEV", ORANGE), "andamento": ("EM ANDAMENTO", BLUE), "analise": ("EM ANÁLISE", PURPLE), "concluida": ("CONCLUÍDA", GREEN)}
    def devs_unicos():
        v = []
        for t in tasks:
            if t["dev"] and t["dev"] not in v: v.append(t["dev"])
        return v
    def tasks_do_dev(d): return [t for t in tasks if t["dev"] == d]
    def avisar(m): page.show_dialog(ft.SnackBar(ft.Text(m)))
    def com_opacidade(c, op=0.09): return ft.Colors.with_opacity(op, c)

    # ---------- PEÇAS VISUAIS ----------
    def avatar(t, s=38):
        ini = "".join(p[0] for p in t.split()[:2]).upper()
        return ft.CircleAvatar(content=ft.Text(ini, color=WHITE, weight=ft.FontWeight.BOLD, size=max(10, s//3)), bgcolor="#8B5CF6", radius=s/2)
    def selo(t, c): return ft.Container(content=ft.Text(t, color=c, size=10, weight=ft.FontWeight.BOLD), bgcolor=com_opacidade(c), padding=ft.Padding.symmetric(horizontal=9, vertical=5), border_radius=20)
    def caixa(c, **kw): return ft.Container(padding=kw.pop("padding", 18), bgcolor=WHITE, border=ft.Border.all(1, BORDER), border_radius=16, content=c, **kw)
    def botao_primario(t, ic, oc): return ft.Container(padding=ft.Padding.symmetric(horizontal=18, vertical=12), bgcolor=PURPLE, border_radius=12, on_click=oc, content=ft.Row([ft.Icon(ic, color=WHITE, size=18), ft.Text(t, color=WHITE, size=13, weight=ft.FontWeight.W_600)], spacing=8, tight=True))
    def link_acao(ic, t, oc, cor=PURPLE): return ft.Container(on_click=oc, padding=ft.Padding.symmetric(horizontal=8, vertical=4), content=ft.Row([ft.Icon(ic, color=cor, size=15), ft.Text(t, color=cor, size=12, weight=ft.FontWeight.W_600)], spacing=5, tight=True))
    def estrelas_fixas(n, s=18): return ft.Row([ft.Icon(ft.Icons.STAR_ROUNDED if i <= n else ft.Icons.STAR_BORDER_ROUNDED, color=GOLD if i <= n else "#CFCBDD", size=s) for i in range(1, 6)], spacing=1, tight=True)
    def estado_vazio(ic, t, x, acao=None):
        itens = [ft.Container(content=ft.Icon(ic, color=PURPLE, size=26), bgcolor=PURPLE_LIGHT, padding=14, border_radius=30), ft.Text(t, color=TEXT, size=13, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), ft.Text(x, color=MUTED, size=11, text_align=ft.TextAlign.CENTER)]
        if acao: itens += [ft.Container(height=4), acao]
        return ft.Row([ft.Column(itens, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8, expand=True)])
    def cabecalho(t, x, acao=None):
        itens = [ft.Column([ft.Text(t, size=26, color=TEXT, weight=ft.FontWeight.BOLD), ft.Text(x, color=MUTED, size=13)], spacing=5, expand=True)]
        if acao: itens.append(acao)
        return ft.Row(itens, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
    def stat_card(ic, t, v, x, c, tv=27): return ft.Container(expand=True, padding=20, bgcolor=WHITE, border=ft.Border.all(1, BORDER), border_radius=18, content=ft.Column([ft.Container(content=ft.Icon(ic, color=c, size=21), bgcolor=com_opacidade(c), padding=11, border_radius=12), ft.Text(t, color=MUTED, size=13), ft.Container(content=ft.Text(v, color=TEXT, size=tv, weight=ft.FontWeight.BOLD), height=34, alignment=ft.Alignment.CENTER_LEFT), ft.Text(x, color=MUTED, size=12, weight=ft.FontWeight.W_500)], spacing=9))
    def chip_filtro(r, v):
        ativo = ui["filtro"] == v
        def clicar(e): ui["filtro"] = v; mostrar()
        return ft.Container(padding=ft.Padding.symmetric(horizontal=14, vertical=8), border_radius=20, bgcolor=PURPLE if ativo else WHITE, border=ft.Border.all(1, PURPLE if ativo else BORDER), on_click=clicar, content=ft.Text(r, size=12, weight=ft.FontWeight.W_600, color=WHITE if ativo else MUTED))

    # ---------- ARQUIVOS ----------
    def guardar_arquivo(a, tid):
        c = a.get("caminho")
        if not c: return
        try:
            d = PASTA_UPLOADS / f"task_{tid}"; d.mkdir(parents=True, exist_ok=True); shutil.copy2(c, d / a["nome"])
        except OSError: pass
    async def escolher_arquivos():
        es = await seletor.pick_files(dialog_title="Anexar arquivos", allow_multiple=True)
        return [{"nome": f.name, "tamanho": f.size, "caminho": f.path} for f in (es or [])]
    def anexar_em_task(t):
        async def tratar(e):
            ns = await escolher_arquivos()
            if not ns: return
            novos = []
            for a in ns:
                guardar_arquivo(a, t["id"]); novos.append({"nome": a["nome"], "tamanho": a["tamanho"]})
            db.adicionar_arquivos_task(t["id"], novos, id_empresa)
            mostrar(); avisar(f"{len(ns)} arquivo(s) anexado(s).")
        return tratar

    # ---------- CARTÃO DE TASK ----------
    def task_card(t, detalhado=False):
        cor, ic = CATEGORIAS[t["categoria"]]; sit = situacao(t); ts, cs = SITUACOES[sit]
        linha_dev = (ft.Row([avatar(t["dev"], 26), ft.Text("Pegou:", color=MUTED, size=12), ft.Text(t["dev"], color=TEXT, size=12, weight=ft.FontWeight.BOLD)], spacing=8)
            if t["dev"] else ft.Row([ft.Icon(ft.Icons.HOURGLASS_EMPTY_ROUNDED, color=ORANGE, size=16), ft.Text("Aguardando um desenvolvedor pegar esta task", color=ORANGE, size=12, weight=ft.FontWeight.W_500)], spacing=6))
        corpo = [ft.Row([ft.Container(content=ft.Icon(ic, color=cor, size=20), bgcolor=com_opacidade(cor), padding=10, border_radius=11), ft.Column([ft.Text(t["titulo"], color=TEXT, weight=ft.FontWeight.BOLD, size=14), ft.Text(f"Prazo: {t['prazo']}  ·  {brl(t['valor'])}", color=MUTED, size=12)], spacing=3, expand=True), selo(t["categoria"], cor), selo(ts, cs)], spacing=10)]
        if detalhado and t["descricao"]: corpo.append(ft.Text(t["descricao"], color=MUTED, size=12))
        corpo.append(linha_dev)
        corpo.append(ft.Row([ft.Text("Progresso", color=MUTED, size=12), ft.Container(expand=True), ft.Text(f"{t['progresso']}%", color=TEXT, size=12, weight=ft.FontWeight.BOLD)]))
        corpo.append(ft.ProgressBar(value=t["progresso"]/100, color=cs if sit == "concluida" else cor, bgcolor="#F0EDF7", height=6, border_radius=8))
        if detalhado and t["arquivos"]:
            corpo.append(ft.Row([ft.Container(padding=ft.Padding.symmetric(horizontal=10, vertical=6), bgcolor="#F7F6FC", border=ft.Border.all(1, BORDER), border_radius=10, content=ft.Row([ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED, color=MUTED, size=14), ft.Text(f"{a['nome']} {('· '+tamanho_legivel(a['tamanho'])) if a['tamanho'] else ''}", color=TEXT, size=11)], spacing=6, tight=True)) for a in t["arquivos"]], wrap=True, spacing=8, run_spacing=8))
        n = len(t["arquivos"])
        acoes = [ft.Icon(ft.Icons.ATTACH_FILE_ROUNDED, color=MUTED, size=14), ft.Text(f"{n} arquivo(s)" if n else "Sem arquivos", color=MUTED, size=11), ft.Container(expand=True), link_acao(ft.Icons.UPLOAD_FILE_ROUNDED, "Anexar", anexar_em_task(t))]
        if t["dev"]: acoes.append(link_acao(ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED, "Mensagem", lambda e, d=t["dev"]: abrir_chat(d)))
        corpo.append(ft.Row(acoes, spacing=5))
        return ft.Container(padding=18, bgcolor=WHITE, border=ft.Border.all(1, BORDER), border_radius=16, content=ft.Column(corpo, spacing=12))

    # ---------- NOVA TASK ----------
    def abrir_nova_task(e=None):
        def limpar_erro(ev):
            if ev.control.error: ev.control.error = None; page.update()
        def campo(r, **kw): return ft.TextField(label=r, on_change=limpar_erro, border_radius=10, border_color=BORDER, focused_border_color=PURPLE, cursor_color=PURPLE, text_size=13, label_style=ft.TextStyle(color=MUTED), **kw)
        ct = campo("Título da task"); cd = campo("Descrição", multiline=True, min_lines=3, max_lines=5)
        cv = campo("Valor (R$)", prefix="R$ ", keyboard_type=ft.KeyboardType.NUMBER, input_filter=ft.InputFilter(regex_string=r"[0-9.,]", allow=True, replacement_string=""), expand=True)
        cp = campo("Prazo (dd/mm/aaaa)", expand=True)
        cx = campo("XP para o dev (opcional)", hint_text="Automático: 1 XP a cada R$ 10", keyboard_type=ft.KeyboardType.NUMBER, input_filter=ft.InputFilter(regex_string=r"[0-9]", allow=True, replacement_string=""))
        cat = {"valor": "BACK-END"}; anexos = []; lc = ft.Row(wrap=True, spacing=8, run_spacing=8); la = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO); te = ft.Text("", color=RED, size=12, visible=False)
        def desenhar_cats():
            itens = []
            for nc, (c, _) in CATEGORIAS.items():
                m = cat["valor"] == nc
                def es(ev, n=nc): cat["valor"] = n; desenhar_cats(); page.update()
                itens.append(ft.Container(padding=ft.Padding.symmetric(horizontal=12, vertical=7), border_radius=20, bgcolor=c if m else WHITE, border=ft.Border.all(1, c if m else BORDER), on_click=es, content=ft.Text(nc, size=11, weight=ft.FontWeight.BOLD, color=WHITE if m else MUTED)))
            lc.controls = itens
        def desenhar_anex():
            itens = []
            for i, a in enumerate(anexos):
                def rm(ev, idx=i): anexos.pop(idx); desenhar_anex(); page.update()
                itens.append(ft.Container(padding=ft.Padding.symmetric(horizontal=10, vertical=6), bgcolor="#F7F6FC", border=ft.Border.all(1, BORDER), border_radius=10, content=ft.Row([ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED, color=MUTED, size=16), ft.Text(a["nome"], size=12, color=TEXT, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Text(tamanho_legivel(a["tamanho"]), size=11, color=MUTED), ft.Container(content=ft.Icon(ft.Icons.CLOSE_ROUNDED, color=MUTED, size=16), on_click=rm)], spacing=8)))
            la.controls = itens; la.height = 132 if len(itens) > 3 else None
        async def anexar(ev):
            for a in await escolher_arquivos(): anexos.append(a)
            desenhar_anex(); page.update()
        def converter(t): t = t.strip(); return float(t.replace(".", "").replace(",", ".") if "," in t else t)
        def publicar(ev):
            ti = (ct.value or "").strip(); de = (cd.value or "").strip()
            for c in (ct, cv, cp): c.error = None
            te.visible = False; pr = False
            if not ti: ct.error = "Informe o título."; pr = True
            try:
                va = converter(cv.value or "")
                if va <= 0: raise ValueError
            except ValueError: cv.error = "Valor inválido."; pr = True; va = 0.0
            try:
                pz = datetime.strptime((cp.value or "").strip(), "%d/%m/%Y").date()
                if pz < date.today(): cp.error = "O prazo já passou."; pr = True
            except ValueError: cp.error = "Use dd/mm/aaaa."; pr = True
            if pr: page.update(); return
            arq = [{"nome": a["nome"], "tamanho": a["tamanho"]} for a in anexos]
            xp_txt = (cx.value or "").strip()
            xp = int(xp_txt) if xp_txt.isdigit() and int(xp_txt) > 0 else db.xp_sugerido(va)
            tid = db.publicar_task(id_empresa, ti, de, cat["valor"], va, xp, pz.strftime("%d/%m/%Y"), arq)
            for a in anexos: guardar_arquivo(a, tid)
            carregar_tasks()
            ui["prox_id"] = max(ui["prox_id"], tid + 1)
            page.pop_dialog(); mostrar(); avisar("Task publicada!")
        desenhar_cats(); desenhar_anex()
        cont = ft.Container(width=540, content=ft.Column([ct, cd, ft.Text("Categoria", size=12, color=MUTED, weight=ft.FontWeight.W_600), lc, ft.Row([cv, cp], spacing=12), cx, ft.Text("Arquivos da task", size=12, color=MUTED, weight=ft.FontWeight.W_600), la, link_acao(ft.Icons.UPLOAD_FILE_ROUNDED, "Anexar arquivos", anexar), te], spacing=14, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
        page.show_dialog(ft.AlertDialog(modal=True, bgcolor=WHITE, title=ft.Text("Nova task", weight=ft.FontWeight.BOLD, color=TEXT), content=cont, actions=[ft.TextButton(content=ft.Text("Cancelar", color=MUTED), on_click=lambda ev: page.pop_dialog()), ft.Button(content=ft.Text("Publicar task", color=WHITE, weight=ft.FontWeight.W_600), bgcolor=PURPLE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)), on_click=publicar)]))

    # ---------- AVALIAÇÃO ----------
    def abrir_avaliacao(dev):
        atual = avaliacoes.get(dev, {"nota": 0, "comentario": ""}); nota = [atual["nota"]]
        le = ft.Row(spacing=2, tight=True)
        cc = ft.TextField(label="Comentário (opcional)", value=atual["comentario"], multiline=True, min_lines=3, max_lines=4, border_radius=10, border_color=BORDER, focused_border_color=PURPLE, cursor_color=PURPLE, text_size=13, label_style=ft.TextStyle(color=MUTED))
        te = ft.Text("Escolha de 1 a 5 estrelas.", color=RED, size=12, visible=False)
        def desenhar_est(): le.controls = [ft.Container(padding=2, on_click=lambda ev, n=i: es(n), content=ft.Icon(ft.Icons.STAR_ROUNDED if i <= nota[0] else ft.Icons.STAR_BORDER_ROUNDED, color=GOLD if i <= nota[0] else "#CFCBDD", size=36)) for i in range(1, 6)]
        def es(n): nota[0] = n; te.visible = False; desenhar_est(); page.update()
        def salvar(ev):
            if nota[0] == 0: te.visible = True; page.update(); return
            ddev = id_dev_do_nome(dev)
            if ddev: db.salvar_avaliacao(id_empresa, ddev, nota[0], (cc.value or "").strip())
            avaliacoes[dev] = {"nota": nota[0], "comentario": (cc.value or "").strip()}
            page.pop_dialog(); mostrar(); avisar(f"Avaliação de {dev} enviada.")
        desenhar_est()
        page.show_dialog(ft.AlertDialog(modal=True, bgcolor=WHITE, title=ft.Text(f"Avaliar {dev}", weight=ft.FontWeight.BOLD, color=TEXT), content=ft.Container(width=420, content=ft.Column([ft.Text("Como foi o trabalho deste desenvolvedor?", color=MUTED, size=13), le, te, cc], spacing=14, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)), actions=[ft.TextButton(content=ft.Text("Cancelar", color=MUTED), on_click=lambda ev: page.pop_dialog()), ft.Button(content=ft.Text("Enviar avaliação", color=WHITE, weight=ft.FontWeight.W_600), bgcolor=PURPLE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)), on_click=salvar)]))

    # ======================================================================
    # TELA: ENTREGAS (CORRIGIDA - sem erros de sintaxe)
    # ======================================================================
    def view_entregas():
        entregas = db.buscar_entregas_pendentes(id_empresa)
        topo = cabecalho("Entregas pendentes", "Aprove ou recuse as entregas enviadas pelos desenvolvedores.")
        if not entregas:
            return ft.Column([topo, caixa(estado_vazio(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, "Nenhuma entrega pendente", "Quando um desenvolvedor enviar uma entrega, ela aparecerá aqui para você revisar."), padding=ft.Padding.symmetric(horizontal=18, vertical=50))], spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)

        def aprovar(ent):
            def tratar(ev):
                try:
                    # id_empresa garante que só o dono da task consegue aprovar
                    r = db.aprovar_entrega_empresa(ent["id"], ent["id_dev"], id_empresa)
                except (ValueError, PermissionError) as erro:
                    page.pop_dialog()
                    mostrar()
                    avisar(f"Não foi possível aprovar: {erro}")
                    return
                page.pop_dialog()
                mostrar()   # recarrega as tasks do banco (a task passa a CONCLUÍDA)
                avisar(f"Entrega aprovada! {ent['dev']} ganhou +{r['xp_ganho']} XP." + (" Subiu de nível!" if r["subiu_nivel"] else ""))
            return tratar

        def recusar(ent):
            def tratar(ev):
                try:
                    db.recusar_entrega_empresa(ent["id"], ent["id_dev"], id_empresa)
                except (ValueError, PermissionError) as erro:
                    page.pop_dialog()
                    mostrar()
                    avisar(f"Não foi possível recusar: {erro}")
                    return
                page.pop_dialog()  # fecha o dialog ANTES de mostrar()
                mostrar()
                avisar(f"Entrega de {ent['dev']} recusada. O dev pode reenviar.")
            return tratar

        def abrir_dialog(ent):
            arqs = ent.get("entrega_arquivos", []); nt = ent.get("entrega_nota", "")
            corpo = [
                ft.Row([avatar(ent["dev"], 40), ft.Column([ft.Text(ent["dev"], color=TEXT, size=14, weight=ft.FontWeight.BOLD), ft.Text(ent["titulo"], color=MUTED, size=12)], spacing=3, expand=True)]),
                ft.Divider(color=BORDER),
                ft.Text("Arquivos entregues:", color=TEXT, size=13, weight=ft.FontWeight.W_600),
            ]
            if arqs:
                for a in arqs:
                    corpo.append(ft.Container(padding=ft.Padding.symmetric(horizontal=10, vertical=6), bgcolor="#F7F6FC", border=ft.Border.all(1, BORDER), border_radius=10, content=ft.Row([ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED, color=MUTED, size=14), ft.Text(a["nome"], color=TEXT, size=12)], spacing=6, tight=True)))
            else:
                corpo.append(ft.Text("Nenhum arquivo anexado.", color=MUTED, size=12))
            if nt:
                corpo += [ft.Divider(color=BORDER), ft.Text("Observação do dev:", color=TEXT, size=13, weight=ft.FontWeight.W_600), ft.Text(nt, color=MUTED, size=12)]
            corpo += [ft.Divider(color=BORDER), ft.Row([ft.Icon(ft.Icons.BOLT_ROUNDED, color=PURPLE, size=16), ft.Text(f"XP que o dev ganhará: {ent['xp']}", color=PURPLE, size=13, weight=ft.FontWeight.W_600)])]

            page.show_dialog(ft.AlertDialog(
                modal=True, bgcolor=WHITE,
                title=ft.Text("Revisar entrega", weight=ft.FontWeight.BOLD, color=TEXT),
                content=ft.Container(width=480, content=ft.Column(corpo, spacing=10, tight=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)),
                actions=[
                    ft.TextButton(content=ft.Text("Recusar", color=RED, weight=ft.FontWeight.W_600), on_click=recusar(ent)),
                    ft.Button(content=ft.Text("Aprovar e dar XP", color=WHITE, weight=ft.FontWeight.W_600), bgcolor=GREEN, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)), on_click=aprovar(ent)),
                ]))

        # Lista de entregas (list comprehension correta)
        itens_lista = []
        for e in entregas:
            cor_cat, ic_cat = CATEGORIAS[e["categoria"]]
            itens_lista.append(ft.Container(
                padding=18, bgcolor=WHITE, border=ft.Border.all(1, BORDER), border_radius=16,
                content=ft.Column([
                    ft.Row([
                        ft.Container(content=ft.Icon(ic_cat, color=cor_cat, size=20), bgcolor=com_opacidade(cor_cat), padding=10, border_radius=11),
                        ft.Column([ft.Text(e["titulo"], color=TEXT, weight=ft.FontWeight.BOLD, size=14), ft.Text(f"Entregue por {e['dev']} · {e['categoria']}", color=MUTED, size=12)], spacing=3, expand=True),
                        selo(f"+{e['xp']} XP", PURPLE),
                    ]),
                    ft.Row([
                        ft.Text(f"{len(e.get('entrega_arquivos', []))} arquivo(s) entregue(s)", color=MUTED, size=12),
                        ft.Container(expand=True),
                        botao_primario("Revisar entrega", ft.Icons.VISIBILITY_ROUNDED, lambda ev, ee=e: abrir_dialog(ee)),
                    ]),
                ], spacing=12),
            ))
        lista = ft.Column(itens_lista, spacing=12)
        return ft.Column([topo, lista], spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)

    # ---------- DASHBOARD ----------
    def view_dashboard():
        abertas = [t for t in tasks if situacao(t) != "concluida"]; aguardando = [t for t in tasks if situacao(t) == "aberta"]
        andamento = [t for t in tasks if situacao(t) in ("andamento", "analise")]; concluidas = [t for t in tasks if situacao(t) == "concluida"]
        total = sum(t["valor"] for t in tasks); pago = sum(t["valor"] for t in tasks if t["pago"]); devs = devs_unicos()
        stats = ft.Row([stat_card(ft.Icons.ASSIGNMENT_ROUNDED, "Tasks em aberto", str(len(abertas)), f"{len(aguardando)} aguardando dev", PURPLE), stat_card(ft.Icons.GROUP_ROUNDED, "Em andamento", str(len(andamento)), f"{len(devs)} desenvolvedor(es)", BLUE), stat_card(ft.Icons.CHECK_CIRCLE_ROUNDED, "Concluídas", str(len(concluidas)), "Entregas finalizadas", GREEN), stat_card(ft.Icons.PAYMENTS_ROUNDED, "Investimento total", brl(total), f"{brl(pago)} pagos", ORANGE, 23)], spacing=14)
        lista_tasks = (ft.Column([task_card(t) for t in abertas], spacing=12) if abertas else caixa(estado_vazio(ft.Icons.ASSIGNMENT_ROUNDED, "Nenhuma task em aberto", "Publique sua primeira task.", botao_primario("Publicar primeira task", ft.Icons.ADD_ROUNDED, abrir_nova_task)), padding=ft.Padding.symmetric(horizontal=18, vertical=36)))
        if devs:
            linhas = []
            for d in devs:
                ts = tasks_do_dev(d); media = round(sum(t["progresso"] for t in ts) / len(ts)); av = avaliacoes.get(d)
                linhas.append(ft.Container(padding=ft.Padding.symmetric(vertical=11), border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)), on_click=lambda ev, dd=d: abrir_chat(dd), content=ft.Row([avatar(d, 38), ft.Column([ft.Text(d, color=TEXT, size=13, weight=ft.FontWeight.W_600), ft.Text(f"{len(ts)} task(s) · progresso médio {media}%", color=MUTED, size=11)], spacing=3, expand=True), estrelas_fixas(av["nota"], 14) if av else ft.Text("Sem avaliação", color=MUTED, size=10)], spacing=12)))
            painel_devs = caixa(ft.Column(linhas, spacing=0), padding=ft.Padding.symmetric(horizontal=16, vertical=4))
        else:
            painel_devs = caixa(estado_vazio(ft.Icons.PERSON_SEARCH_ROUNDED, "Ninguém pegou suas tasks ainda", "Quando um desenvolvedor pegar uma task, ele aparece aqui."), padding=ft.Padding.symmetric(horizontal=18, vertical=30))
        dica = caixa(ft.Row([ft.Container(content=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=ORANGE, size=22), bgcolor="#FFF4E5", padding=10, border_radius=12), ft.Column([ft.Text("Dica", color=TEXT, size=12, weight=ft.FontWeight.BOLD), ft.Text("Anexe especificações e referências à task.", color=MUTED, size=11)], spacing=4, expand=True)], spacing=10), padding=16)
        return ft.Column([cabecalho("Painel da empresa", f"Bem-vindo, {nome.split()[0]}!", botao_primario("Nova task", ft.Icons.ADD_ROUNDED, abrir_nova_task)), stats, ft.Row([ft.Column([ft.Text("Tasks em aberto", color=TEXT, size=17, weight=ft.FontWeight.BOLD), lista_tasks], spacing=14, expand=3), ft.Column([ft.Text("Quem pegou suas tasks", color=TEXT, size=17, weight=ft.FontWeight.BOLD), painel_devs, dica], spacing=14, expand=2)], spacing=18, vertical_alignment=ft.CrossAxisAlignment.START)], spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)

    # ---------- TASKS ----------
    def view_tasks():
        f = ui["filtro"]; vis = tasks if f == "todas" else [t for t in tasks if situacao(t) == f]
        if vis: lista = ft.Column([task_card(t, True) for t in vis], spacing=12)
        elif tasks: lista = caixa(estado_vazio(ft.Icons.ASSIGNMENT_ROUNDED, "Nenhuma task nesta situação", "Troque o filtro."), padding=ft.Padding.symmetric(horizontal=18, vertical=36))
        else: lista = caixa(estado_vazio(ft.Icons.ASSIGNMENT_ROUNDED, "Você ainda não publicou nenhuma task", "Descreva o que precisa e publique.", botao_primario("Nova task", ft.Icons.ADD_ROUNDED, abrir_nova_task)), padding=ft.Padding.symmetric(horizontal=18, vertical=36))
        return ft.Column([cabecalho("Tasks", "Publique tasks e veja quem pegou cada uma.", botao_primario("Nova task", ft.Icons.ADD_ROUNDED, abrir_nova_task)), ft.Row([chip_filtro("Todas", "todas"), chip_filtro("Aguardando dev", "aberta"), chip_filtro("Em andamento", "andamento"), chip_filtro("Em análise", "analise"), chip_filtro("Concluídas", "concluida")], spacing=8, wrap=True), lista], spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)

    # ---------- MENSAGENS ----------
    def abrir_chat(dev): ui["dev"] = dev; mostrar("mensagens")
    def bolha(m):
        minha = m["de"] == "empresa"; larg = max(90, min(380, len(m["texto"]) * 7.2 + 34))
        return ft.Row([ft.Container(width=larg, padding=ft.Padding.symmetric(horizontal=14, vertical=10), border_radius=14, bgcolor=PURPLE if minha else "#F1EEF9", content=ft.Column([ft.Text(m["texto"], color=WHITE if minha else TEXT, size=13), ft.Text(m["hora"], color="#D9CFFF" if minha else MUTED, size=10)], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.START))], alignment=ft.MainAxisAlignment.END if minha else ft.MainAxisAlignment.START)
    def view_mensagens():
        devs = devs_unicos(); topo = cabecalho("Mensagens", "Converse com quem pegou suas tasks.")
        if not devs: return ft.Column([topo, caixa(estado_vazio(ft.Icons.FORUM_OUTLINED, "Nenhuma conversa ainda", "Quando um dev pegar uma task, você poderá conversar com ele."), padding=ft.Padding.symmetric(horizontal=18, vertical=50))], spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)
        if ui["dev"] not in devs: ui["dev"] = devs[0]
        dev = ui["dev"]; altura = max(460, (page.height or 800) - 200)
        previas = {}; itens = []
        for d in devs:
            ms = mensagens.get(d, []); pv = ft.Text(ms[-1]["texto"] if ms else "Nenhuma mensagem", color=MUTED, size=11, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS); previas[d] = pv
            itens.append(ft.Container(padding=12, border_radius=12, bgcolor=PURPLE_LIGHT if d == dev else None, on_click=lambda ev, dd=d: abrir_chat(dd), content=ft.Row([avatar(d, 38), ft.Column([ft.Text(d, color=TEXT, size=13, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Text(", ".join(t["titulo"] for t in tasks_do_dev(d)), color=PURPLE, size=10, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), pv], spacing=2, expand=True)], spacing=10)))
        lista = ft.Container(width=290, height=altura, padding=10, bgcolor=WHITE, border=ft.Border.all(1, BORDER), border_radius=16, content=ft.Column(itens, spacing=4, scroll=ft.ScrollMode.AUTO))
        lm = ft.Column(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO, auto_scroll=True)
        def desenhar_msgs():
            ms = mensagens.get(dev, []); lm.controls = [bolha(m) for m in ms] or [ft.Container(padding=ft.Padding.symmetric(vertical=40), content=ft.Text(f"Envie a primeira mensagem para {dev}.", color=MUTED, size=12, text_align=ft.TextAlign.CENTER), alignment=ft.Alignment.CENTER)]
        cm = ft.TextField(hint_text="Escreva uma mensagem...", hint_style=ft.TextStyle(color="#A29DB4"), border_radius=12, border_color=BORDER, focused_border_color=PURPLE, cursor_color=PURPLE, text_size=13, expand=True, content_padding=ft.Padding.symmetric(horizontal=14, vertical=12))
        async def enviar(ev):
            tx = (cm.value or "").strip()
            if not tx: return
            du = db.buscar_id_usuario_por_nome_dev(dev)
            if du: db.enviar_mensagem(id_usuario, du, tx)
            mensagens.setdefault(dev, []).append({"de": "empresa", "texto": tx, "hora": datetime.now().strftime("%H:%M")})
            cm.value = ""; desenhar_msgs(); previas[dev].value = tx; page.update(); await cm.focus()
        cm.on_submit = enviar; desenhar_msgs()
        av = avaliacoes.get(dev)
        bloco = ft.Row([estrelas_fixas(av["nota"], 18) if av else ft.Text("Sem avaliação", color=MUTED, size=11), link_acao(ft.Icons.RATE_REVIEW_ROUNDED, "Editar avaliação" if av else "Avaliar", lambda ev: abrir_avaliacao(dev))], spacing=6, tight=True)
        painel = ft.Container(expand=True, height=altura, bgcolor=WHITE, border=ft.Border.all(1, BORDER), border_radius=16, content=ft.Column([ft.Container(padding=ft.Padding.symmetric(horizontal=18, vertical=14), border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)), content=ft.Row([avatar(dev, 40), ft.Column([ft.Text(dev, color=TEXT, size=14, weight=ft.FontWeight.BOLD), ft.Text(f"{len(tasks_do_dev(dev))} task(s) com você", color=MUTED, size=11)], spacing=3, expand=True), bloco], spacing=12)), ft.Container(expand=True, padding=ft.Padding.symmetric(horizontal=18, vertical=12), content=lm), ft.Container(padding=ft.Padding.all(14), border=ft.Border.only(top=ft.BorderSide(1, BORDER)), content=ft.Row([cm, ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color=WHITE, bgcolor=PURPLE, tooltip="Enviar", on_click=enviar, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))], spacing=10))], spacing=0))
        return ft.Column([topo, ft.Row([lista, painel], spacing=16, vertical_alignment=ft.CrossAxisAlignment.START)], spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)

    # ---------- FINANCEIRO ----------
    def registrar_pagamento(t):
        def tratar(ev):
            msg = f"Pagamento de {brl(t['valor'])} para {t['dev']} registrado."
            if not db.registrar_pagamento(t["id"], id_empresa):
                avisar("Só é possível registrar o pagamento depois de aprovar a entrega."); return
            mostrar(); avisar(msg)
        return tratar
    def view_financeiro():
        total = sum(t["valor"] for t in tasks); pago = sum(t["valor"] for t in tasks if t["pago"])
        a_pagar = sum(t["valor"] for t in tasks if situacao(t) == "concluida" and not t["pago"]); aguardando = sum(t["valor"] for t in tasks if not t["dev"] and not t["pago"])
        n_a = len([t for t in tasks if situacao(t) == "concluida" and not t["pago"]]); n_g = len([t for t in tasks if not t["dev"]]); pct = pago / total if total else 0
        stats = ft.Row([stat_card(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, "Total em tasks", brl(total), f"{len(tasks)} task(s) publicadas", PURPLE, 23), stat_card(ft.Icons.PAID_ROUNDED, "Já pago", brl(pago), f"{int(pct*100)}% do total", GREEN, 23), stat_card(ft.Icons.PENDING_ACTIONS_ROUNDED, "A pagar", brl(a_pagar), f"{n_a} entrega(s) aprovada(s)", BLUE, 23), stat_card(ft.Icons.HOURGLASS_EMPTY_ROUNDED, "Aguardando dev", brl(aguardando), f"{n_g} task(s) sem dev", ORANGE, 23)], spacing=14)
        def cel(c, e=None, w=None): return ft.Container(content=c, expand=e, width=w)
        def cc(x): return ft.Text(x, color=MUTED, size=11, weight=ft.FontWeight.BOLD)
        linhas = [ft.Container(padding=ft.Padding.symmetric(vertical=10), border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)), content=ft.Row([cel(cc("TASK"), 4), cel(cc("DESENVOLVEDOR"), 3), cel(cc("VALOR"), 2), cel(cc("SITUAÇÃO"), 2), cel(cc(""), w=150)], spacing=12))]
        for t in tasks:
            if t["pago"]: si, co = "PAGO", GREEN; ac = ft.Text(f"em {t['pago_em']}", color=MUTED, size=11)
            elif situacao(t) in ("andamento", "analise"): si, co = SITUACOES[situacao(t)]; ac = ft.Text("Pague após aprovar", color=MUTED, size=11)
            elif t["dev"]: si, co = "A PAGAR", BLUE; ac = ft.Container(padding=ft.Padding.symmetric(horizontal=12, vertical=7), bgcolor=PURPLE, border_radius=10, on_click=registrar_pagamento(t), content=ft.Text("Registrar pagamento", color=WHITE, size=11, weight=ft.FontWeight.W_600))
            else: si, co = "AGUARDANDO DEV", ORANGE; ac = ft.Text("—", color=MUTED, size=12)
            linhas.append(ft.Container(padding=ft.Padding.symmetric(vertical=12), border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)), content=ft.Row([cel(ft.Text(t["titulo"], color=TEXT, size=13, weight=ft.FontWeight.W_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), 4), cel(ft.Text(t["dev"] or "—", color=MUTED, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), 3), cel(ft.Text(brl(t["valor"]), color=TEXT, size=13, weight=ft.FontWeight.BOLD), 2), cel(ft.Row([selo(si, co)], tight=True), 2), cel(ac, w=150)], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)))
        tabela = (caixa(ft.Column([ft.Row([ft.Text("Controle de pagamentos", color=TEXT, size=16, weight=ft.FontWeight.BOLD), ft.Container(expand=True), ft.Text(f"{int(pct*100)}% do orçamento pago", color=MUTED, size=12)]), ft.ProgressBar(value=pct, color=GREEN, bgcolor="#F0EDF7", height=6, border_radius=8), ft.Column(linhas, spacing=0)], spacing=12), padding=ft.Padding.symmetric(horizontal=20, vertical=18)) if tasks else caixa(estado_vazio(ft.Icons.PAYMENTS_ROUNDED, "Nenhuma movimentação financeira", "Cada task publicada aparece aqui.", botao_primario("Nova task", ft.Icons.ADD_ROUNDED, abrir_nova_task)), padding=ft.Padding.symmetric(horizontal=18, vertical=40)))
        return ft.Column([cabecalho("Financeiro", "Controle quanto já foi pago."), stats, tabela], spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)

    # ---------- MENU LATERAL ----------
    menu = ft.Column(spacing=0)
    def item_menu(ch, ic, ro):
        sel = ui["tela"] == ch
        return ft.Container(content=ft.Row([ft.Icon(ic, size=20, color=WHITE if sel else "#B9B3D1"), ft.Text(ro, size=14, weight=ft.FontWeight.W_600 if sel else ft.FontWeight.NORMAL, color=WHITE if sel else "#C9C4DE")], spacing=14), padding=ft.Padding.symmetric(horizontal=16, vertical=13), bgcolor="#5A2FC7" if sel else None, border_radius=12, margin=ft.Margin.only(bottom=5), on_click=lambda e: mostrar(ch))
    def desenhar_menu():
        n_analise = len([t for t in tasks if situacao(t) == "analise"])
        menu.controls = [
            item_menu("dashboard", ft.Icons.SPACE_DASHBOARD_ROUNDED, "Dashboard"),
            item_menu("tasks", ft.Icons.ASSIGNMENT_ROUNDED, "Tasks"),
            item_menu("entregas", ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, f"Entregas ({n_analise})" if n_analise else "Entregas"),
            item_menu("mensagens", ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED, "Mensagens"),
            item_menu("financeiro", ft.Icons.PAYMENTS_ROUNDED, "Financeiro"),
        ]
    def sair(e=None):
        if seletor in page.services: page.services.remove(seletor)
        if ao_sair: ao_sair()
        else: avisar("Abra pelo main.py para entrar e sair.")
    sidebar = ft.Container(width=245, bgcolor="#25164A", padding=ft.Padding.symmetric(horizontal=18, vertical=24), content=ft.Column([ft.Row([ft.Container(content=ft.Icon(ft.Icons.CODE_ROUNDED, color=WHITE, size=24), bgcolor=PURPLE, padding=10, border_radius=13), ft.Column([ft.Text("DevSphere", color=WHITE, size=20, weight=ft.FontWeight.BOLD), ft.Text("PAINEL DA EMPRESA", color="#A9A0C9", size=9, weight=ft.FontWeight.BOLD)], spacing=2)], spacing=10), ft.Container(height=28), ft.Text("MENU PRINCIPAL", color="#8F84B8", size=10, weight=ft.FontWeight.BOLD), ft.Container(height=8), menu, ft.Container(expand=True), ft.Container(padding=15, bgcolor="#34245B", border_radius=14, on_click=abrir_nova_task, content=ft.Column([ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED, color="#C7B4FF", size=25), ft.Text("Precisa de ajuda?", color=WHITE, size=13, weight=ft.FontWeight.BOLD), ft.Text("Publique uma task.", color="#C4BBDD", size=11), ft.Container(height=3), ft.Text("Nova task  →", color="#D6C9FF", size=12, weight=ft.FontWeight.BOLD)], spacing=8)), ft.Container(height=8), ft.Row([ft.CircleAvatar(content=ft.Text(iniciais_empresa, color=WHITE, weight=ft.FontWeight.BOLD), bgcolor="#8B5CF6", radius=20), ft.Column([ft.Text(nome, color=WHITE, size=12, weight=ft.FontWeight.BOLD, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS), ft.Text("Empresa", color="#A9A0C9", size=10)], spacing=3, expand=True), ft.IconButton(icon=ft.Icons.LOGOUT_ROUNDED, tooltip="Sair", icon_color="#A9A0C9", icon_size=18, on_click=sair)], spacing=9)], spacing=0, expand=True))
    area = ft.Container(expand=True, padding=ft.Padding.all(28))
    def construir():
        carregar_tasks()   # sempre reflete o banco (entregas novas, aprovações, pagamentos)
        c = {"dashboard": view_dashboard, "tasks": view_tasks, "entregas": view_entregas, "mensagens": view_mensagens, "financeiro": view_financeiro}
        desenhar_menu(); area.content = c[ui["tela"]]()
    def mostrar(t=None):
        if t: ui["tela"] = t
        construir(); page.update()
    def ao_redimensionar(e=None):
        if ui["tela"] == "mensagens": mostrar()
    page.on_resize = ao_redimensionar; construir()
    page.add(ft.Row([sidebar, area], spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH))

if __name__ == "__main__": ft.run(dashboard)