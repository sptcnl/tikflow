# TikFlow

TikFlow는 ADB로 Android 기기에 연결해서 일정 간격마다 TikTok 화면을 위로 스와이프하는 자동화 도구입니다. 이제 Flask 웹 GUI에서 시작, 중지, 스와이프 간격, ADB 대상 주소를 제어할 수 있습니다.

## Requirements

- Python 3.10 이상
- ADB 설치 및 PATH 등록
- Android 11 이상
- Android 개발자 옵션에서 Wireless Debugging 활성화
- Flask

## 설치

Python 패키지를 설치합니다.

```sh
pip install Flask
```

ADB가 설치되어 있는지 확인합니다.

```sh
adb version
```

## 실행 방법

Flask 웹 서버를 실행합니다.

```sh
python app.py
```

브라우저에서 아래 주소를 엽니다.

```text
http://localhost:8080
```

웹 화면에서 다음 값을 설정한 뒤 `Start`를 누릅니다.

- `ADB target`: 기본값은 `192.168.0.20:35473`
- `Interval`: 5~60초, 기본값은 `20`초

중지하려면 웹 화면에서 `Stop`을 누릅니다.

## CLI 실행

웹 GUI 없이 기존 방식처럼 직접 실행할 수도 있습니다.

```sh
python tikflow.py
```

중지하려면 `Ctrl+C`를 누릅니다.

## How It Works

- `app.py`가 Flask 서버를 `http://localhost:8080`에서 실행합니다.
- 웹 UI에서 `Start`를 누르면 `tikflow.py`의 core runner가 background thread로 시작됩니다.
- 시작 시 `adb connect <ADB target>`으로 기기에 연결합니다.
- 설정한 interval마다 아래 ADB 명령을 실행합니다.

```sh
adb shell input swipe 540 1800 540 400 300
```

- 로그는 메모리에 최근 100줄만 저장됩니다.
- 웹 UI는 2초마다 상태와 로그를 polling해서 갱신합니다.
- 데이터베이스는 사용하지 않습니다.

## 파일 구조

- `tikflow.py`: ADB 연결, 스와이프 실행, background thread, in-memory log 관리
- `app.py`: Flask 서버, API endpoint, 단일 페이지 dark theme 웹 UI

## API

- `GET /api/status`: 실행 상태, 설정값, 로그 조회
- `POST /api/start`: TikFlow 시작
- `POST /api/stop`: TikFlow 중지
