import os
import xml.etree.ElementTree as ET
from googletrans import Translator, LANGUAGES
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
import threading
import queue

def read_mod_files(mod_directory):
    # 모든 xml 파일을 찾기
    mod_files = []
    for root, dirs, files in os.walk(mod_directory):
        for file in files:
            if file.endswith(".xml"):
                mod_files.append(os.path.join(root, file))
    return mod_files

def extract_text_from_xml(file_path):
    # XML 파일에서 텍스트 추출
    tree = ET.parse(file_path)
    root = tree.getroot()
    texts = []
    for element in root.iter():
        if element.text:
            texts.append(element.text)
    return texts, root

def translate_text(texts, src_language, target_language):
    # 텍스트 번역
    translator = Translator()
    translated_texts = []
    for text in texts:
        try:
            translated_text = translator.translate(text, src=src_language, dest=target_language).text
            translated_texts.append(translated_text)
        except Exception as e:
            # 번역 실패 시 원본 텍스트 사용
            translated_texts.append(text)
    return translated_texts

def save_translated_texts(original_file, translated_texts, root):
    # 번역된 텍스트 저장
    elements = []
    for element in root.iter():
        if element.text:
            elements.append(element)
    
    for element, translated_text in zip(elements, translated_texts):
        element.text = translated_text
    
    tree = ET.ElementTree(root)
    tree.write(original_file, encoding="utf-8", xml_declaration=True)

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
        mod_files = read_mod_files(mod_directory)
        log_queue.put(f"Found {len(mod_files)} XML files to translate.")
        
        for file in mod_files:
            log_queue.put(f"Translating {file}...")
            texts, root = extract_text_from_xml(file)
            translated_texts = translate_text(texts, src_language, target_language)
            save_translated_texts(file, translated_texts, root)
            log_queue.put(f"Finished translating {file}.")

        log_queue.put("Translation completed for all files.")
    except Exception as e:
        log_queue.put(f"Error during translation: {e}")
    finally:
        log_queue.put("DONE")

def start_translation(log_queue, src_language_var, target_language_var):
    # 폴더 선택
    mod_directory = filedialog.askdirectory()
    if not mod_directory:
        return

    src_language = src_language_var.get()
    target_language = target_language_var.get()

    # 번역 스레드 시작
    threading.Thread(target=translation_thread, args=(mod_directory, src_language, target_language, log_queue)).start()

root = tk.Tk()
root.title("RimWorld Mod Translator")

frame = tk.Frame(root)
frame.pack(pady=10)

src_language_label = tk.Label(frame, text="Source Language:")
src_language_label.pack(side=tk.LEFT)
src_language_var = tk.StringVar()
src_language_menu = ttk.Combobox(frame, textvariable=src_language_var, values=list(LANGUAGES.values()))
src_language_menu.pack(side=tk.LEFT)
src_language_menu.set("English")  # 기본 값 설정

target_language_label = tk.Label(frame, text="Target Language:")
target_language_label.pack(side=tk.LEFT)
target_language_var = tk.StringVar()
target_language_menu = ttk.Combobox(frame, textvariable=target_language_var, values=list(LANGUAGES.values()))
target_language_menu.pack(side=tk.LEFT)
target_language_menu.set("Korean")  # 기본 값 설정

button = tk.Button(frame, text="Select Mod Directory and Translate", command=lambda: start_translation(log_queue, src_language_var, target_language_var))
button.pack()

log = scrolledtext.ScrolledText(root, width=80, height=20, state=tk.DISABLED)
log.pack(pady=10)

log_queue = queue.Queue()
threading.Thread(target=update_log, args=(log_queue, log), daemon=True).start()

root.mainloop()
