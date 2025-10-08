import shlex, argparse, sys, os, zipfile, base64

# --- CLI ---
p = argparse.ArgumentParser()
p.add_argument("--vfs", help="Путь к ZIP-архиву VFS")
p.add_argument("--script", help="Путь к стартовому скрипту")
a = p.parse_args()
print(f"DEBUG: vfs='{a.vfs}', script='{a.script}'")

CWD = []
HISTORY = []
OWNER = {" /": "root"} if False else {}  # можно не трогать корень
def _abs_path(parts):
    return "/" if not parts else "/" + "/".join(parts)

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
                    OWNER[_abs_path(parts)] = "root"  # <— владелец файла
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
PROMPT = os.path.basename(a.vfs) if a.vfs else "vfs"
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

def _ensure_dir(tree, parts):
    cur = tree
    built = []
    for s in parts:
        if not s or s == '.':
            continue
        built.append(s)
        if s not in cur or not isinstance(cur[s], dict):
            cur[s] = {}
            OWNER[_abs_path(built)] = "root"   # <— владелец каталога
        cur = cur[s]
    return cur

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
    print("\033[2J\033[H", end='')

def cmd_rev(args):
    s = ' '.join(args)
    print(s[::-1])

def cmd_chown(args):
    # chown [-R] owner path
    if not args or len(args) < 2:
        print("chown: usage: chown [-R] OWNER PATH")
        return
    i = 0
    recursive = False
    if args[0] == "-R":
        recursive = True
        i += 1
        if len(args) - i < 2:
            print("chown: usage: chown [-R] OWNER PATH")
            return
    owner = args[i]
    target = args[i + 1]

    node, parts = _resolve(target)
    if node is None:
        print(f"chown: нет такого файла или каталога: {target}")
        return

    def apply(n, p):
        OWNER[_abs_path(p)] = owner
        if recursive and isinstance(n, dict):
            for name, child in n.items():
                apply(child, p + [name])

    apply(node, parts)

def cmd_cp(args):
    # cp SRC DST   (только файлы, без -r)
    if len(args) != 2:
        print("cp: usage: cp SRC DST")
        return
    src, dst = args

    src_node, src_parts = _resolve(src)
    if src_node is None:
        print(f"cp: не найден источник: {src}")
        return
    if isinstance(src_node, dict):
        print("cp: каталоги не поддерживаются без -r")
        return

    dst_node, dst_parts = _resolve(dst)

    def set_file(parts, file_tuple, owner):
        # parts = список сегментов абсолютного пути
        parent_node, parent_parts = _resolve("/" + "/".join(parts[:-1]) if len(parts) > 1 else "/")
        if parent_node is None or not isinstance(parent_node, dict):
            print("cp: нет такого каталога назначения")
            return False
        name = parts[-1]
        parent_node[name] = ('f', file_tuple[1], file_tuple[2])
        OWNER[_abs_path(parts)] = owner
        return True

    src_owner = OWNER.get(_abs_path(src_parts), "root")

    if dst_node is None:
        # создать новый файл по полному пути dst
        new_parts = [p for p in dst.split('/') if p]
        if not new_parts:  # нельзя писать прямо в /
            print("cp: неверный путь назначения")
            return
        set_file(new_parts, src_node, src_owner)
    elif isinstance(dst_node, dict):
        # копируем внутрь каталога
        name = src_parts[-1] if src_parts else "copy"
        set_file(dst_parts + [name], src_node, src_owner)
    else:
        # перезаписываем существующий файл
        parent_parts = dst_parts[:-1]
        set_file(parent_parts + [dst_parts[-1]], src_node, src_owner)

HELP = {
    "ls":     "ls [PATH]              — вывести содержимое каталога или имя файла",
    "cd":     "cd [PATH]              — перейти в каталог (без аргумента — в корень)",
    "history":"history [N]            — показать всю историю или последние N команд (N > 0)",
    "clear":  "clear                  — очистить экран",
    "rev":    "rev TEXT...            — вывести текст в обратном порядке",
    "chown":  "chown [-R] OWNER PATH  — сменить владельца (с -R рекурсивно)",
    "cp":     "cp SRC DST             — копировать файл (каталоги без -r не поддерживаются)",
    "help":   "help [CMD]             — справка по всем командам или по команде CMD",
    "exit":   "exit                   — выход",
}

def cmd_help(args):
    if not args:
        print("Доступные команды:")
        for name in sorted(HELP):
            print("  " + HELP[name])
        return
    # help CMD [CMD2 ...]
    for name in args:
        if name in HELP:
            print(HELP[name])
        else:
            print(f"help: неизвестная команда: {name}")


def run_line(line):
    parts = shlex.split(line, comments=True)
    if not parts:
        return
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
    elif cmd == "chown":
        cmd_chown(args)
    elif cmd == "cp":
        cmd_cp(args)
    elif cmd == "help":
        cmd_help(args)
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
