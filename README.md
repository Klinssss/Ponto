# 🕐 Sistema de Ponto Eletrônico

Sistema desktop completo de controle de ponto eletrônico desenvolvido em Python, com interface gráfica moderna, banco de dados local e exportação para Excel.

---

## 📋 Sobre o Projeto

Aplicação desenvolvida para o **Supermercado Mendes CRT** com o objetivo de gerenciar o registro de ponto dos funcionários de forma simples e eficiente. O sistema registra entradas, saídas e intervalos de almoço, mantendo um histórico completo que pode ser exportado em formato de cartão ponto individual ou relatório geral diário.

---

## ✨ Funcionalidades

- **🏠 Ponto Eletrônico** — Registro de ponto por código do funcionário com identificação automática do tipo (Entrada, Saída Almoço, Retorno Almoço, Saída)
- **👥 Cadastro de Funcionários** — Adicionar, editar e excluir funcionários com código, nome, cargo, observação e horários de trabalho personalizados
- **📊 Exportação Individual** — Gera cartão ponto em Excel (`.xlsx`) por funcionário com filtro de período por data
- **📋 Exportação Geral** — Relatório diário com todos os funcionários e seus pontos do dia
- **📋 Movimentações** — Visualização, edição e exclusão dos últimos 50 registros de ponto
- **⚙️ Configurações** — Alteração de senha de administrador e informações gerais do sistema
- **🔒 Autenticação** — Acesso protegido por senha para abas administrativas
- **📅 Calendário integrado** — Seleção de período com popup de calendário (via `tkcalendar`)

---

## 🖥️ Interface

A interface utiliza o tema claro do **CustomTkinter**, com sistema de abas e carregamento otimizado (lazy loading) para inicialização rápida. O banco de dados é carregado em background sem travar a tela principal.

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Uso |
|---|---|
| `Python 3.x` | Linguagem principal |
| `CustomTkinter` | Interface gráfica moderna |
| `SQLite3` | Banco de dados local |
| `openpyxl` | Geração de arquivos Excel |
| `tkcalendar` | Seletor de data com calendário |
| `threading` | Carregamento em background |
| `hashlib` | Hash SHA-256 para senhas |
| `json` | Armazenamento de configurações |

---

## 📦 Instalação

**1. Clone o repositório:**
```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
```

**2. Instale as dependências:**
```bash
pip install customtkinter openpyxl tkcalendar
```

**3. Execute o sistema:**
```bash
python Cadastro_e_exportacao.py
```

> O banco de dados `ponto_eletronico.db` será criado automaticamente na primeira execução.

---

## 🔐 Acesso

A senha padrão de administrador é:

```
admin123
```

É recomendado alterá-la na aba **⚙️ Configurações** após o primeiro acesso.

---

## 📁 Arquivos Gerados

| Arquivo | Descrição |
|---|---|
| `ponto_eletronico.db` | Banco de dados SQLite com funcionários e registros |
| `config_seguranca.json` | Hash da senha de administrador |
| `icone.ico` *(opcional)* | Ícone da janela (se presente na mesma pasta) |

---

## 📊 Estrutura do Banco de Dados

**Tabela `funcionarios`**
```
id, codigo, nome, departamento, observacao,
horario_entrada, horario_saida_almoco,
horario_volta_almoco, horario_saida
```

**Tabela `registros_ponto`**
```
id, codigo_funcionario, tipo, data_hora
```

---

## 📄 Exportação Excel

### Cartão Ponto Individual
Gera um arquivo `.xlsx` formatado com:
- Dados do funcionário (nome, número, função, observação)
- Horário de trabalho padrão
- Tabela com todos os dias do período selecionado e os pontos batidos
- Bordas, cabeçalhos destacados e dias da semana em português

### Relatório Geral Diário
Gera um arquivo `.xlsx` com todos os funcionários e seus horários de um dia específico, com formatação zebrada e colunas de pontos extras.

---

## ⚙️ Requisitos do Sistema

- Python 3.8 ou superior
- Windows 10/11 *(recomendado)*
- Resolução mínima: 1024x768

---

## 📌 Versão

**Versão:** 2.0  
**Última atualização:** 18/01/2026  
**Desenvolvido para:** Supermercado Mendes CRT
