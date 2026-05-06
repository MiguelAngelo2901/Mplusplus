# =============================================================================
#  INSTALADOR M++ v3.5  —  Setup Profissional da Linguagem M++
#  Requer: Python 3.8+, customtkinter
#  IMPORTANTE: solicita elevação automática ao Admin no Windows
# =============================================================================

import customtkinter as ctk
from tkinter import messagebox, filedialog
import os, sys, subprocess, shutil

# ──────────────────────────────────────────────────────────────────────────────
#  ELEVAÇÃO AUTOMÁTICA PARA ADMINISTRADOR
# ──────────────────────────────────────────────────────────────────────────────
def verificar_e_elevar_admin():
    import ctypes
    if ctypes.windll.shell32.IsUserAnAdmin():
        return
    params = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit(0)

# ──────────────────────────────────────────────────────────────────────────────
#  MOTOR DA LINGUAGEM M++ v3.5
# ──────────────────────────────────────────────────────────────────────────────
MOTOR_MPP = r'''
# mpp_engine.py — Motor da Linguagem M++ v3.5
import sys, re, os, math, random, datetime, json, time

# Imports opcionais (não quebra se não tiver)
try:    import urllib.request as _urllib; import urllib.parse as _urlparse; _HTTP = True
except: _HTTP = False

try:    import urllib.request as _urllib2; _HTTP = True
except: _HTTP = False

VERSAO = "3.5"

# ══════════════════════════════════════════════════════════════════════════════
#  CORES ANSI — terminal colorido nativo
# ══════════════════════════════════════════════════════════════════════════════
if os.name == 'nt':
    os.system('')  # habilita ANSI no Windows 10+

CORES = {
    "RESET"  : "\033[0m",
    "BOLD"   : "\033[1m",
    "DIM"    : "\033[2m",
    "UNDER"  : "\033[4m",
    # Texto
    "PRETO"  : "\033[30m", "VERMELHO": "\033[31m", "VERDE"  : "\033[32m",
    "AMARELO": "\033[33m", "AZUL"    : "\033[34m", "ROXO"   : "\033[35m",
    "CIANO"  : "\033[36m", "BRANCO"  : "\033[37m",
    # Texto bright
    "BPRETO" : "\033[90m", "BVERMELHO":"\033[91m","BVERDE" : "\033[92m",
    "BAMARELO":"\033[93m","BAZUL"    : "\033[94m", "BROXO"  : "\033[95m",
    "BCIANO" : "\033[96m", "BBRANCO" : "\033[97m",
    # Fundo
    "BG_PRETO":"\033[40m","BG_VERMELHO":"\033[41m","BG_VERDE":"\033[42m",
    "BG_AMARELO":"\033[43m","BG_AZUL":"\033[44m","BG_ROXO":"\033[45m",
    "BG_CIANO":"\033[46m","BG_BRANCO":"\033[47m",
}

# ══════════════════════════════════════════════════════════════════════════════
#  MENSAGENS DE ERRO
# ══════════════════════════════════════════════════════════════════════════════
ERROS = {
    "var_nao_definida"  : "Variável '{nome}' não existe. Defina com: SET {nome} = valor",
    "func_nao_definida" : "Função '{nome}' não definida. Crie com: FUNCTION {nome}",
    "arquivo_nao_found" : "Arquivo '{path}' não encontrado. Verifique o caminho.",
    "import_nao_found"  : "Módulo '{path}' não encontrado para IMPORT.",
    "loop_infinito"     : "Loop infinito detectado! Verifique a condição do WHILE.",
    "for_invalido"      : "FOR precisa de números. Ex: FOR i FROM 1 TO 10",
    "list_nao_definida" : "Lista '{nome}' não existe. Crie com: LIST.NEW {nome}",
    "list_indice"       : "Índice {idx} fora do intervalo da lista '{nome}' (tamanho: {tam}).",
    "dict_nao_definido" : "Dicionário '{nome}' não existe. Crie com: DICT.NEW {nome}",
    "dict_chave"        : "Chave '{chave}' não existe no dicionário '{nome}'.",
    "divisao_zero"      : "Divisão por zero.",
    "http_sem_lib"      : "HTTP não disponível. Verifique sua instalação do Python.",
    "json_invalido"     : "JSON inválido: {detalhe}",
    "sintaxe_geral"     : "Comando desconhecido na linha {num}: '{linha}'\n          → Digite  mpp --ajuda  para ver todos os comandos.",
}

def erro(tipo, num=None, **kw):
    msg = ERROS.get(tipo, "Erro desconhecido.")
    for k, v in kw.items():
        msg = msg.replace('{' + k + '}', str(v))
    pre = f"\033[91m[M++ ERRO linha {num}]\033[0m" if num else "\033[91m[M++ ERRO]\033[0m"
    print(f"{pre} {msg}")

def aviso(msg, num=None):
    pre = f"\033[93m[M++ AVISO linha {num}]\033[0m" if num else "\033[93m[M++ AVISO]\033[0m"
    print(f"{pre} {msg}")

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _cast(v):
    try: return int(v)
    except (ValueError, TypeError):
        try: return float(v)
        except (ValueError, TypeError):
            return str(v).strip('"').strip("'")

def _resolve(token, variaveis, listas, dicts):
    token = token.strip()
    # lista[idx]
    lm = re.match(r'^(\w+)\[(\d+)\]$', token)
    if lm:
        lst = listas.get(lm.group(1), [])
        idx = int(lm.group(2))
        return lst[idx] if 0 <= idx < len(lst) else None
    if token in variaveis:
        return variaveis[token]
    return _cast(token)

def _interp_str(texto, variaveis, listas, dicts):
    """Substitui {var}, {lista[i]}, {CORE:COR} em strings."""
    def sub(m):
        expr = m.group(1)
        # Cor: {COR:VERDE}
        if expr.startswith("COR:"):
            return CORES.get(expr[4:].upper(), "")
        if expr == "RESET":
            return CORES["RESET"]
        # lista[indice]
        lm = re.match(r'^(\w+)\[(\d+)\]$', expr)
        if lm:
            lst = listas.get(lm.group(1), [])
            idx = int(lm.group(2))
            return str(lst[idx]) if 0 <= idx < len(lst) else f"{{{expr}}}"
        return str(variaveis.get(expr, f"{{{expr}}}"))
    return re.sub(r'\{([^}]+)\}', sub, texto)

def _eval_expr(expr, variaveis, listas, dicts, num=None):
    expr = expr.strip()
    for nome, val in sorted(variaveis.items(), key=lambda x: -len(x[0])):
        expr = re.sub(rf'\b{re.escape(nome)}\b', str(val), expr)
    expr = re.sub(r'\bRAIZ\(', 'math.sqrt(', expr)
    expr = re.sub(r'\bPOT\(',  'math.pow(',  expr)
    expr = re.sub(r'\bABS\(',  'abs(',        expr)
    expr = re.sub(r'\bARRED\(','round(',      expr)
    expr = re.sub(r'\bPI\b',   str(math.pi),  expr)
    expr = re.sub(r'\bE\b',    str(math.e),   expr)
    if re.fullmatch(r'[\d\s\+\-\*\/\%\.\(\)eE]+', expr):
        try: return eval(expr)
        except ZeroDivisionError: erro("divisao_zero", num=num); return 0
        except Exception: pass
    try:
        return eval(expr, {"__builtins__": {}},
                    {"math": math, "abs": abs, "round": round, "len": len})
    except Exception:
        pass
    return _cast(expr)

def _eval_cond(esq, op, dir_):
    try:
        ops = {'==': esq==dir_, '!=': esq!=dir_,
               '>': esq>dir_,   '<': esq<dir_,
               '>=': esq>=dir_, '<=': esq<=dir_}
        return ops.get(op, False)
    except TypeError:
        esq, dir_ = str(esq), str(dir_)
        ops = {'==': esq==dir_, '!=': esq!=dir_}
        return ops.get(op, False)

def _coleta_bloco(linhas, i):
    bloco = []
    while i < len(linhas):
        l = linhas[i].strip()
        i += 1
        if l in ("FIM", "END", "}"):
            break
        bloco.append(linhas[i-1])  # preserva indentação original
    return bloco, i

def _coleta_bloco_raw(linhas, i):
    """Coleta bloco e retorna próxima linha (para ELSE look-ahead)."""
    bloco = []
    while i < len(linhas):
        l = linhas[i].strip()
        i += 1
        if l in ("FIM", "END", "}"):
            break
        bloco.append(linhas[i-1])
    return bloco, i

# ══════════════════════════════════════════════════════════════════════════════
#  STDLIB NATIVA
# ══════════════════════════════════════════════════════════════════════════════
def _stdlib(nome, variaveis, listas, dicts):

    # ── MATH ──────────────────────────────────────────────────────────────────
    if nome == "STD.MATH.PI":      variaveis["PI"]   = math.pi;  return True
    if nome == "STD.MATH.E":       variaveis["E"]    = math.e;   return True
    if nome == "STD.MATH.RAND":    variaveis["RAND"] = random.random(); return True
    if nome == "STD.MATH.RANDINT":
        variaveis["RAND"] = random.randint(int(variaveis.get("RAND_MIN",0)),
                                           int(variaveis.get("RAND_MAX",100))); return True
    if nome == "STD.MATH.SHUFFLE":
        n = str(variaveis.get("LISTA",""))
        if n in listas: random.shuffle(listas[n]); return True
    if nome == "STD.MATH.SIN":     variaveis["RESULT"] = math.sin(float(variaveis.get("X",0))); return True
    if nome == "STD.MATH.COS":     variaveis["RESULT"] = math.cos(float(variaveis.get("X",0))); return True
    if nome == "STD.MATH.TAN":     variaveis["RESULT"] = math.tan(float(variaveis.get("X",0))); return True
    if nome == "STD.MATH.LOG":     variaveis["RESULT"] = math.log(float(variaveis.get("X",1))); return True
    if nome == "STD.MATH.LOG10":   variaveis["RESULT"] = math.log10(float(variaveis.get("X",1))); return True
    if nome == "STD.MATH.SQRT":    variaveis["RESULT"] = math.sqrt(float(variaveis.get("X",0))); return True
    if nome == "STD.MATH.POW":     variaveis["RESULT"] = math.pow(float(variaveis.get("BASE",0)),float(variaveis.get("EXP",1))); return True
    if nome == "STD.MATH.ABS":     variaveis["RESULT"] = abs(float(variaveis.get("X",0))); return True
    if nome == "STD.MATH.ROUND":   variaveis["RESULT"] = round(float(variaveis.get("X",0)),int(variaveis.get("DECIMAIS",0))); return True
    if nome == "STD.MATH.FLOOR":   variaveis["RESULT"] = math.floor(float(variaveis.get("X",0))); return True
    if nome == "STD.MATH.CEIL":    variaveis["RESULT"] = math.ceil(float(variaveis.get("X",0))); return True
    if nome == "STD.MATH.MAX":
        lst = listas.get(str(variaveis.get("LISTA","")), [])
        variaveis["RESULT"] = max(lst) if lst else 0; return True
    if nome == "STD.MATH.MIN":
        lst = listas.get(str(variaveis.get("LISTA","")), [])
        variaveis["RESULT"] = min(lst) if lst else 0; return True
    if nome == "STD.MATH.SUM":
        lst = listas.get(str(variaveis.get("LISTA","")), [])
        variaveis["RESULT"] = sum(lst); return True
    if nome == "STD.MATH.AVG":
        lst = listas.get(str(variaveis.get("LISTA","")), [])
        variaveis["RESULT"] = sum(lst)/len(lst) if lst else 0; return True

    # ── STRING ────────────────────────────────────────────────────────────────
    if nome == "STD.STR.TRIM":      variaveis["RESULT"] = str(variaveis.get("X","")).strip(); return True
    if nome == "STD.STR.LTRIM":     variaveis["RESULT"] = str(variaveis.get("X","")).lstrip(); return True
    if nome == "STD.STR.RTRIM":     variaveis["RESULT"] = str(variaveis.get("X","")).rstrip(); return True
    if nome == "STD.STR.REVERSE":   variaveis["RESULT"] = str(variaveis.get("X",""))[::-1]; return True
    if nome == "STD.STR.COUNT":
        variaveis["RESULT"] = str(variaveis.get("X","")).count(str(variaveis.get("SUB",""))); return True
    if nome == "STD.STR.STARTSWITH":
        variaveis["RESULT"] = 1 if str(variaveis.get("X","")).startswith(str(variaveis.get("PREFIX",""))  ) else 0; return True
    if nome == "STD.STR.ENDSWITH":
        variaveis["RESULT"] = 1 if str(variaveis.get("X","")).endswith(str(variaveis.get("SUFFIX",""))) else 0; return True
    if nome == "STD.STR.REPEAT":
        variaveis["RESULT"] = str(variaveis.get("X","")) * int(variaveis.get("N",1)); return True
    if nome == "STD.STR.ISNUMBER":
        try: float(str(variaveis.get("X",""))); variaveis["RESULT"] = 1
        except: variaveis["RESULT"] = 0
        return True
    if nome == "STD.STR.TOINT":
        try: variaveis["RESULT"] = int(float(str(variaveis.get("X",0))))
        except: variaveis["RESULT"] = 0
        return True
    if nome == "STD.STR.TOFLOAT":
        try: variaveis["RESULT"] = float(str(variaveis.get("X",0)))
        except: variaveis["RESULT"] = 0.0
        return True
    if nome == "STD.STR.TOSTR":   variaveis["RESULT"] = str(variaveis.get("X","")); return True
    if nome == "STD.STR.FORMAT":
        # Formata número: SET X=3.14159 SET DECIMAIS=2 → "3.14"
        try: variaveis["RESULT"] = f"{float(variaveis.get('X',0)):.{int(variaveis.get('DECIMAIS',2))}f}"
        except: variaveis["RESULT"] = str(variaveis.get("X",""))
        return True
    if nome == "STD.STR.PADLEFT":
        s = str(variaveis.get("X",""))
        n = int(variaveis.get("N", len(s)))
        c = str(variaveis.get("CHAR"," "))
        variaveis["RESULT"] = s.rjust(n, c); return True
    if nome == "STD.STR.PADRIGHT":
        s = str(variaveis.get("X",""))
        n = int(variaveis.get("N", len(s)))
        c = str(variaveis.get("CHAR"," "))
        variaveis["RESULT"] = s.ljust(n, c); return True
    if nome == "STD.STR.ENCODE_URL":
        import urllib.parse
        variaveis["RESULT"] = urllib.parse.quote(str(variaveis.get("X",""))); return True

    # ── REGEX ─────────────────────────────────────────────────────────────────
    if nome == "STD.REGEX.MATCH":
        pattern = str(variaveis.get("PATTERN",""))
        texto   = str(variaveis.get("X",""))
        variaveis["RESULT"] = 1 if re.search(pattern, texto) else 0; return True
    if nome == "STD.REGEX.FIND":
        pattern = str(variaveis.get("PATTERN",""))
        texto   = str(variaveis.get("X",""))
        m = re.search(pattern, texto)
        variaveis["RESULT"] = m.group(0) if m else ""; return True
    if nome == "STD.REGEX.FINDALL":
        pattern = str(variaveis.get("PATTERN",""))
        texto   = str(variaveis.get("X",""))
        listas["__regex__"] = re.findall(pattern, texto); return True
    if nome == "STD.REGEX.REPLACE":
        pattern = str(variaveis.get("PATTERN",""))
        texto   = str(variaveis.get("X",""))
        repl    = str(variaveis.get("REPL",""))
        variaveis["RESULT"] = re.sub(pattern, repl, texto); return True

    # ── LIST ──────────────────────────────────────────────────────────────────
    if nome == "STD.LIST.SORT":
        n = str(variaveis.get("LISTA",""))
        if n in listas: listas[n].sort(); return True
    if nome == "STD.LIST.SORT_DESC":
        n = str(variaveis.get("LISTA",""))
        if n in listas: listas[n].sort(reverse=True); return True
    if nome == "STD.LIST.REVERSE":
        n = str(variaveis.get("LISTA",""))
        if n in listas: listas[n].reverse(); return True
    if nome == "STD.LIST.CONTAINS":
        n = str(variaveis.get("LISTA",""))
        variaveis["RESULT"] = 1 if variaveis.get("VALOR","") in listas.get(n,[]) else 0; return True
    if nome == "STD.LIST.INDEXOF":
        n   = str(variaveis.get("LISTA",""))
        val = variaveis.get("VALOR","")
        lst = listas.get(n,[])
        variaveis["RESULT"] = lst.index(val) if val in lst else -1; return True
    if nome == "STD.LIST.COPY":
        listas[str(variaveis.get("DESTINO",""))] = list(listas.get(str(variaveis.get("ORIGEM","")),[]))
        return True
    if nome == "STD.LIST.CLEAR":
        n = str(variaveis.get("LISTA",""))
        if n in listas: listas[n].clear(); return True
    if nome == "STD.LIST.JOIN":
        n   = str(variaveis.get("LISTA",""))
        sep = str(variaveis.get("SEP",","))
        variaveis["RESULT"] = sep.join(str(x) for x in listas.get(n,[])); return True
    if nome == "STD.LIST.UNIQUE":
        n = str(variaveis.get("LISTA",""))
        if n in listas: listas[n] = list(dict.fromkeys(listas[n])); return True
    if nome == "STD.LIST.SLICE":
        n     = str(variaveis.get("LISTA",""))
        start = int(variaveis.get("START",0))
        end   = int(variaveis.get("END", len(listas.get(n,[]))))
        listas["__slice__"] = listas.get(n,[])[start:end]; return True
    if nome == "STD.LIST.EXTEND":
        dst = str(variaveis.get("DESTINO",""))
        src = str(variaveis.get("ORIGEM",""))
        if dst in listas: listas[dst].extend(listas.get(src,[])); return True

    # ── DICT ──────────────────────────────────────────────────────────────────
    if nome == "STD.DICT.KEYS":
        n = str(variaveis.get("DICT",""))
        listas["__keys__"] = list(dicts.get(n,{}).keys()); return True
    if nome == "STD.DICT.VALUES":
        n = str(variaveis.get("DICT",""))
        listas["__values__"] = list(dicts.get(n,{}).values()); return True
    if nome == "STD.DICT.LEN":
        variaveis["RESULT"] = len(dicts.get(str(variaveis.get("DICT","")),{})); return True
    if nome == "STD.DICT.CLEAR":
        n = str(variaveis.get("DICT",""))
        if n in dicts: dicts[n].clear(); return True
    if nome == "STD.DICT.COPY":
        dicts[str(variaveis.get("DESTINO",""))] = dict(dicts.get(str(variaveis.get("ORIGEM","")),{}))
        return True
    if nome == "STD.DICT.MERGE":
        dst = str(variaveis.get("DESTINO",""))
        src = str(variaveis.get("ORIGEM",""))
        if dst in dicts: dicts[dst].update(dicts.get(src,{})); return True

    # ── JSON ──────────────────────────────────────────────────────────────────
    if nome == "STD.JSON.LOAD":
        path = str(variaveis.get("PATH",""))
        nome_d = str(variaveis.get("DICT","dados"))
        try:
            with open(path, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            if isinstance(dados, dict):
                dicts[nome_d] = {str(k): str(v) if not isinstance(v,(dict,list)) else json.dumps(v)
                                 for k,v in dados.items()}
            elif isinstance(dados, list):
                listas[nome_d] = [str(x) if not isinstance(x,(dict,list)) else json.dumps(x) for x in dados]
            variaveis["RESULT"] = 1
        except Exception as e:
            erro("json_invalido", detalhe=str(e)); variaveis["RESULT"] = 0
        return True
    if nome == "STD.JSON.SAVE":
        path   = str(variaveis.get("PATH","saida.json"))
        nome_d = str(variaveis.get("DICT",""))
        dados  = dicts.get(nome_d, {})
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            variaveis["RESULT"] = 1
        except Exception as e:
            print(f"[M++ ERRO] STD.JSON.SAVE: {e}"); variaveis["RESULT"] = 0
        return True
    if nome == "STD.JSON.PARSE":
        # Converte string JSON em dict
        src    = str(variaveis.get("X","{}"))
        nome_d = str(variaveis.get("DICT","dados"))
        try:
            dados = json.loads(src)
            if isinstance(dados, dict):
                dicts[nome_d] = {str(k): str(v) for k,v in dados.items()}
            variaveis["RESULT"] = 1
        except Exception as e:
            erro("json_invalido", detalhe=str(e)); variaveis["RESULT"] = 0
        return True
    if nome == "STD.JSON.STRINGIFY":
        nome_d = str(variaveis.get("DICT",""))
        variaveis["RESULT"] = json.dumps(dicts.get(nome_d,{}), ensure_ascii=False)
        return True

    # ── HTTP ──────────────────────────────────────────────────────────────────
    if nome == "STD.HTTP.GET":
        if not _HTTP: erro("http_sem_lib"); return True
        url     = str(variaveis.get("URL",""))
        timeout = int(variaveis.get("TIMEOUT", 10))
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "MPlusPlus/3.5"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                variaveis["RESPONSE"] = r.read().decode('utf-8', errors='replace')
                variaveis["STATUS"]   = r.status
        except Exception as e:
            variaveis["RESPONSE"] = f"ERRO: {e}"; variaveis["STATUS"] = 0
        return True
    if nome == "STD.HTTP.POST":
        if not _HTTP: erro("http_sem_lib"); return True
        url     = str(variaveis.get("URL",""))
        body    = str(variaveis.get("BODY","")).encode('utf-8')
        ctype   = str(variaveis.get("CONTENT_TYPE","application/json"))
        timeout = int(variaveis.get("TIMEOUT",10))
        try:
            import urllib.request
            req = urllib.request.Request(url, data=body, method="POST",
                headers={"User-Agent":"MPlusPlus/3.5","Content-Type":ctype})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                variaveis["RESPONSE"] = r.read().decode('utf-8', errors='replace')
                variaveis["STATUS"]   = r.status
        except Exception as e:
            variaveis["RESPONSE"] = f"ERRO: {e}"; variaveis["STATUS"] = 0
        return True
    if nome == "STD.HTTP.GET_JSON":
        # GET + parse automático do JSON → DICT
        if not _HTTP: erro("http_sem_lib"); return True
        url     = str(variaveis.get("URL",""))
        nome_d  = str(variaveis.get("DICT","resposta"))
        timeout = int(variaveis.get("TIMEOUT",10))
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent":"MPlusPlus/3.5","Accept":"application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                dados = json.loads(r.read().decode('utf-8'))
                variaveis["STATUS"] = r.status
            if isinstance(dados, dict):
                dicts[nome_d] = {str(k): str(v) if not isinstance(v,(dict,list)) else json.dumps(v)
                                 for k,v in dados.items()}
            elif isinstance(dados, list):
                listas[nome_d] = [str(x) for x in dados]
            variaveis["RESULT"] = 1
        except Exception as e:
            variaveis["RESPONSE"] = f"ERRO: {e}"; variaveis["STATUS"] = 0; variaveis["RESULT"] = 0
        return True

    # ── SISTEMA / DATA ────────────────────────────────────────────────────────
    if nome == "STD.SYS.DATE":     variaveis["DATA"]     = datetime.date.today().strftime("%d/%m/%Y"); return True
    if nome == "STD.SYS.TIME":     variaveis["HORA"]     = datetime.datetime.now().strftime("%H:%M:%S"); return True
    if nome == "STD.SYS.DATETIME": variaveis["DATETIME"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"); return True
    if nome == "STD.SYS.TIMESTAMP":variaveis["TIMESTAMP"]= int(time.time()); return True
    if nome == "STD.SYS.SLEEP":    time.sleep(float(variaveis.get("SEGUNDOS",1))); return True
    if nome == "STD.SYS.CLEAR":    os.system('cls' if os.name=='nt' else 'clear'); return True
    if nome == "STD.SYS.PAUSE":    input("  Pressione Enter para continuar..."); return True
    if nome == "STD.SYS.NEWLINE":  print(); return True
    if nome == "STD.SYS.OS":       variaveis["OS"]  = os.name; return True
    if nome == "STD.SYS.CWD":      variaveis["CWD"] = os.getcwd(); return True
    if nome == "STD.SYS.EXIT":      sys.exit(int(variaveis.get("CODE",0)))
    if nome == "STD.SYS.ARGS":
        listas["__args__"] = sys.argv[2:]; return True
    if nome == "STD.SYS.ENV":
        k = str(variaveis.get("KEY",""))
        variaveis["RESULT"] = os.environ.get(k,""); return True

    # ── IO ────────────────────────────────────────────────────────────────────
    if nome == "STD.IO.LISTDIR":
        path = str(variaveis.get("PATH","."))
        try: listas["__dir__"] = os.listdir(path)
        except: listas["__dir__"] = []
        return True
    if nome == "STD.IO.MKDIR":
        try: os.makedirs(str(variaveis.get("PATH","")), exist_ok=True)
        except Exception as e: print(f"[M++ ERRO] STD.IO.MKDIR: {e}")
        return True
    if nome == "STD.IO.ISFILE":  variaveis["RESULT"] = 1 if os.path.isfile(str(variaveis.get("PATH",""))) else 0; return True
    if nome == "STD.IO.ISDIR":   variaveis["RESULT"] = 1 if os.path.isdir(str(variaveis.get("PATH","")))  else 0; return True
    if nome == "STD.IO.FILESIZE":
        try: variaveis["RESULT"] = os.path.getsize(str(variaveis.get("PATH","")))
        except: variaveis["RESULT"] = -1
        return True
    if nome == "STD.IO.RENAME":
        try: os.rename(str(variaveis.get("ORIGEM","")), str(variaveis.get("DESTINO","")))
        except Exception as e: print(f"[M++ ERRO] STD.IO.RENAME: {e}")
        return True
    if nome == "STD.IO.COPY":
        try: shutil.copy2(str(variaveis.get("ORIGEM","")), str(variaveis.get("DESTINO","")))
        except Exception as e: print(f"[M++ ERRO] STD.IO.COPY: {e}")
        return True

    return False

# ══════════════════════════════════════════════════════════════════════════════
#  INTERPRETADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def interpretar(linhas, variaveis=None, funcoes=None, listas=None, dicts=None, inicio=0, args_func=None):
    if variaveis  is None: variaveis  = {}
    if funcoes    is None: funcoes    = {}
    if listas     is None: listas     = {}
    if dicts      is None: dicts      = {}
    if args_func:
        variaveis.update(args_func)

    i = inicio
    while i < len(linhas):
        linha = linhas[i].strip()
        num   = i + 1
        i    += 1

        if not linha or linha.startswith("//"):
            continue

        if linha in ("FIM", "END", "}"):
            return variaveis, listas, dicts, i

        # ── IMPORT ────────────────────────────────────────────────────────────
        m = re.match(r'^IMPORT\s+"(.+?)"$', linha)
        if m:
            path = m.group(1)
            if not os.path.isabs(path):
                base = os.path.dirname(os.path.abspath(sys.argv[1])) if len(sys.argv)>1 else "."
                path = os.path.join(base, path)
            if not os.path.isfile(path):
                erro("import_nao_found", num=num, path=path)
            else:
                with open(path, 'r', encoding='utf-8') as fh:
                    mod = [l.rstrip() for l in fh.read().splitlines()]
                variaveis, listas, dicts, _ = interpretar(mod, variaveis, funcoes, listas, dicts)
            continue

        # ── FUNCTION ──────────────────────────────────────────────────────────
        m = re.match(r'^FUNCTION\s+(\w+)(?:\s+(.+))?\s*\{?\s*$', linha)
        if m:
            nome_f  = m.group(1)
            params  = [p.strip() for p in m.group(2).split(",")] if m.group(2) else []
            corpo, i = _coleta_bloco(linhas, i)
            funcoes[nome_f] = {"corpo": corpo, "params": params}
            continue

        # ── CALL nome [arg1 arg2 ...] ──────────────────────────────────────────
        m = re.match(r'^CALL\s+(\S+)(?:\s+(.+))?$', linha)
        if m:
            nome_f = m.group(1)
            args_raw = m.group(2)
            if _stdlib(nome_f, variaveis, listas, dicts):
                pass
            elif nome_f in funcoes:
                func   = funcoes[nome_f]
                corpo  = func["corpo"] if isinstance(func, dict) else func
                params = func["params"] if isinstance(func, dict) else []
                kw = {}
                if args_raw and params:
                    vals = [a.strip() for a in args_raw.split(",")]
                    for p, v in zip(params, vals):
                        kw[p] = _resolve(v, variaveis, listas, dicts)
                variaveis, listas, dicts, _ = interpretar(corpo, variaveis, funcoes, listas, dicts, args_func=kw)
            else:
                erro("func_nao_definida", num=num, nome=nome_f)
            continue

        # ── SAY.IT ────────────────────────────────────────────────────────────
        m = re.match(r'^SAY\.IT"(.*)"$', linha)
        if m:
            print(_interp_str(m.group(1), variaveis, listas, dicts) + CORES["RESET"])
            continue

        # ── COLOR.PRINT"texto" ────────────────────────────────────────────────
        m = re.match(r'^COLOR\.PRINT"(.*)"$', linha)
        if m:
            print(_interp_str(m.group(1), variaveis, listas, dicts) + CORES["RESET"])
            continue

        # ── SET ───────────────────────────────────────────────────────────────
        m = re.match(r'^SET\s+(\w+)\s*=\s*(.+)$', linha)
        if m:
            variaveis[m.group(1)] = _eval_expr(m.group(2).strip(), variaveis, listas, dicts, num)
            continue

        # ── PRINT ─────────────────────────────────────────────────────────────
        m = re.match(r'^PRINT\s+(.+)$', linha)
        if m:
            print(_eval_expr(m.group(1).strip(), variaveis, listas, dicts, num))
            continue

        # ── INPUT ─────────────────────────────────────────────────────────────
        m = re.match(r'^INPUT\s+(\w+)\s+"(.*)"$', linha)
        if m:
            variaveis[m.group(1)] = _cast(input(_interp_str(m.group(2), variaveis, listas, dicts) + " "))
            continue

        # ── RETURN ────────────────────────────────────────────────────────────
        m = re.match(r'^RETURN\s+(.+)$', linha)
        if m:
            variaveis["__RETURN__"] = _resolve(m.group(1).strip(), variaveis, listas, dicts)
            return variaveis, listas, dicts, i

        # ══════════════════════════════════════════════════════════════════════
        #  CONTROLE DE FLUXO
        # ══════════════════════════════════════════════════════════════════════

        # ── IF / ELSE IF / ELSE ───────────────────────────────────────────────
        m = re.match(r'^IF\s+(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*\{?\s*$', linha)
        if m:
            esq  = _resolve(m.group(1), variaveis, listas, dicts)
            op   = m.group(2)
            dir_ = _resolve(m.group(3).rstrip('{').strip(), variaveis, listas, dicts)
            bloco_if, i = _coleta_bloco_raw(linhas, i)

            # look-ahead para ELSE
            bloco_else = []
            if i < len(linhas) and linhas[i].strip() in ("ELSE", "SENAO"):
                i += 1  # pula o ELSE
                bloco_else, i = _coleta_bloco_raw(linhas, i)

            if _eval_cond(esq, op, dir_):
                variaveis, listas, dicts, _ = interpretar(bloco_if, variaveis, funcoes, listas, dicts)
            elif bloco_else:
                variaveis, listas, dicts, _ = interpretar(bloco_else, variaveis, funcoes, listas, dicts)
            continue

        # ── WHILE ─────────────────────────────────────────────────────────────
        m = re.match(r'^WHILE\s+(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*\{?\s*$', linha)
        if m:
            esq_t, op, dir_t = m.group(1), m.group(2), m.group(3).rstrip('{').strip()
            bloco, i = _coleta_bloco_raw(linhas, i)
            lim = 100_000
            while _eval_cond(_resolve(esq_t, variaveis, listas, dicts), op,
                              _resolve(dir_t, variaveis, listas, dicts)):
                variaveis, listas, dicts, _ = interpretar(bloco, variaveis, funcoes, listas, dicts)
                lim -= 1
                if lim <= 0: erro("loop_infinito", num=num); break
            continue

        # ── FOR ───────────────────────────────────────────────────────────────
        m = re.match(r'^FOR\s+(\w+)\s+FROM\s+(.+?)\s+TO\s+(.+?)(?:\s+STEP\s+(.+?))?\s*\{?\s*$', linha)
        if m:
            var, de_t, ate_t, passo_t = m.group(1), m.group(2), m.group(3), m.group(4)
            try:
                de    = int(_eval_expr(de_t,    variaveis, listas, dicts, num))
                ate   = int(_eval_expr(ate_t,   variaveis, listas, dicts, num))
                passo = int(_eval_expr(passo_t, variaveis, listas, dicts, num)) if passo_t else 1
            except (ValueError, TypeError):
                erro("for_invalido", num=num); bloco, i = _coleta_bloco_raw(linhas, i); continue
            bloco, i = _coleta_bloco_raw(linhas, i)
            for v in range(de, ate + (1 if passo > 0 else -1), passo):
                variaveis[var] = v
                variaveis, listas, dicts, _ = interpretar(bloco, variaveis, funcoes, listas, dicts)
            continue

        # ── FOR.EACH ──────────────────────────────────────────────────────────
        m = re.match(r'^FOR\.EACH\s+(\w+)\s+IN\s+(\w+)\s*\{?\s*$', linha)
        if m:
            var, nome_lst = m.group(1), m.group(2)
            bloco, i = _coleta_bloco_raw(linhas, i)
            for item in list(listas.get(nome_lst, [])):
                variaveis[var] = item
                variaveis, listas, dicts, _ = interpretar(bloco, variaveis, funcoes, listas, dicts)
            continue

        # ── BREAK (sai de loop) ───────────────────────────────────────────────
        if linha == "BREAK":
            variaveis["__BREAK__"] = 1
            return variaveis, listas, dicts, i

        # ══════════════════════════════════════════════════════════════════════
        #  LISTAS
        # ══════════════════════════════════════════════════════════════════════
        m = re.match(r'^LIST\.NEW\s+(\w+)$', linha)
        if m: listas[m.group(1)] = []; continue

        m = re.match(r'^LIST\.ADD\s+(\w+)\s+(.+)$', linha)
        if m:
            n, val = m.group(1), m.group(2).strip()
            if n not in listas: listas[n] = []
            listas[n].append(_resolve(val, variaveis, listas, dicts)); continue

        m = re.match(r'^LIST\.GET\s+(\w+)\s+(\w+)\s+(.+)$', linha)
        if m:
            dest, n, idx_t = m.group(1), m.group(2), m.group(3)
            idx = int(_eval_expr(idx_t, variaveis, listas, dicts, num))
            lst = listas.get(n)
            if lst is None: erro("list_nao_definida", num=num, nome=n); continue
            if not (0 <= idx < len(lst)): erro("list_indice", num=num, idx=idx, nome=n, tam=len(lst)); continue
            variaveis[dest] = lst[idx]; continue

        m = re.match(r'^LIST\.SET\s+(\w+)\s+(.+?)\s+(.+)$', linha)
        if m:
            n, idx_t, val = m.group(1), m.group(2), m.group(3)
            idx = int(_eval_expr(idx_t, variaveis, listas, dicts, num))
            if n not in listas: erro("list_nao_definida", num=num, nome=n); continue
            listas[n][idx] = _resolve(val, variaveis, listas, dicts); continue

        m = re.match(r'^LIST\.REMOVE\s+(\w+)\s+(.+)$', linha)
        if m:
            n, idx_t = m.group(1), m.group(2)
            idx = int(_eval_expr(idx_t, variaveis, listas, dicts, num))
            if n in listas and 0 <= idx < len(listas[n]): listas[n].pop(idx)
            continue

        m = re.match(r'^LIST\.LEN\s+(\w+)\s+(\w+)$', linha)
        if m: variaveis[m.group(1)] = len(listas.get(m.group(2),[])); continue

        m = re.match(r'^LIST\.PRINT\s+(\w+)$', linha)
        if m: print(listas.get(m.group(1),[])); continue

        # ══════════════════════════════════════════════════════════════════════
        #  DICIONÁRIOS
        # ══════════════════════════════════════════════════════════════════════
        m = re.match(r'^DICT\.NEW\s+(\w+)$', linha)
        if m: dicts[m.group(1)] = {}; continue

        m = re.match(r'^DICT\.SET\s+(\w+)\s+"(.+?)"\s+(.+)$', linha)
        if m:
            n, ch, val = m.group(1), m.group(2), m.group(3)
            if n not in dicts: dicts[n] = {}
            dicts[n][ch] = _resolve(val, variaveis, listas, dicts); continue

        m = re.match(r'^DICT\.GET\s+(\w+)\s+(\w+)\s+"(.+?)"$', linha)
        if m:
            dest, n, ch = m.group(1), m.group(2), m.group(3)
            d = dicts.get(n)
            if d is None: erro("dict_nao_definido", num=num, nome=n); continue
            if ch not in d: erro("dict_chave", num=num, chave=ch, nome=n); continue
            variaveis[dest] = d[ch]; continue

        m = re.match(r'^DICT\.HAS\s+(\w+)\s+(\w+)\s+"(.+?)"$', linha)
        if m:
            variaveis[m.group(1)] = 1 if m.group(3) in dicts.get(m.group(2),{}) else 0; continue

        m = re.match(r'^DICT\.DELETE\s+(\w+)\s+"(.+?)"$', linha)
        if m:
            if m.group(1) in dicts: dicts[m.group(1)].pop(m.group(2), None)
            continue

        m = re.match(r'^DICT\.LEN\s+(\w+)\s+(\w+)$', linha)
        if m: variaveis[m.group(1)] = len(dicts.get(m.group(2),{})); continue

        m = re.match(r'^DICT\.PRINT\s+(\w+)$', linha)
        if m: print(dicts.get(m.group(1),{})); continue

        # ══════════════════════════════════════════════════════════════════════
        #  STRING
        # ══════════════════════════════════════════════════════════════════════
        m = re.match(r'^STR\.LEN\s+(\w+)\s+(.+)$', linha)
        if m: variaveis[m.group(1)] = len(str(_resolve(m.group(2).strip(), variaveis, listas, dicts))); continue
        m = re.match(r'^STR\.UPPER\s+(\w+)\s+(.+)$', linha)
        if m: variaveis[m.group(1)] = str(_resolve(m.group(2).strip(), variaveis, listas, dicts)).upper(); continue
        m = re.match(r'^STR\.LOWER\s+(\w+)\s+(.+)$', linha)
        if m: variaveis[m.group(1)] = str(_resolve(m.group(2).strip(), variaveis, listas, dicts)).lower(); continue
        m = re.match(r'^STR\.REPLACE\s+(\w+)\s+(\w+)\s+"(.+?)"\s+"(.*)"$', linha)
        if m: variaveis[m.group(1)] = str(variaveis.get(m.group(2),'')).replace(m.group(3), m.group(4)); continue
        m = re.match(r'^STR\.CONTAINS\s+(\w+)\s+(\w+)\s+"(.+?)"$', linha)
        if m: variaveis[m.group(1)] = 1 if m.group(3) in str(variaveis.get(m.group(2),'')) else 0; continue
        m = re.match(r'^STR\.JOIN\s+(\w+)\s+"(.*?)"\s+(.+)$', linha)
        if m:
            tokens = [p.strip() for p in m.group(3).split()]
            variaveis[m.group(1)] = m.group(2).join(str(_resolve(t, variaveis, listas, dicts)) for t in tokens); continue
        m = re.match(r'^STR\.SPLIT\s+(\w+)\s+(\w+)\s+"(.+?)"$', linha)
        if m: listas[m.group(1)] = str(variaveis.get(m.group(2),'')).split(m.group(3)); continue
        m = re.match(r'^STR\.SUBSTR\s+(\w+)\s+(\w+)\s+(\d+)\s+(\d+)$', linha)
        if m:
            s = str(variaveis.get(m.group(2),''))
            variaveis[m.group(1)] = s[int(m.group(3)):int(m.group(4))]; continue

        # ══════════════════════════════════════════════════════════════════════
        #  ARQUIVOS
        # ══════════════════════════════════════════════════════════════════════
        m = re.match(r'^FILE\.WRITE\s+"(.+?)"\s+"(.*)"$', linha)
        if m:
            p = _interp_str(m.group(1), variaveis, listas, dicts)
            c = _interp_str(m.group(2), variaveis, listas, dicts)
            try:
                with open(p, 'w', encoding='utf-8') as fh: fh.write(c)
            except Exception as e: print(f"[M++ ERRO linha {num}] FILE.WRITE: {e}")
            continue
        m = re.match(r'^FILE\.APPEND\s+"(.+?)"\s+"(.*)"$', linha)
        if m:
            p = _interp_str(m.group(1), variaveis, listas, dicts)
            c = _interp_str(m.group(2), variaveis, listas, dicts)
            try:
                with open(p, 'a', encoding='utf-8') as fh: fh.write(c + '\n')
            except Exception as e: print(f"[M++ ERRO linha {num}] FILE.APPEND: {e}")
            continue
        m = re.match(r'^FILE\.READ\s+(\w+)\s+"(.+?)"$', linha)
        if m:
            p = _interp_str(m.group(2), variaveis, listas, dicts)
            try:
                with open(p, 'r', encoding='utf-8') as fh: variaveis[m.group(1)] = fh.read()
            except FileNotFoundError: erro("arquivo_nao_found", num=num, path=p); variaveis[m.group(1)] = ""
            continue
        m = re.match(r'^FILE\.EXISTS\s+(\w+)\s+"(.+?)"$', linha)
        if m: variaveis[m.group(1)] = 1 if os.path.exists(m.group(2)) else 0; continue
        m = re.match(r'^FILE\.DELETE\s+"(.+?)"$', linha)
        if m:
            try: os.remove(m.group(1))
            except Exception as e: print(f"[M++ ERRO linha {num}] FILE.DELETE: {e}")
            continue
        m = re.match(r'^FILE\.LINES\s+(\w+)\s+"(.+?)"$', linha)
        if m:
            p = m.group(2)
            try:
                with open(p, 'r', encoding='utf-8') as fh:
                    listas[m.group(1)] = [l.rstrip('\n') for l in fh.readlines()]
            except FileNotFoundError: erro("arquivo_nao_found", num=num, path=p); listas[m.group(1)] = []
            continue

        # ── Linha não reconhecida ──────────────────────────────────────────────
        erro("sintaxe_geral", num=num, linha=linha)

    return variaveis, listas, dicts, i


# ══════════════════════════════════════════════════════════════════════════════
#  AJUDA
# ══════════════════════════════════════════════════════════════════════════════
AJUDA = """
M++ v3.5 — Referência completa
════════════════════════════════════════════════════════════════
  SAÍDA / ENTRADA
    SAY.IT"texto {var}"          Imprime com interpolação e cores
    COLOR.PRINT"texto"           Alias para SAY.IT
    PRINT expressao              Imprime valor ou cálculo
    INPUT nome "mensagem"        Lê entrada do usuário
    RETURN valor                 Retorna valor de função

  CORES  (dentro de SAY.IT / COLOR.PRINT)
    {COR:VERDE}  {COR:VERMELHO}  {COR:AZUL}  {COR:AMARELO}
    {COR:CIANO}  {COR:ROXO}      {COR:BRANCO} {RESET}
    Bright: {COR:BVERDE}  {COR:BVERMELHO}  etc.
    Fundo: {COR:BG_AZUL}  {COR:BG_VERDE}   etc.

  VARIÁVEIS
    SET nome = expressao
    Operadores: + - * / %  |  RAIZ() POT() ABS() ARRED() PI E

  CONTROLE
    IF x op y { ... FIM
    ELSE / SENAO { ... FIM       Bloco alternativo após IF
    WHILE x op y { ... FIM
    FOR i FROM 1 TO 10 { FIM     STEP opcional
    FOR.EACH item IN lista { FIM
    BREAK                        Sai do loop

  FUNÇÕES
    FUNCTION nome param1,param2 { ... FIM
    CALL nome arg1,arg2
    RETURN valor

  LISTAS / DICTS / STRING / ARQUIVOS
    (igual v3.0 + STR.SUBSTR, FILE.LINES)

  HTTP
    SET URL = "https://api.example.com/data"
    CALL STD.HTTP.GET            → RESPONSE, STATUS
    CALL STD.HTTP.POST           → BODY, CONTENT_TYPE
    CALL STD.HTTP.GET_JSON       → DICT (parse automático)

  JSON
    SET PATH = "dados.json"
    CALL STD.JSON.LOAD           → DICT ou LISTA
    CALL STD.JSON.SAVE           → salva DICT em arquivo
    CALL STD.JSON.PARSE          → parse de string X → DICT
    CALL STD.JSON.STRINGIFY      → DICT → string RESULT

  REGEX
    SET PATTERN = "\\d+"  SET X = "abc123"
    CALL STD.REGEX.MATCH         → RESULT (0/1)
    CALL STD.REGEX.FIND          → RESULT (primeiro match)
    CALL STD.REGEX.FINDALL       → __regex__ (lista)
    CALL STD.REGEX.REPLACE       → RESULT (texto substituído)

  STDLIB EXTRAS
    STD.MATH.FLOOR/CEIL/LOG10/SHUFFLE
    STD.STR.FORMAT/PADLEFT/PADRIGHT/LTRIM/RTRIM/ENCODE_URL
    STD.LIST.SORT_DESC/UNIQUE/SLICE/EXTEND
    STD.DICT.COPY/MERGE
    STD.SYS.SLEEP/TIMESTAMP/EXIT/ARGS/ENV
    STD.IO.FILESIZE/RENAME/COPY

  // comentário                  Linha ignorada
════════════════════════════════════════════════════════════════"""

def main():
    if len(sys.argv) < 2:
        print(f"M++ Language v{VERSAO}")
        print("Uso:  mpp <arquivo.mpp>")
        print("      mpp --version")
        print("      mpp --ajuda")
        return

    arg = sys.argv[1]
    if arg in ("--version", "--versao"): print(f"M++ v{VERSAO}"); return
    if arg == "--ajuda": print(AJUDA); return

    if not os.path.isfile(arg):
        if not arg.endswith(".mpp"): print(f"[M++ ERRO] '{arg}' não é um arquivo .mpp válido.")
        else: erro("arquivo_nao_found", path=arg)
        sys.exit(1)

    with open(arg, 'r', encoding='utf-8') as f:
        codigo = f.read()

    linhas = [l.rstrip() for l in codigo.splitlines()]
    interpretar(linhas)

if __name__ == "__main__":
    main()
'''

