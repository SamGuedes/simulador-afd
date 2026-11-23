import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


def lista(dados, campo):
    valores = dados.get(campo)
    if not isinstance(valores, list):
        raise ValueError(f"O campo '{campo}' deve ser uma lista.")
    for valor in valores:
        if not isinstance(valor, str) or not valor:
            raise ValueError(f"Use textos não vazios em '{campo}'.")
    if len(set(valores)) != len(valores):
        raise ValueError(f"Há valores repetidos em '{campo}'.")
    return valores


def sem_chaves_repetidas(pares):
    objeto = {}
    for chave, valor in pares:
        if chave in objeto:
            raise ValueError(f"Chave repetida no JSON: {chave!r}.")
        objeto[chave] = valor
    return objeto


def carregar_afd(caminho):
    with open(caminho, encoding="utf-8-sig") as arquivo:
        dados = json.load(arquivo, object_pairs_hook=sem_chaves_repetidas)
    if not isinstance(dados, dict):
        raise ValueError("O arquivo deve conter um objeto JSON.")

    estados = lista(dados, "estados")
    alfabeto = lista(dados, "alfabeto")
    finais = lista(dados, "finais")
    if dados.get("inicial") not in estados:
        raise ValueError("O estado inicial deve pertencer à lista de estados.")
    if not set(finais).issubset(estados):
        raise ValueError("Todos os estados finais devem pertencer à lista de estados.")
    if any(len(simbolo) != 1 for simbolo in alfabeto):
        raise ValueError("Cada símbolo do alfabeto deve ter um caractere.")

    tabela = dados.get("transicoes")
    if not isinstance(tabela, dict) or set(tabela) != set(estados):
        raise ValueError("Informe uma linha de transições para cada estado declarado.")
    for origem, linha in tabela.items():
        if not isinstance(linha, dict) or set(linha) != set(alfabeto):
            raise ValueError(f"Em '{origem}', informe um destino para cada símbolo do alfabeto.")
        for destino in linha.values():
            if destino not in estados:
                raise ValueError(f"Destino inválido na linha de '{origem}': {destino!r}.")
    return dados


class Simulador:
    def __init__(self, janela):
        self.janela = janela
        self.afd = None
        janela.title("Simulador de AFD")
        painel = ttk.Frame(janela, padding=16)
        painel.pack(fill="both", expand=True)
        painel.columnconfigure(0, weight=1)
        painel.rowconfigure(5, weight=1)

        ttk.Button(painel, text="Abrir arquivo JSON", command=self.abrir).grid(sticky="w")
        self.modelo = ttk.Label(painel, text="Carregue um autômato para começar.")
        self.modelo.grid(row=1, sticky="w", pady=8)
        ttk.Label(painel, text="Sentença (deixe em branco para testar ε)").grid(row=2, sticky="w")
        self.sentenca = tk.StringVar()
        ttk.Entry(painel, textvariable=self.sentenca).grid(row=3, sticky="ew")
        botoes = ttk.Frame(painel)
        botoes.grid(row=4, sticky="w", pady=10)
        ttk.Button(botoes, text="Próximo passo", command=self.avancar).pack(side="left")
        ttk.Button(botoes, text="Executar até o fim", command=self.executar).pack(side="left", padx=6)
        ttk.Button(botoes, text="Reiniciar", command=self.reiniciar).pack(side="left")

        colunas = ("Passo", "Origem", "Símbolo", "Destino")
        self.historico = ttk.Treeview(painel, columns=colunas, show="headings", height=10)
        for coluna in colunas:
            self.historico.heading(coluna, text=coluna)
            self.historico.column(coluna, width=125, anchor="center")
        self.historico.grid(row=5, sticky="nsew")
        barra = ttk.Scrollbar(painel, command=self.historico.yview)
        barra.grid(row=5, column=1, sticky="ns")
        self.historico.configure(yscrollcommand=barra.set)
        self.status = ttk.Label(painel)
        self.status.grid(row=6, sticky="w", pady=(8, 0))
        self.sentenca.trace_add("write", self.reiniciar)
        self.carregar(Path(__file__).with_name("exemplo.json"))

    def abrir(self):
        caminho = filedialog.askopenfilename(filetypes=[("Autômato JSON", "*.json")])
        if caminho:
            self.carregar(caminho)

    def carregar(self, caminho):
        try:
            self.afd = carregar_afd(caminho)
        except (OSError, ValueError) as erro:
            messagebox.showerror("Erro ao abrir autômato", str(erro))
            return
        finais = ", ".join(self.afd["finais"]) or "∅"
        self.modelo.config(text=f"{Path(caminho).name}   |   Inicial: {self.afd['inicial']}   |   Finais: {finais}")
        self.reiniciar()

    def reiniciar(self, *args):
        if self.afd is None:
            return
        self.historico.delete(*self.historico.get_children())
        self.fita = self.sentenca.get()
        self.posicao = 0
        self.estado = self.afd["inicial"]
        self.terminou = False
        self.status.config(text=f"Estado inicial: {self.estado}   |   Símbolos lidos: 0 de {len(self.fita)}")

    def avancar(self):
        if self.afd is None or self.terminou:
            return
        if self.posicao < len(self.fita):
            simbolo = self.fita[self.posicao]
            passo = self.posicao + 1
            if simbolo not in self.afd["alfabeto"]:
                self.registrar(passo, simbolo, "—")
                self.status.config(text=f"Rejeitada. Símbolo {simbolo!r} fora do alfabeto na posição {passo}.")
                self.terminou = True
                return
            destino = self.afd["transicoes"][self.estado][simbolo]
            self.registrar(passo, simbolo, destino)
            self.estado = destino
            self.posicao = passo
        if self.posicao == len(self.fita):
            self.terminou = True
            resultado = "Aceita" if self.estado in self.afd["finais"] else "Rejeitada"
            self.status.config(text=f"{resultado}. Fim da fita no estado {self.estado}.")
        else:
            self.status.config(text=f"Estado atual: {self.estado}   |   Símbolos lidos: {self.posicao} de {len(self.fita)}")

    def registrar(self, passo, simbolo, destino):
        linha = self.historico.insert("", "end", values=(passo, self.estado, simbolo, destino))
        self.historico.see(linha)

    def executar(self):
        if self.afd is None:
            return
        while not self.terminou:
            self.avancar()


if __name__ == "__main__":
    janela = tk.Tk()
    Simulador(janela)
    janela.mainloop()
