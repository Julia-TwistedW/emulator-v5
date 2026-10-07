import tkinter as tk
from tkinter import scrolledtext
import shlex
import sys
import getpass
import socket
import os
import json
import calendar
from datetime import datetime

def parse_cli_args(args):
    """Парсит аргументы командной строки.
    Args: args: Список аргументов из sys.argv[1:].
    Returns: dict: Словарь с ключами 'vfs' и 'script'."""
    result = {"vfs": None, "script": None}
    i = 0
    while i < len(args):
        if args[i] == "-vfs" and i + 1 < len(args):
            result["vfs"] = args[i + 1]
            i += 2
        elif args[i] == "-script" and i + 1 < len(args):
            result["script"] = args[i + 1]
            i += 2
        else:
            i += 1
    return result
def load_vfs(path):
    """Загружает виртуальную файловую систему из JSON.
    Args: path: Путь к файлу JSON.
    Returns: dict: Словарь, представляющий файловую систему. """
    default_fs = {
        "/": {"type": "dir", "content": ["home", "bin"]},
        "/home": {"type": "dir", "content": ["user"]},
        "/home/user": {"type": "dir", "content": []},
        "/bin": {"type": "dir", "content": ["ls", "cd"]}
    }
    if not path or not os.path.exists(path):
        print(f"VFS файл '{path}' не найден. Используется пустая ФС.")
        return default_fs
    try:
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        if "/" not in data:
            data["/"] = {"type": "dir", "content": []}
        return data
    except json.JSONDecodeError:
        print(f"Ошибка формата JSON в '{path}'. Используется пустая ФС.")
        return default_fs
def create_gui(username, hostname):
    """Создает графический интерфейс эмулятора.
    Args: username: Имя текущего пользователя. hostname: Имя хоста.
    Returns: tuple: (root_window, output_area, input_entry, prompt_label) """
    root = tk.Tk()
    title = f"Эмулятор - [{username}@{hostname}]"
    root.title(title)
    root.geometry("750x550")
    out = scrolledtext.ScrolledText(
        root, state='disabled', bg='black',
        fg='white', font=('Consolas', 10)
    )
    out.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    frame = tk.Frame(root)
    frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    prompt = tk.Label(
        frame, text=f"{username}@{hostname}:/$ ",
        bg='black', fg='lightgreen', font=('Consolas', 10)
    )
    prompt.pack(side=tk.LEFT)
    entry = tk.Entry(
        frame, bg='black', fg='white',
        insertbackground='white', font=('Consolas', 10)
    )
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    entry.focus_set()
    return root, out, entry, prompt
def write_output(widget, text):
    """Выводит текст в виджет ScrolledText.
    Args: widget: Виджет вывода. text: Текст для отображения."""
    widget.config(state='normal')
    widget.insert(tk.END, text)
    widget.see(tk.END)
    widget.config(state='disabled')
def update_prompt(widget, user, host, cur_dir):
    """Обновляет текст приглашения командной строки.
    Args: widget: Виджет Label для промпта. user: Имя пользователя.
        host: Имя хоста. cur_dir: Текущая директория."""
    widget.config(text=f"{user}@{host}:{cur_dir}$ ")
def cmd_ls(vfs, cur_dir, args, out_widget):
    """Реализует команду ls.
    Args: vfs: Словарь файловой системы. cur_dir: Текущий путь.
        args: Аргументы команды. out_widget: Виджет вывода."""
    target = cur_dir
    if args:
        path = args[0]
        if path.startswith("/"):
            target = path
        else:
            target = os.path.join(cur_dir, path).replace("\\", "/")
    target = target.rstrip("/") if target != "/" else "/"
    if target in vfs and vfs[target]["type"] == "dir":
        content = vfs[target].get("content", [])
        write_output(out_widget, "  ".join(content) + "\n")
    elif target in vfs:
        write_output(out_widget, os.path.basename(target) + "\n")
    else:
        name = args[0] if args else target
        msg = f"ls: cannot access '{name}': No such file\n"
        write_output(out_widget, msg)
def cmd_cd(vfs, cur_dir, args, out_widget, prompt_widget, user, host):
    """Реализует команду cd.
    Args: vfs: Словарь файловой системы. cur_dir: Текущий путь.
        args: Аргументы команды. out_widget: Виджет вывода.
        prompt_widget: Виджет промпта. user: Имя пользователя.
        host: Имя хоста.
    Returns: str: Новый текущий путь."""
    if not args: new_path = "/"
    elif args[0] == "..": new_path = os.path.dirname(cur_dir) or "/"
    elif args[0].startswith("/"): new_path = args[0]
    else: new_path = os.path.join(cur_dir, args[0]).replace("\\", "/")
    new_path = new_path.rstrip("/") if new_path != "/" else "/"
    if new_path in vfs and vfs[new_path]["type"] == "dir":
        update_prompt(prompt_widget, user, host, new_path)
        return new_path
    else:
        msg = f"cd: {args[0]}: No such file or directory\n"
        write_output(out_widget, msg)
        return cur_dir