# ──────────────────────────────────────────────────────────────────────────────
#  ARQUIVO DE EXEMPLO v3.5
# ──────────────────────────────────────────────────────────────────────────────
EXEMPLO_MPP = '''\
// M++ v3.5 — exemplo completo
// ─────────────────────────────

// 1. Cores no terminal
SAY.IT"{COR:BCIANO}=============================={RESET}"
SAY.IT"{COR:BBRANCO}   BEM-VINDO AO M++ v3.5   {RESET}"
SAY.IT"{COR:BCIANO}=============================={RESET}"

// 2. Variáveis e operações
SET nome = "Miguel"
SET idade = 17
SET maioridade = idade + 1
SAY.IT"{COR:VERDE}Olá, {nome}! Em {maioridade} anos você será maior de idade.{RESET}"

// 3. IF / ELSE
IF idade >= 18 {
    SAY.IT"{COR:VERDE}Você é maior de idade!{RESET}"
FIM
ELSE {
    SAY.IT"{COR:AMARELO}Você é menor de idade.{RESET}"
FIM

// 4. Função com parâmetros
FUNCTION somar a,b {
    SET resultado = a + b
    RETURN resultado
FIM
CALL somar 10,25
SAY.IT"10 + 25 = {__RETURN__}"

// 5. Lista + FOR.EACH
LIST.NEW linguagens
LIST.ADD linguagens "M++"
LIST.ADD linguagens "Python"
LIST.ADD linguagens "Rust"
SAY.IT"{COR:ROXO}Linguagens:{RESET}"
FOR.EACH lang IN linguagens {
    SAY.IT"  {COR:CIANO}>{RESET} {lang}"
FIM

// 6. Dicionário
DICT.NEW usuario
DICT.SET usuario "nome" nome
DICT.SET usuario "idade" idade
DICT.PRINT usuario

// 7. HTTP + JSON (requer internet)
// SET URL = "https://jsonplaceholder.typicode.com/todos/1"
// CALL STD.HTTP.GET_JSON
// DICT.GET titulo resposta "title"
// SAY.IT"API retornou: {titulo}"

// 8. Regex
SET PATTERN = "\\d+"
SET X = "versao 35 do M++"
CALL STD.REGEX.FIND
SAY.IT"Número encontrado pelo regex: {RESULT}"

// 9. Data e hora
CALL STD.SYS.DATE
CALL STD.SYS.TIME
SAY.IT"{COR:DIM}Data: {DATA}  Hora: {HORA}{RESET}"

// 10. Arquivo
FILE.WRITE "saida_v35.txt" "Gerado pelo M++ v3.5 — {nome}"
FILE.EXISTS ok "saida_v35.txt"
IF ok == 1 {
    SAY.IT"{COR:VERDE}Arquivo salvo!{RESET}"
FIM

SAY.IT"{COR:BCIANO}=============================={RESET}"
'''

