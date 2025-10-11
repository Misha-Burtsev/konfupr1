<h1 align="center">Эмулятор командной оболочки UNIX-подобной ОС</h1>
<p align="center">
  <i>CLI-эмулятор с виртуальной файловой системой (VFS), работающей в памяти, и базовыми командами в стиле UNIX.</i>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-black"></a>
  <a href="#"><img src="https://img.shields.io/badge/Status-Completed-success"></a>
</p>

---

## Цель проекта
Разработать **эмулятор командной строки**, имитирующий работу терминала UNIX-подобных систем.  
Виртуальная файловая система (VFS) полностью хранится **в оперативной памяти**, а исходные ZIP-файлы не изменяются.

---

## Быстрый запуск

```bash
git clone https://github.com/Misha-Burtsev/konfupr1.git
cd konfupr1
python3 main.py --vfs vfs_src/vfs_min.zip --script scripts/start_stage5.txt
```

При запуске выводится отладочная информация и содержимое `motd` (если есть в архиве).

---

## Этапы разработки

| Этап | Цель | Статус |
|------|------|---------|
| 1. Базовый REPL | CLI-цикл, команды `ls`, `cd`, `exit` | ✅ |
| 2. Конфигурация | Параметры командной строки (`--vfs`, `--script`), выполнение скриптов | ✅ |
| 3. Виртуальная ФС | Подключение ZIP-архива, работа в памяти, вывод `motd` | ✅ |
| 4. Основные команды | `history`, `clear`, `rev` + улучшенные `ls` и `cd` | ✅ |
| 5. Дополнительные команды | `chown`, `cp`, `help`, итоговый скрипт тестирования | ✅ |

---

## Реализованные команды

| Команда | Назначение |
|----------|-------------|
| `ls` | Выводит содержимое каталога или имя файла |
| `cd` | Переходит в каталог (без аргумента — в корень) |
| `history [N]` | Показывает историю команд (всю или последние N) |
| `clear` | Очищает экран |
| `rev TEXT...` | Выводит текст в обратном порядке |
| `chown [-R] OWNER PATH` | Изменяет владельца файла/каталога в памяти |
| `cp SRC DST` | Копирует файл в пределах VFS |
| `help [CMD...]` | Отображает справку по командам |
| `exit` | Завершает работу эмулятора |

---

## Тестовые сценарии

Папка [`scripts/`](scripts) содержит стартовые скрипты для проверки всех этапов:

```
scripts/
├── start_stage4.txt   # тест ls, cd, history, clear, rev
├── start_stage5.txt   # тест chown, cp, help и ошибок
├── test_vfs_min.sh    # запуск с минимальной VFS
├── test_vfs_multi.sh  # запуск с VFS c несколькими уровнями
└── test_vfs_deep.sh   # запуск с глубокой VFS
```

Пример запуска:

```bash
python3 main.py --vfs vfs_src/vfs_multi.zip --script scripts/start_stage5.txt
```

---

### Пример `scripts/start_stage5.txt`

```bash
# Тестирование cp, chown, help и обработки ошибок

ls /
cp readme.txt a/readme_copy.txt
chown user1 readme.txt
chown -R user2 a
help
help cp chown
help nosuch
rev Hello world
history 5
clear
bad "arg
exit
ls /
```

---

## Основные технические решения

- Виртуальная ФС представлена как древовидный словарь:
  ```python
  {
      "dir1": { "file.txt": ('f', 'data', False) },
      "dir2": {}
  }
  ```
- Узлы типа `('f', data, is_b64)` — файлы (is_b64=True для бинарных).
- Все команды реализованы отдельными функциями (`cmd_*`) и вызываются через `run_line()`.
- Комментарии в скриптах (`# ...`) корректно игнорируются при разборе через `shlex.split(..., comments=True)`.

---

<p align="center">
  <img src="https://img.shields.io/badge/Author-Misha%20Burtsev-blue?style=for-the-badge&logo=github" />
</p>

<p align="center">
  <sub>Проект по дисциплине <b>Конфигурационное управление</b> • Вариант 2 • 2025</sub>
</p>