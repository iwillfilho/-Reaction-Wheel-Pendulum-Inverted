"""Conversor LaTeX -> HTML só para o subconjunto que plano/montagem_fisica.tex usa.

Não é um conversor geral: trata as macros e os ambientes do guia (tarefas, passos,
checklists, tabelas, figuras do CAD) e manda os desenhos TikZ para `snippets`, que
tools/gerar_visualizacao.py compila à parte e devolve como imagem.

Marcadores deixados no HTML e resolvidos depois:
    \\x00REF:rótulo\\x00   referência cruzada (\\ref)
    <img data-fig="nome">  figura de plano/figuras/ (a página põe o src)
    <img data-tikz="n">    desenho TikZ número n de `snippets`
"""
from __future__ import annotations

import html
import re
from collections import Counter

UNIDADES = [
    (r"\kilo", "k"), (r"\micro", "µ"), (r"\nano", "n"), (r"\milli", "m"),
    (r"\ohm", "Ω"), (r"\farad", "F"), (r"\volt", "V"), (r"\ampere", "A"),
    (r"\hertz", "Hz"), (r"\second", "s"), (r"\gram", "g"), (r"\metre", "m"),
    (r"\meter", "m"), (r"\celsius", "°C"),
]

# macros sem argumento que viram texto
SIMBOLOS = {
    "flecha": "→", "aprox": "≈", "caixa": "☐", "dots": "…", "ldots": "…",
    "textbullet": "•", "textonequarter": "¼", "quad": " ", "qquad": " ",
    "hfill": " ", "times": "×", "pm": "±", "geq": "≥", "leq": "≤", "approx": "≈",
    "textendash": "–", "textemdash": "—", "LaTeX": "LaTeX",
}

# macros ignoradas, com o número de argumentos {} que consomem
IGNORADAS = {
    "centering": 0, "small": 0, "footnotesize": 0, "scriptsize": 0, "tiny": 0,
    "large": 0, "Large": 0, "Huge": 0, "normalsize": 0, "sffamily": 0, "bfseries": 0,
    "noindent": 0, "protect": 0, "newpage": 0, "clearpage": 0, "tableofcontents": 0,
    "appendix": 0, "raggedright": 0, "arraybackslash": 0, "smallskip": 0,
    "medskip": 0, "bigskip": 0, "toprule": 0, "bottomrule": 0, "endfirsthead": 0,
    "endhead": 0, "endlastfoot": 0, "vfill": 0, "linewidth": 0, "textwidth": 0,
    "color": 1, "needspace": 1, "vspace": 1, "hspace": 1, "hypersetup": 1,
}

TRILHAS = {"mec": "mecanica", "ele": "eletrica", "int": "integracao"}


def esc(s: str) -> str:
    return html.escape(s, quote=False)


