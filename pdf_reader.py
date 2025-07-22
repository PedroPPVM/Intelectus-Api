import fitz  # PyMuPDF
import re

def search_status_marcas(codigo, filepath):
    doc = fitz.open(filepath)

    pagina_encontrada = None

    padrao_id = re.compile(r"^\d{9}$")  

    for num_pagina in range(len(doc)):
        pagina = doc[num_pagina]
        linhas = pagina.get_text().splitlines()

        for i, linha in enumerate(linhas):
            if codigo.lower() in linha.lower():
                pagina_encontrada = num_pagina

                bloco = [linha]
                for seguinte in linhas[i + 1:]:
                    if padrao_id.match(seguinte.strip()):
                        break
                    bloco.append(seguinte)

                process_json = {
                   "process_number": bloco[0],
                   "process_type": "marcas",
                   "status": bloco[1],
                }

                resultado = "\n".join(bloco)

                print(f"\nTexto encontrado na página {pagina_encontrada + 1}:\n")
                print(resultado)
                return process_json

    print("Texto não encontrado no documento.")
    return None

def search_status_programa_de_computador(codigo, filepath):
    doc = fitz.open(filepath)

    padrao_inicio = re.escape(codigo)
    padrao_bloco = re.compile(r"Processo: \bBR \d{2} \d{4} \d{6}-\d\b")

    for num_pagina in range(len(doc)):
        pagina = doc[num_pagina]
        linhas = pagina.get_text().splitlines()

        for i, linha in enumerate(linhas):
            if re.search(padrao_inicio, linha, re.IGNORECASE):
                bloco = [linha]
                for seguinte in linhas[i + 1:]:
                    if padrao_bloco.match(seguinte.strip()):
                        break
                    bloco.append(seguinte)

                process_json = {
                   "process_number": bloco[0].split(":")[1],
                   "process_type": "programa_de_computador",
                   "status": bloco[1],
                   "title": bloco[2]
                }

                resultado = "\n".join(bloco)
                print(f"\nTexto encontrado na página {num_pagina + 1}:\n")
                print(resultado)
                return process_json

    print("Texto não encontrado no documento.")
    return None

def search_status_patentes(codigo, filepath):
    doc = fitz.open(filepath)

    padrao_inicio = re.escape(codigo)
    padrao_bloco = re.compile(r"\(21\) BR \d{2} \d{4} \d{6}-\d")

    for num_pagina in range(len(doc)):
        pagina = doc[num_pagina]
        linhas = pagina.get_text().splitlines()

        for i, linha in enumerate(linhas):
            if re.search(padrao_inicio, linha, re.IGNORECASE):
                bloco = [linha]
                for seguinte in linhas[i + 1:]:
                    if padrao_bloco.match(seguinte.strip()):
                        break
                    bloco.append(seguinte)

                process_json = {
                   "process_number": bloco[0].split(" ", 1)[1],
                   "process_type": "patentes",
                   "status": bloco[1],
                }
                
                resultado = "\n".join(bloco)
                print(f"\nTexto encontrado na página {num_pagina + 1}:\n")
                print(resultado)
                return process_json

    print("Texto não encontrado no documento.")
    return None

def search_status_desenhos_industriais(codigo, filepath):
    doc = fitz.open(filepath)

    padrao_inicio = re.escape(codigo)

    padroes = [re.compile(r"\bDI\d{7,8}-\d\b"), re.compile(r"\b\d{12}\b"), re.compile(r"\bBR\d{2}\d{4}\d{6}-\d\b")]

    padrao_bloco = None

    for padrao in padroes:
        if padrao.search(codigo):
            padrao_bloco = padrao
            break

    for num_pagina in range(len(doc)):
        pagina = doc[num_pagina]
        linhas = pagina.get_text().splitlines()

        for i, linha in enumerate(linhas):
            if re.search(padrao_inicio, linha, re.IGNORECASE):
                bloco = [linha]
                for seguinte in linhas[i + 1:]:
                    if padrao_bloco.match(seguinte.strip()):
                        break
                    bloco.append(seguinte)
            
                process_json = {
                   "process_number": bloco[0],
                   "process_type": "desenho_industrial",
                   "status": bloco[2],

                }
                resultado = "\n".join(bloco)
                print(f"\nTexto encontrado na página {num_pagina + 1}:\n")
                print(resultado)
                return process_json

    print("Texto não encontrado no documento.")
    return None

a = search_status_desenhos_industriais("BR302025003653-4", "downloads/Desenhos_Industriais2845.pdf")
b = search_status_marcas("501554355", "downloads/Marcas2845.pdf")
c = search_status_patentes("(21) BR 11 2025 013613-5", "downloads/Patentes2845.pdf")
d = search_status_programa_de_computador("BR 51 2025 001727-8", "downloads/Programa_de_computador2845.pdf")

print(f"\na = {a}\nb = {b}\nc = {c}\nd = {d}\n")
