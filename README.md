# Calendar Briefing Agent

사용자의 하루 일정을 분석해 일정 밀도, 충돌, 전환 시간 부족, 일정 유형, 미리 챙길 일을 정리해주는 캘린더 브리핑 웹 데모입니다.

초기에는 Streamlit으로 빠르게 화면을 검증했고, 현재 제품형 데모는 **FastAPI + React** 구조로 구성했습니다. 백엔드는 기존 파이썬 분석 로직을 API로 제공하고, 프론트엔드는 밝고 카드 기반의 한국어 일정 브리핑 UI를 보여줍니다.

## 프로젝트 구조

```text
calendar-briefing-agent/
├── backend/
│   ├── app/
│   │   ├── main.py        FastAPI 엔드포인트
│   │   ├── analyzer.py    일정 수, 총 시간, 충돌, 전환 시간 분석
│   │   ├── persona.py     일정 유형 분류
│   │   ├── briefing.py    요약, 조심할 점, 챙길 일 생성
│   │   └── schema.py      일정 데이터 파싱
│   ├── data/
│   │   └── sample_schedule.json
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── package.json
│   └── tailwind.config.js
├── app/                  기존 파이썬 프로토타입 로직
├── app_ui.py             초기 Streamlit 프로토타입
└── README.md
```

## 백엔드 실행

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000
```

백엔드는 `backend/data/sample_schedule.json`을 읽어 일정 데이터를 분석합니다.

## 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 아래 주소를 엽니다.

```text
http://localhost:5173
```

프론트엔드는 FastAPI 백엔드의 아래 API를 호출합니다.

```text
http://localhost:8000/schedule
http://localhost:8000/briefing
```

## API 엔드포인트

| Method | Endpoint | 설명 |
| --- | --- | --- |
| GET | `/health` | 백엔드 상태 확인 |
| GET | `/schedule` | 샘플 일정 원본 데이터 반환 |
| GET | `/briefing` | 일정 분석 결과, 일정 유형, 브리핑 결과 반환 |

`/briefing` 응답은 다음 세 영역으로 구성됩니다.

- `analysis`: 일정 수, 예정된 시간, 겹치는 일정, 전환 시간이 부족한 구간
- `persona`: 하루 일정 유형과 설명
- `briefing`: 오늘 하루 요약, 조심할 점, 미리 챙기면 좋은 것

## UI Preview

React UI는 밝은 배경, 넓은 여백, 부드러운 카드, 세로 타임라인을 사용합니다.

- 상단에는 `오늘 일정 브리핑` 히어로 영역과 날짜/타임존 표시가 있습니다.
- 왼쪽에는 오늘 일정이 시간순 타임라인 카드로 표시됩니다.
- 오른쪽에는 `일정 수`, `예정된 시간`, `주의 구간`, `일정 유형` 요약 카드가 있습니다.
- `오늘 일정 분석하기` 버튼을 누르면 `오늘 하루 요약`, `조심할 점`, `미리 챙기면 좋은 것`, `나의 일정 유형` 카드가 나타납니다.

전체 톤은 개발자 대시보드가 아니라, 사용자가 하루를 시작할 때 자연스럽게 확인하는 한국어 생산성 앱을 목표로 합니다.

## 검증

백엔드 문법 확인:

```bash
python3 -m compileall backend/app
```

프론트엔드 빌드 확인:

```bash
cd frontend
npm run build
```

## 포트폴리오 관점

이 프로젝트는 단순한 화면 구현보다, 제품 흐름을 다음처럼 분리해 보여주는 데 의미가 있습니다.

- 일정 데이터를 구조화된 입력으로 다루는 방식
- 일정 충돌과 전환 시간 부족처럼 사용자가 실제로 겪는 문제 정의
- 분석 로직과 사용자 화면을 분리한 FastAPI + React 구조
- 빠른 Streamlit 프로토타입에서 제품형 웹 데모로 확장하는 과정
- 이후 Google Calendar, Outlook Calendar, 날씨 API, 개인화 브리핑으로 확장 가능한 기반