class Conversor:
    def __init__(self, il_nargs: dict[str, int]):
        self.il_nargs = il_nargs          # \ilXxx -> número de argumentos
        self.snippets: list[str] = []     # LaTeX cru dos desenhos TikZ
        self.figuras: set[str] = set()    # PNGs de plano/figuras usados
        self.rotulos: dict[str, str] = {} # \label -> texto do \ref
        self.tarefas: list[dict] = []
        self.secoes: list[dict] = []
        self.desconhecidas: Counter = Counter()
        self.nfig = 0
        self.ntab = 0
        self.nsec = 0
        self.apendice = False
        self.ultimo = ""                  # o que um \label logo depois nomeia
        self.ncheck = 0
        self.tarefa_atual = ""
        self.em_tabela = False

    # ------------------------------------------------------------------ leitura
    @staticmethod
    def pula_espacos(s: str, i: int) -> int:
        while i < len(s) and s[i] in " \t\n":
            i += 1
        return i

    def grupo(self, s: str, i: int) -> tuple[str, int]:
        """Lê {..} (ou um único token) a partir de i; devolve (conteúdo, fim)."""
        i = self.pula_espacos(s, i)
        if i >= len(s):
            return "", i
        if s[i] != "{":
            if s[i] == "\\":
                m = re.match(r"\\([A-Za-z]+|.)", s[i:])
                return m.group(0), i + len(m.group(0))
            return s[i], i + 1
        n, j = 0, i
        while j < len(s):
            c = s[j]
            if c == "\\":
                j += 2
                continue
            if c == "{":
                n += 1
            elif c == "}":
                n -= 1
                if n == 0:
                    return s[i + 1:j], j + 1
            j += 1
        raise ValueError(f"chave sem par perto de: {s[i:i + 60]!r}")

    def opcional(self, s: str, i: int) -> tuple[str | None, int]:
        j = self.pula_espacos(s, i)
        if j < len(s) and s[j] == "[":
            n = 0
            for k in range(j, len(s)):
                if s[k] == "[":
                    n += 1
                elif s[k] == "]":
                    n -= 1
                    if n == 0:
                        return s[j + 1:k], k + 1
        return None, i

    def corpo_ambiente(self, s: str, i: int, nome: str) -> tuple[str, int]:
        abre, fecha = "\\begin{" + nome + "}", "\\end{" + nome + "}"
        n, j = 1, i
        while True:
            a, f = s.find(abre, j), s.find(fecha, j)
            if f < 0:
                raise ValueError(f"\\end{{{nome}}} não encontrado")
            if 0 <= a < f:
                n, j = n + 1, a + len(abre)
            else:
                n -= 1
                if n == 0:
                    return s[i:f], f + len(fecha)
                j = f + len(fecha)

    @staticmethod
    def divide_topo(s: str, sep: str) -> list[str]:
        """Divide s em `sep` fora de chaves e de ambientes aninhados."""
        partes, n, prof, ini, i = [], 0, 0, 0, 0
        while i < len(s):
            if s.startswith("\\begin{", i):
                prof += 1
            elif s.startswith("\\end{", i):
                prof -= 1
            if s[i] == "\\" and not s.startswith(sep, i):
                i += 2
                continue
            if s[i] == "{":
                n += 1
            elif s[i] == "}":
                n -= 1
            elif n == 0 and prof == 0 and s.startswith(sep, i):
                if sep[-1].isalpha() and i + len(sep) < len(s) and s[i + len(sep)].isalpha():
                    i += 1
                    continue
                partes.append(s[ini:i])
                ini = i = i + len(sep)
                continue
            i += 1
        partes.append(s[ini:])
        return partes

    # ---------------------------------------------------------------- conversão
    def conv(self, s: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(s):
            c = s[i]
            if c == "%":                          # comentário até o fim da linha
                j = s.find("\n", i)
                i = len(s) if j < 0 else j + 1
                continue
            if c == "\\":
                if i + 1 < len(s) and not s[i + 1].isalpha():
                    sym = s[i + 1]
                    i += 2
                    out.append({"\\": "<br>", ",": "\u202f", "%": "%", "_": "_",
                                "&": "&amp;", "#": "#", "{": "{", "}": "}", " ": " ",
                                "$": "$", "-": ""}.get(sym, ""))
                    continue
                nome = re.match(r"[A-Za-z]+\*?", s[i + 1:]).group(0)
                i += 1 + len(nome)
                txt, i = self.macro(nome, s, i)
                out.append(txt)
                continue
            if c == "$":
                j = s.index("$", i + 1)
                out.append(self.matematica(s[i + 1:j]))
                i = j + 1
                continue
            if s.startswith("``", i):
                out.append("“"); i += 2; continue
            if s.startswith("''", i):
                out.append("”"); i += 2; continue
            if s.startswith("---", i):
                out.append("—"); i += 3; continue
            if s.startswith("--", i):
                out.append("–"); i += 2; continue
            if c == "~":
                out.append("\u00a0"); i += 1; continue
            if c in "{}":
                i += 1; continue
            if c == "\n":
                m = re.match(r"\n[ \t]*\n\s*", s[i:])
                if m:
                    out.append('\n<span class="par"></span>')
                    i += len(m.group(0))
                    continue
            out.append(esc(c))
            i += 1
        return "".join(out)

    def matematica(self, s: str) -> str:
        s = re.sub(r"_\\text\{([^}]*)\}", r"<sub>\1</sub>", s)
        s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
        s = re.sub(r"_\{([^}]*)\}", r"<sub>\1</sub>", s)
        s = re.sub(r"_(\w)", r"<sub>\1</sub>", s)
        s = s.replace("{,}", ",").replace("\\,", "\u202f")
        for k, v in SIMBOLOS.items():
            espaco = " " if k in ("times", "approx", "geq", "leq") else ""
            s = re.sub(r"\s*\\" + k + r"(?![A-Za-z])\s*", (espaco + v + espaco) if espaco else v, s)
        s = s.replace("{", "").replace("}", "")
        s = re.sub(r"\b([A-Za-z])\b(?![^<]*>)", r"<i>\1</i>", s)
        return s

    def unidade(self, u: str) -> str:
        for k, v in UNIDADES:
            u = u.replace(k, v)
        return u.replace("\\per", "/").replace(" ", "")

    def texto_puro(self, s: str) -> str:
        """Conversão para títulos e atributos: sem tags."""
        return re.sub(r"<[^>]+>", "", self.conv(s)).strip()

    def legenda(self, tipo: str) -> str:
        if tipo == "figura":
            self.nfig += 1
            self.ultimo = f"figura {self.nfig}"
            return f"<b>Figura {self.nfig}.</b> "
        self.ntab += 1
        self.ultimo = f"tabela {self.ntab}"
        return f"<b>Tabela {self.ntab}.</b> "

    def tikz(self, cru: str, classe: str = "") -> str:
        self.snippets.append(cru)
        return f'<img class="tikz {classe}" data-tikz="{len(self.snippets) - 1}" alt="desenho">'

    def macro(self, nome: str, s: str, i: int) -> tuple[str, int]:
        if nome in SIMBOLOS:
            return SIMBOLOS[nome], self.pula_espacos_controle(s, i)
        if nome in IGNORADAS:
            for _ in range(IGNORADAS[nome]):
                _, i = self.grupo(s, i)
            return "", self.pula_espacos_controle(s, i) if IGNORADAS[nome] == 0 else i
        if nome == "begin":
            amb, i = self.grupo(s, i)
            corpo_ini = i
            corpo, i = self.corpo_ambiente(s, corpo_ini, amb)
            return self.ambiente(amb, corpo), i
        if nome in ("textbf", "textit", "emph", "texttt", "textsc", "mbox"):
            a, i = self.grupo(s, i)
            tag = {"textbf": "strong", "textit": "em", "emph": "em", "texttt": "code"}.get(nome)
            return (f"<{tag}>{self.conv(a)}</{tag}>" if tag else self.conv(a)), i
        if nome in ("cmd", "detokenize"):
            a, i = self.grupo(s, i)
            return f"<code>{esc(a)}</code>", i
        if nome in ("arq", "path"):
            a, i = self.grupo(s, i)
            return f'<code class="arq">{esc(a)}</code>', i
        if nome == "qty":
            n, i = self.grupo(s, i)
            u, i = self.grupo(s, i)
            return f"{esc(n)}\u00a0{self.unidade(u)}", i
        if nome == "linha":
            _, i = self.opcional(s, i)
            return '<span class="linha"></span>', i
        if nome == "ref":
            a, i = self.grupo(s, i)
            return f"\x00REF:{a}\x00", i
        if nome == "label":
            a, i = self.grupo(s, i)
            self.rotulos[a] = self.ultimo
            return f'<a id="{esc(a)}"></a>', i
        if nome in ("section", "subsection", "paragraph"):
            a, i = self.grupo(s, i)
            titulo = self.conv(a)
            if nome == "paragraph":
                return f"<strong>{titulo}</strong> ", i
            if nome == "section":
                self.nsec += 1
                num = chr(64 + self.nsec - self.inicio_apendice) if self.apendice else str(self.nsec)
                self.ultimo = ("apêndice " if self.apendice else "seção ") + num
                return f"\x00SEC:{num}:{titulo}\x00", i
            self.ultimo = "a seção “" + self.texto_puro(a) + "”"
            return f"<h3>{titulo}</h3>", i
        if nome == "objetivo":
            a, i = self.grupo(s, i)
            return f'<p class="objetivo"><b>Objetivo:</b> {self.conv(a)}</p>', i
        if nome == "includegraphics":
            _, i = self.opcional(s, i)
            a, i = self.grupo(s, i)
            self.figuras.add(a)
            return f'<img class="cad" data-fig="{esc(a)}" alt="{esc(a)}">', i
        if nome == "figpasso":
            img, i = self.grupo(s, i)
            _, i = self.grupo(s, i)
            leg, i = self.grupo(s, i)
            self.figuras.add(img)
            return (f'<figure class="passo"><img class="cad" data-fig="{esc(img)}" alt="">'
                    f"<figcaption>{self.conv(leg)}</figcaption></figure>"), i
        if nome == "figdupla":
            a, i = self.grupo(s, i)
            b, i = self.grupo(s, i)
            _, i = self.grupo(s, i)
            la, i = self.grupo(s, i)
            lb, i = self.grupo(s, i)
            self.figuras.update([a, b])
            return ('<div class="dupla">'
                    f'<figure class="passo"><img class="cad" data-fig="{esc(a)}" alt=""><figcaption>{self.conv(la)}</figcaption></figure>'
                    f'<figure class="passo"><img class="cad" data-fig="{esc(b)}" alt=""><figcaption>{self.conv(lb)}</figcaption></figure>'
                    "</div>"), i
        if nome == "figil":
            conteudo, i = self.grupo(s, i)
            leg, i = self.grupo(s, i)
            rot, i = self.grupo(s, i)
            if "\\il" in conteudo or "tikzpicture" in conteudo:
                corpo = self.tikz(conteudo)
            else:
                corpo = self.conv(conteudo)
            num = self.legenda("figura")
            self.rotulos[rot] = self.ultimo
            return (f'<figure class="il" id="{esc(rot)}">{corpo}'
                    f"<figcaption>{num}{self.conv(leg)}</figcaption></figure>"), i
        if nome in ("caption", "captionof"):
            tipo = "figure"
            if nome == "captionof":
                tipo, i = self.grupo(s, i)
            a, i = self.grupo(s, i)
            if self.em_tabela:
                tipo = "table"
            num = self.legenda("figura" if tipo == "figure" else "tabela")
            return f"<figcaption>{num}{self.conv(a)}</figcaption>", i
        if nome == "resizebox":
            _, i = self.grupo(s, i)
            _, i = self.grupo(s, i)
            a, i = self.grupo(s, i)
            return self.conv(a), i
        if nome == "multicolumn":
            n, i = self.grupo(s, i)
            _, i = self.grupo(s, i)
            a, i = self.grupo(s, i)
            return f"\x00COLSPAN:{n}\x00{self.conv(a)}", i
        if nome in self.il_nargs:
            ini = i
            for _ in range(self.il_nargs[nome]):
                _, i = self.grupo(s, i)
            return self.tikz("\\" + nome + s[ini:i]), i
        if nome == "item":
            return "", i
        if nome == "text":
            a, i = self.grupo(s, i)
            return self.conv(a), i
        self.desconhecidas[nome] += 1
        return "", i

    @staticmethod
    def pula_espacos_controle(s: str, i: int) -> int:
        # como no LaTeX: espaços depois de uma palavra de controle somem
        while i < len(s) and s[i] in " \t":
            i += 1
        if s.startswith("{}", i):
            i += 2
        return i

    # --------------------------------------------------------------- ambientes
    def itens(self, corpo: str) -> list[str]:
        partes = self.divide_topo(corpo, "\\item")
        return [p for p in partes[1:]]

    def ambiente(self, nome: str, corpo: str) -> str:
        if nome in ("passos", "enumerate"):
            _, k = self.opcional(corpo, 0)
            itens = "".join(f"<li>{self.conv(p)}</li>" for p in self.itens(corpo[k:]))
            return f'<ol class="{nome}">{itens}</ol>'
        if nome == "itemize":
            _, k = self.opcional(corpo, 0)
            return "<ul>" + "".join(f"<li>{self.conv(p)}</li>" for p in self.itens(corpo[k:])) + "</ul>"
        if nome == "checklist":
            lis = []
            for p in self.itens(corpo):
                self.ncheck += 1
                cid = f"{self.tarefa_atual or 'geral'}-{self.ncheck}"
                lis.append(f'<li><label><input type="checkbox" data-check="{cid}"> '
                           f"<span>{self.conv(p)}</span></label></li>")
            return '<ul class="checklist">' + "".join(lis) + "</ul>"
        if nome == "verbatim":
            return f"<pre>{esc(corpo.strip(chr(10)))}</pre>"
        if nome == "comandos":
            return f'<div class="comandos">{self.conv(corpo)}</div>'
        if nome in ("atencao", "dica"):
            tit, k = self.opcional(corpo, 0)
            tit = self.conv(tit) if tit else ("Atenção" if nome == "atencao" else "Dica")
            return (f'<div class="caixa {nome}"><div class="caixa-tit">{tit}</div>'
                    f"<div>{self.conv(corpo[k:])}</div></div>")
        if nome == "center":
            return f'<div class="centro">{self.conv(corpo)}</div>'
        if nome == "minipage":
            _, k = self.opcional(corpo, 0)
            _, k = self.grupo(corpo, k)
            return f'<div class="mini">{self.conv(corpo[k:])}</div>'
        if nome == "multicols":
            _, k = self.grupo(corpo, 0)
            return f'<div class="colunas">{self.conv(corpo[k:])}</div>'
        if nome in ("figure", "table"):
            _, k = self.opcional(corpo, 0)
            tag = "figure" if nome == "figure" else "div"
            self.em_tabela = nome == "table"
            miolo = self.conv(corpo[k:])
            self.em_tabela = False
            return f'<{tag} class="flt {nome}">{miolo}</{tag}>'
        if nome in ("tikzpicture", "circuitikz"):
            return self.tikz("\\begin{" + nome + "}" + corpo + "\\end{" + nome + "}", "larga")
        if nome in ("tabular", "tabularx", "xltabular"):
            k = 0
            if nome != "tabular":
                _, k = self.grupo(corpo, k)
            _, k = self.grupo(corpo, k)
            return self.tabela(corpo[k:])
        if nome == "tarefa":
            return self.tarefa(corpo)
        if nome in ("titlepage", "tcolorbox"):
            return ""
        if nome == "document":
            return self.conv(corpo)
        self.desconhecidas["env:" + nome] += 1
        return self.conv(corpo)

    def tabela(self, corpo: str) -> str:
        if "\\endfirsthead" in corpo:
            cab = corpo.split("\\endfirsthead")[0]
            resto = corpo.split("\\endlastfoot")[1]
            corpo = cab + resto
        linhas = [l for l in self.divide_topo(corpo, "\\\\")]
        cab_html, corpo_html, no_cab = [], [], True
        for l in linhas:
            sep = "\\midrule" in l
            l = l.replace("\\toprule", "").replace("\\midrule", "").replace("\\bottomrule", "")
            if not l.strip():
                if sep and no_cab and cab_html:
                    no_cab = False
                continue
            if sep and no_cab and cab_html:
                no_cab = False
            celulas = self.divide_topo(l, "&")
            tds = []
            for c in celulas:
                h = self.conv(c.strip())
                m = re.match(r"\x00COLSPAN:(\d+)\x00", h)
                if m:
                    tds.append(f'<td colspan="{m.group(1)}" class="grupo">{h[m.end():]}</td>')
                else:
                    tds.append(f"<td>{h}</td>")
            linha = "<tr>" + "".join(tds) + "</tr>"
            if no_cab and not cab_html:
                cab_html.append(linha.replace("<td", "<th").replace("</td>", "</th>"))
            else:
                corpo_html.append(linha)
        return ('<div class="tabela"><table><thead>' + "".join(cab_html) + "</thead><tbody>"
                + "".join(corpo_html) + "</tbody></table></div>")

    def tarefa(self, corpo: str) -> str:
        tipo, k = self.opcional(corpo, 0)
        tipo = tipo or "mec"
        campos = []
        for _ in range(5):
            a, k = self.grupo(corpo, k)
            campos.append(a)
        tid, titulo, pessoas, duracao, depende = campos
        self.tarefa_atual, self.ncheck = tid, 0
        deps = re.findall(r"\b([MEI]\d+)\b", depende)
        miolo = self.conv(corpo[k:])
        self.tarefa_atual = ""
        self.tarefas.append({
            "id": tid, "trilha": TRILHAS[tipo], "titulo": self.texto_puro(titulo),
            "pessoas": self.texto_puro(pessoas), "duracao": self.texto_puro(duracao),
            "depende": self.texto_puro(depende), "deps": deps,
        })
        dep_html = self.conv(depende)
        return (f'<article class="tarefa {TRILHAS[tipo]}" id="tarefa-{tid}" data-tarefa="{tid}">'
                f'<header><span class="tid">{tid}</span><span class="ttit">{self.conv(titulo)}</span>'
                f'<button class="ver3d" data-tarefa="{tid}" title="mostrar no 3D">ver no 3D</button></header>'
                f'<div class="meta"><span><b>Pessoas:</b> {self.conv(pessoas)}</span>'
                f"<span><b>Duração:</b> {self.conv(duracao)}</span>"
                f"<span><b>Depende de:</b> {dep_html}</span></div>"
                f'<div class="tcorpo">{miolo}</div></article>')

    # -------------------------------------------------------------- documento
    def documento(self, tex: str) -> str:
        corpo = tex.split("\\begin{document}", 1)[1].split("\\end{document}", 1)[0]
        # o apêndice numera com letras
        partes = corpo.split("\\appendix", 1)
        self.inicio_apendice = 0
        h = self.conv(partes[0])
        if len(partes) > 1:
            self.apendice = True
            self.inicio_apendice = self.nsec
            h += self.conv(partes[1])
        h = re.sub(r"\x00REF:([^\x00]+)\x00",
                   lambda m: f'<a href="#{esc(m.group(1))}" class="ref">{self.rotulos.get(m.group(1), "?")}</a>', h)
        # seções: cada uma vira um <section>, com o índice ao lado
        pedacos = re.split(r"\x00SEC:([^:]*):([^\x00]*)\x00", h)
        out = [pedacos[0]]
        for k in range(1, len(pedacos), 3):
            num, tit, conteudo = pedacos[k], pedacos[k + 1], pedacos[k + 2]
            sid = "sec-" + num
            self.secoes.append({"id": sid, "num": num, "titulo": re.sub(r"<[^>]+>", "", tit)})
            out.append(f'<section class="secao" id="{sid}"><h2><span class="snum">{num}</span> {tit}</h2>'
                       f"{conteudo}</section>")
        return "".join(out)
