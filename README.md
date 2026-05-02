# Calendar Briefing Agent

Calendar Briefing Agent는 사용자의 하루 캘린더 데이터를 분석하고, 일정 패턴에 따라 사용자 페르소나를 분류한 뒤, 개인화된 데일리 브리핑을 생성하는 Python MVP입니다.

이 프로젝트는 OpenAI API를 바로 붙이기보다, 먼저 일정 분석, 페르소나 판단, 리스크 탐지, 추천 액션 생성이라는 핵심 제품 로직을 명확히 분리하는 데 초점을 맞췄습니다. 이후 LangGraph, VectorDB, Langfuse 같은 AI Agent 구성 요소를 자연스럽게 확장할 수 있도록 모듈형 구조로 설계했습니다.

## 프로젝트 목적

이 MVP는 AI/Agent Product Role 포트폴리오를 위해 만든 작은 제품 실험입니다. 단순히 LLM으로 문장을 생성하는 것이 아니라, 사용자의 실제 컨텍스트를 구조화하고, 분석 가능한 신호로 바꾸고, 그 결과를 사용자에게 유용한 브리핑 형태로 전달하는 흐름을 보여주는 것이 목적입니다.

## 아키텍처

```text
app/main.py       입력 로드, 분석, 페르소나 분류, 브리핑 생성, JSON 저장을 오케스트레이션합니다.
app/schema.py     일정 데이터 구조와 입력 파싱 로직을 정의합니다.
app/analyzer.py   일정 수, 총 일정 시간, 카테고리 분포, 일정 충돌, 버퍼 부족을 분석합니다.
app/persona.py    분석 결과를 바탕으로 사용자 페르소나를 분류합니다.
app/briefing.py   사용자에게 보여줄 데일리 브리핑 결과를 생성합니다.
data/             샘플 캘린더 입력 데이터를 저장합니다.
app_ui.py         샘플 일정을 확인하고 분석할 수 있는 한국어 Streamlit UI입니다.
logs/             생성된 결과 파일(result.json)을 저장합니다.
```

핵심 분석 로직과 UI, CLI 실행 흐름을 분리해 두었기 때문에 이후 LLM 호출, Agent workflow, 추적/관측 기능을 추가하기 쉽습니다.

## 주요 기능

- `data/sample_schedule.json`에서 샘플 일정 데이터 로드
- 전체 일정 개수 계산
- 총 일정 시간 계산
- 일정 카테고리 분포 분석
- 겹치는 일정 충돌 탐지
- 일정 사이 버퍼 시간이 부족한 구간 탐지
- 사용자 페르소나 분류
  - Work-Focused Planner
  - Growth-Oriented Planner
  - Life-Balanced Planner
  - Light Scheduler
- 데일리 브리핑 생성
  - 요약
  - 페르소나 설명
  - 일정 목록
  - 리스크 메시지
  - 추천 액션
- 한국어 Streamlit UI에서 일정 확인 및 분석 실행
- 분석 결과를 `logs/result.json`에 저장

## CLI 실행 방법

프로젝트 루트에서 아래 명령어를 실행합니다.

```bash
python3 app/main.py
```

실행 결과는 아래 경로에 저장됩니다.

```text
logs/result.json
```

CLI 실행은 Python 표준 라이브러리만 사용합니다.

## Streamlit UI 실행 방법

먼저 의존성을 설치합니다.

```bash
pip install -r requirements.txt
```

프로젝트 루트에서 Streamlit 앱을 실행합니다.

```bash
streamlit run app_ui.py
```

UI는 한국어로 표시됩니다. 기본적으로 `data/sample_schedule.json`을 불러오고, 일정 목록을 확인한 뒤 `일정 분석하기` 버튼을 눌러 분석 결과를 볼 수 있습니다.

## 출력 예시

`logs/result.json`은 크게 두 영역으로 구성됩니다.

- `analysis`: 일정 개수, 총 일정 시간, 카테고리 분포, 충돌, 버퍼 부족 등 구조화된 분석 결과
- `briefing`: 페르소나, 요약, 리스크 메시지, 추천 액션 등 사용자에게 보여줄 브리핑 결과

## 향후 개선 방향

- OpenAI API를 연결해 자연어 브리핑 품질 개선
- LangGraph를 활용해 분석, 판단, 추천 단계를 Agent workflow로 구성
- VectorDB를 붙여 사용자 선호도, 과거 브리핑, 회의 메모 검색
- Langfuse로 프롬프트, 실행 단계, 출력 결과 추적
- Google Calendar 또는 Outlook Calendar 연동
- 페르소나 분류와 추천 액션 품질을 평가할 수 있는 테스트 데이터셋 추가
- 브리핑 히스토리와 일정 리스크를 볼 수 있는 UI 확장

## AI/Agent Product Role과의 관련성

이 프로젝트는 AI 기능을 단순히 API 호출로 처리하지 않고, 제품 관점에서 어떤 사용자 신호를 분석해야 하는지, 어떤 판단 로직이 필요한지, 어떤 결과를 사용자에게 전달해야 하는지를 분리해 보여줍니다.

AI/Agent Product Role 관점에서는 다음 역량을 보여줄 수 있습니다.

- 사용자 컨텍스트를 구조화하는 능력
- Agent workflow로 확장 가능한 제품 구조 설계
- 일정 충돌과 버퍼 부족 같은 실질적 리스크 정의
- 페르소나 기반 개인화 로직 설계
- LLM 도입 전 deterministic MVP로 문제를 검증하는 접근
- LangGraph, VectorDB, Langfuse로 확장 가능한 로드맵 제시
