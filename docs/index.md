---
type: Index
title: BMS AI Plugin 문서 루트
description: BMS SW 성능 분석·개선용 AI Plugin 프로젝트의 계획·조사·결정 문서 묶음 (OKF v0.1 형식)
tags: [index, bms, plan, research]
timestamp: 2026-10-15T00:00:00Z
---

# BMS AI Plugin 문서

이 디렉터리는 Google Open Knowledge Format(OKF) v0.1 규칙을 따른다.
각 파일은 개념 하나이고 YAML frontmatter의 `type`이 필수다. 각 디렉터리의 `index.md`가 목차, `log.md`가 변경 이력이다.
나중에 `knowledge/`(제품 지식 위키)를 만들 때 같은 규칙을 쓴다.

## 읽는 순서

1. [계획 개요](/plan/00_overview.md): 결론, 요구사항별 가능성, 일정 요약
2. [요구사항 추적표](/plan/01_requirements_traceability.md): 요구사항 → 설계 → 검증 → 단계 매핑과 수용 기준
3. [아키텍처·데이터 계약](/plan/02_architecture.md): 계층 구조, 표준 로그 스키마, 파라미터 레지스트리, MCP 도구 목록, 위키 스키마
4. [모듈 상세 설계](/plan/03_module_specs.md): 모듈별 입력·출력·알고리즘·수용 기준
5. [로드맵·WBS](/plan/04_roadmap_wbs.md): 주 단위 작업 분해, 마일스톤, 인력, 완료 정의
6. [위험 관리 대장](/plan/05_risk_register.md): 위험 점수, 징후, 대응, 비상 계획
7. [갭 검토](/plan/06_gap_review.md): v0.1 계획의 부족한 점과 보완 내용
8. [추가 기능 제안](/plan/07_additional_features.md): 있으면 좋은 기능과 우선순위
9. [결정 기록](/plan/08_decisions.md): 확정된 결정(ADR)과 질문·답변 현황
10. [파라미터 추론·예측 설계](/plan/09_param_inference.md): AI가 최적화 대상 파라미터를 고르고 효과를 예측하는 방법
11. [SPM 모델 정확도 향상 트랙](/plan/10_model_accuracy_track.md): 현재 최우선 목표. 평가 체계, 구조 오차 분리, 확장 후보, 정확도-연산량 파레토

## 규격

- [SBL v1 표준 로그 형식](/spec/sbl_v1.md) ([규격 목차](/spec/index.md))

## 조사 자료

- [조사 목차](/research/index.md)

## 변경 이력

- [log.md](/log.md)
