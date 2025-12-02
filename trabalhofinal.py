from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date
import sys
import os

COMPANY = {
    "nome_empresa": "SoftLib Solutions",
    "nome_produto": "EmpréstimoEasy",
    "historia": (
        "Fundada em 2025 por entusiastas de bibliotecas e desenvolvedores, "
        "a SoftLib Solutions cria soluções simples e escaláveis para gestão "
        "de acervos e empréstimos. Nossa missão é aproximar leitores e "
        "conhecimento com tecnologia acessível."
    ),
    "funcionarios": [
        ("Mateus de Mattos", "Desenvolvedor Líder"),
        ("Kauã Neves", "Analista de Sistemas"),
        ("Arthur Santanna", "Testador QA"),
    ],
    "logo_ascii":
        """
         ,_,
        [0,0]
        |)--)- SoftLib Solutions
        -”-”- 
        """
}

# -------------------------
# DATACLASSES
# -------------------------
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
class BookStatus:
    codigo_livro: str
    posicao: str
    estado_conservacao: str
    acessivel_emprestimo: bool

@dataclass
class LoanRecord:
    codigo_emprestimo: str
    codigo_cliente: str
    codigo_livro: str
    data_emprestimo: datetime
    data_devolucao_prevista: datetime
    data_devolucao_real: Optional[datetime] = None
    multa_cobrada: float = 0.0  # mantido campo mas sem lógica de cobrança
    renovacoes_realizadas: int = 0


