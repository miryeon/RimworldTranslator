import os
import re
import threading
import time
import queue
import shutil
import json
from googletrans import Translator, LANGUAGES
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from colorama import init, Fore
from concurrent.futures import ThreadPoolExecutor, as_completed

CONFIG_FILE = 'config.json'

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def disable_buttons():
    start_button.config(state=tk.DISABLED)
    browse_button.config(state=tk.DISABLED)
    start_move_button.config(state=tk.DISABLED)
    browse_source_button.config(state=tk.DISABLED)
    browse_destination_button.config(state=tk.DISABLED)

def enable_buttons():
    start_button.config(state=tk.NORMAL)
    browse_button.config(state=tk.NORMAL)
    start_move_button.config(state=tk.NORMAL)
    browse_source_button.config(state=tk.NORMAL)
    browse_destination_button.config(state=tk.NORMAL)

def save_config(config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    return {}

def update_config(key, value):
    config = load_config()
    config[key] = value
    save_config(config)

def load_initial_settings():
    config = load_config()
    if 'mod_directory' in config:
        directory_var.set(config['mod_directory'])
    if 'source_directory' in config:
        source_directory_var.set(config['source_directory'])
    if 'destination_directory' in config:
        destination_directory_var.set(config['destination_directory'])
    if 'src_language' in config:
        src_language_var.set(config['src_language'])
    if 'target_language' in config:
        target_language_var.set(config['target_language'])



def escape_xml_characters(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("'", "&apos;")
                .replace('"', "&quot;"))

def translate_text(text, src_lang, dest_lang, retry_count=0):
    translator = Translator()
    try:
        placeholder_pattern = re.compile(r'\[.*?\]')
        placeholders = placeholder_pattern.findall(text)
        clean_text = placeholder_pattern.sub('{}', text)

        translated = translator.translate(clean_text, src=src_lang, dest=dest_lang).text
        translated_escaped = escape_xml_characters(translated)

        for placeholder in placeholders:
            translated_escaped = translated_escaped.replace('{}', placeholder, 1)

        return translated_escaped
    except Exception as e:
        if retry_count < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return translate_text(text, src_lang, dest_lang, retry_count + 1)
        else:
            write_log(f"번역 오류: {str(e)}", error=True)
            return text

def find_translation_targets(directory):
    translation_targets = []

    # 'DefInjected', 'Keyed' 폴더 탐색
    for root, dirs, files in os.walk(directory):
        for folder in ['DefInjected', 'Keyed']:
            if folder in dirs:
                folder_path = os.path.join(root, folder)
                for sub_root, _, sub_files in os.walk(folder_path):
                    # 'AlienRace.ThingDef_AlienRace' 및 'RulePackDef' 폴더 제외
                    if 'AlienRace.ThingDef_AlienRace' in sub_root or 'RulePackDef' in sub_root :
                        continue
                    for file in sub_files:
                        if file.endswith('.xml'):
                            translation_targets.append(os.path.join(sub_root, file))

    return translation_targets




def write_log(message, error=False, success=False):
    if error:
        log_queue.put(Fore.RED + message)
    elif success:
        log_queue.put(Fore.GREEN + message)
    else:
        log_queue.put(message)

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

        threading.Thread(target=update_log, args=(log_queue, log_widget), daemon=True).start()



def translate_file(file_path, src_lang, dest_lang, file_index, total_files):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        tags = re.findall(r'(<[^>]+>)([^<]+)(</[^>]+>)', content)
        translated_content = content

        for tag in tags:
            before, text, after = tag
            write_log(f"파일 {file_index + 1}/{total_files} - {file_path} 태그 번역 중... ")

            if '->' in text:
                left, right = text.split('->', 1)
                translated_text = f"{left}->{translate_text(right.strip(), src_lang, dest_lang)}"
            else:
                translated_text = translate_text(text, src_lang, dest_lang)
                
            translated_content = translated_content.replace(f"{before}{text}{after}", f"{before}{translated_text}{after}", 1)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(translated_content)

        write_log(f"{file_path} 번역 완료", success=True)
    except Exception as e:
        write_log(f"파일 번역 중 오류 발생 ({file_path}): {e}", error=True)

def translate_directory(directory, src_lang, dest_lang):
    futures = []
    translation_targets = find_translation_targets(directory)
    total_files = len(translation_targets)

    with ThreadPoolExecutor(max_workers=10) as executor:
        for file_index, file_path in enumerate(translation_targets):
            futures.append(executor.submit(translate_file, file_path, src_lang, dest_lang, file_index, total_files))

        for future in as_completed(futures):
            future.result()  # This will raise any exceptions caught in the threads

    write_log("모든 번역이 완료되었습니다.", success=True)


def translation_thread(mod_directory, src_language, target_language, log_queue):
    try:
        log_queue.put("번역을 시작합니다...")
        translate_directory(mod_directory, src_language, target_language)
    except Exception as e:
        log_queue.put(f"번역 중 오류 발생: {e}")
    finally:
        log_queue.put("DONE")
        root.after(0, enable_buttons)

def start_translation():
    disable_buttons()
    mod_directory = directory_var.get()
    if not mod_directory:
        write_log("Please select a mod directory.", error=True)
        enable_buttons()
        return

    src_language_name = src_language_var.get()
    target_language_name = target_language_var.get()

    src_language = [code for code, name in LANGUAGES.items() if name == src_language_name]
    target_language = [code for code, name in LANGUAGES.items() if name == target_language_name]

    if not src_language or not target_language:
        write_log("Invalid source or target language selected.", error=True)
        enable_buttons()
        return

    src_language = src_language[0]
    target_language = target_language[0]

    update_config('mod_directory', mod_directory)
    update_config('src_language', src_language_name)
    update_config('target_language', target_language_name)

    threading.Thread(target=translation_thread, args=(mod_directory, src_language, target_language, log_queue)).start()








def move_and_copy_languages(source_dir, target_dir):
    try:
        for folder_name in os.listdir(source_dir):
            folder_path = os.path.join(source_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue

            important_number_match = re.search(r'\d+', folder_name)
            if not important_number_match:
                write_log(f"폴더명에서 중요한 숫자를 찾을 수 없음: {folder_name}", error=True)
                continue

            important_number = important_number_match.group(0)
            for target_folder_name in os.listdir(target_dir):
                if important_number in target_folder_name:
                    target_folder_path = os.path.join(target_dir, target_folder_name)
                    if os.path.isdir(target_folder_path):
                        source_languages_path = os.path.join(folder_path, 'Languages')
                        target_languages_path = os.path.join(target_folder_path, 'Languages')
                        if os.path.exists(source_languages_path):
                            if os.path.exists(target_languages_path):
                                shutil.rmtree(target_languages_path)
                            shutil.copytree(source_languages_path, target_languages_path)
                            write_log(f"'{source_languages_path}'를 '{target_languages_path}'로 이동 완료", success=True)
                        else:
                            write_log(f"'Languages' 폴더를 찾을 수 없음: {source_languages_path}", error=True)
                    else:
                        write_log(f"대상 폴더가 존재하지 않음: {target_folder_path}", error=True)
                    break
            else:
                write_log(f"대상 경로에서 해당 숫자를 포함하는 폴더를 찾을 수 없음: {important_number}", error=True)
    except Exception as e:
        write_log(f"이동 및 복사 작업 중 오류 발생: {e}", error=True)

def move_and_copy_thread(src_dir, dest_dir, log_queue):
    try:
        log_queue.put("이동 및 복사 작업을 시작합니다...")
        move_and_copy_languages(src_dir, dest_dir)
    except Exception as e:
        log_queue.put(f"이동 및 복사 작업 중 오류 발생: {e}")
    finally:
        log_queue.put("DONE")
        root.after(0, enable_buttons)

def start_move_and_copy():
    disable_buttons()
    source_directory = source_directory_var.get()
    destination_directory = destination_directory_var.get()
    if not source_directory or not destination_directory:
        write_log("Source 및 Destination 경로를 모두 선택하십시오.", error=True)
        enable_buttons()
        return

    update_config('source_directory', source_directory)
    update_config('destination_directory', destination_directory)

    threading.Thread(target=move_and_copy_thread, args=(source_directory, destination_directory, log_queue)).start()
    
def browse_source_directory():
    directory = filedialog.askdirectory()
    source_directory_var.set(directory)

def browse_destination_directory():
    directory = filedialog.askdirectory()
    destination_directory_var.set(directory)
def browse_directory():
    directory = filedialog.askdirectory()
    directory_var.set(directory)

def create_ui_element(widget_type, parent, **options):
    widget = widget_type(parent, **options)
    widget.grid(options.pop('grid', {}))
    return widget

root = tk.Tk()
root.title("RimWorld Mod Translator")
root.geometry("700x750")
root.configure(bg="#2e2e2e")

style = ttk.Style()
style.theme_use('clam')

style.configure('TFrame', background="#464646")
style.configure('TButton', font=('Helvetica', 12), padding=10)
style.configure('TLabel', font=('Helvetica', 12), background="#2e2e2e", foreground="#ffffff")
style.configure('TCombobox', font=('Helvetica', 12))
style.configure('TEntry', font=('Helvetica', 12))

frame = ttk.Frame(root, padding="20 20 20 20", style="TFrame")
frame.pack(fill=tk.BOTH, expand=True)

header = tk.Label(frame, text="RimWorld Mod Translator", font=('Helvetica', 18, 'bold'), bg="#2e2e2e", fg="#ffffff")
header.grid(row=0, column=0, columnspan=3, pady=10)

src_language_label = ttk.Label(frame, text="Source Language:", style="TLabel")
src_language_label.grid(row=1, column=0, sticky=tk.E, pady=5, padx=5)
src_language_var = tk.StringVar()
src_language_menu = ttk.Combobox(frame, textvariable=src_language_var, values=list(LANGUAGES.values()), state='readonly')
src_language_menu.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
src_language_menu.set("english")

target_language_label = ttk.Label(frame, text="Target Language:", style="TLabel")
target_language_label.grid(row=2, column=0, sticky=tk.E, pady=5, padx=5)
target_language_var = tk.StringVar()
target_language_menu = ttk.Combobox(frame, textvariable=target_language_var, values=list(LANGUAGES.values()), state='readonly')
target_language_menu.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
target_language_menu.set("korean")

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

source_directory_label = ttk.Label(frame, text="Source Directory:", style="TLabel")
source_directory_label.grid(row=7, column=0, sticky=tk.E, pady=5, padx=5)
source_directory_var = tk.StringVar()
source_directory_entry = ttk.Entry(frame, textvariable=source_directory_var, state='readonly', width=40)
source_directory_entry.grid(row=7, column=1, sticky=tk.W, pady=5, padx=5)
browse_source_button = ttk.Button(frame, text="Browse", command=browse_source_directory)
browse_source_button.grid(row=7, column=2, sticky=tk.W, pady=5, padx=5)

destination_directory_label = ttk.Label(frame, text="Destination Directory:", style="TLabel")
destination_directory_label.grid(row=8, column=0, sticky=tk.E, pady=5, padx=5)
destination_directory_var = tk.StringVar()
destination_directory_entry = ttk.Entry(frame, textvariable=destination_directory_var, state='readonly', width=40)
destination_directory_entry.grid(row=8, column=1, sticky=tk.W, pady=5, padx=5)
browse_destination_button = ttk.Button(frame, text="Browse", command=browse_destination_directory)
browse_destination_button.grid(row=8, column=2, sticky=tk.W, pady=5, padx=5)

start_move_button = ttk.Button(frame, text="Start Move & Copy", command=start_move_and_copy)
start_move_button.grid(row=9, column=0, columnspan=3, pady=20)

log_queue = queue.Queue()
threading.Thread(target=update_log, args=(log_queue, log_widget), daemon=True).start()

load_initial_settings()

frame.columnconfigure(1, weight=1)
frame.columnconfigure(2, weight=1)

root.mainloop()
