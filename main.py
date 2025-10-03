import shlex

VFS = "myvfs"  # имя виртуальной файловой системы

line = input(f"{VFS}$ ")
while line != "exit":
    parts = shlex.split(line)
    command = parts[0]
    args = parts[1:]

    if command in ("ls", "cd"):
        print(f"{command} {args}")

    else:
        print(f"Ошибка: команда '{command}' не существует.")

    line = input(f"{VFS}$ ")