# ──────────────────────────────────────────────────────────────────────────────
#  INSTALADOR UI
# ──────────────────────────────────────────────────────────────────────────────
class InstaladorMPP(ctk.CTk):

    TITULO      = "Instalador M++ v3.5"
    GEOMETRIA   = "640x500"
    PATH_PADRAO = r"C:\MPlusPlus"

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title(self.TITULO)
        self.geometry(self.GEOMETRIA)
        self.resizable(False, False)

        self.passo_atual        = 0
        self.path_instalacao    = ctk.StringVar(value=self.PATH_PADRAO)
        self.adicionar_path     = ctk.BooleanVar(value=True)
        self.registrar_extensao = ctk.BooleanVar(value=True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self.telas = [
            self._tela_boas_vindas(),
            self._tela_configuracao(),
            self._tela_instalando(),
            self._tela_finalizado(),
        ]
        self._construir_barra_botoes()
        self._mostrar_tela()

    def _tela_boas_vindas(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="Bem-vindo ao Setup da Linguagem M++ v3.5",
                     font=("Segoe UI", 20, "bold")).pack(pady=(26, 10))
        ctk.CTkLabel(f, justify="left", font=("Segoe UI", 12), text=(
            "Novidades da v3.5:\n\n"
            "  • HTTP nativo  —  GET, POST, GET_JSON\n"
            "  • JSON  —  LOAD, SAVE, PARSE, STRINGIFY\n"
            "  • REGEX  —  MATCH, FIND, FINDALL, REPLACE\n"
            "  • Cores ANSI no terminal  {COR:VERDE}, {COR:VERMELHO}...\n"
            "  • ELSE / SENAO após IF\n"
            "  • Funções com parâmetros  FUNCTION soma a,b\n"
            "  • RETURN, BREAK, STR.SUBSTR, FILE.LINES\n"
            "  • 60+ funções stdlib\n\n"
            "  ✅  Executando como Administrador."
        )).pack(padx=36, anchor="w")
        return f

    def _tela_configuracao(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="Configurações de Instalação",
                     font=("Segoe UI", 18, "bold")).pack(pady=(24, 16))
        fp = ctk.CTkFrame(f, fg_color="transparent")
        fp.pack(fill="x", padx=36)
        ctk.CTkLabel(fp, text="Pasta de instalação:", font=("Segoe UI", 12)).pack(anchor="w")
        row = ctk.CTkFrame(fp, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        ctk.CTkEntry(row, textvariable=self.path_instalacao, width=400, height=32).pack(side="left")
        ctk.CTkButton(row, text="...", width=40, height=32,
                      command=self._escolher_pasta).pack(side="left", padx=(6, 0))
        fo = ctk.CTkFrame(f, fg_color="transparent")
        fo.pack(fill="x", padx=36, pady=20)
        ctk.CTkCheckBox(fo, text="Adicionar M++ ao PATH do sistema  (Recomendado)",
                        variable=self.adicionar_path).pack(anchor="w", pady=6)
        ctk.CTkCheckBox(fo, text="Registrar extensão .mpp no Windows  (Recomendado)",
                        variable=self.registrar_extensao).pack(anchor="w", pady=6)
        return f

    def _tela_instalando(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="Instalando M++ v3.5...",
                     font=("Segoe UI", 18, "bold")).pack(pady=(36, 10))
        self.lbl_status = ctk.CTkLabel(f, text="Iniciando...",
                                       font=("Segoe UI", 12), text_color="gray")
        self.lbl_status.pack(pady=4)
        self.progress = ctk.CTkProgressBar(f, width=480, height=16)
        self.progress.set(0)
        self.progress.pack(pady=10)
        self.lbl_pct = ctk.CTkLabel(f, text="0%", font=("Segoe UI", 11))
        self.lbl_pct.pack()
        return f

    def _tela_finalizado(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="✅  M++ v3.5 instalada com sucesso!",
                     font=("Segoe UI", 22, "bold"), text_color="#2ecc71").pack(pady=(44, 10))
        ctk.CTkLabel(f, justify="left", font=("Segoe UI", 12), text=(
            "Abra um novo terminal e execute:\n\n"
            "    mpp seu_arquivo.mpp\n"
            "    mpp --ajuda\n\n"
            f"Exemplo em:\n    {self.path_instalacao.get()}\\projetos\\exemplo.mpp\n\n"
            f"Para desinstalar:\n    {self.path_instalacao.get()}\\desinstalar.bat"
        )).pack(padx=36)
        return f

    def _construir_barra_botoes(self):
        bar = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=("gray90","gray20"))
        bar.grid(row=1, column=0, sticky="ew")
        self.btn_back = ctk.CTkButton(bar, text="◀  Voltar", width=110,
                                      command=self._voltar, state="disabled")
        self.btn_back.pack(side="right", padx=10, pady=12)
        self.btn_next = ctk.CTkButton(bar, text="Próximo  ▶", width=110,
                                      command=self._proximo)
        self.btn_next.pack(side="right", padx=(0,6), pady=12)

    def _mostrar_tela(self):
        for t in self.telas: t.grid_forget()
        self.telas[self.passo_atual].grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        ultimo     = self.passo_atual == len(self.telas)-1
        instalando = self.passo_atual == 2
        self.btn_back.configure(state="disabled" if (self.passo_atual==0 or instalando or ultimo) else "normal")
        if ultimo:
            self.btn_next.configure(text="Fechar", command=self.quit, state="normal")
        elif instalando:
            self.btn_next.configure(state="disabled")
            self.after(300, self._executar_instalacao)
        else:
            self.btn_next.configure(text="Próximo  ▶", command=self._proximo, state="normal")

    def _proximo(self):
        if self.passo_atual < len(self.telas)-1:
            self.passo_atual += 1; self._mostrar_tela()

    def _voltar(self):
        if self.passo_atual > 0:
            self.passo_atual -= 1; self._mostrar_tela()

    def _escolher_pasta(self):
        p = filedialog.askdirectory(title="Selecione a pasta de instalação")
        if p: self.path_instalacao.set(p.replace("/","\\"))

    def _status(self, msg, pct):
        self.lbl_status.configure(text=msg)
        self.progress.set(pct)
        self.lbl_pct.configure(text=f"{int(pct*100)}%")
        self.update_idletasks()

    def _executar_instalacao(self):
        raiz       = self.path_instalacao.get()
        bin_dir    = os.path.join(raiz, "bin")
        lib_dir    = os.path.join(raiz, "lib")
        proj_dir   = os.path.join(raiz, "projetos")
        motor_py   = os.path.join(bin_dir, "mpp_engine.py")
        bat_path   = os.path.join(bin_dir, "mpp.bat")
        uninst_bat = os.path.join(raiz, "desinstalar.bat")
        python_exe = sys.executable

        try:
            self._status("Criando estrutura de pastas...", 0.08)
            for d in (bin_dir, lib_dir, proj_dir):
                os.makedirs(d, exist_ok=True)

            self._status("Instalando motor M++ v3.5...", 0.20)
            with open(motor_py, "w", encoding="utf-8") as fh:
                fh.write(MOTOR_MPP)

            self._status("Criando comando 'mpp'...", 0.34)
            with open(bat_path, "w", encoding="utf-8") as fh:
                fh.write(f'@echo off\n"{python_exe}" "{motor_py}" %*\n')

            self._status("Criando desinstalador...", 0.46)
            bin_esc = bin_dir.replace('\\','\\\\')
            with open(uninst_bat, "w", encoding="utf-8") as fh:
                fh.write(
                    f'@echo off\necho Desinstalando M++ v3.5...\n'
                    f'reg delete "HKCR\\.mpp" /f >nul 2>&1\n'
                    f'reg delete "HKCR\\MPlusPlus.Script" /f >nul 2>&1\n'
                    f'powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable(\'Path\',\'Machine\');'
                    f'$p=$p -replace \';{bin_esc}\',\'\';'
                    f'[Environment]::SetEnvironmentVariable(\'Path\',$p,\'Machine\')"\n'
                    f'rmdir /s /q "{raiz}"\necho Concluido!\npause\n'
                )

            if self.adicionar_path.get():
                self._status("Adicionando ao PATH do sistema...", 0.60)
                self._adicionar_ao_path(bin_dir)

            if self.registrar_extensao.get():
                self._status("Registrando extensão .mpp...", 0.75)
                self._registrar_extensao_mpp(motor_py, python_exe)

            self._status("Criando arquivo de exemplo...", 0.90)
            with open(os.path.join(proj_dir, "exemplo.mpp"), "w", encoding="utf-8") as fh:
                fh.write(EXEMPLO_MPP)

            self._status("Concluído!", 1.0)
            self._atualizar_tela_final(raiz)
            self.after(800, self._proximo)

        except PermissionError:
            messagebox.showerror("Permissão Negada",
                "Execute novamente como Administrador.")
            self.passo_atual = 1; self._mostrar_tela()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro inesperado:\n\n{e}")
            self.passo_atual = 1; self._mostrar_tela()

    def _adicionar_ao_path(self, bin_dir):
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            0, winreg.KEY_READ | winreg.KEY_WRITE)
        try: path_atual, _ = winreg.QueryValueEx(k, "Path")
        except FileNotFoundError: path_atual = ""
        entradas = [p for p in path_atual.split(";") if p and p != bin_dir]
        entradas.append(bin_dir)
        novo = ";".join(entradas)
        winreg.SetValueEx(k, "Path", 0, winreg.REG_EXPAND_SZ, novo)
        winreg.CloseKey(k)
        subprocess.run(["powershell","-NoProfile","-Command",
            f'[Environment]::SetEnvironmentVariable("Path","{novo}","Machine")'],
            capture_output=True)

    def _registrar_extensao_mpp(self, motor_path, python_exe):
        import winreg
        cmd = f'"{python_exe}" "{motor_path}" "%1"'
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ".mpp") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "MPlusPlus.Script")
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "MPlusPlus.Script") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Script M++")
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"MPlusPlus.Script\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd)
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r"MPlusPlus.Script\DefaultIcon") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f"{python_exe},0")
        subprocess.run(["ie4uinit.exe","-show"], capture_output=True)

    def _atualizar_tela_final(self, raiz):
        tela_antiga = self.telas[3]
        f = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(f, text="✅  M++ v3.5 instalada com sucesso!",
                     font=("Segoe UI", 22, "bold"), text_color="#2ecc71").pack(pady=(44, 10))
        ctk.CTkLabel(f, justify="left", font=("Segoe UI", 12), text=(
            "Abra um novo terminal e execute:\n\n"
            "    mpp seu_arquivo.mpp\n"
            "    mpp --ajuda\n\n"
            f"Exemplo em:\n    {raiz}\\projetos\\exemplo.mpp\n\n"
            f"Para desinstalar:\n    {raiz}\\desinstalar.bat"
        )).pack(padx=36)
        self.telas[3] = f
        tela_antiga.destroy()


# ──────────────────────────────────────────────────────────────────────────────
#  PONTO DE ENTRADA
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    verificar_e_elevar_admin()
    app = InstaladorMPP()
    app.mainloop()
