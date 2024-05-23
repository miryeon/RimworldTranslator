# RimWorld Mod Translator

## 프로젝트

이 프로젝트는 RimWorld 모드 파일을 번역하는 도구입니다. 사용자는 특정 폴더를 선택하여 해당 폴더 내 모든 XML 파일을 번역할 수 있습니다. 이 도구는 Google Translate API를 사용합니다.

## 기능

- 폴더 내 모든 XML 파일 번역
- 원본 언어와 대상 언어 선택 가능
- 번역 진행 상황을 실시간으로 로그에 표시

## 설치 방법

1. **Python 설치**: Python 3.7 이상 설치필요 Python이 설치되어 있지 않다면 [python.org](https://www.python.org/)에서 설치하세요.

2. **필요한 라이브러리 설치**: 필요한 라이브러리를 설치합니다.

    ```sh
    pip install googletrans==4.0.0-rc1
    pip install tkinter
    ```


## 사용법

1. **프로그램 실행**: 다음 명령어를 사용하여 프로그램을 실행하거나 Idle이용하여 실행하십시오.

    ```sh
    python translator.py
    ```

2. **언어 선택**: 프로그램이 실행되면 원본 언어와 대상 언어를 선택합니다. 기본값은 영어(English)에서 한국어(Korean)로 번역합니다.

3. **폴더 선택**: "Select Mod Directory and Translate" 버튼을 클릭하여 번역할 모드 파일이 있는 폴더를 선택합니다.

4. **번역 진행 확인**: 번역 진행 상황이 GUI의 로그 창에 실시간으로 표시됩니다. 번역이 완료되면 "Translation completed for all files."라는 메시지가 표시됩니다.

## 예제

1. **GUI 초기 화면**:
    - 원본 언어와 대상 언어를 선택할 수 있는 드롭다운 메뉴가 있습니다.
    - "Select Mod Directory and Translate" 버튼이 있습니다.

2. **번역 진행 중**:
    - 번역 진행 상황이 로그 창에 실시간으로 표시됩니다.
    - 예: "Translating example.xml..." 및 "Finished translating example.xml."

