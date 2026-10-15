---
type: Source
title: 라이선스·의존성 조사
description: 요구 R9 근거 — 후보 라이브러리별 라이선스, 사용 정책, 검증 수준
tags: [research, license, dependencies, sbom]
timestamp: 2026-10-15T00:00:00Z
---

# 라이선스·의존성

## 1. 정책

| 등급 | 라이선스 | 사용 방법 |
|---|---|---|
| 허용 | MIT, BSD-2/3, Apache-2.0, PSF, ISC, Zlib, Unlicense | 자유 사용, NOTICE 고지 |
| 조건부 | LGPL-2.1/3.0, MPL-2.0 | **선택 extras로만**, 수정하지 않고 동적 사용, 수정하면 소스 공개 |
| 금지 | GPL, AGPL (배포물에 포함되는 경우), 라이선스 없음, CC-NC, SSPL | 사용 금지. 별도 프로세스로 실행하는 외부 CLI는 검토 후 허용 |

## 2. 후보 라이브러리

| 라이브러리 | 용도 | 라이선스 | 등급 | 검증 | 결정 |
|---|---|---|---|---|---|
| numpy, scipy | 수치 계산 | BSD-3 | 허용 | ⚪ | 필수 |
| pyyaml | 설정·frontmatter | MIT | 허용 | ⚪ | 필수 |
| jinja2 | 리포트 템플릿 | BSD-3 | 허용 | ⚪ | 필수 |
| tree-sitter (core, CLI) | 코드 파싱 | MIT | 허용 | ✅ 설치 패키지 메타데이터 (0.26.0) | 선택 `[code]` |
| tree-sitter-c | C 문법 | MIT | 허용 | ✅ 설치 패키지 메타데이터 (0.24.2) | 선택 `[code]` |
| libclang | 정밀 전처리 | Apache-2.0 + LLVM 예외 | 허용 | ⚪ | 선택 |
| pyarrow | Parquet | Apache-2.0 | 허용 | ⚪ | 선택 `[parquet]` |
| openpyxl | `.xlsx` 읽기·쓰기 (SBL 엑셀, 기존 엑셀 로그) | MIT | 허용 | ⚪ (이번 검색에서 미확인, PyPI 확인 필요) | 선택 `[excel]` |
| xlrd | 구형 `.xls` 읽기 (2.0부터 `.xlsx` 미지원) | BSD-3 | 허용 | 🟡 | 선택, 필요할 때만 |
| plotly.py | 인터랙티브 그래프 | MIT | 허용 | 🟡 (오래된 Debian 사본 기준, 현재 저장소 확인 필요) | 필수 또는 선택 |
| LTTB (lttb, pylttb) | 다운샘플링 | MIT | 허용 | 🟡 | 자체 구현(약 50줄) |
| matplotlib | 정적 그래프 | PSF 계열 | 허용 | ⚪ | 선택 |
| cantools | DBC 디코딩 | MIT | 허용 | ⚪ (이번 검색에서 미확인) | 선택 `[can]`, 사용 전 확인 |
| **asammdf** | MDF4 읽기 | **LGPL-3.0+** | 조건부 | 🟡 (여러 색인 일치) | 선택 `[mdf]` |
| python-can | BLF/ASC | LGPL-3.0 | 조건부 | ⚪ | 선택 `[can]` |
| **pyA2L** | A2L 파싱 | **LGPL-3.0+** | 조건부 | 🟡 공식 문서 | 미사용 → 자체 부분 파서 |
| **pya2ldb** | A2L 파싱 | **GPL** | 금지 | 🟡 PyPI/libraries.io | 미사용 |
| PyBaMM | 전기화학 모델 | BSD-3 | 허용 | 🟡 | 선택 `[pybamm]` |
| pybammsolvers (IDAKLU) | DAE 솔버 | SUNDIALS BSD-3 + **KLU LGPL** | 조건부 | ✅ SUNDIALS 문서 | 선택, 휠 라이선스 파일 확인 |
| PyBOP | 파라미터 추정 | BSD-3 | 허용 | 🟡 | 선택 `[pybamm]` |
| PINTS | MCMC (PyBOP 의존) | BSD-3 | 허용 | ⚪ | 선택 |
| Optuna | BO/TPE | MIT | 허용 | ⚪ | 선택 `[bo]` 기본 |
| BoTorch | 고급 BO | MIT | 허용 | 🟡 | 선택 `[bo]` |
| PyTorch (BoTorch 의존) | - | BSD-3 | 허용 | ⚪ | 용량이 커서 선택 |
| SALib | 민감도 분석 | MIT | 허용 | 🟡 | 선택 또는 자체 구현 |
| networkx | 그래프 (필요 시) | BSD-3 | 허용 | ⚪ | 기본은 자체 구현 |
| PySide6 | 네이티브 GUI | LGPL-3.0 / GPL / 상용 | 조건부 | 🟡 | 미사용 (ADR-007) |
| NiceGUI | 웹 GUI | MIT | 허용 | 🟡 | 대안 |
| Starlette | 웹 서버 | BSD-3 | 허용 | ⚪ | 선택 `[gui]` |
| ruff, mypy, pytest | 개발 도구 | MIT | 허용 | ⚪ | `[dev]` |
| CMake | C 빌드 | BSD-3 | 허용 | ⚪ | 빌드 도구 |
| cppcheck | 정적 분석 | GPL-3.0 | 외부 CLI만 | ⚪ | 별도 실행만, 번들 금지 |
| SQLite (FTS5) | 검색 | Public Domain | 허용 | ⚪ | Python 표준 라이브러리 |

## 3. 운영 규칙

1. 새 의존성을 추가할 때 이 표에 행을 추가하고 검증 수준을 ✅로 올린 뒤 머지한다.
2. CI의 `tools/license_gate.py`가 `importlib.metadata`로 설치 패키지 라이선스를 모아 정책과 비교한다. 위반이면 실패한다.
3. 릴리스마다 SBOM(CycloneDX JSON)과 THIRD_PARTY_NOTICES를 생성한다.
4. 외부 코드 조각을 복사하지 않는다. 라이선스가 없는 저장소 코드(예: 일부 SAASBO 구현)는 참고만 하고 복사하지 않는다.

## 출처

- https://openapps.pro/packages/xlrd
- https://libraries.io/pypi/asammdf
- https://pypistats.org/packages/asammdf
- https://pya2l.readthedocs.io/en/latest/README.html
- https://pypi.org/project/pya2ldb/
- https://libraries.io/pypi/pya2ldb
- https://depscope.dev/pkg/pypi/SALib
- https://computing.llnl.gov/projects/sundials/license
- https://hub.optuna.org/samplers/botorch_sampler/
- https://pypi.org/project/lttb/
- https://salsa.debian.org/debian/plotly/-/blob/master/LICENSE.txt
- https://en.wikipedia.org/wiki/Tree-sitter_(parser_generator)
- https://pkgs.chimera-linux.org/package/current/main/ppc/tree-sitter-c
- https://www.pythonguis.com/faq/not-an-open-source-application-which-one-to-use-pyqt5-or-pyside2/
- https://courses.pythonguis.com/faq/which-python-gui-library/
