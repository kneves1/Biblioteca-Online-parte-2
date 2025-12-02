import sys
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk

# DADOS DA EMPRESA 
COMPANY = {
    "nome_empresa": "SoftLib Solutions",
    "nome_produto": "EmpréstimoEasy",
    "historia": (
        "Fundada em 2025 por entusiastas de bibliotecas e desenvolvedores,\n"
        "a SoftLib Solutions cria soluções simples e escaláveis.\n"
        "Nossa missão é aproximar leitores e conhecimento."
    ),
    "funcionarios": [
        ("Mateus de Mattos", "Desenvolvedor Líder"),
        ("Kauã Neves", "Analista de Sistemas"),
        ("Arthur Santanna", "Testador QA"),
        ("Nicolas Abranches", "Engenheiro de software"),
        ("Flavio Schmitz", "Designer"),
    ]
}

# DADOS
@dataclass
class User:
    codigo: str
    nome: str
    tipo: str
    login: str
    senha: str

@dataclass
class Book:
    codigo: str
    titulo: str
    autor: str

@dataclass
class LoanRecord:
    codigo_emprestimo: str
    codigo_cliente: str
    codigo_livro: str
    data_emprestimo: datetime
    data_devolucao_prevista: datetime
    data_devolucao_real: Optional[datetime] = None
    multa_cobrada: float = 0.0
    renovacoes_realizadas: int = 0

# LÓGICA DO SISTEMA
class LibrarySystem:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.books: Dict[str, Book] = {}
        self.loans: List[LoanRecord] = []
        self.current_user: Optional[User] = None
        
        # Regras de Negócio
        self.PRAZO_DIAS_INICIAL = 7
        self.PRAZO_DIAS_RENOVACAO = 7
        self.MAX_RENOVACOES = 2
        self.MULTA_DIA = 0.50

        self.load_files()

    def load_files(self):
        # 1. Carregar USUARIOS
        if os.path.exists("usuarios.txt"):
            try:
                with open("usuarios.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"): continue
                        parts = line.split(";")
                        if len(parts) >= 5:
                            u = User(parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip(), parts[4].strip())
                            self.users[u.login] = u
            except Exception as e:
                print(f"Erro ao ler usuarios.txt: {e}")

        # 2. Carregar LIVROS
        if os.path.exists("livros.txt"):
            try:
                with open("livros.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"): continue
                        parts = line.split(";")
                        if len(parts) >= 3:
                            b = Book(parts[0].strip(), parts[1].strip(), parts[2].strip())
                            self.books[b.codigo] = b
            except Exception as e:
                print(f"Erro ao ler livros.txt: {e}")

        # 3. Carregar EMPRESTIMOS
        if os.path.exists("emprestimos.txt"):
            try:
                with open("emprestimos.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"): continue
                        parts = line.split(";")
                        if len(parts) >= 4:
                            try:
                                dt_emp = datetime.strptime(parts[3].strip(), "%Y-%m-%d")
                            except ValueError:
                                dt_emp = datetime.strptime(parts[3].strip(), "%d/%m/%Y")
                            
                            prevista = dt_emp + timedelta(days=self.PRAZO_DIAS_INICIAL)
                            ln = LoanRecord(parts[0].strip(), parts[1].strip(), parts[2].strip(), dt_emp, prevista)
                            self.loans.append(ln)
            except Exception as e:
                print(f"Erro ao ler emprestimos.txt: {e}")

    def validate_user(self, login, senha):
        user = self.users.get(login)
        if user and user.senha == senha:
            self.current_user = user
            return True
        return False

    def get_user_active_loans(self):
        return [ln for ln in self.loans if ln.codigo_cliente == self.current_user.codigo and ln.data_devolucao_real is None]

    def create_loan(self, codigo_livro):
        if codigo_livro not in self.books:
            return False, "Livro não encontrado."
        
        for ln in self.loans:
            if ln.codigo_livro == codigo_livro and ln.data_devolucao_real is None:
                return False, "Livro indisponível (já emprestado)."

        novo_codigo = str(len(self.loans) + 1).zfill(3)
        hoje = datetime.now()
        prevista = hoje + timedelta(days=self.PRAZO_DIAS_INICIAL)

        novo_emp = LoanRecord(novo_codigo, self.current_user.codigo, codigo_livro, hoje, prevista)
        self.loans.append(novo_emp)
        return True, f"Sucesso! Devolução prevista: {prevista.strftime('%d/%m/%Y')}"

    def renew_loan(self, codigo_livro):
        # Busca o empréstimo ativo desse livro para esse usuário
        loan = next((ln for ln in self.loans 
                     if ln.codigo_livro == codigo_livro 
                     and ln.codigo_cliente == self.current_user.codigo 
                     and ln.data_devolucao_real is None), None)

        if not loan:
            return False, "Empréstimo não encontrado."

        if loan.renovacoes_realizadas >= self.MAX_RENOVACOES:
            return False, f"Limite de {self.MAX_RENOVACOES} renovações atingido."

        hoje = datetime.now()
        if hoje > loan.data_devolucao_prevista:
            return False, "Não é possível renovar livro em atraso. Devolva e pague a multa."

        loan.renovacoes_realizadas += 1
        loan.data_devolucao_prevista += timedelta(days=self.PRAZO_DIAS_RENOVACAO)
        return True, f"Renovado! Nova data: {loan.data_devolucao_prevista.strftime('%d/%m/%Y')}"

    def return_book(self, codigo_livro):
        loan = next((ln for ln in self.loans 
                     if ln.codigo_livro == codigo_livro 
                     and ln.codigo_cliente == self.current_user.codigo 
                     and ln.data_devolucao_real is None), None)

        if not loan:
            return False, "Empréstimo não encontrado."

        hoje = datetime.now()
        multa = 0.0
        msg_multa = ""

        # Cálculo de multa se estiver atrasado
        # Ajustamos as horas para comparar apenas datas
        data_prevista_sem_hora = loan.data_devolucao_prevista.replace(hour=0, minute=0, second=0, microsecond=0)
        hoje_sem_hora = hoje.replace(hour=0, minute=0, second=0, microsecond=0)

        if hoje_sem_hora > data_prevista_sem_hora:
            dias_atraso = (hoje_sem_hora - data_prevista_sem_hora).days
            multa = dias_atraso * self.MULTA_DIA
            msg_multa = f"\nMULTA COBRADA: R$ {multa:.2f} ({dias_atraso} dias de atraso)."

        loan.data_devolucao_real = hoje
        loan.multa_cobrada = multa

        return True, f"Livro devolvido com sucesso!{msg_multa}"

