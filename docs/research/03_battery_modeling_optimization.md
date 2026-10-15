---
type: Source
title: 배터리 모델링·파라미터 최적화 조사
description: 요구 R4, O1 설계 근거 — PyBaMM, PyBOP, SUNDIALS, BO 라이브러리, 민감도 분석
tags: [research, pybamm, pybop, bayesian-optimization, sensitivity]
timestamp: 2026-10-15T00:00:00Z
---

# 배터리 모델링·파라미터 최적화

## 1. 시뮬레이션

| 항목 | 내용 | 검증 |
|---|---|---|
| PyBaMM | 전기화학 모델(SPM, SPMe, DFN)과 ECM 제공. 라이선스 BSD-3 | 🟡 (메타데이터 기준, LICENSE 직접 확인 필요) |
| IDAKLU 솔버 | SUNDIALS IDA + KLU 희소 직접 솔버. `pybammsolvers` 패키지로 제공 | 🟡 |
| SUNDIALS | BSD-3 (LLNL, SMU) | ✅ 공식 라이선스 페이지 |
| **KLU 주의** | SUNDIALS 문서: KLU 등 서드파티를 링크하면 해당 라이선스를 검토하라. KLU를 정적 링크하면 **LGPL** 조건이 적용됨 | ✅ |
| 결론 | PyBaMM은 선택 extra `[pybamm]`. `pybammsolvers` 휠의 KLU 링크 방식과 라이선스 파일 확인을 P2 착수 작업에 포함 | - |

## 2. 파라미터 추정

| 항목 | 내용 | 검증 |
|---|---|---|
| PyBOP | PyBaMM 모델(전기화학·ECM)의 파라미터화·최적화. 베이지안과 빈도주의 방법 모두 지원. BSD-3 | 🟡 PyPI/GitHub/JOSS |
| PyBOP 샘플러 | 베이지안 추론은 샘플러 클래스, MCMC는 PINTS 제공 | 🟡 JOSS |
| PyBOP 성숙도 | v25.10에서 기반 클래스 대규모 재구성, "API가 바뀔 수 있음" 경고 | 🟡 → 버전 고정, 얇은 어댑터로 감싸기 |
| pybamm-param | 별도 패키지, BSD-3 | 🟡 |
| 입문 자료 | 배터리 시뮬레이터용 베이지안 파라미터 추정·모델 선택 입문 (arXiv 2512.10055), 예제 코드가 PyBOP 사용 | 🟡 |

## 3. 베이지안 최적화

| 항목 | 내용 | 검증 |
|---|---|---|
| BoTorch | MIT. TuRBO, BAxUS 튜토리얼도 MIT | 🟡 |
| Optuna BoTorch sampler | MIT, Optuna 팀 관리, `optuna-integration` 필요 | 🟡 |
| Optuna 본체 | MIT | ⚪ |
| SAASBO | 공식 Ax/BoTorch 구현은 확인 필요. 일부 서드파티 구현은 **라이선스 없음** | 🟡 → 공식 BoTorch 구현만 사용 |
| 고차원 BO | 벤치마크 논문(arXiv 2406.04739, 2505.20685): 고차원에서는 SAASBO, TuRBO, 부분공간 방법 등이 쓰임 | 🟡 |

## 4. 민감도 분석

| 항목 | 내용 | 검증 |
|---|---|---|
| SALib | MIT, 전역 민감도 분석(Sobol, Morris 등) | 🟡 패키지 색인 |
| 자체 구현 | Morris·Saltelli/Sobol 추정기는 수백 줄 수준으로 구현 가능 | ⚪ |

## 5. 설계 결론

1. 단계별 충실도: ECM(자체 구현) → SPM/SPMe → DFN.
2. Morris → Sobol → 식별성 분석 순으로 수백 개를 10~40개로 줄인다.
3. 최적화 기본 엔진은 Optuna(경량), 고급은 BoTorch(선택). 사후분포는 PyBOP 샘플러를 쓴다.
4. 기존 34개 + diffusivity BO 결과를 warm start와 비교 기준으로 쓴다.

## 출처

- https://github.com/pybop-team/PyBOP
- https://pypi.org/project/pybop
- https://joss.theoj.org/papers/10.21105/joss.07874.pdf
- https://arxiv.org/pdf/2512.10055
- https://computing.llnl.gov/projects/sundials/license
- https://www.mintlify.com/pybamm-team/PyBaMM/api/solvers/idaklu
- https://hub.optuna.org/samplers/botorch_sampler/
- https://arxiv.org/pdf/2406.04739
- https://arxiv.org/pdf/2505.20685
- https://depscope.dev/pkg/pypi/SALib
