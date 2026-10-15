---
type: Log
title: 문서 변경 이력
---

# 변경 이력

## 2026-10-15 — v0.3 (사용자 답변 반영)
- 답변: 사내 gateway API로 코드·로그 전송 가능 / BMS는 C / 로그는 엑셀·txt 시계열(세부 비공개) / 기존 모델은 P2D보다 훨씬 가벼운 경량 모델(SPM 계열 추정) / 34개는 최소 정보, 최적화 대상은 AI가 추론
- 신규 규격: [SBL v1](/spec/sbl_v1.md) 표준 로그 형식 + 참조 구현(`python/bmskit/logs/sbl.py`, `legacy.py`), 예제, 테스트(Python 3.10~3.13 통과)
- 신규 설계: [파라미터 추론·예측](/plan/09_param_inference.md) — 코드 후보 발견 → SIL 잔차 서명 → 민감도 귀속·개선량 예측 → 식별성 → 부분집합 최적화 → 예측 검증. 34개는 블라인드 평가 기준
- ADR-013~017 추가 (gateway, SBL, 사내 C 모델 시뮬레이터, AI 파라미터 추론, SIL 앞당김), 질문 현황 갱신
- 갱신: 00 개요(v0.3), 01 R4 수용 기준, 02 로그 스키마 → SBL·gateway 연결, 03 M2/M5/M13, 04 WBS(P1에 SIL, P2 재구성), 05 위험(K1 하향, K21~K23 추가), 조사 02(gateway)·05(openpyxl, xlrd)

## 2026-10-15 — v0.2
- 문서를 OKF 번들 구조(`docs/plan`, `docs/research`)로 재구성
- `PLAN_feasibility.md`(v0.1)를 `plan/00_overview.md`로 옮기고 v0.2로 갱신
- 추가: 요구사항 추적표, 아키텍처·데이터 계약, 모듈 상세 설계, WBS, 위험 관리 대장, 갭 검토, 추가 기능 제안, 결정 기록
- 조사 자료를 주제별 6개 문서로 기록하고 각 사실의 검증 상태를 표시
- 조사로 새로 반영한 사항
  - OpenCode가 `.claude/skills/`를 공식 지원한다는 것을 문서로 확인
  - OpenCode의 CLAUDE.md 폴백이 제거됐다는 주장이 있음 → AGENTS.md를 단일 소스로 확정
  - pyA2L은 LGPL, pya2ldb는 GPL → A2L은 필요한 부분만 자체 파서로 구현
  - SALib MIT 확인
  - EU 배터리 규정의 SOH 보고 요구(2027-02)를 추가 기능 후보로 반영

## 2026-10-15 — v0.1
- 첫 가능성 분석, 계획, 위험도 분석 (`docs/PLAN_feasibility.md`)
