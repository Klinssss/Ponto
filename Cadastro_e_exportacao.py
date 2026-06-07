import sqlite3
from customtkinter import *
from datetime import datetime, timedelta
from tkinter import ttk, messagebox, filedialog
import os
import hashlib
import json
import threading


# Configuração da aparência - TEMA MAIS CLARO
set_appearance_mode('light')
set_default_color_theme('blue')


class JanelaComIcone(CTkToplevel):
    """Classe base para todas as janelas com ícone"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.definir_icone_janela()

    def definir_icone_janela(self):
        """Define o ícone da janela"""
        try:
            if os.path.exists("icone.ico"):
                self.iconbitmap("icone.ico")
            elif os.path.exists("icone"):
                self.iconbitmap("icone")
        except:
            pass


class SistemaPontoEletronicoCompleto:
    def __init__(self):
        # 1. Criar a janela base imediatamente
        self.janela = CTk()
        self.timer_limpeza = None

        # Inicializações básicas de memória (quase instantâneas)
        self.conn = None
        self.cursor = None
        self.senha_hash = None
        self.cache_funcionarios = {}
        self.autenticado = False
        self.cache_funcionarios_completo = []
        self.abas_carregadas = {"ponto": True, "cadastro": False, "exportar": False, "movimentacoes": False,
                                "config": False}

        # Configurações de layout (sem forçar renderização pesada ainda)
        largura_janela = 580
        altura_janela = 595
        self.centralizar_janela_otimizado(largura_janela, altura_janela)
        self.janela.title('Ponto Eletrônico')
        self.janela.resizable(False, False)

        # 2. Agendar a construção da UI para ocorrer logo após o loop iniciar
        # Isso faz a janela "vazia" aparecer e logo em seguida o conteúdo brotar
        self.janela.after(1, self.configurar_interface_inicial)

    def configurar_interface_inicial(self):
        """Constrói apenas o essencial para a tela de ponto"""
        # Ícone e Temas
        self.definir_icone_janela()

        # Criar sistema de abas e a tela de ponto (prioridade máxima)
        self.criar_sistema_abas_lazy()
        self.atualizar_relogio()

        # Focar no campo de entrada
        if hasattr(self, 'entry_codigo_ponto'):
            self.entry_codigo_ponto.focus_set()

        # 3. Iniciar carregamento pesado com um pequeno delay para não travar a UI
        self.janela.after(100, self.iniciar_carregamento_background)

    def centralizar_janela_otimizado(self, largura, altura):
        """Centraliza sem chamar update_idletasks (mais rápido)"""
        largura_tela = self.janela.winfo_screenwidth()
        altura_tela = self.janela.winfo_screenheight()
        pos_x = (largura_tela // 2) - (largura // 2)
        pos_y = (altura_tela // 2) - (altura // 2)
        self.janela.geometry(f'{largura}x{altura}+{pos_x}+{pos_y}')

    def iniciar_carregamento_background(self):
        """Inicia carregamento de recursos em background - AGORA COMPLETO"""

        def carregar_tudo():
            # 1. Configurar banco de dados (agora em background)
            self.configurar_banco_dados()
            self.carregar_configuracoes_senha()
            
            # 2. Carregar cache de funcionários
            self.atualizar_cache_funcionarios()
            
            # 3. Carregar último ponto
            self.carregar_ultimo_ponto()
            
            # 4. Pré-carregar lista de funcionários
            self.carregar_funcionarios_background()
            
            # 5. Sinalizar que o sistema está pronto
            self.janela.after(0, lambda: self.label_status_sistema.configure(
                text="✅ Sistema carregado",
                text_color="#2AA876"
            ))

        # Usar thread para não bloquear a interface
        thread = threading.Thread(target=carregar_tudo, daemon=True)
        thread.start()

    def carregar_funcionarios_background(self):
        """Carrega funcionários em background para cache"""
        try:
            if self.cursor:
                self.cursor.execute('''
                                    SELECT codigo,
                                           nome,
                                           horario_entrada,
                                           horario_saida_almoco,
                                           horario_volta_almoco,
                                           horario_saida
                                    FROM funcionarios
                                    ORDER BY CAST(codigo AS INTEGER)
                                    ''')
                self.cache_funcionarios_completo = self.cursor.fetchall()
        except Exception as e:
            print(f"Erro ao carregar funcionários em background: {e}")

    def atualizar_cache_funcionarios(self):
        """Atualiza o cache de funcionários"""
        try:
            if self.cursor:
                self.cursor.execute("SELECT codigo, nome, departamento FROM funcionarios")
                funcionarios = self.cursor.fetchall()
                self.cache_funcionarios.clear()
                for codigo, nome, departamento in funcionarios:
                    self.cache_funcionarios[codigo] = (nome, departamento)
                self.ultima_atualizacao_cache = datetime.now()
        except Exception as e:
            print(f"Erro ao atualizar cache: {e}")

    def validar_entrada_numerica(self, texto):
        """Valida se a entrada contém apenas números"""
        return texto.isdigit() or texto == ""

    def definir_icone_janela(self):
        """Define o ícone da janela principal"""
        try:
            if os.path.exists("icone.ico"):
                self.janela.iconbitmap("icone.ico")
            elif os.path.exists("icone"):
                self.janela.iconbitmap("icone")
        except:
            pass

    def centralizar_janela(self, largura, altura):
        """Centraliza a janela na tela"""
        self.janela.update_idletasks()
        largura_tela = self.janela.winfo_screenwidth()
        altura_tela = self.janela.winfo_screenheight()
        pos_x = (largura_tela // 2) - (largura // 2)
        pos_y = (altura_tela // 2) - (altura // 2)
        self.janela.geometry(f'{largura}x{altura}+{pos_x}+{pos_y}')

    def hash_senha(self, senha):
        """Cria um hash SHA-256 da senha"""
        return hashlib.sha256(senha.encode()).hexdigest()

    def carregar_configuracoes_senha(self):
        """Carrega ou cria as configurações de senha"""
        try:
            if os.path.exists('config_seguranca.json'):
                with open('config_seguranca.json', 'r') as f:
                    config = json.load(f)
                    self.senha_hash = config.get('senha_hash', self.hash_senha('admin123'))
            else:
                # Senha padrão: admin123
                self.senha_hash = self.hash_senha('admin123')
                self.salvar_configuracoes_senha()

        except Exception as e:
            self.senha_hash = self.hash_senha('admin123')

    def salvar_configuracoes_senha(self):
        """Salva as configurações de senha"""
        try:
            config = {'senha_hash': self.senha_hash}
            with open('config_seguranca.json', 'w') as f:
                json.dump(config, f)
        except Exception as e:
            messagebox.showerror('Erro', f'Erro ao salvar configurações: {str(e)}')

    def verificar_senha(self, senha):
        """Verifica se a senha está correta"""
        return self.hash_senha(senha) == self.senha_hash

    def alterar_senha(self, senha_atual, nova_senha):
        """Altera a senha do sistema"""
        if not self.verificar_senha(senha_atual):
            return False, "Senha atual incorreta!"

        if len(nova_senha) < 2:  # MUDADO: mínimo 2 caracteres
            return False, "A nova senha deve ter pelo menos 2 caracteres!"

        self.senha_hash = self.hash_senha(nova_senha)
        self.salvar_configuracoes_senha()
        return True, "Senha alterada com sucesso!"

    def alterar_senha_config(self):
        """Altera a senha a partir da aba de configurações"""
        senha_atual = self.entry_senha_atual.get()
        nova_senha = self.entry_nova_senha.get()
        conf_senha = self.entry_conf_senha.get()

        if not senha_atual or not nova_senha or not conf_senha:
            self.label_status_senha.configure(
                text="Preencha todos os campos!",
                text_color="red"
            )
            return

        if nova_senha != conf_senha:
            self.label_status_senha.configure(
                text="As senhas não coincidem!",
                text_color="red"
            )
            return

        sucesso, mensagem = self.alterar_senha(senha_atual, nova_senha)

        if sucesso:
            self.label_status_senha.configure(
                text=mensagem,
                text_color="#1F6AA5"
            )
            self.entry_senha_atual.delete(0, END)
            self.entry_nova_senha.delete(0, END)
            self.entry_conf_senha.delete(0, END)
        else:
            self.label_status_senha.configure(
                text=mensagem,
                text_color="red"
            )

    def configurar_banco_dados(self):
        """Configura o banco de dados SQLite - VERSÃO OTIMIZADA"""
        try:
            self.conn = sqlite3.connect('ponto_eletronico.db', check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # Verificação RÁPIDA se as tabelas existem
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS funcionarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE,
                    nome TEXT,
                    departamento TEXT,
                    observacao TEXT,
                    horario_entrada TEXT,
                    horario_saida_almoco TEXT,
                    horario_volta_almoco TEXT,
                    horario_saida TEXT
                )
            """)
            
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS registros_ponto (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_funcionario TEXT,
                    tipo TEXT,
                    data_hora DATETIME,
                    FOREIGN KEY (codigo_funcionario) REFERENCES funcionarios(codigo)
                )
            """)
            
            self.conn.commit()
            
        except Exception as e:
            print(f"Erro ao configurar banco: {e}")
            # Reagenda na thread principal com segurança
            self.janela.after(2000, lambda: self.configurar_banco_dados())

    def criar_sistema_abas_lazy(self):
        """Cria o sistema de abas principal com lazy loading"""
        # Criar widget de abas
        self.tabview = CTkTabview(self.janela)
        self.tabview.pack(fill='both', expand=True, padx=10, pady=10)

        # Adicionar abas (apenas a de ponto será carregada inicialmente)
        self.tab_ponto = self.tabview.add("🏠 Ponto Eletrônico")
        self.tab_cadastro = self.tabview.add("👥 Cadastro")
        self.tab_exportar = self.tabview.add("📊 Exportar")
        self.tab_movimentacoes = self.tabview.add("📋 Movimentações")
        self.tab_config = self.tabview.add("⚙️ Configurações")

        # Configurar apenas a aba de ponto inicialmente
        self.criar_aba_ponto()

        # Para outras abas, criar apenas um placeholder
        self.criar_placeholder_abas()

        # Bind para mudança de aba - lazy loading
        self.tabview.configure(command=self.verificar_acesso_e_carregar_aba)

    def criar_placeholder_abas(self):
        """Cria placeholders para abas não carregadas"""
        # Mapeamento dos nomes das abas para seus atributos
        mapa_abas = {
            "🏠 Ponto Eletrônico": "tab_ponto",
            "👥 Cadastro": "tab_cadastro",
            "📊 Exportar": "tab_exportar",
            "📋 Movimentações": "tab_movimentacoes",
            "⚙️ Configurações": "tab_config"
        }

        # Adicionar placeholders apenas nas abas que não são a de ponto
        for tab_name, attr_name in mapa_abas.items():
            if tab_name != "🏠 Ponto Eletrônico":
                tab = getattr(self, attr_name)
                label = CTkLabel(tab, text="Carregando...", font=('Arial', 16))
                label.pack(expand=True, pady=20)

    def verificar_acesso_e_carregar_aba(self):
        """Verifica acesso e carrega a aba sob demanda"""
        aba_selecionada = self.tabview.get()

        # Mapear nomes das abas para métodos
        mapa_abas = {
            "🏠 Ponto Eletrônico": ("ponto", None),
            "👥 Cadastro": ("cadastro", self.criar_aba_cadastro),
            "📊 Exportar": ("exportar", self.criar_aba_exportar),
            "📋 Movimentações": ("movimentacoes", self.criar_aba_movimentacoes),
            "⚙️ Configurações": ("config", self.criar_aba_configuracoes)
        }

        nome_aba, metodo_criacao = mapa_abas.get(aba_selecionada, (None, None))

        if nome_aba and not self.abas_carregadas[nome_aba]:
            # Carregar aba sob demanda
            if metodo_criacao:
                # Limpar placeholder
                attr_name = f"tab_{nome_aba}"
                tab = getattr(self, attr_name)
                for widget in tab.winfo_children():
                    widget.destroy()

                # Criar conteúdo real
                metodo_criacao()
                self.abas_carregadas[nome_aba] = True
        else:
            # ATUALIZAR ABA ESPECÍFICA SE JÁ CARREGADA
            if nome_aba == "movimentacoes" and self.abas_carregadas[nome_aba]:
                # Forçar atualização da lista de movimentações
                self.carregar_movimentacoes()
            elif nome_aba == "cadastro" and self.abas_carregadas[nome_aba]:
                # Atualizar lista de funcionários
                if getattr(self, 'cache_funcionarios_completo', None):
                    self.carregar_funcionarios_from_cache()
                else:
                    self.carregar_funcionarios()

        # Verificar autenticação
        abas_protegidas = ["👥 Cadastro", "📊 Exportar", "⚙️ Configurações", "📋 Movimentações"]

        if aba_selecionada in abas_protegidas and not self.autenticado:
            self.tabview.set("🏠 Ponto Eletrônico")
            self.solicitar_senha(aba_selecionada)
        elif aba_selecionada == "🏠 Ponto Eletrônico":
            self.entry_codigo_ponto.focus_set()

    def solicitar_senha(self, aba_destino):
        """Solicita senha para acessar abas protegidas"""
        janela_senha = JanelaComIcone(self.janela)
        janela_senha.title("Autenticação Requerida")
        janela_senha.geometry("400x300")
        janela_senha.resizable(False, False)
        janela_senha.transient(self.janela)
        janela_senha.grab_set()

        # Centralizar janela de senha
        janela_senha.update_idletasks()
        x = self.janela.winfo_x() + (self.janela.winfo_width() - janela_senha.winfo_width()) // 2
        y = self.janela.winfo_y() + (self.janela.winfo_height() - janela_senha.winfo_height()) // 2
        janela_senha.geometry(f"+{x}+{y}")

        frame = CTkFrame(janela_senha)
        frame.pack(padx=20, pady=20, fill='both', expand=True)

        CTkLabel(frame, text=f"Acesso à {aba_destino}",
                 font=('Arial', 16, 'bold')).pack(pady=10)

        CTkLabel(frame, text="Digite a senha de administrador:",
                 font=('Arial', 14)).pack(pady=5)

        entry_senha = CTkEntry(frame, show="•", width=200, height=35,
                               font=('Arial', 14))
        entry_senha.pack(pady=10)
        entry_senha.focus()

        label_status = CTkLabel(frame, text="", font=('Arial', 12))
        label_status.pack(pady=5)

        def verificar_e_entrar():
            senha = entry_senha.get()
            if self.verificar_senha(senha):
                self.autenticado = True
                janela_senha.destroy()
                self.tabview.set(aba_destino)
            else:
                label_status.configure(
                    text="Senha incorreta! Tente novamente.",
                    text_color="red"
                )
                entry_senha.delete(0, END)
                entry_senha.focus()

        frame_botoes = CTkFrame(frame, fg_color='transparent')
        frame_botoes.pack(pady=15)

        btn_entrar = CTkButton(frame_botoes, text="Entrar", command=verificar_e_entrar,
                               width=100, height=35, font=('Arial', 14))
        btn_entrar.grid(row=0, column=0, padx=5)

        def cancelar():
            janela_senha.destroy()
            self.tabview.set("🏠 Ponto Eletrônico")

        btn_cancelar = CTkButton(frame_botoes, text="Cancelar", command=cancelar,
                                 width=100, height=35, font=('Arial', 14),
                                 fg_color='gray', hover_color='darkgray')
        btn_cancelar.grid(row=0, column=1, padx=5)

        entry_senha.bind('<Return>', lambda e: verificar_e_entrar())
        janela_senha.protocol("WM_DELETE_WINDOW", cancelar)

    # ========== ABA PONTO ELETRÔNICO ==========
    def criar_aba_ponto(self):
        """Cria a interface da aba de ponto eletrônico - COM INDICADOR"""
        frame_principal = CTkFrame(self.tab_ponto)
        frame_principal.pack(pady=0, padx=0, fill='both', expand=True)

        # Título
        titulo = CTkLabel(frame_principal, text='Sistema de Ponto Eletrônico',
                          font=('Arial', 20, 'bold'))
        titulo.pack(pady=2)

        # DATA
        self.label_data = CTkLabel(frame_principal, text='',
                                   font=('Arial', 16, 'bold'),
                                   text_color='#1F6AA5')
        self.label_data.pack(pady=0)

        # RELÓGIO GRANDE
        frame_relogio = CTkFrame(frame_principal, fg_color='transparent')
        frame_relogio.pack(pady=0)

        self.label_hora = CTkLabel(frame_relogio, text='12:00:00',
                                   font=('Arial', 70, 'bold'),
                                   text_color='#2AA876')
        self.label_hora.pack()

        # Status do sistema
        self.label_status_sistema = CTkLabel(frame_principal, 
                                            text="⏳ Inicializando sistema...",
                                            font=('Arial', 12),
                                            text_color="orange")
        self.label_status_sistema.pack(pady=5)

        # Separador
        separador = CTkLabel(frame_principal, text='─' * 40,
                             text_color='gray', font=('Arial', 14))
        separador.pack(pady=0)

        # Frame para entrada de dados
        frame_entrada = CTkFrame(frame_principal)
        frame_entrada.pack(pady=0, fill='x', padx=30)

        # Campo para código do funcionário
        label_codigo = CTkLabel(frame_entrada, text='Digite seu código:',
                                font=('Arial', 14))
        label_codigo.pack(pady=5)

        self.entry_codigo_ponto = CTkEntry(frame_entrada,
                                           width=200,
                                           height=35,
                                           font=('Arial', 14))
        # Validar que só aceita números
        self.entry_codigo_ponto.configure(validate='key')
        self.entry_codigo_ponto.configure(
            validatecommand=(self.janela.register(self.validar_entrada_numerica), '%P')
        )
        self.entry_codigo_ponto.pack(pady=5)

        # Botão para registrar ponto
        self.botao_registrar = CTkButton(frame_entrada,
                                         text='REGISTRAR PONTO',
                                         command=self.registrar_ponto,
                                         width=200,
                                         height=40,
                                         font=('Arial', 14, 'bold'),
                                         fg_color='#2AA876',
                                         hover_color='#1E8C5F')
        self.botao_registrar.pack(pady=5)

        # Bind Enter para registrar ponto
        self.entry_codigo_ponto.bind('<Return>', lambda event: self.registrar_ponto())

        # Info do funcionário
        self.label_info_funcionario = CTkLabel(frame_entrada, text='',
                                               font=('Arial', 20),
                                               text_color='#2AA876')
        self.label_info_funcionario.pack(pady=5)

        # Separador
        separador = CTkLabel(frame_principal, text='─' * 40,
                             text_color='gray', font=('Arial', 14))
        separador.pack(pady=0)

        # Frame para ÚLTIMO PONTO MARCADO
        self.frame_ultimo_ponto = CTkFrame(frame_principal)
        self.frame_ultimo_ponto.pack(pady=0, fill='x', padx=30)

        # Título do último ponto
        titulo_ultimo_ponto = CTkLabel(self.frame_ultimo_ponto,
                                       text='Último Ponto Marcado',
                                       font=('Arial', 16, 'bold'),
                                       text_color='#1F6AA5')
        titulo_ultimo_ponto.pack(pady=5)

        # Frame principal das informações
        frame_info_ultimo = CTkFrame(self.frame_ultimo_ponto, fg_color='transparent')
        frame_info_ultimo.pack(pady=5, padx=10, fill='x')

        # Nome
        frame_nome = CTkFrame(frame_info_ultimo, fg_color='transparent')
        frame_nome.pack(side='left', expand=True, padx=5, pady=2)
        CTkLabel(frame_nome, text='Nome:', font=('Arial', 14, 'bold')).pack(anchor='w')
        self.label_ultimo_nome = CTkLabel(frame_nome, text='NENHUM REGISTRO',
                                          font=('Arial', 16), text_color='#1F6AA5')
        self.label_ultimo_nome.pack(anchor='w')

        # Número
        frame_numero = CTkFrame(frame_info_ultimo, fg_color='transparent')
        frame_numero.pack(side='left', expand=True, padx=5, pady=2)
        CTkLabel(frame_numero, text='Número:', font=('Arial', 14, 'bold')).pack(anchor='w')
        self.label_ultimo_numero = CTkLabel(frame_numero, text='---',
                                            font=('Arial', 16), text_color='#1F6AA5')
        self.label_ultimo_numero.pack(anchor='w')

        # Hora
        frame_hora = CTkFrame(frame_info_ultimo, fg_color='transparent')
        frame_hora.pack(side='left', expand=True, padx=5, pady=2)
        CTkLabel(frame_hora, text='Hora:', font=('Arial', 14, 'bold')).pack(anchor='w')
        self.label_ultima_hora = CTkLabel(frame_hora, text='--:--:--',
                                          font=('Arial', 16), text_color='#1F6AA5')
        self.label_ultima_hora.pack(anchor='w')

        # Data
        frame_data = CTkFrame(frame_info_ultimo, fg_color='transparent')
        frame_data.pack(side='left', expand=True, padx=5, pady=2)
        CTkLabel(frame_data, text='Data:', font=('Arial', 14, 'bold')).pack(anchor='w')
        self.label_ultima_data = CTkLabel(frame_data, text='--/--/----',
                                          font=('Arial', 16), text_color='#1F6AA5')
        self.label_ultima_data.pack(anchor='w')

    def atualizar_relogio(self):
        """Atualiza a data e hora em tempo real"""
        agora = datetime.now()
        data_formatada = agora.strftime('%d/%m/%Y')
        self.label_data.configure(text=data_formatada)
        hora_formatada = agora.strftime('%H:%M:%S')
        self.label_hora.configure(text=hora_formatada)
        self.janela.after(1000, self.atualizar_relogio)

    def buscar_funcionario(self, codigo):
        """Busca funcionário pelo código usando cache"""
        # Verificar se o banco já foi inicializado
        if self.cursor is None:
            return None
            
        # Verificar cache primeiro
        if codigo in self.cache_funcionarios:
            nome, departamento = self.cache_funcionarios[codigo]
            return (nome, departamento)

        # Se não estiver no cache, buscar no banco
        self.cursor.execute("SELECT nome, departamento FROM funcionarios WHERE codigo = ?", (codigo,))
        resultado = self.cursor.fetchone()

        # Atualizar cache se encontrou
        if resultado:
            self.cache_funcionarios[codigo] = resultado

        return resultado

    def verificar_ultimo_registro(self, codigo):
        """Verifica qual foi o último registro do funcionário"""
        if self.cursor is None:
            return None

        self.cursor.execute('''SELECT tipo, data_hora
                               FROM registros_ponto
                               WHERE codigo_funcionario = ?
                               ORDER BY substr(data_hora, 7, 4) || substr(data_hora, 4, 2) || substr(data_hora, 1, 2) || substr(data_hora, 12) DESC LIMIT 1''', (codigo,))
        return self.cursor.fetchone()

    def determinar_proximo_tipo(self, codigo_funcionario):
        """Define o tipo do ponto (Entrada, Almoço, etc) resetando a cada novo dia"""
        try:
            # Pega apenas a data de hoje para filtrar
            data_hoje = datetime.now().strftime('%d/%m/%Y')

            # Conta quantos registros esse funcionário já tem hoje
            self.cursor.execute('''
                SELECT COUNT(*) FROM registros_ponto 
                WHERE codigo_funcionario = ? AND substr(data_hora, 1, 10) = ?
            ''', (codigo_funcionario, data_hoje))

            contagem_hoje = self.cursor.fetchone()[0]

            # Lógica de sequência diária
            if contagem_hoje == 0:
                return "Entrada"
            elif contagem_hoje == 1:
                return "Saída Almoço"
            elif contagem_hoje == 2:
                return "Retorno Almoço"
            elif contagem_hoje == 3:
                return "Saída"
            else:
                return f"Extra {contagem_hoje + 1}"

        except Exception as e:
            print(f"Erro ao determinar tipo: {e}")
            return "Registro"  # Fallback caso dê erro

    def carregar_ultimo_ponto(self):
        """Carrega o último ponto registrado no sistema"""
        if self.cursor is None:
            return
            
        self.cursor.execute('''SELECT r.codigo_funcionario, r.tipo, r.data_hora, f.nome
                               FROM registros_ponto r
                                        JOIN funcionarios f ON r.codigo_funcionario = f.codigo
                               ORDER BY substr(r.data_hora, 7, 4) || substr(r.data_hora, 4, 2) || substr(r.data_hora, 1, 2) || substr(r.data_hora, 12) DESC LIMIT 1''')
        ultimo_ponto = self.cursor.fetchone()

        if ultimo_ponto:
            codigo, tipo, data_hora, nome = ultimo_ponto
            data = data_hora.split(' ')[0] if data_hora else '--/--/----'
            hora = data_hora.split(' ')[1] if data_hora else '--:--:--'

            self.label_ultimo_numero.configure(text=codigo)
            self.label_ultimo_nome.configure(text=nome)
            self.label_ultima_data.configure(text=data)
            self.label_ultima_hora.configure(text=hora)

    def atualizar_ultimo_ponto(self, codigo, nome, data_hora):
        """Atualiza a seção do último ponto com os novos dados"""
        data = data_hora.split(' ')[0]
        hora = data_hora.split(' ')[1]

        self.label_ultimo_numero.configure(text=codigo)
        self.label_ultimo_nome.configure(text=nome)
        self.label_ultima_data.configure(text=data)
        self.label_ultima_hora.configure(text=hora)

    def registrar_ponto(self):
        """Registra o ponto do funcionário com lógica de reset diário"""
        # Verificar se o banco está inicializado
        if self.conn is None or self.cursor is None:
            self.label_info_funcionario.configure(
                text="⚠️ Sistema inicializando...\nAguarde alguns segundos",
                text_color="orange"
            )
            return

        codigo = self.entry_codigo_ponto.get().strip()
        self.entry_codigo_ponto.delete(0, 'end')
        self.entry_codigo_ponto.focus_set()

        if not codigo:
            self.label_info_funcionario.configure(text="Digite um código!", text_color="red")
            return

        funcionario = self.buscar_funcionario(codigo)

        if not funcionario:
            self.label_info_funcionario.configure(text="Código não encontrado!", text_color="red")
            return

        nome, departamento = funcionario

        # O SEGREDO ESTÁ AQUI: O método agora decide baseado no dia de hoje
        novo_tipo = self.determinar_proximo_tipo(codigo)

        data_hora_atual = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        try:
            self.cursor.execute(
                "INSERT INTO registros_ponto (codigo_funcionario, tipo, data_hora) VALUES (?, ?, ?)",
                (codigo, novo_tipo, data_hora_atual)
            )
            self.conn.commit()

            self.atualizar_ultimo_ponto(codigo, nome, data_hora_atual)

            # Atualizar movimentações se a aba estiver aberta
            if self.abas_carregadas["movimentacoes"]:
                self.carregar_movimentacoes()

            # Feedback visual
            cargo = departamento if departamento else ""
            self.label_info_funcionario.configure(
                text=f"👤 {nome} {'- ' + cargo if cargo else ''}\n✅ {novo_tipo.upper()} REGISTRADA",
                text_color="#2AA876"
            )

            # Timer para limpar a mensagem
            if self.timer_limpeza is not None:
                self.janela.after_cancel(self.timer_limpeza)
            self.timer_limpeza = self.janela.after(15000, self.limpar_campo_ponto)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar no banco: {e}")

    def limpar_campo_ponto(self):
        """Limpa o campo de código e mensagens na aba de ponto"""
        self.entry_codigo_ponto.delete(0, 'end')
        self.label_info_funcionario.configure(text="")
        self.entry_codigo_ponto.focus()
        self.timer_limpeza = None

    # ========== ABA MOVIMENTAÇÕES ==========
    def criar_aba_movimentacoes(self):
        """Cria a aba de movimentações para visualizar/editar/excluir pontos"""
        frame_principal = CTkFrame(self.tab_movimentacoes)
        frame_principal.pack(fill='both', expand=True, padx=10, pady=10)

        CTkLabel(frame_principal, text="Movimentações - Últimos 50 Pontos",
                 font=('Arial', 18, 'bold')).pack(pady=10)

        frame_tree = CTkFrame(frame_principal)
        frame_tree.pack(fill='both', expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview',
                        background='white',
                        foreground='black',
                        fieldbackground='white',
                        rowheight=25,
                        font=('Arial', 10))

        style.configure("Treeview.Heading",
                        font=('Arial', 10, 'bold'),
                        background='#1F6AA5',
                        foreground='white')

        colunas = ('ID', 'Código', 'Nome', 'Tipo', 'Data', 'Hora')
        self.tree_mov = ttk.Treeview(frame_tree, columns=colunas, show='headings', height=15)

        # ADICIONAR: Configurar tags para zebrado
        self.tree_mov.tag_configure('even', background='#FFFFFF')  # Branco
        self.tree_mov.tag_configure('odd', background='#D9D9D9')  # Cinza claro

        for col in colunas:
            self.tree_mov.heading(col, text=col)
            self.tree_mov.column(col, width=100, anchor='center')

        self.tree_mov.column('ID', width=30)
        self.tree_mov.column('Código', width=45)
        self.tree_mov.column('Nome', width=100, anchor='w')
        self.tree_mov.column('Tipo', width=120)
        self.tree_mov.column('Data', width=60)
        self.tree_mov.column('Hora', width=55)

        scrollbar = ttk.Scrollbar(frame_tree, orient='vertical', command=self.tree_mov.yview)
        self.tree_mov.configure(yscrollcommand=scrollbar.set)

        self.tree_mov.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        frame_botoes = CTkFrame(frame_principal, fg_color='transparent')
        frame_botoes.pack(pady=0)

        self.btn_atualizar_mov = CTkButton(frame_botoes, text='Atualizar',
                                           command=self.carregar_movimentacoes,
                                           width=100, height=35,
                                           font=('Arial', 12), fg_color='#1F6AA5')
        self.btn_atualizar_mov.pack(side='left', padx=5)

        self.btn_editar_mov = CTkButton(frame_botoes, text='Editar Ponto',
                                        command=self.editar_ponto_mov,
                                        width=100, height=35,
                                        font=('Arial', 12), fg_color='#2AA876')
        self.btn_editar_mov.pack(side='left', padx=5)

        self.btn_excluir_mov = CTkButton(frame_botoes, text='Excluir Ponto',
                                         command=self.excluir_ponto_mov,
                                         width=100, height=35,
                                         font=('Arial', 12), fg_color='#D35B5B')
        self.btn_excluir_mov.pack(side='left', padx=5)

        self.carregar_movimentacoes()

    def carregar_movimentacoes(self):
        """Carrega os últimos 50 pontos batidos"""
        if self.cursor is None:
            return

        for item in self.tree_mov.get_children():
            self.tree_mov.delete(item)

        # CORREÇÃO AQUI: Ordenação por Ano-Mês-Dia forçada via substr
        self.cursor.execute('''
                            SELECT r.id, r.codigo_funcionario, f.nome, r.tipo, r.data_hora
                            FROM registros_ponto r
                                     JOIN funcionarios f ON r.codigo_funcionario = f.codigo
                            ORDER BY substr(r.data_hora, 7, 4) || substr(r.data_hora, 4, 2) || substr(r.data_hora, 1, 2) || substr(r.data_hora, 12) DESC LIMIT 50
                            ''')
        pontos = self.cursor.fetchall()

        # MODIFICADO: Alternar entre tags 'even' e 'odd'
        for i, ponto in enumerate(pontos):
            id_ponto, codigo, nome, tipo, data_hora = ponto
            # Proteção caso data_hora venha vazio ou incompleto
            if data_hora and ' ' in data_hora:
                data, hora = data_hora.split(' ')
            else:
                data, hora = data_hora, ""

            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree_mov.insert('', 'end', values=(id_ponto, codigo, nome, tipo, data, hora), tags=(tag,))

    def editar_ponto_mov(self):
        """Edita o ponto selecionado"""
        if self.cursor is None:
            return
            
        selecionado = self.tree_mov.selection()
        if not selecionado:
            messagebox.showwarning('Aviso', 'Selecione um ponto para editar!')
            return

        item = self.tree_mov.item(selecionado[0])
        id_ponto = item['values'][0]
        data_antiga, hora_antiga = item['values'][4], item['values'][5]

        janela_editar = JanelaComIcone(self.janela)
        janela_editar.title(f"Editar Ponto ID {id_ponto}")
        janela_editar.geometry("350x230")
        janela_editar.resizable(False, False)
        janela_editar.transient(self.janela)
        janela_editar.grab_set()

        janela_editar.update_idletasks()
        x = self.janela.winfo_x() + (self.janela.winfo_width() - janela_editar.winfo_width()) // 2
        y = self.janela.winfo_y() + (self.janela.winfo_height() - janela_editar.winfo_height()) // 2
        janela_editar.geometry(f"+{x}+{y}")

        frame = CTkFrame(janela_editar)
        frame.pack(padx=20, pady=20, fill='both', expand=True)

        CTkLabel(frame, text="Editar Horário do Ponto",
                 font=('Arial', 14, 'bold')).pack(pady=10)

        frame_data = CTkFrame(frame, fg_color='transparent')
        frame_data.pack(pady=5)
        CTkLabel(frame_data, text="Data:", font=('Arial', 12)).pack(side='left', padx=5)
        entry_data = CTkEntry(frame_data, width=100, font=('Arial', 12))
        entry_data.pack(side='left', padx=5)
        entry_data.insert(0, data_antiga)

        frame_hora = CTkFrame(frame, fg_color='transparent')
        frame_hora.pack(pady=5)
        CTkLabel(frame_hora, text="Hora:", font=('Arial', 12)).pack(side='left', padx=5)
        entry_hora = CTkEntry(frame_hora, width=100, font=('Arial', 12))
        entry_hora.pack(side='left', padx=5)
        entry_hora.insert(0, hora_antiga)

        def salvar_edicao():
            nova_data = entry_data.get().strip()
            nova_hora = entry_hora.get().strip()

            try:
                datetime.strptime(nova_data, '%d/%m/%Y')
                datetime.strptime(nova_hora, '%H:%M:%S')

                nova_data_hora = f"{nova_data} {nova_hora}"
                self.cursor.execute("UPDATE registros_ponto SET data_hora = ? WHERE id = ?",
                                    (nova_data_hora, id_ponto))
                self.conn.commit()

                messagebox.showinfo('Sucesso', 'Ponto atualizado com sucesso!')
                janela_editar.destroy()
                self.carregar_movimentacoes()

            except ValueError:
                messagebox.showerror('Erro', 'Formato inválido! Use DD/MM/AAAA e HH:MM:SS')

        btn_salvar = CTkButton(frame, text="Salvar", command=salvar_edicao,
                               width=100, height=30, font=('Arial', 12), fg_color='#2AA876')
        btn_salvar.pack(pady=15)

    def excluir_ponto_mov(self):
        """Exclui o ponto selecionado"""
        if self.cursor is None:
            return
            
        selecionado = self.tree_mov.selection()
        if not selecionado:
            messagebox.showwarning('Aviso', 'Selecione um ponto para excluir!')
            return

        item = self.tree_mov.item(selecionado[0])
        id_ponto = item['values'][0]
        codigo = item['values'][1]
        nome = item['values'][2]

        if messagebox.askyesno('Confirmação',
                               f'Tem certeza que deseja excluir o ponto de {nome} (Código: {codigo})?'):
            self.cursor.execute("DELETE FROM registros_ponto WHERE id = ?", (id_ponto,))
            self.conn.commit()
            messagebox.showinfo('Sucesso', 'Ponto excluído com sucesso!')
            self.carregar_movimentacoes()

    # ========== ABA CADASTRO ==========
    def criar_aba_cadastro(self):
        """Cria a interface da aba de cadastro de funcionários"""
        frame_principal = CTkFrame(self.tab_cadastro)
        frame_principal.pack(fill='both', expand=True, padx=10, pady=10)

        titulo = CTkLabel(frame_principal, text='Cadastro de Funcionários',
                          font=('Arial', 18, 'bold'))
        titulo.pack(pady=5)

        frame_busca = CTkFrame(frame_principal)
        frame_busca.pack(fill='x', padx=10, pady=5)

        CTkLabel(frame_busca, text='Buscar:', font=('Arial', 15)).pack(side='left', padx=10, pady=5)

        self.entry_busca = CTkEntry(frame_busca, width=250, font=('Arial', 15),
                                    placeholder_text='Digite código, nome ou cargo...')
        self.entry_busca.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        self.entry_busca.bind('<KeyRelease>', self.buscar_funcionarios)

        self.btn_limpar_busca = CTkButton(frame_busca, text='Limpar', command=self.limpar_busca,
                                          width=80, height=25, font=('Arial', 15))
        self.btn_limpar_busca.pack(side='left', padx=5, pady=5)

        frame_form = CTkFrame(frame_principal)
        frame_form.pack(fill='x', padx=10, pady=5)

        frame_linha1 = CTkFrame(frame_form, fg_color='transparent')
        frame_linha1.pack(fill='x', padx=5, pady=2)

        CTkLabel(frame_linha1, text='Código:*', font=('Arial', 15)).pack(side='left', padx=5)
        self.entry_codigo_cad = CTkEntry(frame_linha1, height=30, width=80, font=('Arial', 15))
        # Validar que só aceita números
        self.entry_codigo_cad.configure(validate='key')
        self.entry_codigo_cad.configure(
            validatecommand=(self.janela.register(self.validar_entrada_numerica), '%P')
        )
        self.entry_codigo_cad.pack(side='left', padx=5)

        CTkLabel(frame_linha1, text='Nome:*', font=('Arial', 15)).pack(side='left', padx=5)
        self.entry_nome = CTkEntry(frame_linha1, height=30, width=250, font=('Arial', 15))
        self.entry_nome.pack(side='left', fill='x', expand=True, padx=5)

        frame_linha2 = CTkFrame(frame_form, fg_color='transparent')
        frame_linha2.pack(fill='x', padx=5, pady=2)

        CTkLabel(frame_linha2, text='Cargo:', font=('Arial', 15)).pack(side='left', padx=5)
        self.entry_departamento = CTkEntry(frame_linha2, height=30, width=95, font=('Arial', 15))
        self.entry_departamento.pack(side='left', padx=5)

        CTkLabel(frame_linha2, text='Observação:', font=('Arial', 15)).pack(side='left', padx=5)
        self.entry_observacao = CTkEntry(frame_linha2, height=30, font=('Arial', 15))
        self.entry_observacao.pack(side='left', fill='x', expand=True, padx=5)

        frame_horarios = CTkFrame(frame_form, fg_color='transparent')
        frame_horarios.pack(fill='x', padx=10, pady=5)

        for i in range(4):
            frame_horarios.grid_columnconfigure(i, weight=1)

        CTkLabel(frame_horarios, text='Entrada:', font=('Arial', 15)).grid(row=0, column=0, padx=5, pady=2)
        self.entry_entrada = CTkEntry(frame_horarios, font=('Arial', 15), width=100)
        self.entry_entrada.grid(row=1, column=0, padx=5, pady=2)
        self.entry_entrada.insert(0, '08:30')  # VALOR PADRÃO DEFINITIVO

        CTkLabel(frame_horarios, text='Saída Almoço:', font=('Arial', 15)).grid(row=0, column=1, padx=5, pady=2)
        self.entry_saida_almoco = CTkEntry(frame_horarios, font=('Arial', 15), width=100)
        self.entry_saida_almoco.grid(row=1, column=1, padx=5, pady=2)
        self.entry_saida_almoco.insert(0, '11:30')  # VALOR PADRÃO DEFINITIVO

        CTkLabel(frame_horarios, text='Volta Almoço:', font=('Arial', 15)).grid(row=0, column=2, padx=5, pady=2)
        self.entry_volta_almoco = CTkEntry(frame_horarios, font=('Arial', 15), width=100)
        self.entry_volta_almoco.grid(row=1, column=2, padx=5, pady=2)
        self.entry_volta_almoco.insert(0, '13:30')  # VALOR PADRÃO DEFINITIVO

        CTkLabel(frame_horarios, text='Saída:', font=('Arial', 15)).grid(row=0, column=3, padx=5, pady=2)
        self.entry_saida = CTkEntry(frame_horarios, font=('Arial', 15), width=100)
        self.entry_saida.grid(row=1, column=3, padx=5, pady=2)
        self.entry_saida.insert(0, '18:30')  # VALOR PADRÃO DEFINITIVO

        frame_botoes = CTkFrame(frame_form, fg_color='transparent')
        frame_botoes.pack(pady=5)

        self.btn_adicionar = CTkButton(frame_botoes, text='Adicionar', command=self.adicionar_funcionario,
                                       width=90, height=30, font=('Arial', 12), fg_color='#2AA876')
        self.btn_adicionar.pack(side='left', padx=3)

        self.btn_editar = CTkButton(frame_botoes, text='Editar', command=self.editar_funcionario,
                                    width=90, height=30, font=('Arial', 12), fg_color='#1F6AA5')
        self.btn_editar.pack(side='left', padx=3)

        self.btn_excluir = CTkButton(frame_botoes, text='Excluir', command=self.excluir_funcionario,
                                     width=90, height=30, font=('Arial', 12), fg_color='#D35B5B')
        self.btn_excluir.pack(side='left', padx=3)

        self.btn_limpar_campos = CTkButton(frame_botoes, text='Limpar', command=self.limpar_campos_cadastro,
                                           width=90, height=30, font=('Arial', 12))
        self.btn_limpar_campos.pack(side='left', padx=3)

        frame_tree = CTkFrame(frame_principal)
        frame_tree.pack(fill='both', expand=True, padx=10, pady=5)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview',
                        background='white',
                        foreground='black',
                        fieldbackground='white',
                        rowheight=22,
                        font=('Arial', 10))

        # ADICIONAR: Configurar tags para linhas pares e ímpares
        style.map('Treeview',
                  background=[('selected', '#1F6AA5')],  # Cor de fundo quando selecionado
                  foreground=[('selected', 'white')])  # Cor do texto quando selecionado

        style.configure("Treeview.Heading",
                        font=('Arial', 10, 'bold'),
                        background='#1F6AA5',
                        foreground='white')

        colunas = ('Código', 'Nome', 'ENT.1', 'SAÍ.1', 'ENT.2', 'SAÍ.2')
        self.tree = ttk.Treeview(frame_tree, columns=colunas, show='headings', height=10)

        # ADICIONAR: Configurar tags para zebrado
        self.tree.tag_configure('even', background='#FFFFFF')  # Branco
        self.tree.tag_configure('odd', background='#D9D9D9')  # Cinza muito claro

        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor='center')

        self.tree.column('Código', width=45)
        self.tree.column('Nome', width=160, anchor='w')
        self.tree.column('ENT.1', width=40)
        self.tree.column('SAÍ.1', width=40)
        self.tree.column('ENT.2', width=40)
        self.tree.column('SAÍ.2', width=40)

        scrollbar = ttk.Scrollbar(frame_tree, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.tree.bind('<<TreeviewSelect>>', self.selecionar_funcionario)

        # Carregar funcionários do cache se disponível
        if getattr(self, 'cache_funcionarios_completo', None):
            self.carregar_funcionarios_from_cache()
        else:
            self.carregar_funcionarios()

    def carregar_funcionarios_from_cache(self):
        """Carrega funcionários do cache em vez do banco"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        # MODIFICADO: Alternar entre tags 'even' e 'odd'
        for i, func in enumerate(self.cache_funcionarios_completo):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', values=func, tags=(tag,))

    # ========== MÉTODOS DA ABA CADASTRO ==========

    def buscar_funcionarios(self, event=None):
        """Busca funcionários por código, nome ou departamento"""
        termo_busca = self.entry_busca.get().strip().lower()

        if not termo_busca:
            if getattr(self, 'cache_funcionarios_completo', None):
                self.carregar_funcionarios_from_cache()
            else:
                self.carregar_funcionarios()
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        # Buscar no cache primeiro
        resultados = []
        for func in getattr(self, 'cache_funcionarios_completo', []):
            codigo, nome, entrada, saida_almoco, volta_almoco, saida = func
            if (termo_busca in str(codigo).lower() or
                    termo_busca in nome.lower()):
                resultados.append(func)

        # Se não encontrou no cache, buscar no banco
        if not resultados and self.cursor:
            self.cursor.execute('''
                                SELECT codigo,
                                       nome,
                                       horario_entrada,
                                       horario_saida_almoco,
                                       horario_volta_almoco,
                                       horario_saida
                                FROM funcionarios
                                WHERE LOWER(codigo) LIKE ?
                                   OR LOWER(nome) LIKE ?
                                   OR LOWER(departamento) LIKE ?
                                   OR LOWER(observacao) LIKE ?
                                ORDER BY CAST(codigo AS INTEGER)
                                ''', (f'%{termo_busca}%', f'%{termo_busca}%', f'%{termo_busca}%', f'%{termo_busca}%'))
            resultados = self.cursor.fetchall()

        # MODIFICADO: Alternar entre tags 'even' e 'odd'
        for i, func in enumerate(resultados):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', values=func, tags=(tag,))

    def limpar_busca(self):
        """Limpa a busca e recarrega todos os funcionários"""
        self.entry_busca.delete(0, END)
        if getattr(self, 'cache_funcionarios_completo', None):
            self.carregar_funcionarios_from_cache()
        else:
            self.carregar_funcionarios()

    def carregar_funcionarios(self):
        """Carrega os funcionários na treeview"""
        if self.cursor is None:
            return
            
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Ordena pelo código convertido para inteiro (CAST(codigo AS INTEGER))
        self.cursor.execute('''
                            SELECT codigo,
                                   nome,
                                   horario_entrada,
                                   horario_saida_almoco,
                                   horario_volta_almoco,
                                   horario_saida
                            FROM funcionarios
                            ORDER BY CAST(codigo AS INTEGER)
                            ''')
        funcionarios = self.cursor.fetchall()

        # Atualizar cache
        self.cache_funcionarios_completo = funcionarios

        # MODIFICADO: Alternar entre tags 'even' e 'odd'
        for i, func in enumerate(funcionarios):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', values=func, tags=(tag,))

    def validar_horario(self, horario):
        """Valida se o horário está no formato HH:MM"""
        if not horario:
            return True

        try:
            if len(horario) != 5 or horario[2] != ':':
                return False

            horas = int(horario[:2])
            minutos = int(horario[3:])

            if horas < 0 or horas > 23 or minutos < 0 or minutos > 59:
                return False

            return True
        except ValueError:
            return False

    def adicionar_funcionario(self):
        """Adiciona um novo funcionário - CARGO NÃO É OBRIGATÓRIO"""
        if self.cursor is None:
            messagebox.showerror('Erro', 'Banco de dados não inicializado!')
            return
            
        codigo = self.entry_codigo_cad.get().strip()
        nome = self.entry_nome.get().strip()
        departamento = self.entry_departamento.get().strip()
        observacao = self.entry_observacao.get().strip()
        # VALIDAÇÃO EXTRA: verificar se o código contém apenas números
        if not codigo.isdigit():
            messagebox.showwarning('Aviso', 'O código deve conter apenas números!')
            return

        horario_entrada = self.entry_entrada.get().strip()
        horario_saida_almoco = self.entry_saida_almoco.get().strip()
        horario_volta_almoco = self.entry_volta_almoco.get().strip()
        horario_saida = self.entry_saida.get().strip()

        if not codigo or not nome:
            messagebox.showwarning('Aviso', 'Código e nome são obrigatórios!')
            return

        horarios = [
            (horario_entrada, 'Entrada'),
            (horario_saida_almoco, 'Saída para Almoço'),
            (horario_volta_almoco, 'Volta do Almoço'),
            (horario_saida, 'Saída')
        ]

        for horario, tipo in horarios:
            if horario and not self.validar_horario(horario):
                messagebox.showwarning('Aviso', f'Horário de {tipo} inválido! Use o formato HH:MM')
                return

        try:
            self.cursor.execute(
                """INSERT INTO funcionarios
                   (codigo, nome, departamento, observacao, horario_entrada, horario_saida_almoco, horario_volta_almoco,
                    horario_saida)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (codigo, nome, departamento, observacao, horario_entrada, horario_saida_almoco, horario_volta_almoco,
                 horario_saida)
            )
            self.conn.commit()

            messagebox.showinfo('Sucesso', 'Funcionário adicionado com sucesso!')
            self.limpar_campos_cadastro()
            self.carregar_funcionarios()
            self.atualizar_cache_funcionarios()

        except sqlite3.IntegrityError:
            messagebox.showerror('Erro', 'Código já existe!')

    def editar_funcionario(self):
        """Edita o funcionário selecionado"""
        if self.cursor is None:
            messagebox.showerror('Erro', 'Banco de dados não inicializado!')
            return
            
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning('Aviso', 'Selecione um funcionário para editar!')
            return

        codigo = self.entry_codigo_cad.get().strip()
        nome = self.entry_nome.get().strip()
        # VALIDAÇÃO EXTRA: verificar se o código contém apenas números
        if not codigo.isdigit():
            messagebox.showwarning('Aviso', 'O código deve conter apenas números!')
            return
        departamento = self.entry_departamento.get().strip()
        observacao = self.entry_observacao.get().strip()

        horario_entrada = self.entry_entrada.get().strip()
        horario_saida_almoco = self.entry_saida_almoco.get().strip()
        horario_volta_almoco = self.entry_volta_almoco.get().strip()
        horario_saida = self.entry_saida.get().strip()

        if not codigo or not nome:
            messagebox.showwarning('Aviso', 'Código e nome são obrigatórios!')
            return

        horarios = [
            (horario_entrada, 'Entrada'),
            (horario_saida_almoco, 'Saída para Almoço'),
            (horario_volta_almoco, 'Volta do Almoço'),
            (horario_saida, 'Saída')
        ]

        for horario, tipo in horarios:
            if horario and not self.validar_horario(horario):
                messagebox.showwarning('Aviso', f'Horário de {tipo} inválido! Use o formato HH:MM')
                return

        item = self.tree.item(selecionado[0])
        codigo_selecionado = item['values'][0]

        try:
            self.cursor.execute(
                """UPDATE funcionarios
                   SET codigo=?,
                       nome=?,
                       departamento=?,
                       observacao=?,
                       horario_entrada=?,
                       horario_saida_almoco=?,
                       horario_volta_almoco=?,
                       horario_saida=?
                   WHERE codigo = ?""",
                (codigo, nome, departamento, observacao, horario_entrada, horario_saida_almoco, horario_volta_almoco,
                 horario_saida, codigo_selecionado)
            )
            self.conn.commit()

            messagebox.showinfo('Sucesso', 'Funcionário atualizado com sucesso!')
            self.limpar_campos_cadastro()
            self.carregar_funcionarios()
            self.atualizar_cache_funcionarios()

        except sqlite3.IntegrityError:
            messagebox.showerror('Erro', 'Código já existe!')

    def excluir_funcionario(self):
        """Exclui o funcionário selecionado - COM VERIFICAÇÃO DE PONTOS E SENHA"""
        if self.cursor is None:
            messagebox.showerror('Erro', 'Banco de dados não inicializado!')
            return
            
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning('Aviso', 'Selecione um funcionário para excluir!')
            return

        item = self.tree.item(selecionado[0])
        codigo_funcionario = item['values'][0]
        nome_funcionario = item['values'][1]

        self.cursor.execute("SELECT COUNT(*) FROM registros_ponto WHERE codigo_funcionario = ?",
                            (codigo_funcionario,))
        count = self.cursor.fetchone()[0]

        precisa_senha = count > 0

        if precisa_senha:
            if not self.solicitar_senha_simples("excluir funcionário com pontos batidos"):
                return

        if messagebox.askyesno('Confirmação', f'Tem certeza que deseja excluir {nome_funcionario}?'):
            if count > 0:
                self.cursor.execute("DELETE FROM registros_ponto WHERE codigo_funcionario = ?", (codigo_funcionario,))

            self.cursor.execute("DELETE FROM funcionarios WHERE codigo=?", (codigo_funcionario,))
            self.conn.commit()

            messagebox.showinfo('Sucesso', 'Funcionário excluído com sucesso!')
            self.limpar_campos_cadastro()
            self.carregar_funcionarios()
            self.atualizar_cache_funcionarios()

    def selecionar_funcionario(self, event):
        """Preenche os campos quando um funcionário é selecionado na treeview"""
        if self.cursor is None:
            return
            
        selecionado = self.tree.selection()
        if selecionado:
            item = self.tree.item(selecionado[0])
            codigo_funcionario = item['values'][0]

            self.cursor.execute('''
                                SELECT codigo,
                                       nome,
                                       departamento,
                                       observacao,
                                       horario_entrada,
                                       horario_saida_almoco,
                                       horario_volta_almoco,
                                       horario_saida
                                FROM funcionarios
                                WHERE codigo = ?
                                ''', (codigo_funcionario,))

            funcionario = self.cursor.fetchone()

            if funcionario:
                codigo, nome, departamento, observacao, entrada, saida_almoco, volta_almoco, saida = funcionario

                self.entry_codigo_cad.delete(0, END)
                self.entry_codigo_cad.insert(0, codigo)

                self.entry_nome.delete(0, END)
                self.entry_nome.insert(0, nome)

                self.entry_departamento.delete(0, END)
                self.entry_departamento.insert(0, departamento or '')

                self.entry_observacao.delete(0, END)
                self.entry_observacao.insert(0, observacao or '')

                self.entry_entrada.delete(0, END)
                self.entry_entrada.insert(0, entrada or '')

                self.entry_saida_almoco.delete(0, END)
                self.entry_saida_almoco.insert(0, saida_almoco or '')

                self.entry_volta_almoco.delete(0, END)
                self.entry_volta_almoco.insert(0, volta_almoco or '')

                self.entry_saida.delete(0, END)
                self.entry_saida.insert(0, saida or '')

    def limpar_campos_cadastro(self):
        """Limpa todos os campos do formulário de cadastro"""
        self.entry_codigo_cad.delete(0, END)
        self.entry_nome.delete(0, END)
        self.entry_departamento.delete(0, END)
        self.entry_observacao.delete(0, END)
        self.entry_entrada.delete(0, END)
        self.entry_entrada.insert(0, '08:30')  # RESTAURA VALOR PADRÃO
        self.entry_saida_almoco.delete(0, END)
        self.entry_saida_almoco.insert(0, '11:30')  # RESTAURA VALOR PADRÃO
        self.entry_volta_almoco.delete(0, END)
        self.entry_volta_almoco.insert(0, '13:30')  # RESTAURA VALOR PADRÃO
        self.entry_saida.delete(0, END)
        self.entry_saida.insert(0, '18:30')  # RESTAURA VALOR PADRÃO
        self.tree.selection_remove(self.tree.selection())

    def solicitar_senha_simples(self, operacao):
        """Solicita senha para operações sensíveis"""
        janela_senha = JanelaComIcone(self.janela)
        janela_senha.title(f"Senha para {operacao}")
        janela_senha.geometry("400x180")
        janela_senha.resizable(False, False)
        janela_senha.transient(self.janela)
        janela_senha.grab_set()

        janela_senha.update_idletasks()
        x = self.janela.winfo_x() + (self.janela.winfo_width() - janela_senha.winfo_width()) // 2
        y = self.janela.winfo_y() + (self.janela.winfo_height() - janela_senha.winfo_height()) // 2
        janela_senha.geometry(f"+{x}+{y}")

        frame = CTkFrame(janela_senha)
        frame.pack(padx=20, pady=20, fill='both', expand=True)

        CTkLabel(frame, text=f"Digite a senha para {operacao}:",
                 font=('Arial', 12)).pack(pady=10)

        entry_senha = CTkEntry(frame, show="•", font=('Arial', 12))
        entry_senha.pack(pady=10)
        entry_senha.focus()

        senha_correta = [False]

        def verificar():
            if self.verificar_senha(entry_senha.get()):
                senha_correta[0] = True
                janela_senha.destroy()
            else:
                messagebox.showerror("Erro", "Senha incorreta!")
                entry_senha.delete(0, END)
                entry_senha.focus()

        btn_verificar = CTkButton(frame, text="Confirmar", command=verificar,
                                  width=80, height=35, font=('Arial', 13))
        btn_verificar.pack(pady=10)

        entry_senha.bind('<Return>', lambda e: verificar())
        self.janela.wait_window(janela_senha)

        return senha_correta[0]

    # ========== ABA EXPORTAR ==========
    def criar_aba_exportar(self):
        """Cria a interface da aba de exportação de pontos com Calendário"""
        frame_principal = CTkFrame(self.tab_exportar)
        frame_principal.pack(fill='both', expand=True, padx=10, pady=10)

        # ==================== EXPORTAÇÃO INDIVIDUAL ====================
        CTkLabel(frame_principal, text='Exportar Individual (Cartão Ponto)',
                 font=('Arial', 18, 'bold'), text_color='#1F6AA5').pack(pady=10)

        frame_funcionario = CTkFrame(frame_principal)
        frame_funcionario.pack(fill='x', padx=10, pady=5)

        CTkLabel(frame_funcionario, text='Funcionário:',
                 font=('Arial', 15, 'bold')).pack(anchor='w', pady=0, padx=10)

        frame_codigo = CTkFrame(frame_funcionario, fg_color='transparent')
        frame_codigo.pack(fill='x', padx=5, pady=2)

        CTkLabel(frame_codigo, text='Código:', font=('Arial', 15)).pack(side='left', padx=5)
        self.entry_codigo_export = CTkEntry(frame_codigo, width=80, font=('Arial', 14))
        self.entry_codigo_export.pack(side='left', padx=5)

        self.btn_buscar_funcionario = CTkButton(frame_codigo, text='Buscar',
                                                command=self.buscar_funcionario_export,
                                                width=80, height=35, font=('Arial', 15))
        self.btn_buscar_funcionario.pack(side='left', padx=5)

        self.label_info_funcionario_export = CTkLabel(frame_funcionario, text='Selecione um funcionário',
                                                      font=('Arial', 15), text_color='gray')
        self.label_info_funcionario_export.pack(pady=2)

        # --- Área de Datas ---
        frame_periodo = CTkFrame(frame_principal)
        frame_periodo.pack(fill='x', padx=10, pady=5)

        CTkLabel(frame_periodo, text='Período:', font=('Arial', 15, 'bold')).pack(anchor='w', pady=0, padx=10)

        frame_datas = CTkFrame(frame_periodo, fg_color='transparent')
        frame_datas.pack(fill='x', padx=5, pady=2)

        # Data Início com Calendário
        frame_data_inicio = CTkFrame(frame_datas, fg_color='transparent')
        frame_data_inicio.pack(side='left', padx=5)
        CTkLabel(frame_data_inicio, text='De:', font=('Arial', 15)).pack(anchor='w')

        f_input_ini = CTkFrame(frame_data_inicio, fg_color='transparent')
        f_input_ini.pack()
        self.entry_data_inicio = CTkEntry(f_input_ini, width=100, font=('Arial', 14), placeholder_text='DD/MM/AAAA')
        self.entry_data_inicio.pack(side='left')
        CTkButton(f_input_ini, text='📅', width=30, fg_color='#555',
                  command=lambda: self.popup_calendario(self.entry_data_inicio)).pack(side='left', padx=2)

        # Data Fim com Calendário
        frame_data_fim = CTkFrame(frame_datas, fg_color='transparent')
        frame_data_fim.pack(side='left', padx=20)  # Espaço maior entre os inputs
        CTkLabel(frame_data_fim, text='Até:', font=('Arial', 15)).pack(anchor='w')

        f_input_fim = CTkFrame(frame_data_fim, fg_color='transparent')
        f_input_fim.pack()
        self.entry_data_fim = CTkEntry(f_input_fim, width=100, font=('Arial', 13), placeholder_text='DD/MM/AAAA')
        self.entry_data_fim.pack(side='left')
        CTkButton(f_input_fim, text='📅', width=30, fg_color='#555',
                  command=lambda: self.popup_calendario(self.entry_data_fim)).pack(side='left', padx=2)

        # --- Botões de Atalho de Período ---
        frame_botoes_periodo = CTkFrame(frame_periodo, fg_color='transparent')
        frame_botoes_periodo.pack(pady=10)

        # Lista de botões para criar em loop (Texto, Função)
        botoes_atalho = [
            ('Hoje', self.periodo_hoje),
            ('Semana', self.periodo_semana),  # Restaurado
            ('Mês', self.periodo_mes),  # Restaurado
            ('Todos', self.periodo_todos)
        ]

        for texto, comando in botoes_atalho:
            CTkButton(frame_botoes_periodo, text=texto, command=comando,
                      width=70, height=30, font=('Arial', 13)).pack(side='left', padx=3)

        self.btn_exportar = CTkButton(frame_principal, text='📊 Exportar Individual',
                                      command=self.exportar_para_excel,
                                      width=180, height=40,
                                      font=('Arial', 14, 'bold'),
                                      fg_color='#2AA876', hover_color='#1E8C5F')
        self.btn_exportar.pack(pady=10)

        # ==================== LINHA DIVISÓRIA ====================
        frame_div = CTkFrame(frame_principal, height=2, fg_color="gray")
        frame_div.pack(fill='x', padx=20, pady=1)

        # ==================== EXPORTAÇÃO GERAL ====================
        CTkLabel(frame_principal, text='Relatório Diário (Todos os Funcionários)',
                 font=('Arial', 18, 'bold'), text_color='#1F6AA5').pack(pady=5)

        frame_geral = CTkFrame(frame_principal)
        frame_geral.pack(fill='x', padx=10, pady=5)

        CTkLabel(frame_geral, text="Selecione a Data:", font=('Arial', 14, 'bold')).pack(side='left', padx=5)

        # Input Data Geral com Calendário
        self.entry_data_geral = CTkEntry(frame_geral, width=120, font=('Arial', 14), placeholder_text='DD/MM/AAAA')
        self.entry_data_geral.pack(side='left', padx=5)
        self.entry_data_geral.insert(0, datetime.now().strftime('%d/%m/%Y'))  # Padrão Hoje

        CTkButton(frame_geral, text='📅', width=20, fg_color='#555',
                  command=lambda: self.popup_calendario(self.entry_data_geral)).pack(side='left', padx=2)

        self.btn_exportar_geral = CTkButton(frame_geral, text='📊 Baixar Relatório do Dia',
                                            command=self.exportar_relatorio_geral,
                                            width=200, height=35,
                                            font=('Arial', 14, 'bold'),
                                            fg_color='#1F6AA5', hover_color='#144F7C')
        self.btn_exportar_geral.pack(side='right', padx=10, pady=10)

        self.label_status = CTkLabel(frame_principal, text='',
                                     font=('Arial', 12), text_color='#1F6AA5')
        self.label_status.pack(pady=5)

    def popup_calendario(self, entry_widget):
        """Abre uma janela popup com calendário para selecionar a data"""
        from tkcalendar import Calendar
        try:
            top = CTkToplevel(self.janela)
            top.title("Selecione a Data")
            top.geometry("300x320")
            top.attributes("-topmost", True)  # Garante que fique na frente
            top.grab_set()

            cal = Calendar(top, selectmode='day', date_pattern='dd/mm/yyyy', locale='pt_BR')
            cal.pack(pady=10, padx=10, expand=True, fill='both')

            def selecionar_data():
                data_selecionada = cal.get_date()
                entry_widget.delete(0, 'end')
                entry_widget.insert(0, data_selecionada)
                top.destroy()

            CTkButton(top, text="Confirmar", command=selecionar_data, fg_color='#2AA876').pack(pady=10)
        except Exception as e:
            messagebox.showwarning("Aviso", "Erro ao carregar calendário. Verifique se 'tkcalendar' está instalado.")

    def periodo_semana(self):
        """Define o período para os últimos 7 dias"""
        hoje = datetime.now()
        inicio = hoje - timedelta(days=7)
        self.entry_data_inicio.delete(0, 'end')
        self.entry_data_inicio.insert(0, inicio.strftime('%d/%m/%Y'))
        self.entry_data_fim.delete(0, 'end')
        self.entry_data_fim.insert(0, hoje.strftime('%d/%m/%Y'))

    def periodo_mes(self):
        """Define o período para o mês atual (do dia 1 até hoje)"""
        hoje = datetime.now()
        inicio = hoje.replace(day=1)
        self.entry_data_inicio.delete(0, 'end')
        self.entry_data_inicio.insert(0, inicio.strftime('%d/%m/%Y'))
        self.entry_data_fim.delete(0, 'end')
        self.entry_data_fim.insert(0, hoje.strftime('%d/%m/%Y'))

    def periodo_hoje(self):
        """Define o período apenas para o dia atual"""
        hoje = datetime.now().strftime('%d/%m/%Y')
        self.entry_data_inicio.delete(0, 'end')
        self.entry_data_inicio.insert(0, hoje)
        self.entry_data_fim.delete(0, 'end')
        self.entry_data_fim.insert(0, hoje)

    def exportar_relatorio_geral(self):
        """Exporta um relatório contendo todos os funcionários e seus pontos de um dia específico"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            messagebox.showerror('Erro', 'Módulo openpyxl não instalado!')
            return

        # 1. Obter e validar a data
        data_str = self.entry_data_geral.get().strip()
        if not self.validar_data(data_str):
            messagebox.showwarning('Aviso', 'Data inválida! Use o formato DD/MM/AAAA')
            return

        if self.cursor is None:
            messagebox.showerror('Erro', 'Banco de dados não inicializado!')
            return

        self.label_status.configure(text="Gerando relatório geral...", text_color="blue")
        self.janela.update()

        try:
            # 2. Buscar TODOS os funcionários ativos (ordenados por nome)
            self.cursor.execute("SELECT codigo, nome, departamento FROM funcionarios ORDER BY nome")
            todos_funcionarios = self.cursor.fetchall()

            if not todos_funcionarios:
                messagebox.showinfo("Aviso", "Nenhum funcionário cadastrado.")
                self.label_status.configure(text="")
                return

            # 3. Buscar os pontos DAQUELA DATA ESPECÍFICA
            # Usando substr para pegar os 10 primeiros caracteres (data) do campo data_hora
            self.cursor.execute('''
                SELECT codigo_funcionario, data_hora 
                FROM registros_ponto 
                WHERE substr(data_hora, 1, 10) = ?
                ORDER BY data_hora ASC
            ''', (data_str,))

            registros = self.cursor.fetchall()

            # 4. Organizar pontos em um dicionário: {codigo: [horario1, horario2...]}
            mapa_pontos = {}
            for cod, dt_hora in registros:
                hora = dt_hora.split(' ')[1][:5]  # Pega apenas HH:MM
                if cod not in mapa_pontos:
                    mapa_pontos[cod] = []
                mapa_pontos[cod].append(hora)

            # 5. Criar Excel
            wb = Workbook()
            ws = wb.active
            ws.title = f"Relatorio_{data_str.replace('/', '-')}"

            # Estilos
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="1F6AA5", end_color="1F6AA5", fill_type="solid")
            center_align = Alignment(horizontal='center', vertical='center')
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                 top=Side(style='thin'), bottom=Side(style='thin'))

            # Cabeçalho Principal
            ws.merge_cells('A1:G1')
            ws['A1'] = f"RELATÓRIO DE PONTO GERAL - DATA: {data_str}"
            ws['A1'].font = Font(bold=True, size=14)
            ws['A1'].alignment = center_align

            # Cabeçalhos da Tabela
            headers = ["CÓDIGO", "NOME", "DEPARTAMENTO", "ENTRADA", "SAÍDA", "ENTRADA", "SAÍDA", "PONTOS EXTRAS"]
            ws.append([])  # Pula linha 2
            ws.append(headers)  # Linha 3

            # Formatar cabeçalhos
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col_num)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align
                cell.border = thin_border

            # Preencher dados
            row_num = 4
            for func in todos_funcionarios:
                cod, nome, dep = func
                pontos = mapa_pontos.get(cod, [])  # Lista de horários ou lista vazia

                # Preparar linha base
                row_data = [cod, nome, dep]

                # Adicionar pontos (garantir pelo menos 4 colunas de horário vazias se não tiver ponto)
                for i in range(4):
                    if i < len(pontos):
                        row_data.append(pontos[i])
                    else:
                        row_data.append("-")

                # Se tiver mais que 4 pontos, juntar os extras na última coluna
                if len(pontos) > 4:
                    extras = ", ".join(pontos[4:])
                    row_data.append(extras)
                else:
                    row_data.append("")

                # Escrever linha no Excel
                ws.append(row_data)

                # Formatação condicional simples (pintar de cinza claro linhas pares)
                if row_num % 2 == 0:
                    fill_color = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
                    for col in range(1, 9):
                        ws.cell(row=row_num, column=col).fill = fill_color

                # Aplicar bordas
                for col in range(1, 9):
                    ws.cell(row=row_num, column=col).border = thin_border
                    # Centralizar tudo exceto Nome
                    if col != 2:
                        ws.cell(row=row_num, column=col).alignment = center_align

                row_num += 1

            # Ajustar largura das colunas
            ws.column_dimensions['A'].width = 10
            ws.column_dimensions['B'].width = 35
            ws.column_dimensions['C'].width = 20
            ws.column_dimensions['D'].width = 10
            ws.column_dimensions['E'].width = 10
            ws.column_dimensions['F'].width = 10
            ws.column_dimensions['G'].width = 10
            ws.column_dimensions['H'].width = 20

            # Salvar Arquivo
            arquivo = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[('Arquivos Excel', '*.xlsx')],
                title='Salvar Relatório Geral',
                initialfile=f'RELATORIO_GERAL_{data_str.replace("/", "-")}.xlsx'
            )

            if arquivo:
                wb.save(arquivo)
                self.label_status.configure(text=f"✅ Relatório salvo com sucesso!", text_color="#2AA876")
                messagebox.showinfo("Sucesso", f"Relatório salvo em:\n{arquivo}")
            else:
                self.label_status.configure(text="Exportação cancelada", text_color="orange")

        except Exception as e:
            self.label_status.configure(text="Erro na exportação", text_color="red")
            messagebox.showerror("Erro Crítico", f"Erro ao gerar relatório geral:\n{str(e)}")

    # ========== MÉTODOS DA ABA EXPORTAÇÃO ==========

    def buscar_funcionario_export(self):
        """Busca funcionário pelo código na aba de exportação"""
        if self.cursor is None:
            messagebox.showerror('Erro', 'Banco de dados não inicializado!')
            return
            
        codigo = self.entry_codigo_export.get().strip()

        if not codigo:
            messagebox.showwarning('Aviso', 'Digite um código!')
            return

        self.cursor.execute("SELECT nome, departamento, observacao FROM funcionarios WHERE codigo = ?", (codigo,))
        resultado = self.cursor.fetchone()

        if resultado:
            nome, departamento, observacao = resultado
            obs_text = observacao if observacao else "SEM OBSERVAÇÃO"
            self.label_info_funcionario_export.configure(
                text=f"👤 {nome} - {departamento} | Obs: {obs_text}",
                text_color="#1F6AA5"
            )
            self.funcionario_selecionado = {
                'codigo': codigo,
                'nome': nome,
                'departamento': departamento,
                'observacao': observacao
            }
        else:
            self.label_info_funcionario_export.configure(
                text="Funcionário não encontrado!",
                text_color="red"
            )
            self.funcionario_selecionado = None

    def periodo_esta_semana(self):
        """Define o período para esta semana"""
        hoje = datetime.now()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        fim_semana = inicio_semana + timedelta(days=6)

        self.entry_data_inicio.delete(0, END)
        self.entry_data_inicio.insert(0, inicio_semana.strftime('%d/%m/%Y'))
        self.entry_data_fim.delete(0, END)
        self.entry_data_fim.insert(0, fim_semana.strftime('%d/%m/%Y'))

    def periodo_este_mes(self):
        """Define o período para este mês"""
        hoje = datetime.now()
        inicio_mes = hoje.replace(day=1)
        if hoje.month == 12:
            fim_mes = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fim_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)

        self.entry_data_inicio.delete(0, END)
        self.entry_data_inicio.insert(0, inicio_mes.strftime('%d/%m/%Y'))
        self.entry_data_fim.delete(0, END)
        self.entry_data_fim.insert(0, fim_mes.strftime('%d/%m/%Y'))

    def periodo_todos(self):
        """Limpa as datas para buscar todos os registros"""
        self.entry_data_inicio.delete(0, END)
        self.entry_data_fim.delete(0, END)

    def validar_data(self, data_str):
        """Valida se a data está no formato DD/MM/AAAA"""
        try:
            datetime.strptime(data_str, '%d/%m/%Y')
            return True
        except ValueError:
            return False

    def converter_data_para_sql(self, data_str):
        """Converte data de DD/MM/AAAA para AAAA-MM-DD"""
        try:
            data_obj = datetime.strptime(data_str, '%d/%m/%Y')
            return data_obj.strftime('%Y-%m-%d')
        except ValueError:
            return None

    def obter_dias_no_periodo(self, data_inicio, data_fim):
        """Retorna lista de dias entre data_inicio e data_fim"""
        dias = []
        data_atual = data_inicio
        while data_atual <= data_fim:
            dias.append(data_atual)
            data_atual += timedelta(days=1)
        return dias

    def exportar_para_excel(self):
        """Exporta os pontos para arquivo Excel - COM FORMATAÇÃO CORRETA"""
        # Importação diferida do openpyxl
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            messagebox.showerror('Erro', 'Módulo openpyxl não instalado!')
            return

        if not hasattr(self, 'funcionario_selecionado') or not self.funcionario_selecionado:
            messagebox.showwarning('Aviso', 'Selecione um funcionário primeiro!')
            return

        if self.cursor is None:
            messagebox.showerror('Erro', 'Banco de dados não inicializado!')
            return
            
        codigo = self.funcionario_selecionado['codigo']
        nome = self.funcionario_selecionado['nome']
        departamento = self.funcionario_selecionado.get('departamento', '')
        observacao = self.funcionario_selecionado.get('observacao', '') or "SEM OBSERVAÇÃO"

        data_inicio_str = self.entry_data_inicio.get().strip()
        data_fim_str = self.entry_data_fim.get().strip()

        if data_inicio_str and not self.validar_data(data_inicio_str):
            messagebox.showwarning('Aviso', 'Data inicial inválida! Use DD/MM/AAAA')
            return

        if data_fim_str and not self.validar_data(data_fim_str):
            messagebox.showwarning('Aviso', 'Data final inválida! Use DD/MM/AAAA')
            return

        query = "SELECT data_hora FROM registros_ponto WHERE codigo_funcionario = ?"
        params = [codigo]

        if data_inicio_str and data_fim_str:
            data_inicio_sql = self.converter_data_para_sql(data_inicio_str)
            data_fim_sql = self.converter_data_para_sql(data_fim_str)

            query += " AND date(substr(data_hora, 7, 4) || '-' || substr(data_hora, 4, 2) || '-' || substr(data_hora, 1, 2)) BETWEEN ? AND ?"
            params.extend([data_inicio_sql, data_fim_sql])
            data_inicio_obj = datetime.strptime(data_inicio_str, '%d/%m/%Y')
            data_fim_obj = datetime.strptime(data_fim_str, '%d/%m/%Y')
        elif data_inicio_str or data_fim_str:
            messagebox.showwarning('Aviso', 'Preencha ambas as datas ou deixe vazio!')
            return
        else:
            # CORREÇÃO: Busca todas as datas e decide o início/fim via Python (cronológico)
            self.cursor.execute("SELECT data_hora FROM registros_ponto WHERE codigo_funcionario = ?", (codigo,))
            todos_registros = self.cursor.fetchall()

            if todos_registros:
                datas_objs = []
                for row in todos_registros:
                    if row[0]:  # Previne erro se houver registro vazio
                        data_str = row[0].split(' ')[0]
                        datas_objs.append(datetime.strptime(data_str, '%d/%m/%Y'))

                if datas_objs:
                    data_inicio_obj = min(datas_objs)  # Pega a verdadeira data mais antiga
                    data_fim_obj = max(datas_objs)  # Pega a verdadeira data mais recente
                else:
                    messagebox.showinfo('Info', 'Nenhum registro válido encontrado!')
                    return
            else:
                messagebox.showinfo('Info', 'Nenhum registro encontrado!')
                return

        # CORREÇÃO: Ordenação correta Ano-Mês-Dia para o relatório
        query += " ORDER BY substr(data_hora, 7, 4) || substr(data_hora, 4, 2) || substr(data_hora, 1, 2) || substr(data_hora, 12)"
        self.cursor.execute(query, params)
        registros = [row[0] for row in self.cursor.fetchall()]

        if not registros and (data_inicio_str and data_fim_str):
            messagebox.showinfo('Info', 'Nenhum registro encontrado!')
            return

        registros_por_dia = self.processar_registros_por_dia_multi(registros)

        arquivo = filedialog.asksaveasfilename(
            defaultextension='.xlsx',
            filetypes=[('Arquivos Excel', '*.xlsx'), ('Todos os arquivos', '*.*')],
            title='Salvar relatório',
            initialfile=f'PONTO_{codigo}_{nome.replace(" ", "_")}.xlsx'
        )

        if not arquivo:
            return

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Cartão Ponto"

            # ========== CONFIGURAÇÃO DE LARGURAS DE COLUNAS ==========
            ws.column_dimensions['A'].width = 14
            ws.column_dimensions['B'].width = 11
            ws.column_dimensions['C'].width = 11
            ws.column_dimensions['D'].width = 11
            ws.column_dimensions['E'].width = 11

            # ========== TÍTULO PRINCIPAL ==========
            ws.merge_cells('A1:E1')
            ws['A1'] = "CARTÃO PONTO"
            ws['A1'].font = Font(bold=True, size=14)
            ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

            # ========== PERÍODO ==========
            periodo = f"De: {data_inicio_str if data_inicio_str else data_inicio_obj.strftime('%d/%m/%Y')} até {data_fim_str if data_fim_str else data_fim_obj.strftime('%d/%m/%Y')}"
            ws.merge_cells('A2:E2')
            ws['A2'] = periodo
            ws['A2'].alignment = Alignment(horizontal='center')

            # ========== INFORMAÇÕES DO FUNCIONÁRIO (COM BORDAS EXTERNAS) ==========
            # Nome
            ws['A4'] = "Nome:"
            ws['A4'].font = Font(bold=True, size=11)
            ws['B4'] = nome
            ws['C4'] = ""
            ws['D4'] = ""
            ws['E4'] = ""
            # Aplicar bordas externas nas células B4, C4, D4, E4
            for col in ['B4', 'C4', 'D4', 'E4']:
                ws[col].border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                        bottom=Side(style='thin'))
            ws['B4'].alignment = Alignment(horizontal='left', vertical='center')

            # Número
            ws['A5'] = "Nº:"
            ws['A5'].font = Font(bold=True, size=11)
            ws['B5'] = codigo
            ws['C5'] = ""
            ws['D5'] = ""
            ws['E5'] = ""
            # Aplicar bordas externas nas células B5, C5, D5, E5
            for col in ['B5', 'C5', 'D5', 'E5']:
                ws[col].border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                        bottom=Side(style='thin'))
            ws['B5'].alignment = Alignment(horizontal='left', vertical='center')

            # Função
            ws['A6'] = "Função:"
            ws['A6'].font = Font(bold=True, size=11)
            ws['B6'] = departamento if departamento else "CADASTRO"
            ws['C6'] = ""
            ws['D6'] = ""
            ws['E6'] = ""
            # Aplicar bordas externas nas células B6, C6, D6, E6
            for col in ['B6', 'C6', 'D6', 'E6']:
                ws[col].border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                        bottom=Side(style='thin'))
            ws['B6'].alignment = Alignment(horizontal='left', vertical='center')

            # Observação
            ws['A7'] = "Obs:"
            ws['A7'].font = Font(bold=True, size=11)
            ws['B7'] = observacao
            ws['C7'] = ""
            ws['D7'] = ""
            ws['E7'] = ""
            # Aplicar bordas externas nas células B7, C7, D7, E7
            for col in ['B7', 'C7', 'D7', 'E7']:
                ws[col].border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                        bottom=Side(style='thin'))
            ws['B7'].alignment = Alignment(horizontal='left', vertical='center')

            # ========== HORÁRIO DE TRABALHO (ENTRE OBS E DIAS) ==========
            ws.merge_cells('A9:E9')
            ws['A9'] = "Horário de Trabalho"
            ws['A9'].font = Font(bold=True)
            ws['A9'].alignment = Alignment(horizontal='center')

            # Cabeçalhos do horário
            ws['A10'] = "ENT.1"
            ws['B10'] = "SAI.1"
            ws['C10'] = "ENT.2"
            ws['D10'] = "SAI.2"

            # Horários padrão
            ws['A11'] = "07:30:00"
            ws['B11'] = "11:00:00"
            ws['C11'] = "13:00:00"
            ws['D11'] = "18:00:00"

            # Centralizar cabeçalhos e valores do horário
            for col in range(1, 5):
                ws.cell(row=10, column=col).alignment = Alignment(horizontal='center')
                ws.cell(row=11, column=col).alignment = Alignment(horizontal='center')

            # ========== CABEÇALHO DA TABELA DE PONTOS (CENTRALIZADO) ==========
            ws['A13'] = "DIAS"
            ws['B13'] = "ENT.1"
            ws['C13'] = "SAI.1"
            ws['D13'] = "ENT.2"
            ws['E13'] = "SAI.2"

            # Estilo do cabeçalho (centralizado)
            for cell in ['A13', 'B13', 'C13', 'D13', 'E13']:
                ws[cell].font = Font(bold=True)
                ws[cell].fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
                ws[cell].alignment = Alignment(horizontal='center')

            # ========== PREENCHIMENTO DOS DADOS (SEM MESCLAGEM, ALINHADOS À ESQUERDA) ==========
            linha_atual = 14
            dias_no_periodo = self.obter_dias_no_periodo(data_inicio_obj, data_fim_obj)

            # Dicionário de tradução dos dias da semana
            traducao_dias = {
                'mon': 'Seg',
                'tue': 'Ter',
                'wed': 'Qua',
                'thu': 'Qui',
                'fri': 'Sex',
                'sat': 'Sab',
                'sun': 'Dom'
            }

            for dia in dias_no_periodo:
                data_str = dia.strftime('%d/%m/%y')
                dia_semana_ingles = dia.strftime('%a').lower()  # Ex: 'sat'
                dia_semana_portugues = traducao_dias.get(dia_semana_ingles, dia_semana_ingles)
                data_completa = f"{data_str} - {dia_semana_portugues}"

                grupos = registros_por_dia.get(dia.strftime('%d/%m/%Y'), [])

                if grupos:
                    for grupo in grupos:
                        # Célula de data (coluna A) - SEM MESCLAR
                        ws.cell(row=linha_atual, column=1, value=data_completa)
                        ws.cell(row=linha_atual, column=1).alignment = Alignment(horizontal='left', vertical='center')

                        # Horários (colunas B-E) - centralizados
                        for i, hora in enumerate(grupo[:4]):
                            ws.cell(row=linha_atual, column=2 + i, value=hora)
                            ws.cell(row=linha_atual, column=2 + i).alignment = Alignment(horizontal='center',
                                                                                         vertical='center')

                        linha_atual += 1
                else:
                    # Dia sem registros
                    ws.cell(row=linha_atual, column=1, value=data_completa)
                    ws.cell(row=linha_atual, column=1).alignment = Alignment(horizontal='left', vertical='center')
                    linha_atual += 1

            # ========== APLICAÇÃO DE BORDAS ==========
            # Define estilo de borda fina
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            # Aplica bordas em todas as células utilizadas
            # Linhas 1-2 (título e período)
            for row in range(1, 3):
                for col in range(1, 6):
                    ws.cell(row=row, column=col).border = thin_border

            # Títulos das informações do funcionário (células A4, A5, A6, A7)
            for cell in ['A4', 'A5', 'A6', 'A7']:
                ws[cell].border = thin_border

            # Dados do funcionário (células B4-E4, B5-E5, B6-E6, B7-E7)
            for row in [4, 5, 6, 7]:
                for col in ['B', 'C', 'D', 'E']:
                    ws[f'{col}{row}'].border = thin_border

            # Horário de trabalho (linhas 9-11)
            for row in range(9, 12):
                for col in range(1, 6):
                    ws.cell(row=row, column=col).border = thin_border

            # Tabela de pontos (linha 13 em diante)
            for row in range(13, linha_atual):
                for col in range(1, 6):
                    ws.cell(row=row, column=col).border = thin_border

            # ========== SALVAR ARQUIVO ==========
            wb.save(arquivo)

            messagebox.showinfo('Sucesso', f'Relatório exportado!\n{arquivo}')
            self.label_status.configure(text=f'✅ Arquivo salvo: {os.path.basename(arquivo)}')

        except Exception as e:
            messagebox.showerror('Erro', f'Erro ao exportar:\n{str(e)}')
            self.label_status.configure(text='❌ Erro ao exportar')

    def processar_registros_por_dia_multi(self, registros):
        """Processa registros permitindo múltiplas linhas por dia (mais de 4 pontos)"""
        registros_por_dia = {}

        for data_hora in registros:
            data, hora_completa = data_hora.split(' ')
            hora = hora_completa[:5]

            if data not in registros_por_dia:
                registros_por_dia[data] = []

            registros_por_dia[data].append(hora)

        resultado = {}
        for data, horarios in registros_por_dia.items():
            grupos = []
            for i in range(0, len(horarios), 4):
                grupos.append(horarios[i:i + 4])
            resultado[data] = grupos

        return resultado

    # ========== ABA CONFIGURAÇÕES ==========
    def criar_aba_configuracoes(self):
        """Cria a aba de configurações do sistema"""
        # Frame principal sem scrollbar
        main_frame = CTkFrame(self.tab_config)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Frame que continha o conteúdo (agora sem canvas)
        scrollable_frame = CTkFrame(main_frame)
        scrollable_frame.pack(fill='both', expand=True)

        # Título principal
        CTkLabel(scrollable_frame, text="Configurações do Sistema",
                 font=('Arial', 18, 'bold')).pack(pady=(0, 10))

        # ========== SEÇÃO DE SENHA ==========
        frame_senha = CTkFrame(scrollable_frame)
        frame_senha.pack(fill='x', padx=20, pady=10)

        CTkLabel(frame_senha, text="Alterar Senha",
                 font=('Arial', 16, 'bold')).pack(pady=5)

        campos = [
            ("Senha Atual:", "entry_senha_atual"),
            ("Nova Senha:", "entry_nova_senha"),
            ("Confirmar:", "entry_conf_senha")
        ]

        for i, (label_text, attr_name) in enumerate(campos):
            frame_campo = CTkFrame(frame_senha, fg_color='transparent')
            frame_campo.pack(fill='x', padx=10, pady=3)
            CTkLabel(frame_campo, text=label_text, font=('Arial', 15)).pack(side='left')

            entry = CTkEntry(frame_campo, show="•", width=150, font=('Arial', 15))
            entry.pack(side='right', padx=5)

            setattr(self, attr_name, entry)

        btn_alterar_senha = CTkButton(frame_senha, text="Alterar Senha",
                                      command=self.alterar_senha_config,
                                      width=120, height=30,
                                      font=('Arial', 15), fg_color='#2AA876')
        btn_alterar_senha.pack(pady=10)

        self.label_status_senha = CTkLabel(frame_senha, text="",
                                           font=('Arial', 15))
        self.label_status_senha.pack(pady=5)

        # ========== SEÇÃO DE INFORMAÇÕES DO SISTEMA ==========
        frame_info = CTkFrame(scrollable_frame)
        frame_info.pack(fill='x', padx=60, pady=20)

        CTkLabel(frame_info, text="Informações do Sistema",
                 font=('Arial', 17, 'bold')).pack(pady=5)

        try:
            if self.cursor:
                self.cursor.execute("SELECT COUNT(*) FROM funcionarios")
                total_func = self.cursor.fetchone()[0]

                self.cursor.execute("SELECT COUNT(*) FROM registros_ponto")
                total_pontos = self.cursor.fetchone()[0]

                info_text = "\n".join([
                    f"Funcionários cadastrados: {total_func}",
                    f"Registros de ponto: {total_pontos}"
                ])

                CTkLabel(
                    frame_info,
                    text=info_text.strip(),
                    font=('Arial', 17),
                    anchor='center',
                    justify='center',
                    width=400
                ).pack(pady=5)

        except Exception as e:
            CTkLabel(frame_info, text="Erro ao carregar informações",
                     text_color="red").pack(pady=5)

        # Versão e atualização
        frame_versao = CTkFrame(scrollable_frame, fg_color='transparent')
        frame_versao.pack(pady=0)

        versao_info = f"""
        Última atualização: 07/06/2026
        Compatível: Windows 10/11
        Desenvolvido por: Supermercado Mendes CRT
        """

        label_versao = CTkLabel(frame_versao,
                                text=versao_info,
                                font=('Arial', 10),
                                text_color='#7f8c8d')
        label_versao.pack()

    def executar(self):
        """Inicia a aplicação"""
        self.janela.mainloop()


# Executar o programa
if __name__ == "__main__":
    app = SistemaPontoEletronicoCompleto()
    app.executar()
