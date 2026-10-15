---
type: ADR
title: 결정 기록과 미결 질문
description: 확정한 설계 결정(ADR), 사용자가 지정한 작업 규칙, 답을 받아야 할 질문
tags: [plan, adr, decisions, questions]
status: draft
version: 0.2
timestamp: 2026-10-15T00:00:00Z
---

# 결정 기록과 미결 질문

## 1. 작업 규칙 (사용자 지정)

| 날짜 | 규칙 |
|---|---|
| 2026-10-15 | 작업 결과는 지정된 개발 브랜치에 **커밋과 push만** 한다. **PR은 만들지 않는다.** |
| 2026-10-15 | 계획과 조사 내용은 `docs/`에 기록하고 변경 이력은 `docs/log.md`에 남긴다. |

## 2. 설계 결정 (ADR)

| ID | 결정 | 이유 | 대안 | 상태 |
|---|---|---|---|---|
| ADR-001 | LLM은 해석만, 계산은 결정론적 도구가 맡는다 | 환각·비용 감소, 재현성, LLM 없이도 동작 | LLM이 원시 데이터를 직접 분석 | 확정 |
| ADR-002 | 도구 인터페이스는 MCP 서버 하나(`bms-mcp`)로 통일 | Claude Code·OpenCode 모두 MCP 지원, 중복 구현 방지 | 에이전트별 별도 도구 | 확정 |
| ADR-003 | 에이전트 지침 원본은 AGENTS.md | OpenCode는 AGENTS.md가 우선이고 CLAUDE.md 폴백 제거 보고가 있음. Claude는 import로 해결 | CLAUDE.md 원본 | 확정 |
| ADR-004 | Skills는 `.claude/skills/`에 둔다 | OpenCode 공식 문서가 이 경로를 지원함을 확인 | `.agents/skills/` (Claude Code 인식이 불확실) | 확정 |
| ADR-005 | 지식 형식은 OKF v0.1 + 선택 확장 필드 | 공개 스펙, 마크다운, 벤더 중립, 필수 필드 최소 | 독자 형식, DB 기반 위키 | 확정 |
| ADR-006 | 검색은 SQLite FTS5 기본, 임베딩은 선택 | 표준 라이브러리만으로 동작, 외부 의존 최소 | 벡터 DB | 확정 |
| ADR-007 | GUI는 로컬 웹 UI (빌드 없는 정적 JS + Plotly) | 설치 최소, 리포트와 렌더링 공유, MIT | PySide6(LGPL), NiceGUI | 잠정 (사용성 테스트 후 확정) |
| ADR-008 | LGPL 의존성(asammdf, python-can, PySide6)은 선택 extras로만 | 라이선스 위험 격리 | 필수 포함 | 확정 |
| ADR-009 | A2L은 자체 부분 파서 | pyA2L LGPL, pya2ldb GPL | 외부 파서 | 확정 |
| ADR-010 | 최적화 엔진 기본은 Optuna, 고급은 BoTorch 선택 | torch 의존성 회피, 둘 다 MIT | BoTorch 기본 | 잠정 (기존 BO 환경 확인 후) |
| ADR-011 | C 코어는 C99, 동적 할당 없음, HAL 분리 | 모든 변종(FW 포함)에 공통 적용 가능 | C++ | 잠정 (기존 코드 언어 확인 후) |
| ADR-012 | 이 `docs/`도 OKF 형식으로 쓴다 | 제품 위키와 같은 도구로 검색·lint 가능 (자기 적용) | 일반 마크다운 | 확정 |

## 3. 미결 질문

| ID | 질문 | 영향 범위 | 긴급도 |
|---|---|---|---|
| Q1 | 사내 코드·로그를 외부 LLM(Claude)에 보낼 수 있나? 기업 계약·데이터 보존 조건은? 사내 모델 서버가 있나? | 전체 (M13, 기본 프로파일) | **최우선** |
| Q2 | BMS 코드 언어(C/C++), MCU·RTOS, 빌드 시스템, 규모(LOC), AUTOSAR 여부, A2L 유무 | M1, M6 | 높음 |
| Q3 | 로그 포맷(CSV/MDF4/BLF/자체), 채널 목록, 샘플링, 기준값(충방전기·실험실) 유무, 데이터 양 | M2 | 높음 |
| Q4 | 기존 34개 + diffusivity BO: 모델(ECM/SPM/DFN, PyBaMM 여부), 파라미터 목록, 목적함수, 실험 프로파일, 실행 시간 | M5 | 높음 |
| Q5 | 셀 화학과 형태(NCM/LFP, 파우치/각형/원통), 적용 분야(EV/ESS/모바일) | M2, M7, M11 | 중간 |
| Q6 | 배포 대상: OS(Windows/Linux), Android 버전, 대상 FW 플랫폼, 사내 패키지 저장소 | M6, M10 | 중간 |
| Q7 | 신규 기능 우선순위와 검증 데이터 (스웰링 두께·압력 센서, ISC 실험 가능 여부) | M7 | 중간 |
| Q8 | 사용자층: 엔지니어 수, 비개발자 비율, 선호 언어(한국어 UI) | M9 | 낮음 |
| Q9 | 기능안전 등급(ASIL), 개발 프로세스(ASPICE 등) 요구 산출물 | 전체 산출물 형식 | 중간 |
| Q10 | 계산 자원: 최적화용 사내 서버·클러스터 사용 가능 여부 | M5 | 중간 |
