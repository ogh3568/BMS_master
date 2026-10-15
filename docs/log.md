---
type: Log
title: 문서 변경 이력
---

# 변경 이력

## 2026-10-15 — v0.5 (사용자 지시 반영 + 도구 구현)
- 지시: **새 SPM을 만들지 말고 사용자의 C 코드를 분석·개선할 것.** 작성 중이던 Python SPM은 커밋 전에 삭제(ADR-021)
- 확인: 셀 단계는 모델 전압 대 실측 전압 최소화, 세트 탑재는 여러 환경에서 SOC·SOH·ISD 정확도. C 언어, 사내 빌드 환경과 별개로 연구 지원
- 구현
  - `bmskit.codeintel.cparams`: C 파라미터 후보 추출
  - `bmskit.sil`: `bms_sil_api.h`, `wrapgen`, `runner`
  - `bmskit.optim.infer`: 서명·민감도·예측·식별성·선택·LM·검증 제외
  - `bmskit.metrics.accuracy`: 세트 SOC·SOH·ISD, 환경별
  - 테스트 15개 (Python 3.10, 3.13 통과)
- 문서: [연구 워크플로](/guide/research_workflow.md), [도구 체인 검증 실험](/research/07_experiment_toolchain_check.md), SBL에 ISD·SOH·기준값·환경 이름 추가, ADR-021~023, Q12 답변, Q13 추가, 00·03·09·10 갱신

## 2026-10-15 — v0.4 (사용자 답변 반영)
- 확인: 모델은 **SPM** / 사내에서 Claude를 외부와 똑같이 사용, **외부 MCP만 불가** / FW 저전력 모델은 **연구 단계**, 현재는 모델 정확도 향상 중
- 신규: [SPM 모델 정확도 향상 트랙](/plan/10_model_accuracy_track.md) — 벤치마크·지표 고정, 잔차의 파라미터/구조/잡음 분해, SPM 확장 후보, 정확도-연산량 파레토(FW 저전력 연구 지원)
- ADR-018(외부 MCP 불가 → 로컬 MCP + CLI 이중 제공), ADR-019(정확도 우선, FW·Android 포팅 후순위), ADR-020(잔차 분해) 추가. Q1·Q4 답변 갱신, Q12 추가
- 갱신: 00 개요, 01 R7, 02 MCP 정책, 03 M6·M7·Skills, 04 P3 재구성·MS3, 05 위험(K16 하향, K24·K25 추가), 07 F19, 09 SPM 반영

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
