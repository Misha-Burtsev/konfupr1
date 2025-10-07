import shlex
import argparse

# --- CLI args ---
p = argparse.ArgumentParser()
p.add_argument("--vfs", default="myvfs", help="Путь к физическому расположению VFS")
p.add_argument("--script", help="Путь к стартовому скрипту")
a = p.parse_args()
print(f"DEBUG: vfs='{a.vfs}', script='{a.script}'")

VFS = a.vfs

def run_line(vfs, line):
    parts = shlex.split(line)  # может бросить ValueError при кривых кавычках
    if not parts:
        return
    cmd, *args = parts
    if cmd in ("ls", "cd"):
        print(f"{cmd} {args}")
    else:
        print(f"Ошибка: команда '{cmd}' не существует.")

# --- выполнение стартового скрипта ---
if a.script:
    try:
        with open(a.script, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                print(f"{VFS}$ {line}")  # эхо ввода
                try:
                    run_line(VFS, line)
                except SystemExit:
                    print("SCRIPT ERROR: попытка завершить выполнение внутри скрипта — игнорирую.")
                except Exception as e:
                    print(f"SCRIPT ERROR: {e}")
    except Exception as e:
        print(f"SCRIPT ERROR: не удалось открыть скрипт: {e}")

# --- REPL ---
line = input(f"{VFS}$ ")
while line != "exit":
    try:
        run_line(VFS, line)
    except Exception as e:
        print(f"ERROR: {e}")
    line = input(f"{VFS}$ ")
