---
type: Log
title: 문서 변경 이력
---

# 변경 이력

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