def cmd_mkdir(vfs, cur_dir, args, out_widget):
    """Реализует команду mkdir (только в памяти).
    Args: vfs: Словарь файловой системы. cur_dir: Текущий путь.
        args: Аргументы команды. out_widget: Виджет вывода."""
    if not args:
        write_output(out_widget, "mkdir: missing operand\n")
        return
    name = args[0]
    new_path = name if name.startswith("/") \
        else os.path.join(cur_dir, name).replace("\\", "/")
    new_path = new_path.rstrip("/") if new_path != "/" else "/"
    if new_path in vfs:
        msg = f"mkdir: cannot create '{name}': File exists\n"
        write_output(out_widget, msg)
        return
    parent = os.path.dirname(new_path) or "/"
    if parent not in vfs or vfs[parent]["type"] != "dir":
        msg = f"mkdir: cannot create '{name}': No such dir\n"
        write_output(out_widget, msg)
        return
    vfs[new_path] = {"type": "dir", "content": []}
    if "content" not in vfs[parent]: vfs[parent]["content"] = []
    vfs[parent]["content"].append(os.path.basename(new_path))
    write_output(out_widget, f"Directory '{name}' created.\n")
def execute_command(line, vfs, cur_dir, widgets, user, host):
    """Парсит и выполняет одну команду.
    Args: line: Строка команды. vfs: Словарь файловой системы.
        cur_dir: Текущий путь. widgets: Кортеж (out, entry, prompt).
        user: Имя пользователя. host: Имя хоста.
    Returns: str: Обновленный текущий путь."""
    out, _, prompt = widgets
    line = line.strip()
    if not line:
        return cur_dir
    try: parts = shlex.split(line)
    except ValueError as err:
        write_output(out, f"Parse error: {err}\n")
        return cur_dir
    cmd = parts[0]
    args = parts[1:]
    if cmd == "exit": widgets[0].master.destroy()
    elif cmd == "ls": cmd_ls(vfs, cur_dir, args, out)
    elif cmd == "cd": cur_dir = cmd_cd(vfs, cur_dir, args, out, prompt, user, host)
    elif cmd == "mkdir": cmd_mkdir(vfs, cur_dir, args, out)
    elif cmd == "whoami": write_output(out, f"{user}\n")
    elif cmd == "cal":
        now = datetime.now()
        cal_str = calendar.month(now.year, now.month)
        write_output(out, cal_str + "\n")
    elif cmd == "who":
        msg = f"{user}  pts/0  {now.strftime('%Y-%m-%d %H:%M')}\n"
        write_output(out, msg)
    else: write_output(out, f"{cmd}: command not found\n")
    return cur_dir
def run_script(path, vfs, cur_dir, widgets, user, host):
    """Выполняет стартовый скрипт с имитацией диалога.
    Args: path: Путь к файлу скрипта. vfs: Словарь файловой системы.
        cur_dir: Текущий путь. widgets: Кортеж (out, entry, prompt).
        user: Имя пользователя. host: Имя хоста."""
    out = widgets[0]
    write_output(out, f"--- Script: {path} ---\n")
    if not os.path.exists(path):
        write_output(out, f"Script '{path}' not found.\n")
        return
    with open(path, 'r', encoding='utf-8') as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            prefix = f"{user}@{host}:{cur_dir}$ "
            write_output(out, f"{prefix}{line}\n")
            cur_dir = execute_command(
                line, vfs, cur_dir, widgets, user, host
            )
    write_output(out, "--- Script finished ---\n")
def main():
    """Точка входа в приложение."""
    cli = parse_cli_args(sys.argv[1:])
    vfs = load_vfs(cli["vfs"])
    user = getpass.getuser()
    host = socket.gethostname()
    root, out, entry, prompt = create_gui(user, host)
    widgets = (out, entry, prompt)
    current_dir = "/"
    def on_enter(event):
        nonlocal current_dir
        line = entry.get()
        entry.delete(0, tk.END)
        prefix = f"{user}@{host}:{current_dir}$ "
        write_output(out, f"{prefix}{line}\n")
        current_dir = execute_command(
            line, vfs, current_dir, widgets, user, host
        )
    entry.bind('<Return>', on_enter)
    if cli["script"]:
        run_script(
            cli["script"], vfs, current_dir, widgets, user, host
        )
    else:
        welcome = "Welcome to UNIX shell emulator!\nType 'exit' to quit.\n"
        write_output(out, welcome)

    root.mainloop()
if __name__ == "__main__": main()
