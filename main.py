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

def cmd_ls(arg=None):
    # если аргумента нет — листим текущую директорию ('.')
    target = arg if arg else '.'
    node, _ = _resolve(target)
    if node is None:
        print("ls: нет такого пути");
        return
    if isinstance(node, dict):
        names = sorted(node.keys())
        print(' '.join(n + '/' if isinstance(node[n], dict) else n for n in names))
    else:
        print("(файл)")


def cmd_cd(arg=None):
    if not arg:
        CWD.clear(); return
    node, parts = _resolve(arg)
    if node is None or not isinstance(node, dict):
        print("cd: не каталог")
    else:
        CWD[:] = parts

def run_line(line):
    parts = shlex.split(line)
    if not parts: return
    cmd, *args = parts
    if cmd == "ls":
        cmd_ls(args[0] if args else None)
    elif cmd == "cd":
        cmd_cd(args[0] if args else None)
    elif cmd == "exit":
        sys.exit(0)
    else:
        print(f"Ошибка: команда '{cmd}' не существует.")

# --- выполнение стартового скрипта (как и раньше) ---
if a.script:
    try:
        with open(a.script, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                print(f"{PROMPT}$ {line}")
                try:
                    run_line(line)
                except SystemExit:
                    print("SCRIPT ERROR: попытка выйти из REPL внутри скрипта — игнорирую.")
                except Exception as e:
                    print(f"SCRIPT ERROR: {e}")
    except Exception as e:
        print(f"SCRIPT ERROR: не удалось открыть скрипт: {e}")

# --- REPL ---
while True:
    try:
        line = input(f"{PROMPT}$ ")
        run_line(line)
    except KeyboardInterrupt:
        print()
    except Exception as e:
        print(f"ERROR: {e}")