# -------------------------
# SISTEMA
# -------------------------
class LibrarySystem:
    def __init__(self,
                 folder: str = ".",
                 prazo_inicial: int = 7,
                 prazo_renovacao: int = 7,
                 max_renovacoes: int = 3,
                 max_emprestimos_ativos_por_cliente: int = 3):
        self.folder = folder
        self.users: Dict[str, User] = {}
        self.books: Dict[str, Book] = {}
        self.loans: List[LoanRecord] = []
        self.book_statuses: Dict[str, BookStatus] = {}
        self.current_user: Optional[User] = None

        self.PRAZO_DIAS_INICIAL = prazo_inicial
        self.PRAZO_DIAS_RENOVACAO = prazo_renovacao
        self.MAX_RENOVACOES = max_renovacoes
        self.MAX_ACTIVE_LOANS_PER_CLIENT = max_emprestimos_ativos_por_cliente

        # arquivos esperados (use filenames conforme seu projeto)
        self.USERS_FILE = os.path.join(self.folder, "usuarios.txt")
        self.BOOKS_FILE = os.path.join(self.folder, "livros.txt")
        self.STATUS_FILE = os.path.join(self.folder, "status.txt")
        self.LOANS_FILE = os.path.join(self.folder, "emprestimos.txt")

        # carrega tudo
        self.load_all_files()

    # -------------------------
    # UTILITÁRIOS DE DATA
    # -------------------------
    def _parse_date(self, s: str) -> Optional[datetime]:
        if s is None:
            return None
        s = s.strip()
        if s == "" or s.lower() == "none":
            return None
        # tenta ISO YYYY-MM-DD (formato do seu txt)
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            # tenta dd/mm/YYYY
            for fmt in ("%d/%m/%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    continue
        return None

    def _date_to_str(self, d: Optional[datetime]) -> str:
        return d.date().isoformat() if d is not None else "None"

    # -------------------------
    # LEITURA DOS ARQUIVOS
    # -------------------------
    def load_all_files(self):
        # -> Usuários
        self.users = {}
        try:
            with open(self.USERS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = [p.strip() for p in line.split(";")]
                    if len(parts) < 5:
                        continue
                    codigo, nome, tipo, login, senha = parts[:5]
                    self.users[login] = User(codigo, nome, tipo, login, senha)
        except FileNotFoundError:
            print(f"[Aviso] '{self.USERS_FILE}' não encontrado. Nenhum usuário carregado.")

        # -> Livros
        self.books = {}
        try:
            with open(self.BOOKS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = [p.strip() for p in line.split(";")]
                    if len(parts) < 3:
                        continue
                    codigo, titulo, autor = parts[:3]
                    self.books[codigo] = Book(codigo, titulo, autor)
        except FileNotFoundError:
            print(f"[Aviso] '{self.BOOKS_FILE}' não encontrado. Nenhum livro carregado.")

        # -> Status (opcional)
        self.book_statuses = {}
        try:
            with open(self.STATUS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = [p.strip() for p in line.split(";")]
                    if len(parts) < 4:
                        continue
                    codigo, posicao, estado, acess = parts[:4]
                    acess_bool = acess.lower() in ("true", "1", "sim", "s", "yes")
                    self.book_statuses[codigo] = BookStatus(codigo, posicao, estado, acess_bool)
        except FileNotFoundError:
            print(f"[Aviso] '{self.STATUS_FILE}' não encontrado. Criando status padrão para os livros carregados.")
            # cria status padrão
            for codigo in self.books.keys():
                self.book_statuses[codigo] = BookStatus(codigo, "Local Desconhecido", "Bom", True)

        # -> Empréstimos
        self.loans = []
        try:
            with open(self.LOANS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = [p.strip() for p in line.split(";")]
                    # esperamos 8 campos: codigo_emprestimo;codigo_cliente;codigo_livro;
                    # data_emprestimo;data_devolucao_prevista;data_devolucao_real;multa_cobrada;renovacoes_realizadas
                    if len(parts) < 8:
                        continue
                    ce, cc, cl, d_emp, d_prev, d_real, multa, renov = parts[:8]
                    d_emp_dt = self._parse_date(d_emp)
                    d_prev_dt = self._parse_date(d_prev) or (d_emp_dt + timedelta(days=self.PRAZO_DIAS_INICIAL) if d_emp_dt else None)
                    d_real_dt = self._parse_date(d_real)
                    try:
                        multa_f = float(multa)
                    except Exception:
                        multa_f = 0.0
                    try:
                        renov_i = int(renov)
                    except Exception:
                        renov_i = 0

                    ln = LoanRecord(
                        codigo_emprestimo=ce,
                        codigo_cliente=cc,
                        codigo_livro=cl,
                        data_emprestimo=d_emp_dt,
                        data_devolucao_prevista=d_prev_dt,
                        data_devolucao_real=d_real_dt,
                        multa_cobrada=multa_f,
                        renovacoes_realizadas=renov_i
                    )
                    self.loans.append(ln)
        except FileNotFoundError:
            print(f"[Aviso] '{self.LOANS_FILE}' não encontrado. Nenhum empréstimo carregado.")

    # -------------------------
    # GRAVAÇÃO DOS ARQUIVOS (persistência)
    # -------------------------
    def save_loans_to_file(self):
        # sobrescreve emprestimos.txt com o estado atual self.loans
        try:
            with open(self.LOANS_FILE, "w", encoding="utf-8") as f:
                f.write("# codigo_emprestimo;codigo_cliente;codigo_livro;data_emprestimo;data_devolucao_prevista;data_devolucao_real;multa_cobrada;renovacoes_realizadas\n")
                for ln in self.loans:
                    line = ";".join([
                        ln.codigo_emprestimo,
                        ln.codigo_cliente,
                        ln.codigo_livro,
                        self._date_to_str(ln.data_emprestimo),
                        self._date_to_str(ln.data_devolucao_prevista),
                        self._date_to_str(ln.data_devolucao_real),
                        f"{ln.multa_cobrada:.2f}",
                        str(ln.renovacoes_realizadas)
                    ])
                    f.write(line + "\n")
        except Exception as e:
            print(f"[Erro] ao salvar '{self.LOANS_FILE}': {e}")

    def save_status_to_file(self):
        # sobrescreve status.txt com estado atual dos livros
        try:
            with open(self.STATUS_FILE, "w", encoding="utf-8") as f:
                f.write("# codigo_livro;posicao;estado_conservacao;acessivel_emprestimo\n")
                for codigo, st in self.book_statuses.items():
                    line = ";".join([
                        st.codigo_livro,
                        st.posicao,
                        st.estado_conservacao,
                        "True" if st.acessivel_emprestimo else "False"
                    ])
                    f.write(line + "\n")
        except Exception as e:
            print(f"[Erro] ao salvar '{self.STATUS_FILE}': {e}")

    # -------------------------
    # VALIDAÇÃO DO USUÁRIO (LOGIN)
    # -------------------------
    def validate_user(self, login: str, senha: str) -> bool:
        user = self.users.get(login)
        if user and user.senha == senha:
            self.current_user = user
            return True
        return False

    # -------------------------
    # FUNÇÕES PRINCIPAIS (sem multas)
    # -------------------------
    def list_books(self):
        print("\n--- LISTA DE LIVROS ---")
        for b in self.books.values():
            st = self.book_statuses.get(b.codigo)
            emprestado = any(
                ln for ln in self.loans
                if ln.codigo_livro == b.codigo and ln.data_devolucao_real is None
            )
            print(f"[{b.codigo}] {b.titulo} — {b.autor}")
            print(f"   Estado: {st.estado_conservacao if st else '---'} | Local: {st.posicao if st else '---'} | Acessível: {st.acessivel_emprestimo if st else '---'}")
            print(f"   Situação: {'Emprestado' if emprestado else 'Disponível'}")
        print("----------------------------------\n")

    def get_current_user_loans_status(self):
        if not self.current_user:
            return []
        user_loans = [
            ln for ln in self.loans
            if ln.codigo_cliente == self.current_user.codigo and ln.data_devolucao_real is None
        ]
        loan_statuses = []
        for ln in user_loans:
            book = self.books.get(ln.codigo_livro)
            atrasado = False
            if ln.data_devolucao_prevista:
                hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                atrasado = (ln.data_devolucao_real is None) and (hoje.date() > ln.data_devolucao_prevista.date())
            loan_statuses.append({
                'record': ln,
                'titulo': book.titulo if book else "Livro Desconhecido",
                'atrasado': atrasado
            })
        return loan_statuses

    def list_loans_for_current_user(self):
        print(f"\n--- Empréstimos de {self.current_user.nome} ---")
        dados = self.get_current_user_loans_status()
        if not dados:
            print("Nenhum empréstimo ativo.\n")
            return

        for i, st in enumerate(dados, 1):
            ln = st["record"]
            status = "ATRASADO 🔴" if st["atrasado"] else "No Prazo 🟢"
            print(f"{i}. [{ln.codigo_livro}] {st['titulo']}")
            print(f"   Empréstimo: {ln.data_emprestimo.date()} | Prevista: {ln.data_devolucao_prevista.date()}")
            print(f"   Status: {status} | Renovações: {ln.renovacoes_realizadas}/{self.MAX_RENOVACOES}")
        print("----------------------------------\n")

    # -------------------------
    # RENOVAÇÃO DE EMPRÉSTIMO
    # -------------------------
    def renew_loan(self):
        if not self.current_user or self.current_user.tipo.lower() != "cliente":
            print("Apenas clientes podem renovar.")
            return

        dados = self.get_current_user_loans_status()
        if not dados:
            print("Não há empréstimos ativos.")
            return

        print("\n--- RENOVAR EMPRÉSTIMO ---")
        for i, st in enumerate(dados, 1):
            ln = st['record']
            print(f"{i}. {st['titulo']} (Dev. Prevista: {ln.data_devolucao_prevista.date()}) {'- ATRASADO' if st['atrasado'] else ''}")

        try:
            choice = int(input("Número do livro: ")) - 1
            if choice < 0 or choice >= len(dados):
                print("Opção inválida.")
                return

            st = dados[choice]
            ln = st['record']

            if st["atrasado"]:
                print("Não é possível renovar um livro atrasado.")
                return

            if ln.renovacoes_realizadas >= self.MAX_RENOVACOES:
                print("Limite máximo de renovações atingido.")
                return

            # aplica renovação
            ln.renovacoes_realizadas += 1
            ln.data_devolucao_prevista = ln.data_devolucao_prevista + timedelta(days=self.PRAZO_DIAS_RENOVACAO)

            # persiste no arquivo
            self.save_loans_to_file()

            print("\nRenovado com sucesso!")
            print(f"Nova devolução: {ln.data_devolucao_prevista.date()}")

        except ValueError:
            print("Entrada inválida.")

    # -------------------------
    # REALIZAR EMPRÉSTIMO
    # -------------------------
    def create_loan(self):
        if not self.current_user or self.current_user.tipo.lower() != "cliente":
            print("Apenas clientes podem realizar empréstimos.\n")
            return

        # checar limite de empréstimos ativos do cliente
        ativos_do_cliente = [
            ln for ln in self.loans
            if ln.codigo_cliente == self.current_user.codigo and ln.data_devolucao_real is None
        ]
        if len(ativos_do_cliente) >= self.MAX_ACTIVE_LOANS_PER_CLIENT:
            print(f"Você já possui {len(ativos_do_cliente)} empréstimos ativos. Limite de {self.MAX_ACTIVE_LOANS_PER_CLIENT} atingido.\n")
            return

        print("\n--- REALIZAR NOVO EMPRÉSTIMO ---")

        disponiveis = []
        for codigo, book in self.books.items():
            status = self.book_statuses.get(codigo)
            emprestado = any(
                ln for ln in self.loans
                if ln.codigo_livro == codigo and ln.data_devolucao_real is None
            )
            if status and status.acessivel_emprestimo and not emprestado:
                disponiveis.append(book)

        if not disponiveis:
            print("Nenhum livro disponível para empréstimo no momento.\n")
            return

        for i, b in enumerate(disponiveis, 1):
            st = self.book_statuses[b.codigo]
            print(f"{i}. [{b.codigo}] {b.titulo} — {b.autor}")
            print(f"   Local: {st.posicao} | Estado: {st.estado_conservacao}\n")

        try:
            escolha = int(input("Selecione o número do livro para emprestar: ")) - 1
            if escolha < 0 or escolha >= len(disponiveis):
                print("Opção inválida.\n")
                return

            book = disponiveis[escolha]

            # novo código sequencial (maior existente +1)
            existing_ids = [int(ln.codigo_emprestimo) for ln in self.loans if ln.codigo_emprestimo.isdigit()]
            novo_codigo_int = (max(existing_ids) + 1) if existing_ids else 1
            novo_codigo = str(novo_codigo_int).zfill(3)

            hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            devolucao_prevista = hoje + timedelta(days=self.PRAZO_DIAS_INICIAL)

            novo_emprestimo = LoanRecord(
                codigo_emprestimo=novo_codigo,
                codigo_cliente=self.current_user.codigo,
                codigo_livro=book.codigo,
                data_emprestimo=hoje,
                data_devolucao_prevista=devolucao_prevista,
                data_devolucao_real=None,
                multa_cobrada=0.0,
                renovacoes_realizadas=0
            )

            # adiciona e persiste
            self.loans.append(novo_emprestimo)

            # atualizar status do livro (marcar como não acessível)
            st = self.book_statuses.get(book.codigo)
            if st:
                st.acessivel_emprestimo = False
                # salva status
                self.save_status_to_file()

            # salva empréstimos no arquivo
            self.save_loans_to_file()

            print("\n📚 Empréstimo realizado com sucesso!")
            print(f"Livro: {book.titulo}")
            print(f"Data do Empréstimo: {hoje.date()}")
            print(f"Devolução Prevista: {devolucao_prevista.date()}\n")

        except ValueError:
            print("Entrada inválida.\n")

    # -------------------------
    # (Opcional) devolver um livro - marca data_devolucao_real e libera status
    # -------------------------
    def return_loan(self):
        if not self.current_user or self.current_user.tipo.lower() != "cliente":
            print("Apenas clientes podem devolver empréstimos.")
            return

        ativos = [ln for ln in self.loans if ln.codigo_cliente == self.current_user.codigo and ln.data_devolucao_real is None]
        if not ativos:
            print("Nenhum empréstimo ativo para devolver.")
            return

        print("\n--- DEVOLUÇÃO DE EMPRÉSTIMO ---")
        for i, ln in enumerate(ativos, 1):
            book = self.books.get(ln.codigo_livro)
            print(f"{i}. [{ln.codigo_emprestimo}] {book.titulo if book else ln.codigo_livro} - Prevista: {ln.data_devolucao_prevista.date()}")

        try:
            choice = int(input("Número do empréstimo para devolver: ")) - 1
            if choice < 0 or choice >= len(ativos):
                print("Opção inválida.")
                return
            ln = ativos[choice]
            ln.data_devolucao_real = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            # liberar status do livro
            st = self.book_statuses.get(ln.codigo_livro)
            if st:
                st.acessivel_emprestimo = True
                self.save_status_to_file()
            self.save_loans_to_file()
            print("Devolução registrada com sucesso.")
        except ValueError:
            print("Entrada inválida.")

    # -------------------------
    # SOBRE
    # -------------------------
    def show_about(self):
        print("\n" + "=" * 50)
        print(COMPANY["logo_ascii"])
        print(f"Empresa: {COMPANY['nome_empresa']}")
        print(f"Produto: {COMPANY['nome_produto']}\n")
        print("História:")
        print(COMPANY["historia"] + "\n")
        print("Funcionários:")
        for nome, func in COMPANY["funcionarios"]:
            print(f" - {nome}: {func}")
        print("=" * 50 + "\n")

    # -------------------------
    # RODAR CONSOLE
    # -------------------------
    def run_console(self):
        print("=" * 60)
        print("Sistema de Empréstimos — EmpréstimoEasy (SoftLib Solutions)")
        print("Login necessário para continuar.")
        print("=" * 60)

        try:
            login = input("Login: ").strip()
            senha = input("Senha: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("Saindo...")
            sys.exit(0)

        if not self.validate_user(login, senha):
            print("Acesso negado!")
            return

        print(f"\nBem-vindo, {self.current_user.nome} ({self.current_user.tipo})\n")

        if self.current_user.tipo.lower() == "cliente":
            while True:
                print("1 - Visualizar Empréstimos")
                print("2 - Renovar Empréstimo")
                print("3 - Visualizar Livros")
                print("4 - Realizar Empréstimo")
                print("5 - Devolver Empréstimo")
                print("6 - Sobre a SoftLib Solutions")
                print("7 - Sair")
                op = input("Escolha: ")

                if op == "1":
                    self.list_loans_for_current_user()
                elif op == "2":
                    self.renew_loan()
                elif op == "3":
                    self.list_books()
                elif op == "4":
                    self.create_loan()
                elif op == "5":
                    self.return_loan()
                elif op == "6":
                    self.show_about()
                elif op == "7":
                    print("Saindo... Obrigado pela preferência!")
                    break
                else:
                    print("Opção inválida.\n")
        else:
            # menu simplificado para bibliotecário
            while True:
                print("1 - Ver Histórico (todos empréstimos)")
                print("2 - Ver Livros")
                print("3 - Sobre")
                print("4 - Sair")
                op = input("Escolha: ")

                if op == "1":
                    self.list_all_loans()
                elif op == "2":
                    self.list_books()
                elif op == "3":
                    self.show_about()
                elif op == "4":
                    print("Saindo...")
                    break
                else:
                    print("Opção inválida.\n")

    # -------------------------
    # LISTAR HISTÓRICO (BIBLIOTECÁRIO)
    # -------------------------
    def list_all_loans(self):
        print("\n--- HISTÓRICO COMPLETO ---")
        for r in sorted(self.loans, key=lambda x: x.data_emprestimo or datetime.min, reverse=True):
            book = self.books.get(r.codigo_livro)
            real = r.data_devolucao_real.date() if r.data_devolucao_real else "ATIVO"
            status = "DEVOLVIDO" if r.data_devolucao_real else "ATIVO"
            print(f"[{r.codigo_emprestimo}] {status}")
            print(f"  Livro: {book.titulo if book else '???'}")
            print(f"  Empréstimo: {(r.data_emprestimo.date() if r.data_emprestimo else '---')} | Prevista: {(r.data_devolucao_prevista.date() if r.data_devolucao_prevista else '---')}")
            print(f"  Devolução: {real} | Multa (campo ignorado): R$ {r.multa_cobrada:.2f}")
        print("----------------------------------\n")


# -------------------------
# MAIN
# -------------------------
def main():
    system = LibrarySystem(folder=".")
    system.run_console()

if __name__ == "__main__":
    main()
