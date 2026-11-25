"""DevSphere - Painel do desenvolvedor (INTEGRADO COM SQLITE)."""
import shutil
from datetime import datetime
from pathlib import Path
import flet as ft
import database as db

MODO_TESTE=False  # True mostra o botão "Simular aprovação (teste)"; a aprovação real é feita no painel da empresa
PASTA_UPLOADS=Path(__file__).parent/"uploads"
XP_POR_NIVEL=1000; MAX_ATIVOS=3
NOMES_NIVEL=["Iniciante","Júnior","Pleno","Sênior","Especialista"]

def dashboard(page: ft.Page, usuario=None, ao_sair=None):
    usuario=usuario or {"nome":"Convidado","email":"","tipo":"desenvolvedor"}
    nome_inicial=usuario.get("nome") or "Desenvolvedor"
    page.title="DevSphere | Dashboard"; page.bgcolor="#F7F6FC"; page.padding=0
    page.theme_mode=ft.ThemeMode.LIGHT; page.window.min_width=760; page.window.min_height=700
    PURPLE="#6C3CE9"; PURPLE_LIGHT="#EEE8FF"; TEXT="#24213A"; MUTED="#77738D"; BORDER="#E9E6F2"
    WHITE="#FFFFFF"; GREEN="#21A675"; ORANGE="#F19A38"; BLUE="#4385F5"; RED="#DC2626"; GOLD="#F5B301"
    CATEGORIAS={"BACK-END":(PURPLE,ft.Icons.TERMINAL_ROUNDED),"FRONT-END":(BLUE,ft.Icons.WEB_ROUNDED),"FULL-STACK":(GREEN,ft.Icons.LAYERS_ROUNDED),"MOBILE":(ORANGE,ft.Icons.PHONE_ANDROID_ROUNDED),"DADOS":("#D14C8B",ft.Icons.BAR_CHART_ROUNDED)}
    SITUACOES={"andamento":("EM ANDAMENTO",BLUE),"analise":("EM ANÁLISE",ORANGE),"aceita":("ACEITA",GREEN)}
    id_usuario=usuario.get("id_usuario"); id_dev=usuario.get("id_dev")

    pdb=db.buscar_perfil_dev(id_usuario); conta={"xp":pdb.get("pontuacao",0)}
    perfil={"nome":pdb.get("nome",nome_inicial),"bio":pdb.get("bio",""),"localizacao":pdb.get("localizacao",""),"github":pdb.get("github",""),"portfolio":pdb.get("portfolio",""),"habilidades":pdb.get("habilidades",[]) or []}
    tarefas=[{"id":t["id"],"projeto":t,"titulo":t["titulo"],"empresa":t["empresa"],"categoria":t["categoria"],"valor":t["valor"],"xp":t["xp"],"prazo":t["prazo"],"progresso":t["progresso"],"status":t["status"],"entrega":t.get("entrega")} for t in db.buscar_tarefas_do_dev(id_dev)]
    catalogo=db.buscar_catalogo_projetos(); seguindo=db.buscar_empresas_seguidas(id_dev)
    atividades=[(ft.Icons.CHECK_CIRCLE_ROUNDED,a["titulo"],f"{a['titulo']} · {a['empresa']}",a["data_aceite"] or "Hoje","ACEITA",GREEN) for a in db.buscar_atividades_recentes(id_dev,4)]
    mensagens={}; ultima_msg={}
    for emp in db.buscar_empresas():
        du=emp.get("id_usuario")
        if du:
            ms=db.buscar_mensagens(id_usuario,du)
            if ms: mensagens[emp["nome"]]=[{"de":"dev" if m["direcao"]=="eu" else "empresa","texto":m["texto"],"hora":m["hora"]} for m in ms]; ultima_msg[emp["nome"]]=len(mensagens[emp["nome"]])
    ui={"tela":"dashboard","cat":"todas","filtro_tarefa":"todas","empresa":None,"busca":"","empresa_chat":None,"rascunho":"","seq":len(ultima_msg)}
    seletor=ft.FilePicker(); page.services.append(seletor)

    def brl(v): return "R$ "+f"{v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    def fmt(n): return f"{n:,}".replace(",", ".")
    def tamanho_legivel(n):
        if not n: return ""
        return f"{n/1_000_000:.1f} MB".replace(".",",") if n>=1_000_000 else f"{max(1,round(n/1000))} KB"
    def primeiro_nome(): return (perfil["nome"].split() or ["Dev"])[0]
    def nivel_de(x): return x//XP_POR_NIVEL
    def nome_do_nivel(n): return NOMES_NIVEL[min(n,len(NOMES_NIVEL)-1)]
    def com_opacidade(c,op=0.09): return ft.Colors.with_opacity(op,c)
    def avisar(m): page.show_dialog(ft.SnackBar(ft.Text(m)))
    def registrar(ic,t,s,st,c): atividades.insert(0,(ic,t,s,datetime.now().strftime("Hoje, %H:%M"),st,c))
    def tarefas_com(*st): return [t for t in tarefas if t["status"] in st]
    def ranking_completo():
        itens=db.buscar_ranking()
        for i in itens: i["eu"]=i["nome"]==perfil["nome"]
        itens.sort(key=lambda i:(-i["xp"],i["eu"]))
        for p,i in enumerate(itens,1): i["pos"]=p
        return itens
    def minha_posicao(): return next((i["pos"] for i in ranking_completo() if i["eu"]),0)

    def avatar(t,s=38):
        ini="".join(p[0] for p in t.split()[:2]).upper()
        return ft.CircleAvatar(content=ft.Text(ini,color=WHITE,weight=ft.FontWeight.BOLD,size=max(10,s//3)),bgcolor="#8B5CF6",radius=s/2)
    def selo(t,c): return ft.Container(content=ft.Text(t,color=c,size=10,weight=ft.FontWeight.BOLD),bgcolor=com_opacidade(c),padding=ft.Padding.symmetric(horizontal=9,vertical=5),border_radius=20)
    def caixa(c,**kw): return ft.Container(padding=kw.pop("padding",18),bgcolor=WHITE,border=ft.Border.all(1,BORDER),border_radius=16,content=c,**kw)
    def botao_primario(t,ic,oc,ativo=True): return ft.Container(padding=ft.Padding.symmetric(horizontal=18,vertical=12),bgcolor=PURPLE if ativo else "#C9C4DE",border_radius=12,on_click=oc,content=ft.Row([ft.Icon(ic,color=WHITE,size=18),ft.Text(t,color=WHITE,size=13,weight=ft.FontWeight.W_600)],spacing=8,tight=True))
    def link_acao(ic,t,oc,cor=PURPLE): return ft.Container(on_click=oc,padding=ft.Padding.symmetric(horizontal=8,vertical=4),content=ft.Row([ft.Icon(ic,color=cor,size=15),ft.Text(t,color=cor,size=12,weight=ft.FontWeight.W_600)],spacing=5,tight=True))
    def estrelas_fixas(n,s=16):
        ch=round(n); return ft.Row([ft.Icon(ft.Icons.STAR_ROUNDED if i<=ch else ft.Icons.STAR_BORDER_ROUNDED,color=GOLD if i<=ch else "#CFCBDD",size=s) for i in range(1,6)],spacing=1,tight=True)
    def estado_vazio(ic,t,x,acao=None):
        itens=[ft.Container(content=ft.Icon(ic,color=PURPLE,size=26),bgcolor=PURPLE_LIGHT,padding=14,border_radius=30),ft.Text(t,color=TEXT,size=13,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER),ft.Text(x,color=MUTED,size=11,text_align=ft.TextAlign.CENTER)]
        if acao: itens+=[ft.Container(height=4),acao]
        return ft.Row([ft.Column(itens,horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=8,expand=True)])
    def cabecalho(t,x,extra=None):
        itens=[ft.Column([ft.Text(t,size=26,color=TEXT,weight=ft.FontWeight.BOLD),ft.Text(x,color=MUTED,size=13)],spacing=5,expand=True)]
        if extra: itens.append(extra)
        return ft.Row(itens,spacing=12,vertical_alignment=ft.CrossAxisAlignment.CENTER)
    def chip_filtro(r,at,oc): return ft.Container(padding=ft.Padding.symmetric(horizontal=14,vertical=8),border_radius=20,bgcolor=PURPLE if at else WHITE,border=ft.Border.all(1,PURPLE if at else BORDER),on_click=oc,content=ft.Text(r,size=12,weight=ft.FontWeight.W_600,color=WHITE if at else MUTED))
    def campo_texto(r,**kw): return ft.TextField(label=r,border_radius=10,border_color=BORDER,focused_border_color=PURPLE,cursor_color=PURPLE,text_size=13,label_style=ft.TextStyle(color=MUTED),**kw)
    def stat_card(ic,t,v,x,c,sb=False): return ft.Container(expand=True,padding=20,bgcolor=WHITE,border=ft.Border.all(1,BORDER),border_radius=18,content=ft.Column([ft.Row([ft.Container(content=ft.Icon(ic,color=c,size=21),bgcolor=com_opacidade(c),padding=11,border_radius=12),ft.Container(expand=True),ft.Icon(ft.Icons.TRENDING_UP if sb else ft.Icons.TRENDING_FLAT,color=GREEN if sb else MUTED,size=17)]),ft.Text(t,color=MUTED,size=13),ft.Text(v,color=TEXT,size=27,weight=ft.FontWeight.BOLD),ft.Text(x,color=GREEN if sb else MUTED,size=12,weight=ft.FontWeight.W_500)],spacing=9))
    def project_card(nm,cp,cat,pr,c,due,ic): return ft.Container(padding=18,bgcolor=WHITE,border=ft.Border.all(1,BORDER),border_radius=16,content=ft.Column([ft.Row([ft.Container(content=ft.Icon(ic,color=c,size=20),bgcolor=com_opacidade(c),padding=10,border_radius=11),ft.Column([ft.Text(nm,color=TEXT,weight=ft.FontWeight.BOLD,size=14),ft.Text(cp,color=MUTED,size=12)],spacing=3,expand=True),selo(cat,c)],spacing=12),ft.Row([ft.Text("Progresso",color=MUTED,size=12),ft.Container(expand=True),ft.Text(f"{int(pr*100)}%",color=TEXT,size=12,weight=ft.FontWeight.BOLD)]),ft.ProgressBar(value=pr,color=c,bgcolor="#F0EDF7",height=6,border_radius=8),ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED,color=MUTED,size=14),ft.Text(f"Entrega: {due}",color=MUTED,size=11),ft.Container(expand=True),link_acao(ft.Icons.ARROW_FORWARD,"Ver tarefa",lambda e:mostrar("tarefas"))],spacing=5)],spacing=13))
    def activity_row(ic,ti,su,da,st,sc): return ft.Container(padding=ft.Padding.symmetric(vertical=13),border=ft.Border.only(bottom=ft.BorderSide(1,BORDER)),content=ft.Row([ft.Container(content=ft.Icon(ic,color=sc,size=19),bgcolor=com_opacidade(sc),padding=10,border_radius=11),ft.Column([ft.Text(ti,color=TEXT,size=13,weight=ft.FontWeight.W_600),ft.Text(su,color=MUTED,size=11)],spacing=4,expand=True),ft.Column([selo(st,sc),ft.Text(da,color=MUTED,size=10)],horizontal_alignment=ft.CrossAxisAlignment.END,spacing=7)],spacing=12))
    def chip_arquivo(nm,t=None): return ft.Container(padding=ft.Padding.symmetric(horizontal=10,vertical=6),bgcolor="#F7F6FC",border=ft.Border.all(1,BORDER),border_radius=10,content=ft.Row([ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED,color=MUTED,size=14),ft.Text(f"{nm}{' · '+tamanho_legivel(t) if t else ''}",color=TEXT,size=11)],spacing=6,tight=True))

    def pegar_projeto(p):
        if len(tarefas_com("andamento"))>=MAX_ATIVOS: avisar(f"Você já tem {MAX_ATIVOS} projetos em andamento."); return
        if not db.pegar_projeto(id_dev,p["id"]): avisar("Este projeto já foi pego por outro desenvolvedor."); return
        tarefas.insert(0,{"id":p["id"],"projeto":p,"titulo":p["titulo"],"empresa":p["empresa"],"categoria":p["categoria"],"valor":p["valor"],"xp":p["xp"],"prazo":p["prazo"],"progresso":0,"status":"andamento","entrega":None})
        if p in catalogo: catalogo.remove(p)
        registrar(ft.Icons.ROCKET_LAUNCH_ROUNDED,"Projeto pego",f"{p['titulo']} · {p['empresa']}","EM ANDAMENTO",BLUE); mostrar("tarefas")
        avisar(f"Você pegou \"{p['titulo']}\".")
    def atualizar_progresso(t,v):
        t["progresso"]=int(round(v)); db.atualizar_progresso(id_dev,t["id"],t["progresso"]); mostrar()
        if t["progresso"]>=100: avisar("Progresso em 100%! Agora é só enviar a entrega.")
    def abrir_desistencia(t):
        def confirmar(ev):
            db.desistir_projeto(id_dev,t["id"]); tarefas.remove(t); catalogo.insert(0,t["projeto"])
            registrar(ft.Icons.UNDO_ROUNDED,"Desistiu do projeto",f"{t['titulo']} · {t['empresa']}","CANCELADO",RED)
            page.pop_dialog(); mostrar(); avisar("Projeto devolvido.")
        page.show_dialog(ft.AlertDialog(modal=True,bgcolor=WHITE,title=ft.Text("Desistir do projeto?",weight=ft.FontWeight.BOLD,color=TEXT),content=ft.Text(f"\"{t['titulo']}\" volta para a lista e você perde o progresso ({t['progresso']}%).",color=MUTED,size=13),actions=[ft.TextButton(content=ft.Text("Cancelar",color=MUTED),on_click=lambda ev:page.pop_dialog()),ft.Button(content=ft.Text("Desistir",color=WHITE,weight=ft.FontWeight.W_600),bgcolor=RED,style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),on_click=confirmar)]))
    def guardar_arquivo(a,tid):
        c=a.get("caminho")
        if not c: return
        try: d=PASTA_UPLOADS/"entregas"/f"task_{tid}"; d.mkdir(parents=True,exist_ok=True); shutil.copy2(c,d/a["nome"])
        except OSError: pass
    async def escolher_arquivos():
        es=await seletor.pick_files(dialog_title="Anexar arquivos da entrega",allow_multiple=True)
        return [{"nome":f.name,"tamanho":f.size,"caminho":f.path} for f in (es or [])]
    def abrir_entrega(t):
        anexos=[]; la=ft.Column(spacing=6,scroll=ft.ScrollMode.AUTO); cn=campo_texto("Observações para a empresa (opcional)",multiline=True,min_lines=3,max_lines=4)
        def desenhar_anex():
            itens=[]
            for i,a in enumerate(anexos):
                def rm(ev,idx=i): anexos.pop(idx); desenhar_anex(); page.update()
                itens.append(ft.Container(padding=ft.Padding.symmetric(horizontal=10,vertical=6),bgcolor="#F7F6FC",border=ft.Border.all(1,BORDER),border_radius=10,content=ft.Row([ft.Icon(ft.Icons.INSERT_DRIVE_FILE_OUTLINED,color=MUTED,size=16),ft.Text(a["nome"],size=12,color=TEXT,expand=True,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),ft.Text(tamanho_legivel(a["tamanho"]),size=11,color=MUTED),ft.Container(content=ft.Icon(ft.Icons.CLOSE_ROUNDED,color=MUTED,size=16),on_click=rm)],spacing=8)))
            la.controls=itens; la.height=132 if len(itens)>3 else None
        async def anexar(ev): anexos.extend(await escolher_arquivos()); desenhar_anex(); page.update()
        def enviar(ev):
            for a in anexos: guardar_arquivo(a,t["id"])
            arq=[{"nome":a["nome"],"tamanho":a["tamanho"]} for a in anexos]; nt=(cn.value or "").strip()
            if not db.enviar_entrega(id_dev,t["id"],arq,nt): page.pop_dialog(); avisar("Não foi possível enviar: esta tarefa não está em andamento."); return
            t["entrega"]={"arquivos":arq,"nota":nt}; t["status"]="analise"; t["progresso"]=100
            registrar(ft.Icons.UPLOAD_ROUNDED,"Entrega enviada",f"{t['titulo']} · {t['empresa']}","EM ANÁLISE",ORANGE)
            page.pop_dialog(); mostrar(); avisar("Entrega enviada! Aguarde a aprovação da empresa.")
        desenhar_anex()
        page.show_dialog(ft.AlertDialog(modal=True,bgcolor=WHITE,title=ft.Text(f"Enviar entrega: {t['titulo']}",weight=ft.FontWeight.BOLD,color=TEXT,size=18),content=ft.Container(width=480,content=ft.Column([ft.Text("Anexe os arquivos do que você desenvolveu.",color=MUTED,size=13),la,link_acao(ft.Icons.UPLOAD_FILE_ROUNDED,"Anexar arquivos",anexar),cn],spacing=14,tight=True,horizontal_alignment=ft.CrossAxisAlignment.STRETCH)),actions=[ft.TextButton(content=ft.Text("Cancelar",color=MUTED),on_click=lambda ev:page.pop_dialog()),ft.Button(content=ft.Text("Enviar entrega",color=WHITE,weight=ft.FontWeight.W_600),bgcolor=PURPLE,style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),on_click=enviar)]))
    def simular_aprovacao(t):
        def tratar(ev):
            try: r=db.aprovar_entrega(t["id"],id_dev)
            except (ValueError,PermissionError) as erro: avisar(f"Não foi possível aprovar: {erro}"); return
            t["status"]="aceita"; conta["xp"]=r["pontuacao_total"]
            registrar(ft.Icons.CHECK_CIRCLE_ROUNDED,"Entrega aprovada",f"{t['titulo']} · {t['empresa']}","ACEITA",GREEN); mostrar()
            avisar(f"Aprovada! +{r['xp_ganho']} XP."+(f" Subiu para o nível {nivel_de(conta['xp'])}!" if r["subiu_nivel"] else ""))
        return tratar
    def abrir_chat(n,r=""): ui["empresa_chat"]=n; ui["rascunho"]=r; mostrar("mensagens")
    def ver_projetos_da_empresa(n): ui["empresa"]=n; ui["cat"]="todas"; ui["busca"]=""; mostrar("projetos")
    def abrir_empresa(n): ui["empresa_busca"]=n; mostrar("empresas")

    def view_dashboard():
        xp=conta["xp"]; nv=nivel_de(xp); pn=(xp%XP_POR_NIVEL)/XP_POR_NIVEL
        pegas=len(tarefas); ent=len(tarefas_com("analise","aceita")); ap=len(tarefas_com("aceita")); em=tarefas_com("andamento","analise"); novo=xp==0 and pegas==0
        def buscar(ev): ui["busca"]=(ev.control.value or "").strip(); ui["empresa"]=None; ui["cat"]="todas"; mostrar("projetos")
        cab=ft.Row([ft.Column([ft.Text("Dashboard",size=26,color=TEXT,weight=ft.FontWeight.BOLD),ft.Text(f"Bem-vindo, {primeiro_nome()}! Sua conta foi criada." if novo else f"Bem-vindo de volta, {primeiro_nome()}!",color=MUTED,size=13)],spacing=5,expand=True),ft.TextField(hint_text="Buscar projetos...",hint_style=ft.TextStyle(color="#A29DB4"),prefix_icon=ft.Icon(ft.Icons.SEARCH,color=MUTED,size=18),border_radius=12,border_color=BORDER,focused_border_color=PURPLE,bgcolor=WHITE,filled=True,text_size=12,width=220,content_padding=ft.Padding.symmetric(horizontal=10,vertical=10),on_submit=buscar),ft.Container(content=ft.Icon(ft.Icons.NOTIFICATIONS_NONE_ROUNDED,color=MUTED,size=21),padding=11,bgcolor=WHITE,border=ft.Border.all(1,BORDER),border_radius=12,on_click=lambda e:avisar("Sem notificações novas."))],spacing=12,vertical_alignment=ft.CrossAxisAlignment.CENTER)
        banner=ft.Container(padding=22,border_radius=18,gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT,end=ft.Alignment.BOTTOM_RIGHT,colors=["#6C3CE9","#4820A8"]),content=ft.Row([ft.Column([ft.Row([ft.Icon(ft.Icons.AUTO_AWESOME,color="#E0D3FF",size=18),ft.Text("SUA JORNADA DE DESENVOLVEDOR",color="#E0D3FF",size=10,weight=ft.FontWeight.BOLD)],spacing=8),ft.Text("Sua jornada começa agora!" if novo else "Continue evoluindo!",color=WHITE,size=21,weight=ft.FontWeight.BOLD),ft.Text("Aceite seu primeiro projeto para ganhar XP." if novo else f"Você já fez {ent} entrega(s).",color="#E1D8FF",size=12),ft.Container(height=5),ft.Row([ft.Text(f"Próximo nível: {nv+1:02d}",color=WHITE,size=11,weight=ft.FontWeight.W_600),ft.Container(expand=True),ft.Text(f"{int(pn*100)}%",color=WHITE,size=11,weight=ft.FontWeight.BOLD)]),ft.ProgressBar(value=pn,color="#D8C8FF",bgcolor=ft.Colors.with_opacity(0.21,WHITE),height=7,border_radius=8),ft.Text(f"{fmt(xp%XP_POR_NIVEL)} / {fmt(XP_POR_NIVEL)} XP para o próximo nível",color="#E1D8FF",size=10)],spacing=9,expand=True),ft.Container(content=ft.Column([ft.Icon(ft.Icons.MILITARY_TECH_ROUNDED,color="#F9D976",size=42),ft.Text(f"NÍVEL {nv:02d}",color="#F9D976",size=11,weight=ft.FontWeight.BOLD),ft.Text(nome_do_nivel(nv),color=WHITE,size=10)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=5),padding=ft.Padding.all(18),bgcolor=ft.Colors.with_opacity(0.09,WHITE),border_radius=16)],spacing=20,vertical_alignment=ft.CrossAxisAlignment.CENTER))
        taxa=f"{round(ap*100/ent)}% de aprovação" if ent else "Sem entregas ainda"
        stats=ft.Row([stat_card(ft.Icons.STAR_ROUNDED,"Pontuação total",f"{fmt(xp)} XP",f"Nível {nv} · {nome_do_nivel(nv)}" if xp else "Nenhum ponto ainda",PURPLE,xp>0),stat_card(ft.Icons.TASK_ALT_ROUNDED,"Tarefas aceitas",str(pegas),f"{ent} concluídas",GREEN,pegas>0),stat_card(ft.Icons.FOLDER_SPECIAL_ROUNDED,"Projetos ativos",f"{len(em):02d}","Em desenvolvimento" if em else "Nenhum em andamento",BLUE,len(em)>0),stat_card(ft.Icons.VERIFIED_ROUNDED,"Entregas aprovadas",str(ap),taxa,ORANGE,ap>0)],spacing=14)
        projetos=(ft.Column([project_card(t["titulo"],t["empresa"],t["categoria"],t["progresso"]/100,CATEGORIAS[t["categoria"]][0],t["prazo"],CATEGORIAS[t["categoria"]][1]) for t in em],spacing=12) if em else caixa(estado_vazio(ft.Icons.FOLDER_OPEN_ROUNDED,"Nenhum projeto em andamento","Quando você pegar um projeto, ele aparece aqui.",botao_primario("Explorar projetos",ft.Icons.SEARCH,lambda e:mostrar("projetos"))),padding=ft.Padding.symmetric(horizontal=18,vertical=34)))
        ativ=(caixa(ft.Column([activity_row(*a) for a in atividades[:4]],spacing=0),padding=ft.Padding.symmetric(horizontal=16,vertical=4)) if atividades else caixa(estado_vazio(ft.Icons.HISTORY_ROUNDED,"Nenhuma atividade ainda","Suas entregas aceitas aparecem aqui."),padding=ft.Padding.symmetric(horizontal=16,vertical=30)))
        dica=caixa(ft.Row([ft.Container(content=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE,color=ORANGE,size=22),bgcolor="#FFF4E5",padding=10,border_radius=12),ft.Column([ft.Text("Dica da comunidade",color=TEXT,size=12,weight=ft.FontWeight.BOLD),ft.Text("Mantenha seu perfil atualizado.",color=MUTED,size=11)],spacing=4,expand=True)],spacing=10),padding=16,on_click=lambda e:mostrar("perfil"))
        return ft.Column([cab,ft.Container(height=5),banner,stats,ft.Row([ft.Column([ft.Row([ft.Text("Projetos em andamento",color=TEXT,size=17,weight=ft.FontWeight.BOLD),ft.Container(expand=True),link_acao(ft.Icons.ARROW_FORWARD,"Ver todos",lambda e:mostrar("tarefas"))]),projetos],spacing=14,expand=3),ft.Column([ft.Row([ft.Text("Atividades recentes",color=TEXT,size=17,weight=ft.FontWeight.BOLD),ft.Container(expand=True),ft.Icon(ft.Icons.HISTORY_ROUNDED,color=MUTED,size=18)]),ativ,dica],spacing=14,expand=2)],spacing=18,vertical_alignment=ft.CrossAxisAlignment.START)],spacing=20,scroll=ft.ScrollMode.AUTO,expand=True)

    def projeto_card(p):
        cor,ic=CATEGORIAS[p["categoria"]]
        corpo=[ft.Row([ft.Container(content=ft.Icon(ic,color=cor,size=20),bgcolor=com_opacidade(cor),padding=10,border_radius=11),ft.Column([ft.Text(p["titulo"],color=TEXT,weight=ft.FontWeight.BOLD,size=14),ft.Row([ft.Icon(ft.Icons.BUSINESS_ROUNDED,color=MUTED,size=13),ft.Text(p["empresa"],color=MUTED,size=12)],spacing=5)],spacing=3,expand=True),selo(p["categoria"],cor)],spacing=12),ft.Text(p["descricao"],color=MUTED,size=12),ft.Row([ft.Row([ft.Icon(ft.Icons.PAYMENTS_ROUNDED,color=GREEN,size=15),ft.Text(brl(p["valor"]),color=TEXT,size=12,weight=ft.FontWeight.BOLD)],spacing=5,tight=True),ft.Row([ft.Icon(ft.Icons.BOLT_ROUNDED,color=PURPLE,size=15),ft.Text(f"{p['xp']} XP",color=TEXT,size=12,weight=ft.FontWeight.BOLD)],spacing=5,tight=True),ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED,color=MUTED,size=14),ft.Text(f"Prazo: {p['prazo']}",color=MUTED,size=12)],spacing=5,tight=True)],spacing=18,wrap=True,run_spacing=6)]
        if p.get("arquivos"): corpo.append(ft.Row([chip_arquivo(a["nome"],a.get("tamanho")) for a in p["arquivos"]],wrap=True,spacing=8,run_spacing=8))
        corpo.append(ft.Row([link_acao(ft.Icons.BUSINESS_ROUNDED,"Ver empresa",lambda e,n=p["empresa"]:abrir_empresa(n)),link_acao(ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED,"Mensagem",lambda e,pp=p:abrir_chat(pp["empresa"],f"Olá! Dúvida sobre \"{pp['titulo']}\".")),ft.Container(expand=True),botao_primario("Pegar projeto",ft.Icons.ROCKET_LAUNCH_ROUNDED,lambda e,pp=p:pegar_projeto(pp))]))
        return ft.Container(padding=18,bgcolor=WHITE,border=ft.Border.all(1,BORDER),border_radius=16,content=ft.Column(corpo,spacing=12))
    def view_projetos():
        lc=ft.Column(spacing=12)
        def desenhar():
            tm=ui["busca"].lower()
            vis=[p for p in catalogo if (ui["cat"]=="todas" or p["categoria"]==ui["cat"]) and (not ui["empresa"] or p["empresa"]==ui["empresa"]) and (not tm or tm in p["titulo"].lower() or tm in p["empresa"].lower() or tm in p["descricao"].lower())]
            lc.controls=[projeto_card(p) for p in vis] if vis else [caixa(estado_vazio(ft.Icons.FOLDER_OPEN_ROUNDED,"Nenhum projeto encontrado","Tente outra busca."),padding=ft.Padding.symmetric(horizontal=18,vertical=36))]
        def ao_buscar(ev): ui["busca"]=(ev.control.value or "").strip(); desenhar(); page.update()
        def def_cat(v):
            def tr(ev): ui["cat"]=v; mostrar()
            return tr
        def limpar(ev): ui["empresa"]=None; mostrar()
        chips=[chip_filtro("Todos",ui["cat"]=="todas",def_cat("todas"))]+[chip_filtro(c,ui["cat"]==c,def_cat(c)) for c in CATEGORIAS]
        if ui["empresa"]: chips.append(ft.Container(padding=ft.Padding.symmetric(horizontal=12,vertical=8),border_radius=20,bgcolor=PURPLE_LIGHT,border=ft.Border.all(1,PURPLE),on_click=limpar,content=ft.Row([ft.Text(f"Empresa: {ui['empresa']}",size=12,color=PURPLE,weight=ft.FontWeight.W_600),ft.Icon(ft.Icons.CLOSE_ROUNDED,size=14,color=PURPLE)],spacing=6,tight=True)))
        cb=ft.TextField(hint_text="Buscar por título, empresa ou descrição...",hint_style=ft.TextStyle(color="#A29DB4"),prefix_icon=ft.Icon(ft.Icons.SEARCH,color=MUTED,size=18),value=ui["busca"],border_radius=12,border_color=BORDER,focused_border_color=PURPLE,bgcolor=WHITE,filled=True,text_size=13,content_padding=ft.Padding.symmetric(horizontal=10,vertical=10),on_change=ao_buscar)
        desenhar(); ativos=len(tarefas_com("andamento"))
        info=ft.Container(padding=ft.Padding.symmetric(horizontal=14,vertical=10),bgcolor=PURPLE_LIGHT,border_radius=12,content=ft.Text(f"Em andamento: {ativos} de {MAX_ATIVOS}",color=PURPLE,size=12,weight=ft.FontWeight.W_600))
        return ft.Column([cabecalho("Projetos","Escolha um projeto para ganhar XP.",info),cb,ft.Row(chips,wrap=True,spacing=8,run_spacing=8),lc],spacing=18,scroll=ft.ScrollMode.AUTO,expand=True)

    def tarefa_card(t):
        lm=link_acao(ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED,"Mensagem",lambda e,tt=t:abrir_chat(tt["empresa"],f"Olá! Sobre \"{tt['titulo']}\": "))
        cor,ic=CATEGORIAS[t["categoria"]]; ts,cs=SITUACOES[t["status"]]
        corpo=[ft.Row([ft.Container(content=ft.Icon(ic,color=cor,size=20),bgcolor=com_opacidade(cor),padding=10,border_radius=11),ft.Column([ft.Text(t["titulo"],color=TEXT,weight=ft.FontWeight.BOLD,size=14),ft.Text(f"{t['empresa']}  ·  Prazo: {t['prazo']}  ·  {brl(t['valor'])}  ·  {t['xp']} XP",color=MUTED,size=12)],spacing=3,expand=True),selo(t["categoria"],cor),selo(ts,cs)],spacing=10),ft.Row([ft.Text("Progresso",color=MUTED,size=12),ft.Container(expand=True),ft.Text(f"{t['progresso']}%",color=TEXT,size=12,weight=ft.FontWeight.BOLD)]),ft.ProgressBar(value=t["progresso"]/100,color=GREEN if t["status"]=="aceita" else cor,bgcolor="#F0EDF7",height=6,border_radius=8)]
        if t["status"]=="andamento": corpo.append(ft.Row([ft.Text("Atualizar progresso",color=MUTED,size=12),ft.Slider(min=0,max=100,divisions=20,value=t["progresso"],label="{value}%",active_color=cor,expand=True,on_change_end=lambda e,tt=t:atualizar_progresso(tt,e.control.value))],spacing=10))
        if t["entrega"] and t["entrega"]["arquivos"]: corpo.append(ft.Row([chip_arquivo(a["nome"],a.get("tamanho")) for a in t["entrega"]["arquivos"]],wrap=True,spacing=8,run_spacing=8))
        if t["status"]=="andamento":
            pr=t["progresso"]>=100
            corpo.append(ft.Row([link_acao(ft.Icons.UNDO_ROUNDED,"Desistir",lambda e,tt=t:abrir_desistencia(tt),RED),lm,ft.Container(expand=True),ft.Text("" if pr else "Chegue a 100% para entregar",color=MUTED,size=11),botao_primario("Enviar entrega",ft.Icons.UPLOAD_ROUNDED,(lambda e,tt=t:abrir_entrega(tt)) if pr else (lambda e:avisar("Leve a 100% para enviar.")),ativo=pr)],spacing=10,vertical_alignment=ft.CrossAxisAlignment.CENTER))
        elif t["status"]=="analise":
            ln=[ft.Icon(ft.Icons.HOURGLASS_TOP_ROUNDED,color=ORANGE,size=16),ft.Text("Aguardando aprovação da empresa",color=ORANGE,size=12,weight=ft.FontWeight.W_500),ft.Container(expand=True),lm]
            if MODO_TESTE: ln.append(link_acao(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,"Simular aprovação (teste)",simular_aprovacao(t)))
            corpo.append(ft.Row(ln,spacing=6))
        else: corpo.append(ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED,color=GREEN,size=16),ft.Text(f"Aprovada · +{t['xp']} XP",color=GREEN,size=12,weight=ft.FontWeight.W_600),ft.Container(expand=True),lm],spacing=6))
        return ft.Container(padding=18,bgcolor=WHITE,border=ft.Border.all(1,BORDER),border_radius=16,content=ft.Column(corpo,spacing=12))
    def view_tarefas():
        f=ui["filtro_tarefa"]; vis=tarefas if f=="todas" else tarefas_com(f)
        def def_(v):
            def tr(ev): ui["filtro_tarefa"]=v; mostrar()
            return tr
        if vis: lista=ft.Column([tarefa_card(t) for t in vis],spacing=12)
        elif tarefas: lista=caixa(estado_vazio(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,"Nenhuma tarefa nesta situação","Troque o filtro."),padding=ft.Padding.symmetric(horizontal=18,vertical=36))
        else: lista=caixa(estado_vazio(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,"Você ainda não pegou nenhum projeto","Escolha um projeto.",botao_primario("Ver projetos",ft.Icons.SEARCH,lambda e:mostrar("projetos"))),padding=ft.Padding.symmetric(horizontal=18,vertical=40))
        return ft.Column([cabecalho("Minhas tarefas","Atualize progresso, envie entrega e acompanhe aprovação."),ft.Row([chip_filtro("Todas",f=="todas",def_("todas")),chip_filtro("Em andamento",f=="andamento",def_("andamento")),chip_filtro("Em análise",f=="analise",def_("analise")),chip_filtro("Aceitas",f=="aceita",def_("aceita"))],spacing=8,wrap=True),lista],spacing=18,scroll=ft.ScrollMode.AUTO,expand=True)

    def view_empresas():
        grade=ft.Row(wrap=True,spacing=16,run_spacing=16,vertical_alignment=ft.CrossAxisAlignment.START)
        filtro={"texto":ui.pop("empresa_busca","")}; ts=ft.Text("",color=PURPLE,size=12,weight=ft.FontWeight.W_600)
        def empresa_card(e):
            ab=len([p for p in catalogo if p["empresa"]==e["nome"]]); jt=any(t["empresa"]==e["nome"] for t in tarefas); sg=e["nome"] in seguindo
            def alt(ev,n=e["nome"]):
                if n in seguindo: seguindo.remove(n); db.deixar_seguir_empresa(id_dev,n)
                else: seguindo.add(n); db.seguir_empresa(id_dev,n)
                desenhar(); page.update()
            def bc(ic,tx,oc,pf=False): return ft.Container(expand=True,padding=ft.Padding.symmetric(horizontal=10,vertical=9),border_radius=10,border=ft.Border.all(1,PURPLE),bgcolor=PURPLE_LIGHT if pf else None,on_click=oc,content=ft.Row([ft.Icon(ic,color=PURPLE,size=15),ft.Text(tx,color=PURPLE,size=12,weight=ft.FontWeight.W_600)],alignment=ft.MainAxisAlignment.CENTER,spacing=6,tight=True))
            rod=ft.Column([ft.Row([bc(ft.Icons.FAVORITE_ROUNDED if sg else ft.Icons.FAVORITE_BORDER_ROUNDED,"Seguindo" if sg else "Seguir",alt,pf=sg),bc(ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED,"Mensagem",lambda ev,n=e["nome"]:abrir_chat(n))],spacing=8),ft.Row([ft.Container(expand=True,padding=ft.Padding.symmetric(horizontal=14,vertical=11),bgcolor=PURPLE,border_radius=12,on_click=lambda ev,n=e["nome"]:ver_projetos_da_empresa(n),content=ft.Row([ft.Icon(ft.Icons.ARROW_FORWARD,color=WHITE,size=16),ft.Text("Ver projetos",color=WHITE,size=13,weight=ft.FontWeight.W_600)],alignment=ft.MainAxisAlignment.CENTER,spacing=8,tight=True))])],spacing=8)
            sel=[selo(f"{ab} PROJETO(S) ABERTO(S)",PURPLE if ab else MUTED)]
            if jt: sel.append(selo("VOCÊ JÁ TRABALHOU AQUI",GREEN))
            return ft.Container(width=310,padding=18,bgcolor=WHITE,border=ft.Border.all(1,BORDER),border_radius=16,content=ft.Column([ft.Row([avatar(e["nome"],44),ft.Column([ft.Text(e["nome"],color=TEXT,size=14,weight=ft.FontWeight.BOLD,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),ft.Text(f"{e.get('area','')} · {e.get('cidade','')}",color=MUTED,size=11,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS)],spacing=3,expand=True)],spacing=12),ft.Row([estrelas_fixas(e.get("nota",5)),ft.Text(f"{e.get('nota',0):.1f}".replace(".",","),color=TEXT,size=12,weight=ft.FontWeight.BOLD)],spacing=6),ft.Text(e.get("descricao",""),color=MUTED,size=12),ft.Row(sel,wrap=True,spacing=6,run_spacing=6),rod],spacing=12))
        def desenhar():
            ts.value=f"Seguindo: {len(seguindo)}"; tm=filtro["texto"].lower()
            it=[e for e in db.buscar_empresas() if not tm or tm in e["nome"].lower() or tm in e.get("area","").lower()]
            grade.controls=[empresa_card(e) for e in it] or [caixa(estado_vazio(ft.Icons.BUSINESS_ROUNDED,"Nenhuma empresa encontrada","Tente outro nome."),padding=ft.Padding.symmetric(horizontal=40,vertical=36))]
        def ao_buscar(ev): filtro["texto"]=(ev.control.value or "").strip(); desenhar(); page.update()
        cb=ft.TextField(hint_text="Buscar empresa por nome ou área...",hint_style=ft.TextStyle(color="#A29DB4"),prefix_icon=ft.Icon(ft.Icons.SEARCH,color=MUTED,size=18),value=filtro["texto"],border_radius=12,border_color=BORDER,focused_border_color=PURPLE,bgcolor=WHITE,filled=True,text_size=13,content_padding=ft.Padding.symmetric(horizontal=10,vertical=10),on_change=ao_buscar)
        desenhar(); res=ft.Container(padding=ft.Padding.symmetric(horizontal=14,vertical=10),bgcolor=PURPLE_LIGHT,border_radius=12,content=ts)
        return ft.Column([cabecalho("Empresas","Conheça quem publica projetos e siga as favoritas.",res),cb,grade],spacing=18,scroll=ft.ScrollMode.AUTO,expand=True)

    def view_ranking():
        itens=ranking_completo(); eu=next((i for i in itens if i["eu"]),None)
        if not eu: eu={"nome":perfil["nome"],"xp":conta["xp"],"eu":True,"pos":len(itens)+1}; itens.append(eu)
        ac=next((i for i in itens if i["pos"]==eu["pos"]-1),None)
        tm=f"Faltam {fmt(ac['xp']-eu['xp']+1)} XP para ultrapassar {ac['nome']}." if ac else "Você lidera o ranking!"
        banner=ft.Container(padding=22,border_radius=18,gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT,end=ft.Alignment.BOTTOM_RIGHT,colors=["#6C3CE9","#4820A8"]),content=ft.Row([ft.Container(content=ft.Column([ft.Text("SUA POSIÇÃO",color="#E0D3FF",size=10,weight=ft.FontWeight.BOLD),ft.Text(f"#{eu['pos']}",color=WHITE,size=36,weight=ft.FontWeight.BOLD)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=2),padding=ft.Padding.symmetric(horizontal=24,vertical=14),bgcolor=ft.Colors.with_opacity(0.12,WHITE),border_radius=16),ft.Column([ft.Text(f"{fmt(eu['xp'])} XP  ·  Nível {nivel_de(eu['xp'])} ({nome_do_nivel(nivel_de(eu['xp']))})",color=WHITE,size=18,weight=ft.FontWeight.BOLD),ft.Text(f"{eu['pos']}º de {len(itens)} desenvolvedores",color="#E1D8FF",size=12),ft.Text(tm,color="#E1D8FF",size=12)],spacing=6,expand=True)],spacing=20,vertical_alignment=ft.CrossAxisAlignment.CENTER))
        med={1:GOLD,2:"#A8A8B3",3:"#C98A52"}
        def cp(i):
            c=med[i["pos"]]
            return ft.Container(expand=True,padding=18,bgcolor=WHITE,border=ft.Border.all(2 if i["eu"] else 1,PURPLE if i["eu"] else BORDER),border_radius=16,content=ft.Column([ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED,color=c,size=30),avatar(i["nome"],46),ft.Text(f"{i['nome']}{' (você)' if i['eu'] else ''}",color=TEXT,size=13,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER),ft.Text(f"{fmt(i['xp'])} XP",color=PURPLE,size=13,weight=ft.FontWeight.BOLD),selo(f"{i['pos']}º LUGAR",c)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=8))
        podio=ft.Row([cp(i) for i in itens[:3]],spacing=14); linhas=[]
        for i in itens[3:]:
            linhas.append(ft.Container(padding=ft.Padding.symmetric(horizontal=12,vertical=11),border_radius=12,bgcolor=PURPLE_LIGHT if i["eu"] else None,border=ft.Border.only(bottom=ft.BorderSide(1,BORDER)) if not i["eu"] else None,content=ft.Row([ft.Text(f"#{i['pos']}",color=PURPLE if i["eu"] else MUTED,size=13,weight=ft.FontWeight.BOLD,width=36),avatar(i["nome"],34),ft.Column([ft.Text(f"{i['nome']}{' (você)' if i['eu'] else ''}",color=TEXT,size=13,weight=ft.FontWeight.W_600),ft.Text(f"Nível {nivel_de(i['xp'])} · {nome_do_nivel(nivel_de(i['xp']))}",color=MUTED,size=11)],spacing=2,expand=True),ft.Text(f"{fmt(i['xp'])} XP",color=TEXT,size=13,weight=ft.FontWeight.BOLD)],spacing=12)))
        tab=caixa(ft.Column([ft.Text("Classificação geral",color=TEXT,size=16,weight=ft.FontWeight.BOLD),ft.Column(linhas,spacing=2)],spacing=12),padding=ft.Padding.symmetric(horizontal=16,vertical=18)) if linhas else ft.Container()
        info=caixa(ft.Row([ft.Container(content=ft.Icon(ft.Icons.LIGHTBULB_OUTLINE,color=ORANGE,size=22),bgcolor="#FFF4E5",padding=10,border_radius=12),ft.Column([ft.Text("Como subir no ranking",color=TEXT,size=12,weight=ft.FontWeight.BOLD),ft.Text(f"Cada entrega aprovada dá XP. A cada {fmt(XP_POR_NIVEL)} XP você sobe de nível.",color=MUTED,size=11)],spacing=4,expand=True)],spacing=10),padding=16)
        return ft.Column([cabecalho("Ranking","Veja como você se compara aos outros devs."),banner,podio,tab,info],spacing=20,scroll=ft.ScrollMode.AUTO,expand=True)

    def view_perfil():
        xp=conta["xp"]; nv=nivel_de(xp); rs=list(perfil["habilidades"]); ls=ft.Row(wrap=True,spacing=8,run_spacing=8)
        cn=campo_texto("Nome",value=perfil["nome"]); cb=campo_texto("Sobre você",value=perfil["bio"],multiline=True,min_lines=3,max_lines=5)
        cl=campo_texto("Localização",value=perfil["localizacao"],prefix_icon=ft.Icon(ft.Icons.LOCATION_ON_OUTLINED,color=MUTED,size=18))
        cg=campo_texto("GitHub",value=perfil["github"],prefix_icon=ft.Icon(ft.Icons.LINK_ROUNDED,color=MUTED,size=18))
        cp=campo_texto("Portfólio",value=perfil["portfolio"],prefix_icon=ft.Icon(ft.Icons.PUBLIC_ROUNDED,color=MUTED,size=18))
        cs=campo_texto("Nova habilidade (ex.: Python)",expand=True)
        def desenhar_sk():
            ch=[]
            for i,s in enumerate(rs):
                def rm(ev,idx=i): rs.pop(idx); desenhar_sk(); page.update()
                ch.append(ft.Container(padding=ft.Padding.symmetric(horizontal=12,vertical=7),border_radius=20,bgcolor=PURPLE_LIGHT,content=ft.Row([ft.Text(s,color=PURPLE,size=12,weight=ft.FontWeight.W_600),ft.Container(content=ft.Icon(ft.Icons.CLOSE_ROUNDED,color=PURPLE,size=14),on_click=rm)],spacing=6,tight=True)))
            ls.controls=ch or [ft.Text("Nenhuma habilidade adicionada ainda.",color=MUTED,size=12)]
        async def add_sk(ev=None):
            tx=(cs.value or "").strip()
            if not tx: return
            if tx.lower() not in [s.lower() for s in rs]: rs.append(tx)
            cs.value=""; desenhar_sk(); page.update(); await cs.focus()
        cs.on_submit=add_sk
        def salvar(ev):
            nn=(cn.value or "").strip()
            if not nn: cn.error="Informe seu nome."; page.update(); return
            cn.error=None
            db.salvar_perfil_dev(id_usuario,nn,(cb.value or "").strip(),(cl.value or "").strip(),(cg.value or "").strip(),(cp.value or "").strip(),list(rs))
            perfil.update(nome=nn,bio=(cb.value or "").strip(),localizacao=(cl.value or "").strip(),github=(cg.value or "").strip(),portfolio=(cp.value or "").strip(),habilidades=list(rs))
            mostrar(); avisar("Perfil atualizado!")
        desenhar_sk(); ent=len(tarefas_com("analise","aceita")); ap=len(tarefas_com("aceita")); pc=bool(perfil["bio"] and perfil["habilidades"])
        conq=[("Primeiro projeto","Pegue seu primeiro projeto",ft.Icons.ROCKET_LAUNCH_ROUNDED,len(tarefas)>=1),("Primeira entrega","Envie sua primeira entrega",ft.Icons.UPLOAD_ROUNDED,ent>=1),("Aprovado!","Tenha uma entrega aprovada",ft.Icons.VERIFIED_ROUNDED,ap>=1),("Nível 1","Chegue a 1.000 XP",ft.Icons.MILITARY_TECH_ROUNDED,nv>=1),("Top 5","Entre nos 5 do ranking",ft.Icons.LEADERBOARD_ROUNDED,minha_posicao()<=5),("Perfil completo","Preencha bio e habilidades",ft.Icons.PERSON_OUTLINE_ROUNDED,pc)]
        def medalha(ti,de,ic,ok):
            c=GOLD if ok else "#CFCBDD"
            return ft.Container(width=190,padding=14,bgcolor=WHITE,border=ft.Border.all(1,GOLD if ok else BORDER),border_radius=14,content=ft.Row([ft.Container(content=ft.Icon(ic,color=c,size=22),bgcolor=com_opacidade(c,0.14),padding=9,border_radius=11),ft.Column([ft.Text(ti,color=TEXT if ok else MUTED,size=12,weight=ft.FontWeight.BOLD),ft.Text(de,color=MUTED,size=10)],spacing=3,expand=True)],spacing=10))
        cr=caixa(ft.Column([avatar(perfil["nome"],84),ft.Text(perfil["nome"],color=TEXT,size=18,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER),ft.Text(usuario.get("email") or "Desenvolvedor",color=MUTED,size=12),selo(f"NÍVEL {nv:02d} · {nome_do_nivel(nv).upper()}",PURPLE),ft.Divider(color=BORDER,height=12),ft.Row([ft.Text("Pontuação",color=MUTED,size=12),ft.Container(expand=True),ft.Text(f"{fmt(xp)} XP",color=TEXT,size=12,weight=ft.FontWeight.BOLD)]),ft.Row([ft.Text("Ranking",color=MUTED,size=12),ft.Container(expand=True),ft.Text(f"#{minha_posicao()}",color=TEXT,size=12,weight=ft.FontWeight.BOLD)]),ft.Row([ft.Text("Tarefas pegas",color=MUTED,size=12),ft.Container(expand=True),ft.Text(str(len(tarefas)),color=TEXT,size=12,weight=ft.FontWeight.BOLD)]),ft.Row([ft.Text("Entregas aprovadas",color=MUTED,size=12),ft.Container(expand=True),ft.Text(str(ap),color=TEXT,size=12,weight=ft.FontWeight.BOLD)]),ft.Row([ft.Text("Empresas seguidas",color=MUTED,size=12),ft.Container(expand=True),ft.Text(str(len(seguindo)),color=TEXT,size=12,weight=ft.FontWeight.BOLD)])],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=10),padding=22,width=290)
        frm=caixa(ft.Column([ft.Text("Dados do perfil",color=TEXT,size=16,weight=ft.FontWeight.BOLD),cn,cb,ft.Row([ft.Container(cl,expand=True)],spacing=12),ft.Row([ft.Container(cg,expand=True),ft.Container(cp,expand=True)],spacing=12),ft.Text("Habilidades",color=MUTED,size=12,weight=ft.FontWeight.W_600),ls,ft.Row([cs,botao_primario("Adicionar",ft.Icons.ADD_ROUNDED,add_sk)],spacing=10),ft.Row([ft.Container(expand=True),botao_primario("Salvar alterações",ft.Icons.SAVE_ROUNDED,salvar)])],spacing=14,horizontal_alignment=ft.CrossAxisAlignment.STRETCH),padding=22,expand=True)
        return ft.Column([cabecalho("Meu perfil","Mantenha seus dados atualizados."),ft.Row([cr,frm],spacing=18,vertical_alignment=ft.CrossAxisAlignment.START),ft.Text("Conquistas",color=TEXT,size=17,weight=ft.FontWeight.BOLD),ft.Row([medalha(*c) for c in conq],wrap=True,spacing=12,run_spacing=12)],spacing=20,scroll=ft.ScrollMode.AUTO,expand=True)

    def bolha(m):
        mn=m["de"]=="dev"; lg=max(90,min(380,len(m["texto"])*7.2+34))
        return ft.Row([ft.Container(width=lg,padding=ft.Padding.symmetric(horizontal=14,vertical=10),border_radius=14,bgcolor=PURPLE if mn else "#F1EEF9",content=ft.Column([ft.Text(m["texto"],color=WHITE if mn else TEXT,size=13),ft.Text(m["hora"],color="#D9CFFF" if mn else MUTED,size=10)],spacing=4,horizontal_alignment=ft.CrossAxisAlignment.START))],alignment=ft.MainAxisAlignment.END if mn else ft.MainAxisAlignment.START)
    def view_mensagens():
        topo=cabecalho("Mensagens","Converse com as empresas.")
        el=db.buscar_empresas(); nomes=[e["nome"] for e in el]
        def ordem(n): return (-ultima_msg.get(n,0),n)
        if ui["empresa_chat"] not in nomes: ui["empresa_chat"]=sorted(nomes,key=ordem)[0] if nomes else ""
        atual=ui["empresa_chat"]; info=next((e for e in el if e["nome"]==atual),{"nome":atual,"area":"","cidade":"","nota":0,"descricao":""})
        ras=ui["rascunho"]; ui["rascunho"]=""; altura=max(460,(page.height or 800)-200)
        previas={}; lc=ft.Column(spacing=4,scroll=ft.ScrollMode.AUTO,expand=True)
        def desenhar_l(termo=""):
            it=[]
            for n in sorted(nomes,key=ordem):
                if termo and termo.lower() not in n.lower(): continue
                emp=next((x for x in el if x["nome"]==n),None); ms=mensagens.get(n,[])
                pv=ft.Text(ms[-1]["texto"] if ms else (emp["area"] if emp else ""),color=MUTED,size=11,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS); previas[n]=pv
                it.append(ft.Container(padding=12,border_radius=12,bgcolor=PURPLE_LIGHT if n==atual else None,on_click=lambda ev,nn=n:abrir_chat(nn),content=ft.Row([avatar(n,38),ft.Column([ft.Text(n,color=TEXT,size=13,weight=ft.FontWeight.W_600,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),pv],spacing=3,expand=True)],spacing=10)))
            lc.controls=it or [ft.Text("Nenhuma empresa encontrada.",color=MUTED,size=12)]
        def ao_buscar(ev): desenhar_l((ev.control.value or "").strip()); page.update()
        desenhar_l()
        lista=ft.Container(width=290,height=altura,padding=10,bgcolor=WHITE,border=ft.Border.all(1,BORDER),border_radius=16,content=ft.Column([ft.TextField(hint_text="Buscar empresa...",hint_style=ft.TextStyle(color="#A29DB4"),prefix_icon=ft.Icon(ft.Icons.SEARCH,color=MUTED,size=18),border_radius=12,border_color=BORDER,focused_border_color=PURPLE,text_size=12,content_padding=ft.Padding.symmetric(horizontal=10,vertical=8),on_change=ao_buscar),lc],spacing=8))
        lm=ft.Column(spacing=8,expand=True,scroll=ft.ScrollMode.AUTO,auto_scroll=True)
        def desenhar_m():
            ms=mensagens.get(atual,[]); lm.controls=[bolha(m) for m in ms] or [ft.Container(padding=ft.Padding.symmetric(vertical=40),alignment=ft.Alignment.CENTER,content=ft.Text(f"Envie a primeira mensagem para {atual}.",color=MUTED,size=12,text_align=ft.TextAlign.CENTER))]
        cm=ft.TextField(hint_text="Escreva uma mensagem...",hint_style=ft.TextStyle(color="#A29DB4"),value=ras,border_radius=12,border_color=BORDER,focused_border_color=PURPLE,cursor_color=PURPLE,text_size=13,expand=True,content_padding=ft.Padding.symmetric(horizontal=14,vertical=12))
        def usar(t):
            async def tr(ev): cm.value=t; page.update(); await cm.focus()
            return tr
        sug=["Tenho uma dúvida sobre um projeto.","Posso enviar uma proposta?","Qual o prazo para resposta?"]
        cr=ft.Row([chip_filtro(t,False,usar(t)) for t in sug],wrap=True,spacing=8,run_spacing=8,visible=not mensagens.get(atual))
        async def enviar(ev):
            tx=(cm.value or "").strip()
            if not tx: return
            idd=db.buscar_id_usuario_por_nome_empresa(atual)
            if idd: db.enviar_mensagem(id_usuario,idd,tx)
            ui["seq"]+=1; ultima_msg[atual]=ui["seq"]; mensagens.setdefault(atual,[]).append({"de":"dev","texto":tx,"hora":datetime.now().strftime("%H:%M")})
            cm.value=""; cr.visible=False; desenhar_m()
            if atual in previas: previas[atual].value=tx
            page.update(); await cm.focus()
        cm.on_submit=enviar; desenhar_m(); ab=len([p for p in catalogo if p["empresa"]==atual])
        painel=ft.Container(expand=True,height=altura,bgcolor=WHITE,border=ft.Border.all(1,BORDER),border_radius=16,content=ft.Column([ft.Container(padding=ft.Padding.symmetric(horizontal=18,vertical=14),border=ft.Border.only(bottom=ft.BorderSide(1,BORDER)),content=ft.Row([avatar(atual,40),ft.Column([ft.Text(atual,color=TEXT,size=14,weight=ft.FontWeight.BOLD),ft.Text(f"{info.get('area','')} · {ab} projeto(s) aberto(s)",color=MUTED,size=11)],spacing=3,expand=True),link_acao(ft.Icons.FOLDER_OPEN_ROUNDED,"Ver projetos",lambda ev,n=atual:ver_projetos_da_empresa(n))],spacing=12)),ft.Container(expand=True,padding=ft.Padding.symmetric(horizontal=18,vertical=12),content=lm),ft.Container(padding=ft.Padding.symmetric(horizontal=18),content=cr),ft.Container(padding=ft.Padding.all(14),border=ft.Border.only(top=ft.BorderSide(1,BORDER)),content=ft.Row([cm,ft.IconButton(icon=ft.Icons.SEND_ROUNDED,icon_color=WHITE,bgcolor=PURPLE,tooltip="Enviar",on_click=enviar,style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))],spacing=10))],spacing=0))
        return ft.Column([topo,ft.Row([lista,painel],spacing=16,vertical_alignment=ft.CrossAxisAlignment.START)],spacing=18,scroll=ft.ScrollMode.AUTO,expand=True)

    NAV=[("dashboard",ft.Icons.DASHBOARD_ROUNDED,"Dashboard"),("projetos",ft.Icons.FOLDER_OPEN_ROUNDED,"Projetos"),("tarefas",ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,"Minhas tarefas"),("empresas",ft.Icons.BUSINESS_ROUNDED,"Empresas"),("mensagens",ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED,"Mensagens"),("ranking",ft.Icons.LEADERBOARD_ROUNDED,"Ranking"),("perfil",ft.Icons.PERSON_OUTLINE_ROUNDED,"Meu perfil")]
    def item_menu(ch,ic,ro):
        sel=ui["tela"]==ch
        return ft.Container(content=ft.Row([ft.Icon(ic,size=20,color=WHITE if sel else "#B9B3D1"),ft.Text(ro,size=14,weight=ft.FontWeight.W_600 if sel else ft.FontWeight.NORMAL,color=WHITE if sel else "#C9C4DE")],spacing=14),padding=ft.Padding.symmetric(horizontal=16,vertical=13),bgcolor="#5A2FC7" if sel else None,border_radius=12,margin=ft.Margin.only(bottom=5),on_click=lambda e:mostrar(ch))
    def sair(e=None):
        if seletor in page.services: page.services.remove(seletor)
        if ao_sair: ao_sair()
        else: avisar("Abra pelo main.py para entrar e sair.")
    def conteudo_sidebar():
        ini="".join(p[0] for p in perfil["nome"].split()[:2]).upper()
        return ft.Column([ft.Row([ft.Container(content=ft.Icon(ft.Icons.CODE_ROUNDED,color=WHITE,size=24),bgcolor=PURPLE,padding=10,border_radius=13),ft.Column([ft.Text("DevSphere",color=WHITE,size=20,weight=ft.FontWeight.BOLD),ft.Text("DEV COMMUNITY",color="#A9A0C9",size=9,weight=ft.FontWeight.BOLD)],spacing=2)],spacing=10),ft.Container(height=28),ft.Text("MENU PRINCIPAL",color="#8F84B8",size=10,weight=ft.FontWeight.BOLD),ft.Container(height=8),*[item_menu(*n) for n in NAV],ft.Container(expand=True),ft.Container(padding=15,bgcolor="#34245B",border_radius=14,on_click=lambda e:mostrar("projetos"),content=ft.Column([ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED,color="#C7B4FF",size=25),ft.Text("Suba de nível!",color=WHITE,size=13,weight=ft.FontWeight.BOLD),ft.Text("Complete projetos e conquiste XP.",color="#C4BBDD",size=11),ft.Container(height=3),ft.Text("Ver projetos  →",color="#D6C9FF",size=12,weight=ft.FontWeight.BOLD)],spacing=8)),ft.Container(height=8),ft.Row([ft.CircleAvatar(content=ft.Text(ini,color=WHITE,weight=ft.FontWeight.BOLD),bgcolor="#8B5CF6",radius=20),ft.Column([ft.Text(perfil["nome"],color=WHITE,size=12,weight=ft.FontWeight.BOLD,no_wrap=True,overflow=ft.TextOverflow.ELLIPSIS),ft.Text("Desenvolvedor",color="#A9A0C9",size=10)],spacing=3,expand=True),ft.IconButton(icon=ft.Icons.LOGOUT_ROUNDED,tooltip="Sair",icon_color="#A9A0C9",icon_size=18,on_click=sair)],spacing=9)],spacing=0,expand=True)
    sidebar=ft.Container(width=245,bgcolor="#25164A",padding=ft.Padding.symmetric(horizontal=18,vertical=24)); area=ft.Container(expand=True,padding=ft.Padding.all(28))
    def construir():
        c={"dashboard":view_dashboard,"projetos":view_projetos,"tarefas":view_tarefas,"empresas":view_empresas,"mensagens":view_mensagens,"ranking":view_ranking,"perfil":view_perfil}
        sidebar.content=conteudo_sidebar(); area.content=c[ui["tela"]]()
    def mostrar(t=None):
        if t: ui["tela"]=t
        construir(); page.update()
    def ao_redimensionar(e=None):
        if ui["tela"]=="mensagens": mostrar()
    page.on_resize=ao_redimensionar; construir()
    page.add(ft.Row([sidebar,area],spacing=0,expand=True,vertical_alignment=ft.CrossAxisAlignment.STRETCH))

if __name__=="__main__": ft.run(dashboard)