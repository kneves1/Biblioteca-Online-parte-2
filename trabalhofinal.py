from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import sys

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
    multa_cobrada: float = 0.0
    renovacoes_realizadas: int = 0


class LibrarySystem:
    def create_loan(self):
        if not self.current_user or self.current_user.tipo.lower() != "cliente":
            print("Apenas clientes podem realizar empréstimos.\n")
            return

        print("\n--- REALIZAR NOVO EMPRÉSTIMO ---")

        disponiveis = []
        for codigo, book in self.books.items():
            status = self.book_statuses.get(codigo)
            emprestado = any(
                ln for ln in self.loans
                if ln.codigo_livro == codigo and ln.data_devolucao_real is None
            )
            if status.acessivel_emprestimo and not emprestado:
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
            novo_codigo = str(len(self.loans) + 1).zfill(3)

            hoje = datetime.now()
            devolucao_prevista = hoje + timedelta(days=self.PRAZO_DIAS_INICIAL)

            novo_emprestimo = LoanRecord(
                codigo_emprestimo=novo_codigo,
                codigo_cliente=self.current_user.codigo,
                codigo_livro=book.codigo,
                data_emprestimo=hoje,
                data_devolucao_prevista=devolucao_prevista
            )

            self.loans.append(novo_emprestimo)

            print("\n📚 Empréstimo realizado com sucesso!")
            print(f"Livro: {book.titulo}")
            print(f"Data do Empréstimo: {hoje.date()}")
            print(f"Devolução Prevista: {devolucao_prevista.date()}\n")

        except ValueError:
            print("Entrada inválida.\n")

    def pay_fines(self):
        if not self.current_user or self.current_user.tipo.lower() != "cliente":
            print("Apenas clientes podem pagar multas.\n")
            return

        print("\n--- PAGAMENTO DE MULTAS ---")

        loan_statuses = self.get_current_user_loans_status()
        overdue = [s for s in loan_statuses if s['atrasado']]

        if not overdue:
            print("Você não possui multas pendentes!\n")
            return

        total_multa = sum(s["multa_atual"] for s in overdue)

        print(f"\nMultas em aberto encontradas: R$ {total_multa:.2f}\n")

        for i, st in enumerate(overdue, 1):
            ln = st["record"]
            print(f"{i}. Livro: {st['titulo']}")
            print(f"   Multa atual: R$ {st['multa_atual']:.2f}")
            print(f"   Previsão antiga: {ln.data_devolucao_prevista.date()}\n")

        print("0 - Pagar TODAS as multas")

        try:
            choice = int(input("Escolha qual multa pagar: "))

            if choice == 0:
                for st in overdue:
                    ln = st["record"]
                    ln.multa_cobrada += st["multa_atual"]
                    ln.data_devolucao_real = datetime.now()
                print("\n💸 Todas as multas foram pagas com sucesso!\n")
                return

            index = choice - 1
            if index < 0 or index >= len(overdue):
                print("Opção inválida.\n")
                return

            st = overdue[index]
            ln = st["record"]

            ln.multa_cobrada += st["multa_atual"]
            ln.data_devolucao_real = datetime.now()

            print(f"\n💸 Multa do livro '{st['titulo']}' paga com sucesso!")
            print(f"Valor pago: R$ {st['multa_atual']:.2f}\n")

        except ValueError:
            print("Entrada inválida.\n")

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.books: Dict[str, Book] = {}
        self.loans: List[LoanRecord] = []
        self.book_statuses: Dict[str, BookStatus] = {}
        self.current_user: Optional[User] = None

        self.PRAZO_DIAS_INICIAL = 7
        self.PRAZO_DIAS_RENOVACAO = 7
        self.MAX_RENOVACOES = 2
        self.MULTA_DIA = 0.50

        self.load_all_files()
        self.loans = [
            LoanRecord("001", "C101", "L001", datetime(2025,12,1), datetime(2025,12,8), datetime(2025,12,9)),
            LoanRecord("002", "C102", "L002", datetime(2025,12,3), datetime(2025,12,10), datetime(2025,12,11)),
            LoanRecord("003", "C101", "L004", datetime(2025,12,4), datetime(2025,12,11), datetime(2025,12,12), 0.0, 1)
        ]

    def load_all_files(self):
        self.users = {
            "jsilva": User("C101", "João Silva", "Cliente", "jsilva", "12345"),
            "msouza": User("C102", "Maria Souza", "Cliente", "msouza", "45678"),
            "lferreira": User("B001", "Lucas Ferreira", "Bibliotecário", "lferreira", "99999"),
        }

        self.books = {
            "L001": Book("L001", "Python para Todos", "Guido van Rossum"),
            "L002": Book("L002", "Introdução à POO", "Grady Booch"),
            "L003": Book("L003", "A Arte de Programar", "Donald Knuth"),
            "L004": Book("L004", "Fundamentos de Cibersegurança", "Bruce Schneier"),
        }

        self.book_statuses = {
            "L001": BookStatus("L001", "A01, Estante 1", "Bom", True),
            "L002": BookStatus("L002", "A02, Estante 1", "Novo", True),
            "L003": BookStatus("L003", "B01, Armário 3", "Desgastado", False),
            "L004": BookStatus("L004", "B02, Estante 2", "Bom", True),
        }

    def validate_user(self, login: str, senha: str) -> bool:
        user = self.users.get(login)
        if user and user.senha == senha:
            self.current_user = user
            return True
        return False

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

    def calculate_current_fine(self, record: LoanRecord) -> float:
        if record.data_devolucao_real:
            return 0.0
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if hoje > record.data_devolucao_prevista:
            dias = (hoje - record.data_devolucao_prevista).days
            return dias * self.MULTA_DIA
        return 0.0

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
            multa = self.calculate_current_fine(ln)
            atrasado = multa > 0
            loan_statuses.append({
                'record': ln,
                'titulo': book.titulo if book else "Livro Desconhecido",
                'atrasado': atrasado,
                'multa_atual': multa
            })
        return loan_statuses

    def list_loans_for_current_user(self):
        print(f"\n--- Empréstimos de {self.current_user.nome} ---")
        dados = self.get_current_user_loans_status()
        if not dados:
            print("Nenhum empréstimo ativo.\n")
            return

        total = 0
        for i, st in enumerate(dados, 1):
            ln = st["record"]
            status = "ATRASADO 🔴" if st["atrasado"] else "No Prazo 🟢"
            multa = f" (Multa: R$ {st['multa_atual']:.2f})" if st["atrasado"] else ""
            print(f"{i}. [{ln.codigo_livro}] {st['titulo']}")
            print(f"   Empréstimo: {ln.data_emprestimo.date()} | Prevista: {ln.data_devolucao_prevista.date()}")
            print(f"   Status: {status}{multa} | Renovações: {ln.renovacoes_realizadas}/{self.MAX_RENOVACOES}")
            total += st["multa_atual"]

        print("----------------------------------")
        print(f"Total de Multas: R$ {total:.2f}")
        print("----------------------------------\n")

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
            ln = st["record"]
            print(f"{i}. {st['titulo']} (Dev. Prevista: {ln.data_devolucao_prevista.date()})")

        try:
            choice = int(input("Número do livro: ")) - 1
            if choice < 0 or choice >= len(dados):
                print("Opção inválida.")
                return

            st = dados[choice]
            ln = st["record"]

            if st["atrasado"]:
                print("Não é possível renovar um livro atrasado.")
                return

            if ln.renovacoes_realizadas >= self.MAX_RENOVACOES:
                print("Limite máximo de renovações atingido.")
                return

            ln.renovacoes_realizadas += 1
            ln.data_devolucao_prevista += timedelta(days=self.PRAZO_DIAS_RENOVACAO)

            print("\nRenovado com sucesso!")
            print(f"Nova devolução: {ln.data_devolucao_prevista.date()}")

        except ValueError:
            print("Entrada inválida.")

    def list_books(self):
        print("\n--- LISTA DE LIVROS ---")
        for b in self.books.values():
            st = self.book_statuses.get(b.codigo)
            emprestado = any(
                ln for ln in self.loans
                if ln.codigo_livro == b.codigo and ln.data_devolucao_real is None
            )
            print(f"[{b.codigo}] {b.titulo} — {b.autor}")
            print(f"   Estado: {st.estado_conservacao} | Local: {st.posicao} | Acessível: {st.acessivel_emprestimo}")
            print(f"   Situação: {'Emprestado' if emprestado else 'Disponível'}")

        print("----------------------------------\n")

    def list_all_loans(self):
        print("\n--- HISTÓRICO COMPLETO ---")
        for r in sorted(self.loans, key=lambda x: x.data_emprestimo, reverse=True):
            book = self.books.get(r.codigo_livro)
            real = r.data_devolucao_real.date() if r.data_devolucao_real else "ATIVO"
            status = "DEVOLVIDO" if r.data_devolucao_real else "ATIVO"
            print(f"[{r.codigo_emprestimo}] {status}")
            print(f"  Livro: {book.titulo if book else '???'}")
            print(f"  Empréstimo: {r.data_emprestimo.date()} | Prevista: {r.data_devolucao_prevista.date()}")
            print(f"  Devolução: {real} | Multa: R$ {r.multa_cobrada:.2f}")
        print("----------------------------------\n")

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
                print("1 - Visualizar Empréstimos e Multas")
                print("2 - Renovar Empréstimo")
                print("3 - Pagar Multas")
                print("4 - Visualizar Livros")
                print("5 - Realizar Empréstimo")
                print("6 - Sobre a SoftLib Solutions")
                print("7 - Sair")
                op = input("Escolha: ")

                if op == "1":
                    self.list_loans_for_current_user()
                elif op == "2":
                    self.renew_loan()
                elif op == "3":
                    self.pay_fines()
                elif op == "4":
                    self.list_books()
                elif op == "5":
                    self.create_loan()
                elif op == "6":
                    self.show_about()
                elif op == "7":
                    print("Saindo... Obrigado pela preferência!")
                    break
                else:
                    print("Opção inválida.\n")

        else:
            while True:
                print("1 - Ver Histórico")
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


def main():
    system = LibrarySystem()
    system.run_console()

if __name__ == "__main__":
    main()