# INTERFACE 
class LibraryGUI:
    def __init__(self, root, system):
        self.system = system
        self.root = root
        self.root.title(f"{COMPANY['nome_empresa']} - {COMPANY['nome_produto']}")
        self.root.geometry("700x550")
        self.show_login_screen()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login_screen(self):
        self.clear_screen()
        frame = tk.Frame(self.root)
        frame.pack(expand=True)

        tk.Label(frame, text=COMPANY["nome_empresa"], font=("Arial", 16, "bold")).pack(pady=10)
        tk.Label(frame, text="Login:").pack()
        self.entry_login = tk.Entry(frame)
        self.entry_login.pack(pady=5)
        tk.Label(frame, text="Senha:").pack()
        self.entry_senha = tk.Entry(frame, show="*")
        self.entry_senha.pack(pady=5)
        
        tk.Button(frame, text="Entrar", command=self.perform_login, bg="#4CAF50", fg="white", width=15).pack(pady=20)
        tk.Label(frame, text="Verifique usuarios.txt para acesso", fg="gray", font=("Arial", 8)).pack()

    def perform_login(self):
        if self.system.validate_user(self.entry_login.get(), self.entry_senha.get()):
            self.show_main_menu()
        else:
            messagebox.showerror("Erro", "Dados inválidos.")

    def show_main_menu(self):
        self.clear_screen()
        top = tk.Frame(self.root, bg="#ddd", pady=5, padx=10)
        top.pack(fill="x")
        tk.Label(top, text=f"Olá, {self.system.current_user.nome}", bg="#ddd", font=("Arial", 10, "bold")).pack(side="left")
        tk.Button(top, text="Sair", command=self.show_login_screen, bg="red", fg="white", width=8).pack(side="right")

        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self.tab_books = tk.Frame(notebook)
        notebook.add(self.tab_books, text=" 📖 Acervo & Empréstimo ")
        self.setup_books_tab()

        self.tab_loans = tk.Frame(notebook)
        notebook.add(self.tab_loans, text=" 📂 Meus Empréstimos (Renovar/Devolver) ")
        self.setup_loans_tab()

        self.tab_about = tk.Frame(notebook)
        notebook.add(self.tab_about, text=" ℹ️ Sobre ")
        self.setup_about_tab()

    def setup_books_tab(self):
        tk.Label(self.tab_books, text="Selecione um livro para EMPRESTAR:", font=("Arial", 10, "bold")).pack(pady=10)
        
        cols = ("Código", "Título", "Autor")
        self.tree_books = ttk.Treeview(self.tab_books, columns=cols, show="headings", height=12)
        for c in cols: self.tree_books.heading(c, text=c)
        self.tree_books.column("Código", width=60)
        self.tree_books.column("Título", width=300)
        self.tree_books.pack(fill="x", padx=10)

        for b in self.system.books.values():
            self.tree_books.insert("", "end", values=(b.codigo, b.titulo, b.autor))

        tk.Button(self.tab_books, text="CONFIRMAR EMPRÉSTIMO", command=self.action_loan, bg="#2196F3", fg="white").pack(pady=10)

    def action_loan(self):
        if self.system.current_user.tipo.lower() != "cliente":
            messagebox.showwarning("Aviso", "Apenas clientes podem fazer empréstimos.")
            return
        sel = self.tree_books.selection()
        if not sel: return
        cod = self.tree_books.item(sel[0])['values'][0]
        ok, msg = self.system.create_loan(str(cod))
        if ok: 
            messagebox.showinfo("Sucesso", msg)
            self.refresh_loans_list()
        else: messagebox.showerror("Erro", msg)

    def setup_loans_tab(self):
        frame_btns = tk.Frame(self.tab_loans)
        frame_btns.pack(pady=10)

        tk.Button(frame_btns, text="RENOVAR (+7 dias)", command=self.action_renew, bg="#FF9800", fg="white").pack(side="left", padx=5)
        tk.Button(frame_btns, text="DEVOLVER / PAGAR MULTA", command=self.action_return, bg="#4CAF50", fg="white").pack(side="left", padx=5)

        cols = ("Cód. Livro", "Título", "Devolução Prevista", "Renovações")
        self.tree_loans = ttk.Treeview(self.tab_loans, columns=cols, show="headings", height=12)
        self.tree_loans.heading("Cód. Livro", text="Cód.")
        self.tree_loans.column("Cód. Livro", width=50)
        self.tree_loans.heading("Título", text="Livro")
        self.tree_loans.column("Título", width=250)
        self.tree_loans.heading("Devolução Prevista", text="Vencimento")
        self.tree_loans.heading("Renovações", text="Renov.")
        self.tree_loans.column("Renovações", width=60, anchor="center")
        self.tree_loans.pack(fill="x", padx=10)
        
        self.refresh_loans_list()

    def refresh_loans_list(self):
        for i in self.tree_loans.get_children(): self.tree_loans.delete(i)
        for ln in self.system.get_user_active_loans():
            book = self.system.books.get(ln.codigo_livro)
            tit = book.titulo if book else "???"
            self.tree_loans.insert("", "end", values=(ln.codigo_livro, tit, ln.data_devolucao_prevista.strftime("%d/%m/%Y"), f"{ln.renovacoes_realizadas}/{self.system.MAX_RENOVACOES}"))

    def get_selected_loan_book_code(self):
        sel = self.tree_loans.selection()
        if not sel: return None
        return str(self.tree_loans.item(sel[0])['values'][0])

    def action_renew(self):
        cod = self.get_selected_loan_book_code()
        if not cod: return messagebox.showwarning("Atenção", "Selecione um empréstimo na lista.")
        ok, msg = self.system.renew_loan(cod)
        if ok: messagebox.showinfo("Renovação", msg)
        else: messagebox.showerror("Erro", msg)
        self.refresh_loans_list()

    def action_return(self):
        cod = self.get_selected_loan_book_code()
        if not cod: return messagebox.showwarning("Atenção", "Selecione um empréstimo para devolver.")
        
        if messagebox.askyesno("Confirmar", "Deseja realmente devolver este livro? \n(Multas serão calculadas automaticamente)"):
            ok, msg = self.system.return_book(cod)
            messagebox.showinfo("Devolução", msg)
            self.refresh_loans_list()

    def setup_about_tab(self):
        tk.Label(self.tab_about, text=COMPANY["nome_empresa"], font=("Arial", 20, "bold")).pack(pady=20)
        tk.Message(self.tab_about, text=COMPANY["historia"], width=500, justify="center").pack()
        tk.Label(self.tab_about, text="\nEquipe:", font=("Arial", 12, "bold")).pack()
        for n, c in COMPANY["funcionarios"]: tk.Label(self.tab_about, text=f"{n} - {c}").pack()

if __name__ == "__main__":
    system = LibrarySystem()
    root = tk.Tk()
    app = LibraryGUI(root, system)
    root.mainloop()