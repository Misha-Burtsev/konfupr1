import shlex, argparse, sys, os, zipfile, base64

# --- CLI ---
p = argparse.ArgumentParser()
p.add_argument("--vfs", help="Путь к ZIP-архиву VFS")
p.add_argument("--script", help="Путь к стартовому скрипту")
a = p.parse_args()
print(f"DEBUG: vfs='{a.vfs}', script='{a.script}'")

# --- VFS: дир = dict, файл = ('f', data, is_b64) ---
def _ensure_dir(tree, parts):
    cur = tree
    for s in parts:
        if not s or s == '.':
            continue
        if s not in cur or not isinstance(cur[s], dict):
            cur[s] = {}
        cur = cur[s]
    return cur

def load_vfs_zip(path):
    def norm(name: str):
        name = name.replace("\\", "/").lstrip("./").strip("/")
        return name

    tree = {}
    try:
        with zipfile.ZipFile(path, "r") as z:
            for info in z.infolist():
                raw_name = info.filename
                name = norm(raw_name)
                if not name:
                    continue
                if raw_name.endswith("/"):  # каталог
                    _ensure_dir(tree, [p for p in name.split("/") if p])
                else:                       # файл
                    raw = z.read(raw_name)
                    try:
                        node = ("f", raw.decode("utf-8"), False)
                    except UnicodeDecodeError:
                        node = ("f", base64.b64encode(raw).decode("ascii"), True)
                    parts = [p for p in name.split("/") if p]
                    parent = _ensure_dir(tree, parts[:-1])
                    parent[parts[-1]] = node
        return tree, None
    except FileNotFoundError as e:
        return {}, f"VFS ERROR: файл не найден: {e}"
    except zipfile.BadZipFile as e:
        return {}, f"VFS ERROR: неверный формат ZIP: {e}"
    except Exception as e:
        return {}, f"VFS ERROR: {e}"


# инициализация
if a.vfs:
    VFS_TREE, VFS_ERR = load_vfs_zip(a.vfs)
    if VFS_ERR:
        print(VFS_ERR)
        VFS_TREE = {}  # продолжаем с пустой VFS
else:
    VFS_TREE, VFS_ERR = {}, None

CWD = []
HISTORY = []
PROMPT = os.path.basename(a.vfs) if a.vfs else "vfs"
# (временно полезно)
print("DEBUG VFS root:", sorted(VFS_TREE.keys()))

motd = VFS_TREE.get("motd")
if isinstance(motd, tuple) and motd[0] == "f" and not motd[2]:
    print(motd[1])  # показываем только текстовый motd (utf-8)


def _resolve(path):
    if path.startswith('/'):
        base, segs = [], path.split('/')
    else:
        base, segs = CWD[:], path.split('/')
    for s in segs:
        if not s or s == '.':
            continue
        if s == '..':
            if base: base.pop()
        else:
            base.append(s)
    cur = VFS_TREE
    for i, s in enumerate(base):
        if not isinstance(cur, dict) or s not in cur:
            return None, None
        cur = cur[s]
        if isinstance(cur, tuple) and i != len(base) - 1:
            return None, None
    return cur, base

def run_script(path):
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                print(f"{PROMPT}$ {line}")   # эхо строки — печатаем ОДИН раз
                HISTORY.append(line)         # если ведёте историю
                try:
                    run_line(line)
                except SystemExit:
                    print("SCRIPT ERROR: попытка выйти из REPL внутри скрипта — игнорирую.")
                except Exception as e:
                    print(f"SCRIPT ERROR: {e}")
    except Exception as e:
        print(f"SCRIPT ERROR: не удалось открыть скрипт: {e}")

def cmd_ls(arg=None):
    # без аргумента листим текущую директорию
    target = arg if arg else '.'
    node, _ = _resolve(target)
    if node is None:
        print(f"ls: нет такого файла или каталога")
        return
    if isinstance(node, dict):
        names = sorted(node.keys())
        print(' '.join(n + '/' if isinstance(node[n], dict) else n for n in names))
    else:
        # если это файл — как в UNIX: просто печатаем имя целевого файла
        base = target.rstrip('/').split('/')[-1] or target
        print(base)

def cmd_cd(arg=None):
    # без аргумента — в корень (аналог cd /)
    if not arg:
        CWD.clear()
        return
    node, parts = _resolve(arg)
    if node is None:
        print(f"cd: нет такого файла или каталога: {arg}")
    elif not isinstance(node, dict):
        print(f"cd: не каталог: {arg}")
    else:
        CWD[:] = parts

def cmd_history(arg=None):
    # history        -> весь список
    # history N      -> последние N (N > 0)
    if arg is None:
        start = 0
    else:
        try:
            n = int(arg)
        except ValueError:
            print(f"history: аргумент должен быть числом: {arg}")
            return
        start = 0 if n <= 0 else max(0, len(HISTORY) - n)

    for i in range(start, len(HISTORY)):
        print(f"{i+1}  {HISTORY[i]}")

def cmd_clear():
    # ANSI очистка экрана
    print("\033[2J\033[H", end='')

def cmd_rev(args):
    # rev TEXT... -> печатает перевёрнутую строку
    s = ' '.join(args)
    print(s[::-1])


def run_line(line):
    parts = shlex.split(line)
    if not parts: return
    cmd, *args = parts
    if cmd == "ls":
        cmd_ls(args[0] if args else None)
    elif cmd == "cd":
        cmd_cd(args[0] if args else None)
    elif cmd == "history":
        cmd_history(args[0] if args else None)
    elif cmd == "clear":
        cmd_clear()
    elif cmd == "rev":
        cmd_rev(args)
    elif cmd == "exit":
        sys.exit(0)
    else:
        print(f"Ошибка: команда '{cmd}' не существует.")

# --- запуск скрипта, если указан ---
if a.script:
    run_script(a.script)

# --- REPL ---
while True:
    try:
        line = input(f"{PROMPT}$ ")
        HISTORY.append(line)
        run_line(line)
    except KeyboardInterrupt:
        print()
    except Exception as e:
        print(f"ERROR: {e}")
