import os
import re
import threading
import time
import queue
from googletrans import Translator, LANGUAGES
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from colorama import init, Fore
from concurrent.futures import ThreadPoolExecutor, as_completed

init(autoreset=True)

def escape_xml_characters(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("'", "&apos;")
                .replace('"', "&quot;"))

def translate_text(text, src_lang, dest_lang):
    translator = Translator()
    try:
        translated = translator.translate(text, src=src_lang, dest=dest_lang).text
        return escape_xml_characters(translated)
    except Exception as e:
        write_log(f"번역 오류: {str(e)}", error=True)
        return text

def write_log(message, error=False, success=False):
    if error:
        log_queue.put(Fore.RED + message)
    elif success:
        log_queue.put(Fore.GREEN + message)
    else:
        log_queue.put(message)

def translate_file(file_path, src_lang, dest_lang):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        translated_content = re.sub(r'>(.*?)<', 
                                    lambda m: f">{translate_text(m.group(1), src_lang, dest_lang)}<", 
                                    content)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(translated_content)

        write_log(f"{file_path} 번역 완료", success=True)
    except Exception as e:
        write_log(f"파일 번역 중 오류 발생: {e}", error=True)

def translate_directory(directory, src_lang, dest_lang):
    futures = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".xml"):
                    file_path = os.path.join(root, file)
                    futures.append(executor.submit(translate_file, file_path, src_lang, dest_lang))

        for future in as_completed(futures):
            future.result()  # This will raise any exceptions caught in the threads

    write_log("모든 번역이 완료되었습니다.", success=True)

def update_log(log_queue, log_widget):
    while True:
        message = log_queue.get()
        if message == "DONE":
            break
        log_widget.config(state=tk.NORMAL)
        log_widget.insert(tk.END, message + '\n')
        log_widget.config(state=tk.DISABLED)
        log_widget.see(tk.END)
        log_queue.task_done()

def translation_thread(mod_directory, src_language, target_language, log_queue):
    try:
        log_queue.put("번역을 시작합니다...")
        translate_directory(mod_directory, src_language, target_language)
    except Exception as e:
        log_queue.put(f"번역 중 오류 발생: {e}")
    finally:
        log_queue.put("DONE")

def start_translation():
    mod_directory = directory_var.get()
    if not mod_directory:
        write_log("Please select a mod directory.", error=True)
        return

    src_language_name = src_language_var.get()
    target_language_name = target_language_var.get()

    src_language = [code for code, name in LANGUAGES.items() if name == src_language_name]
    target_language = [code for code, name in LANGUAGES.items() if name == target_language_name]

    if not src_language or not target_language:
        write_log("Invalid source or target language selected.", error=True)
        return

    src_language = src_language[0]
    target_language = target_language[0]

    threading.Thread(target=translation_thread, args=(mod_directory, src_language, target_language, log_queue)).start()

def browse_directory():
    directory = filedialog.askdirectory()
    directory_var.set(directory)

root = tk.Tk()
root.title("RimWorld Mod Translator")
root.geometry("700x500")
root.configure(bg="#2e2e2e")

style = ttk.Style()
style.theme_use('clam')

style.configure('TButton', font=('Helvetica', 12), padding=10)
style.configure('TLabel', font=('Helvetica', 12), background="#2e2e2e", foreground="#ffffff")
style.configure('TCombobox', font=('Helvetica', 12))
style.configure('TEntry', font=('Helvetica', 12))

frame = ttk.Frame(root, padding="10 10 10 10", style="TFrame")
frame.pack(fill=tk.BOTH, expand=True)

header = tk.Label(frame, text="RimWorld Mod Translator", font=('Helvetica', 18, 'bold'), bg="#2e2e2e", fg="#ffffff")
header.grid(row=0, column=0, columnspan=3, pady=10)

src_language_label = ttk.Label(frame, text="Source Language:", style="TLabel")
src_language_label.grid(row=1, column=0, sticky=tk.E, pady=5, padx=5)
src_language_var = tk.StringVar()
src_language_menu = ttk.Combobox(frame, textvariable=src_language_var, values=list(LANGUAGES.values()), state='readonly')
src_language_menu.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
src_language_menu.set("English")

target_language_label = ttk.Label(frame, text="Target Language:", style="TLabel")
target_language_label.grid(row=2, column=0, sticky=tk.E, pady=5, padx=5)
target_language_var = tk.StringVar()
target_language_menu = ttk.Combobox(frame, textvariable=target_language_var, values=list(LANGUAGES.values()), state='readonly')
target_language_menu.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
target_language_menu.set("Korean")

directory_label = ttk.Label(frame, text="Mod Directory:", style="TLabel")
directory_label.grid(row=3, column=0, sticky=tk.E, pady=5, padx=5)
directory_var = tk.StringVar()
directory_entry = ttk.Entry(frame, textvariable=directory_var, state='readonly', width=40)
directory_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
browse_button = ttk.Button(frame, text="Browse", command=browse_directory)
browse_button.grid(row=3, column=2, sticky=tk.W, pady=5, padx=5)

start_button = ttk.Button(frame, text="Start Translation", command=start_translation)
start_button.grid(row=4, column=0, columnspan=3, pady=20)

log_label = ttk.Label(frame, text="Log:", style="TLabel")
log_label.grid(row=5, column=0, sticky=tk.W, pady=5, padx=5)
log_widget = scrolledtext.ScrolledText(frame, width=80, height=15, state=tk.DISABLED, font=('Helvetica', 10), bg="#333333", fg="#ffffff")
log_widget.grid(row=6, column=0, columnspan=3, pady=5, sticky=tk.EW)

log_queue = queue.Queue()
threading.Thread(target=update_log, args=(log_queue, log_widget), daemon=True).start()

frame.columnconfigure(1, weight=1)
frame.columnconfigure(2, weight=1)

root.mainloop()
