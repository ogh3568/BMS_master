# BMS AI Plugin — 가능성 분석 · 구현 계획 · 위험도 분석

> 작성일: 2026-10-15 · 상태: Draft v0.1 · 대상 저장소: `BMS_master` (현재 README만 있는 빈 저장소)

---

## 0. 결론 요약

| 구분 | 판단 |
|---|---|
| 전체 가능성 | **가능 (조건부)**. 필수 12개 항목 모두 현재 공개 기술과 허용적(permissive) 라이선스 오픈소스로 구현 가능 |
| 핵심 조건 | ① 사내 소스코드/로그를 클라우드 LLM에 보내도 되는지에 대한 **보안 승인** ② 기존 BMS 코드·로그·34개 파라미터 BO 환경 **접근 권한** ③ AI 생성 코드는 **사람 검토 + SIL 동등성 테스트**를 통과해야만 양산 코드로 이동 |
| 가장 큰 위험 | 데이터 보안(사내 코드 외부 전송), LLM 환각에 의한 잘못된 분석, 수백 개 파라미터의 비식별성(identifiability)으로 인한 과적합, 라이선스 오염(LGPL/GPL) |
| 설계 핵심 원칙 | **"계산은 결정론적 Python/C 도구, 판단·해석은 LLM"** — LLM은 원시 데이터를 직접 보지 않고, 도구가 만든 구조화된 요약·지표만 보고 추론한다. 모든 도구는 **MCP 서버 하나**로 노출해 Claude Code와 OpenCode가 같은 기능을 공유한다 |
| 권장 일정 | 2~3명 기준 약 6개월(MVP 8주 + 확장 4개월) |

---

## 1. 요구사항별 가능성 분석

등급: **A** 바로 가능 / **B** 가능하나 설계·검증 비용 큼 / **C** 연구 성격, 결과 품질 불확실

| # | 요구사항 | 등급 | 핵심 접근 | 주요 위험 |
|---|---|---|---|---|
| 1 | 소스코드 분석 → 파라미터·모듈 성능 분석/개선 | **A/B** | tree-sitter-c로 심볼·콜그래프·파라미터 추출 → 지식 그래프화, + **SIL(Software-in-the-Loop) 재생 하네스**로 실제 성능(오차·연산량) 측정 | 매크로/조건부 컴파일이 많은 코드는 정적 분석 정확도 하락 → libclang 보조 |
| 2 | 시계열 로그 기반 분석·개선점 도출 | **A** | 로그 → 표준 스키마(Parquet) → 결정론적 지표 계산(SOC 오차, 셀 편차, 밸런싱, 센서 오프셋, 상태천이, 고장 플래그) → LLM이 요약을 해석 | 로그 포맷 다양성, 기준값(reference) 부재 |
| 3 | 신규 기능 개발(스웰링, RUL, 만충 예상시간 등) | **B** | "스펙 → Python 기준모델 → 로그 검증 → C(고정소수점) 생성 → SIL 동등성 테스트" 파이프라인 | 스웰링은 두께/압력 센서 없으면 검증 불가(모델 추정만 가능) |
| 4 | 수백 파라미터 중 핵심 선별 + 최적화 | **B** | 민감도 스크리닝(Morris→Sobol) → 식별성 분석 → 부분집합 BO(BoTorch/Optuna) + 다중 충실도(SPM→SPMe→DFN) | 파라미터 상관/비식별성, DFN 계산비용 |
| 5 | 로그 렌더링·리포트·편의기능 | **A** | Plotly(오프라인 HTML) + LTTB 다운샘플링, Jinja2 리포트 템플릿 | 대용량(수억 샘플) 렌더링 성능 |
| 6 | LLM Wiki + Google OKF (계층화·캐시·HOTSPOT·지식그래프) | **A/B** | OKF v0.1 번들(마크다운+YAML) + 계층 index.md + SQLite FTS5 검색 + 링크 기반 그래프 + 핫스팟 점수 | OKF가 v0.1(초기 스펙) → 변경 가능성, 위키 노후화 |
| 7 | 코어 알고리즘 도메인별 특화 버전 | **B** | C99 코어 + HAL 추상화 + CMake 빌드 매트릭스(x86 .so/.dll, Android NDK/AAR, FW 저전력 프로파일) | 변종 간 수치 동등성 유지, 고정소수점 오차 |
| 8 | 기존 코드 완벽 분석 → Wiki 협업 | **B** | 코드 분석 결과를 OKF 개념 페이지로 자동 생성, git 해시 연동, 코드 변경 시 drift 감지 | "완벽"은 불가능 — 커버리지 지표로 관리해야 함 |
| 9 | 사내배포, 외부의존 최소화, 라이선스 준수 | **A** | 허용 라이선스 화이트리스트, 오프라인 wheelhouse, SBOM 자동 생성 | LGPL 의존성(asammdf, PySide6, KLU) 혼입 |
| 10 | Python 3.10+ | **A** | `requires-python = ">=3.10"`, CI 3.10~3.13 매트릭스 | 없음 |
| 11 | Claude 기본 + OpenCode 호환 | **A/B** | AGENTS.md 단일 소스, `.claude/skills/`(OpenCode도 인식), MCP 서버로 도구 공유 | 비-Claude 모델 사용 시 툴 사용 품질 저하 |
| 12 | 직관적 GUI 컨트롤 | **A** | 로컬 웹 UI(Python 내장 서버 + 정적 JS) 권장, GUI에서 `claude -p` / `opencode run` 헤드리스 호출 | GUI 범위 확장(scope creep) |
| O1 | 파라미터 → 가상 V/I/T 생성 | **A** | ECM/PyBaMM 시뮬레이션 + 주행/충전 프로파일 + 센서 노이즈 모델 | 실제 셀과의 괴리 |
| O2 | ISD·SOH 열화/고장 특화 V/I/T 생성 | **B** | ISC 병렬저항 모델, 용량감소·저항증가, 리튬 플레이팅, 센서 고장, 접촉저항 주입 | 실측 ISC 공개 데이터 거의 없음 → 시뮬레이션 의존 |
| O3 | AI 추론 성능 최대 활용 | **A** | 가설→도구 검증 루프, 확장 사고(extended thinking), 다중 에이전트 교차검토 | 비용·지연 |

---

## 2. 전체 아키텍처

```
┌──────────────────────────────────────────────────────────────────────┐
│  사용자 인터페이스                                                     │
│   (a) GUI (로컬 웹 UI)   (b) Claude Code   (c) OpenCode   (d) CLI     │
└───────────────┬──────────────────┬───────────────────┬───────────────┘
                │ HTTP              │ Skills/Commands    │ 명령행
┌───────────────▼──────────────────▼───────────────────▼───────────────┐
│  Agent 계층 (모델 비종속)                                              │
│   AGENTS.md(단일 지침) · Skills(분석 절차서) · Subagents(역할)          │
│   └─ MCP 서버 `bms-mcp` (stdio)  ← Claude/OpenCode 공용 도구 인터페이스 │
└───────────────┬──────────────────────────────────────────────────────┘
                │ Python API 호출 (결정론적)
┌───────────────▼──────────────────────────────────────────────────────┐
│  Core 엔진 `bmskit` (Python 3.10+)                                     │
│   codeintel  │ logs  │ metrics │ models(ECM/PyBaMM) │ optim │ synth   │
│   features(swelling/RUL/TTF) │ report │ sil(C 코어 재생) │ license     │
└───────────────┬──────────────────────────────────────────────────────┘
                │
┌───────────────▼───────────────────┐   ┌──────────────────────────────┐
│ Knowledge 계층 (OKF 번들)          │   │ C 코어 `bmscore` (C99)        │
│  L0 hot cache / L1 index / L2 개념 │   │  x86 .so · Android AAR ·       │
│  L3 원천 · graph.json · FTS5 DB    │   │  FW 저전력 · Python ctypes     │
└───────────────────────────────────┘   └──────────────────────────────┘
```

**원칙**
1. LLM은 수백만 행의 로그나 수만 줄 코드를 직접 읽지 않는다. 도구가 만든 **요약·지표·그래프 조각**만 컨텍스트에 넣는다(비용·환각 동시 감소).
2. 모든 수치 결론은 **재현 가능한 도구 호출 결과**를 근거(citation)로 가져야 한다. 리포트에 "근거: tool=metrics.soc_error, log=xxx, hash=..."를 남긴다.
3. 같은 기능을 GUI·Claude·OpenCode·CLI가 공유하도록 **Core → MCP → Agent** 단방향 의존.

---

## 3. 기능별 상세 설계

### 3.1 소스코드 분석 (요구 1, 8)

**파이프라인**
1. **파싱**: tree-sitter + tree-sitter-c (MIT) → 함수, 전역변수, 구조체, `#define`, `const` 캘리브레이션 테이블, 상태머신(switch/enum) 추출.
   - 매크로/조건부 컴파일이 많으면 libclang(Apache-2.0 with LLVM exception)으로 전처리 후 재분석(옵션).
   - A2L/캘리브레이션 파일이 있으면 파라미터 사전으로 병합.
2. **파라미터 사전(Parameter Registry)**: 이름, 단위, 타입(Q-format 포함), 기본값, 범위, 정의 위치, 사용 모듈, 사용 함수 → `params.yaml` + OKF 개념 페이지.
3. **그래프화**: 호출 그래프, 파라미터→함수→신호 데이터 흐름, 모듈 의존성, 태스크 주기(OS 설정에서 추출).
4. **정적 지표**: 순환 복잡도, 함수 길이, 전역 상태 결합도, 고정소수점 오버플로/정밀도 위험 패턴, 나눗셈/분기 핫패스, 스택 사용 추정.
5. **동적 성능(SIL)**: 대상 알고리즘(SOC/SOH/밸런싱 등)을 x86으로 빌드 → 실제 로그를 입력으로 재생 → 기준값 대비 오차·수렴시간·연산량 측정. *정적 분석만으로는 "성능"을 말할 수 없으므로 이 단계가 핵심.*
6. **개선 제안**: LLM이 (지표 + 그래프 조각 + SIL 결과)로 개선안 작성 → 패치 생성 → SIL 회귀테스트로 자동 검증 → 사람 리뷰.

**산출물**: 모듈별 OKF 페이지(`wiki/code/modules/*.md`), 파라미터 페이지, 핫스팟 리포트, 개선 제안서.

### 3.2 시계열 로그 분석 (요구 2)

| 단계 | 내용 |
|---|---|
| 수집 | CSV/TSV(내장), Parquet(pyarrow, Apache-2.0), CAN DBC 디코딩(cantools, MIT), MDF4(asammdf **LGPL** → 선택 의존성으로 격리), BLF/ASC(python-can, LGPL → 선택) |
| 정규화 | 표준 스키마: `time, pack_v, pack_i, cell_v[n], cell_t[m], soc_bms, soh_bms, flags, state` + 메타데이터(셀 사양, 샘플링, 펌웨어 버전) |
| 지표 | SOC 오차(쿨롱카운팅 재계산/휴지 OCV 기준), 셀 전압 편차·추세, 밸런싱 효과, 전류센서 오프셋/게인, 온도 구배, 상태천이 타임라인, 보호 동작(OV/UV/OC/OT) 마진, 이벤트(급변·결측·포화) 탐지 |
| 해석 | LLM에는 지표 표 + 이벤트 목록 + 다운샘플 그래프만 제공 → 원인 가설 → 필요 시 도구 재호출로 검증 |
| 출력 | 개선점 목록(심각도·근거·관련 코드 위치·관련 파라미터) — 3.1의 그래프와 연결해 "로그 현상 → 코드 위치 → 파라미터"까지 추적 |

### 3.3 신규 기능 개발 (요구 3)

공통 파이프라인: **요구 스펙 → 문헌/위키 조사 → Python 기준 모델 → 로그/합성데이터 검증 → C(고정소수점) 구현 → SIL 동등성 테스트 → 위키 등록**

| 기능 | 기준 접근 | 필요 입력 | 비고 |
|---|---|---|---|
| 스웰링 추정 | 가역 성분(SOC 의존 흑연 삽입 팽창 + 열팽창) + 비가역 성분(SEI 성장·가스 발생, 사이클/캘린더 함수). Oh et al.(2016) 현상학적 모델, 가스 팽창 기계모델 참고 | V, I, T, (가능하면 두께/압력 센서) | 센서 없으면 "추정치 + 불확도"로 제공, 검증 데이터 확보가 관건 |
| 예상 유효 수명(RUL) | 용량감소 경험모델(√t 캘린더 + 사이클 항) + 파티클필터/칼만필터, 또는 GP 회귀 | SOH 이력, 온도·SOC 체류 히스토그램 | 불확도 구간 필수 |
| 예상 만충 시간(TTF) | ECM + 충전기 CC-CV/다단 프로파일 + 온도 디레이팅 + 밸런싱 시간 반영 시뮬레이션, MCU용은 룩업테이블 근사 | SOC, T, 충전 정책, 셀 저항 | MCU 부하 고려해 오프라인 테이블화 |
| ISD/ISC 감지 | 셀간 평균차 모델(mean-difference) + RLS, 휴지 시 자가방전율 비교, pseudo-OCV 차분 | 셀 전압, 전류 | 오탐/미탐 트레이드오프 |

### 3.4 파라미터 선별 및 최적화 (요구 4)

기존: 34개 + diffusivity를 베이지안 최적화. 확장 목표: 수백 개 후보 중 "최적화가 필요한" 부분집합을 자동 도출.

```
[1] 파라미터 사전(수백 개) + 범위/사전분포
      ↓
[2] 스크리닝: Morris(elementary effects) — 저비용, 수천 회 시뮬레이션
      ↓  상위 30~60개
[3] 정량 민감도: Sobol 1차/총효과 지수 (SPM/ECM 등 저충실도 모델에서)
      ↓
[4] 식별성 분석: Fisher 정보행렬 / 프로파일 우도 / 파라미터 상관 → 동시 식별 불가 묶음 고정 또는 재파라미터화
      ↓  최종 10~40개
[5] 최적화: 다중 충실도 BO (SPM → SPMe → DFN), 고차원은 SAASBO/TuRBO,
           기존 34개 결과를 warm-start
      ↓
[6] 검증: 미사용 프로파일(다른 C-rate·온도·SOC 구간) 교차검증, 불확도(사후분포/부트스트랩)
      ↓
[7] 결과 → 파라미터 페이지/위키 등록, 변경 이력(log.md)
```

| 구성 | 후보 | 라이선스 |
|---|---|---|
| 전기화학 모델 | PyBaMM | BSD-3 |
| 파라미터 추정 프레임워크 | PyBOP (베이지안/빈도주의, PyBaMM 연동) | BSD-3 |
| BO 엔진 | BoTorch(SAASBO, TuRBO) / Optuna(TPE·GP, 경량) | MIT / MIT |
| 민감도 분석 | SALib 또는 자체 구현(Morris/Saltelli는 수백 줄 수준) | MIT(확인 필요) |
| ODE/DAE | SUNDIALS(BSD-3) — 단 IDAKLU의 **KLU는 LGPL** → 정적 링크 배포 시 주의 |

**경량 옵션**: torch(대용량) 설치가 부담이면 Optuna GP/TPE만으로 1차 구현 후 BoTorch는 선택 의존성으로.

### 3.5 렌더링·리포트 (요구 5)

- 인터랙티브: Plotly(MIT) 오프라인 단일 HTML(인터넷 불필요), LTTB 다운샘플링으로 수억 샘플 대응, 다중 축(셀 전압 heatmap, 온도, 상태 타임라인 동기 줌).
- 정적: matplotlib(PSF 계열) PNG/SVG.
- 리포트: Jinja2(BSD) 템플릿 → HTML → 브라우저 인쇄 PDF. 템플릿: 로그 진단, 파라미터 최적화, 코드 리뷰, 신규 기능 검증.
- 모든 리포트에 재현 정보(입력 해시, 도구 버전, 실행 명령) 자동 첨부.

### 3.6 지식 관리: LLM Wiki + Google OKF (요구 6, 8)

**포맷**: Google OKF v0.1 — 디렉터리=번들, 파일 1개=개념 1개, YAML frontmatter 필수 필드는 `type`뿐, `index.md`(점진적 공개), `log.md`(변경 이력), 개념 간 링크는 표준 마크다운 링크. Karpathy LLM Wiki 패턴(raw/ → wiki/ → 스키마, ingest/query/lint 연산)을 OKF 형식으로 운영.

```
knowledge/
├── index.md                    # L1 루트 목차
├── _hot.md                     # L0 핫 캐시: 상위 핫스팟 개념 요약 (항상 컨텍스트에 로드)
├── code/      modules/ functions/ params/     # 코드 분석 자동 생성
├── algorithms/ soc/ soh/ balancing/ isd/ swelling/ rul/ ttf/
├── cells/     # 셀 사양·파라미터 세트
├── experiments/ # BO 실행·로그 분석 결과
├── knowhow/   # 사람 노하우(트러블슈팅, 설계결정 ADR)
├── raw/       # L3 원천(논문 요약, 데이터시트) — 불변
└── .cache/    graph.json, fts.sqlite, embeddings(옵션)
```

| 요구 | 구현 |
|---|---|
| 계층화 | L0 `_hot.md`(≤2k 토큰) → L1 `index.md` → L2 개념 페이지 → L3 원천. 에이전트는 위에서부터 필요한 만큼만 내려감 |
| 캐시 | ① 내용 해시 기반 요약 캐시(바뀐 페이지만 재요약) ② SQLite FTS5 전문검색(Python 내장 sqlite3) ③ 안정적 L0/L1을 프롬프트 앞부분에 고정해 LLM 프롬프트 캐싱 효과 극대화 |
| HOTSPOT | 점수 = w1·조회빈도 + w2·코드 churn(git log) + w3·버그/이슈 연관도 + w4·로그 이상 연관도 + w5·그래프 중심성. 주기적으로 `_hot.md` 재생성 |
| 지식 그래프 | frontmatter 확장 필드(`relations: [{type: uses_param, target: ...}]`) + 본문 링크 → `graph.json`; 표준 라이브러리만으로 구축, 시각화는 OKF 레퍼런스 정적 HTML 뷰어 또는 자체 뷰어 |
| 코드 연동 | 페이지에 `source: path#Lxx@githash`; 코드 변경 시 hook/CI가 drift 감지 → "재검토 필요" 태그 |
| 품질 | `lint`: 깨진 링크, 고아 페이지, 오래된 페이지, 근거 없는 주장, 중복 개념 탐지 |

### 3.7 도메인 특화 버전 (요구 7)

```
bmscore/  (C99, 동적할당 없음, 플랫폼 독립)
├── include/bms_*.h     # 공개 API (SOC/SOH/ISD/TTF ...)
├── src/                # 알고리즘 (float/fixed 이중 구현, 매크로로 선택)
├── hal/                # 시간·로그·NVM 추상화
└── ports/
    ├── x86/            # .so/.dll + Python ctypes 바인딩(표준 라이브러리, 추가 의존 0)
    ├── android/        # NDK + JNI → AAR
    ├── fw_lowpower/    # 고정소수점, 실행 주기 감소, 이벤트 기반 갱신, 상태 축약
    └── wasm/ (옵션)    # GUI 내 시뮬레이션
```

- **기준(golden)**: Python 기준모델 ↔ C float ↔ C fixed 간 동등성 테스트(허용오차 명시)를 CI에 상시 실행.
- 빌드: CMake(BSD-3). 프로파일별 설정은 헤더 하나(`bms_profile_*.h`)로.
- LLM 역할: 포팅 초안·고정소수점 변환 제안·코드리뷰. **최종 판정은 동등성 테스트와 사람 리뷰**.

### 3.8 라이선스·의존성 정책 (요구 9, 10)

| 등급 | 라이선스 | 정책 |
|---|---|---|
| 허용 | MIT, BSD-2/3, Apache-2.0, PSF, ISC, Zlib, Unlicense | 자유 사용, NOTICE 고지 |
| 조건부 | LGPL(asammdf, python-can, PySide6, KLU), MPL-2.0 | **선택 의존성(extras)으로 격리**, 동적 링크/별도 설치만, 수정 시 소스 공개 |
| 금지 | GPL/AGPL(배포물 포함 시), 라이선스 없음, CC-NC, SSPL | 사용 금지(외부 도구로 별도 실행하는 것은 검토 후 허용 — 예: cppcheck CLI) |

- 코어 필수 의존성 목표: **numpy, scipy, pyarrow(선택), jinja2, pyyaml, tree-sitter** 수준으로 최소화.
- 오프라인 wheelhouse + 내부 PyPI 미러로 사내 배포. SBOM(CycloneDX 형식) 자동 생성 스크립트, CI에서 금지 라이선스 탐지 시 실패.
- `pyproject.toml`: `requires-python = ">=3.10"`, extras: `[mdf]`, `[pybamm]`, `[bo]`, `[gui]`.

### 3.9 Claude + OpenCode 호환 (요구 11)

| 요소 | Claude Code | OpenCode | 전략 |
|---|---|---|---|
| 지침 | `CLAUDE.md` | `AGENTS.md`(CLAUDE.md 폴백 지원) | **AGENTS.md 단일 소스**, CLAUDE.md는 `@AGENTS.md` import 한 줄 |
| Skills | `.claude/skills/<name>/SKILL.md` | `.opencode/skill/` 및 `.claude/skills/` 인식(커뮤니티 문서 기준, 공식 확인 필요) | `.claude/skills/`에 두고 OpenCode 인식 검증 |
| 도구 | MCP(`.mcp.json`) | MCP(`opencode.json`의 `mcp`) | **동일 MCP 서버 `bms-mcp`** 공유, 설정 파일만 2개 |
| 명령/에이전트 | `.claude/commands`, `.claude/agents` | `.opencode/command`, `.opencode/agent` | 원본 1벌 + 변환 스크립트로 양쪽 생성 |
| 헤드리스 | `claude -p` | `opencode run` | GUI가 둘 중 선택 호출 |

- 플러그인 배포: Claude Code 플러그인(marketplace 형식, 사내 git) + OpenCode용 동일 디렉터리 구조.
- 모델 비종속을 위해 Skill 문서에는 Claude 전용 문법 대신 "도구 이름 + 절차"만 기술. 비-Claude/로컬 모델은 툴 호출 품질이 낮을 수 있으므로 **도구를 굵게(coarse) 설계**(예: `analyze_log(path)` 한 번에 전체 지표).

### 3.10 GUI (요구 12)

| 옵션 | 장점 | 단점 | 라이선스 |
|---|---|---|---|
| **A. 로컬 웹 UI (권장)**: Python 내장 http.server/소형 프레임워크 + 정적 HTML/JS + Plotly | 설치 최소, 브라우저만 있으면 됨, 리포트와 같은 렌더링 재사용 | 네이티브 느낌 약함 | MIT |
| B. NiceGUI | 빠른 개발, Python만으로 UI | 의존성 증가(FastAPI 등) | MIT |
| C. PySide6 | 네이티브 데스크톱 | LGPL, 배포 크기 큼 | LGPL |

**화면 구성(초안)**: ① 대시보드(최근 작업·핫스팟) ② 로그 뷰어(드래그&드롭, 동기 줌, 이벤트 마커) ③ 코드 탐색(모듈 그래프·파라미터 검색) ④ 파라미터 최적화(파라미터 선택 체크박스, 범위 슬라이더, 진행 그래프, 중단/재개) ⑤ 합성데이터 생성기(셀 선택 → 프로파일 → 고장 주입) ⑥ 위키 브라우저(그래프 뷰) ⑦ AI 패널(자연어 지시 → 에이전트 실행 로그 스트리밍, 결과 승인 버튼).

### 3.11 옵션 기능

- **O1 가상 V/I/T 생성**: 파라미터 세트 → ECM(경량) 또는 PyBaMM(정밀) → 프로파일(CC-CV, 펄스, HPPC, WLTP 등 표준 주행 프로파일, 사용자 정의) → 센서 모델(오프셋·게인·양자화·지연·노이즈·결측) 적용 → 표준 스키마로 출력.
- **O2 고장/열화 특화**: ISC(셀에 병렬 저항, 저항값 스윕), SOH(용량↓·R↑·OCV 곡선 이동), 리튬 플레이팅, 셀 불균형, 접촉저항 증가, 센서 고장(고착·드리프트), 열 이상. **라벨이 포함된 데이터셋**으로 생성해 감지 알고리즘 평가(ROC, 감지 지연) 자동화.
- **O3 AI 추론 극대화**: 가설-검증 루프(가설 → 도구로 반증 시도 → 결론), 복잡 분석에 확장 사고 사용, 독립 서브에이전트 2개로 교차 검토 후 불일치만 사람에게 보고, 지식 위키에 결론 축적(재사용으로 비용 감소).

---

## 4. 저장소 구조(제안)

```
BMS_master/
├── AGENTS.md / CLAUDE.md
├── .claude/ skills/ commands/ agents/        # Claude Code (+OpenCode 인식)
├── .opencode/ command/ agent/                # 변환 스크립트로 생성
├── .mcp.json / opencode.json
├── plugin/                                   # 사내 배포용 플러그인 패키징
├── python/bmskit/
│   ├── codeintel/  logs/  metrics/  models/  optim/  synth/
│   ├── features/ (swelling, rul, ttf, isd)
│   ├── report/  sil/  knowledge/  license/
│   └── mcp_server/
├── bmscore/ (C99 코어 + ports)
├── gui/ (정적 웹 자산 + 서버)
├── knowledge/ (OKF 번들)
├── tests/ (단위·동등성·회귀·골든 로그)
└── docs/
```

---

## 5. 단계별 로드맵 (2~3명 기준)

| 단계 | 기간 | 산출물 | 완료 기준 |
|---|---|---|---|
| **P0 기반** | 2주 | 저장소 골격, pyproject, CI(3.10~3.13), 라이선스 게이트, AGENTS.md, MCP 서버 뼈대, OKF 번들 골격 | Claude/OpenCode 양쪽에서 `bms-mcp` 도구 호출 성공 |
| **P1 분석 MVP** | 6주 | 코드 파서·파라미터 사전·콜그래프, 로그 수집·지표·Plotly 뷰, 리포트 v1, 코드→위키 자동 생성 | 실제 BMS 코드 1개 버전 + 로그 10건으로 진단 리포트 생성, 엔지니어 검토 정확도 ≥80% |
| **P2 최적화** | 6주 | 민감도 스크리닝, 식별성 분석, 다중 충실도 BO, 기존 34개 BO와 결과 비교 | 기존 대비 검증 RMSE 동등 이상, 선별 근거 리포트 |
| **P3 SIL·특화버전** | 6주 | `bmscore` 추출, x86/Python 바인딩, 로그 재생 하네스, 동등성 테스트, Android/FW 포트 | 3개 변종 동등성 테스트 통과 |
| **P4 신규기능·합성데이터** | 6주 | TTF → RUL → 스웰링 순 개발, 가상 V/I/T·고장 주입 | 기능별 검증 리포트, 감지 알고리즘 ROC |
| **P5 GUI·운영** | 4주(병행 가능) | 웹 GUI 7개 화면, 핫스팟·lint 자동화, 사내 배포 패키지 | 비개발자 사용성 테스트 통과 |

※ 우선순위: 1·2·5·6·11(P0~P1)이 다른 모든 기능의 토대. 4(최적화)는 기존 자산이 있으므로 P2에서 빠르게 가치 입증 가능.

---

## 6. 위험도 분석

확률(P)·영향(I): 상/중/하

| # | 위험 | P | I | 대응 |
|---|---|---|---|---|
| R1 | **사내 소스코드·로그의 외부 LLM 전송 보안 이슈** | 상 | 상 | 착수 전 보안팀 승인. 기업 계약(데이터 비학습·보존 정책) 확인. 민감 데이터 마스킹 레이어. 대안으로 OpenCode + 사내 호스팅 모델 경로 확보 |
| R2 | LLM 환각으로 잘못된 원인 분석·개선안 | 상 | 상 | 모든 수치 주장에 도구 근거 필수, 가설-검증 루프, 교차검토, 리포트에 "AI 생성/검증 상태" 표시 |
| R3 | AI 생성 코드의 양산 BMS 반영(기능안전 ISO 26262 등) | 중 | 상 | 플러그인 산출물은 "제안"으로 한정, 기존 V&V·코드리뷰·MISRA 검사 절차를 우회 금지, SIL 동등성 테스트 필수 |
| R4 | 수백 파라미터 비식별성·과적합 | 상 | 중 | 민감도+식별성 분석으로 축소, 교차검증 프로파일 분리, 사후분포·불확도 보고 |
| R5 | DFN 기반 BO 계산비용 과다 | 중 | 중 | 다중 충실도, 병렬 실행, 대리모델, 사내 서버/클러스터 실행 |
| R6 | 라이선스 오염(LGPL/GPL, 무라이선스 코드) | 중 | 상 | 화이트리스트·CI 게이트·SBOM, LGPL은 선택 의존성 격리, 무라이선스(SAASBO 일부 구현 등) 코드 복사 금지 |
| R7 | 대형 코드베이스로 컨텍스트 한계 | 상 | 중 | 계층형 위키·그래프 조각 검색, 서브에이전트 분할 분석, 요약 캐시 |
| R8 | 매크로·조건부 컴파일·벤더 코드로 정적분석 정확도 저하 | 중 | 중 | 빌드 설정 기반 전처리(libclang), 커버리지 지표 공개 |
| R9 | OKF v0.1 스펙 변경 | 중 | 하 | 필수 필드 최소 사용, 변환기 계층 분리 |
| R10 | OpenCode 호환 동작 차이(경로·포맷 변경) | 중 | 중 | MCP를 주 인터페이스로, 양쪽 스모크 테스트 CI |
| R11 | ISC·스웰링 실측 검증 데이터 부족 | 상 | 중 | 외부저항 모사 실험 요청, 시뮬레이션 데이터는 "검증 수준" 명시 |
| R12 | 로그 포맷/품질 다양성(결측·시간정렬 오류) | 상 | 중 | 수집 단계 품질검사·보고, 어댑터 플러그인 구조 |
| R13 | 위키 노후화(코드와 불일치) | 중 | 중 | git 해시 연동 drift 감지, 주기적 lint, 소유자 지정 |
| R14 | 범위 확대(12+3 요구 동시 추진) | 상 | 중 | 단계별 완료 기준, MVP 우선, 옵션 기능은 P4 이후 |
| R15 | LLM 사용 비용·지연 | 중 | 하 | 결정론적 전처리, 캐시, 작업별 모델 등급 분리 |
| R16 | 고정소수점 변종 수치 오차 | 중 | 중 | 오차 예산 정의, 동등성 테스트, 포화/오버플로 정적 점검 |

**종합 위험도: 중** — 기술적 불가능 요소는 없으나 R1(보안)·R2(환각)·R3(기능안전)은 착수 조건으로 관리해야 함.

---

## 7. 착수 전 확인 필요 사항

1. BMS 소스코드: 언어(C/C++), MCU/RTOS, 빌드 시스템, 코드 규모(LOC), 캘리브레이션 파일(A2L 등) 유무
2. 로그: 포맷(CSV/MDF4/BLF/자체), 채널 목록, 샘플링 주기, 기준값(충방전기·실험 데이터) 유무, 용량
3. 기존 BO: 사용 모델(ECM/SPM/DFN, PyBaMM 여부), 34개 파라미터 목록, 목적함수, 실행 환경·소요 시간
4. 보안 정책: 클라우드 LLM 사용 허용 범위, 사내 모델 서버 유무
5. 배포 대상: OS(Windows/Linux), Android 버전, 대상 FW 플랫폼, 사내 패키지 저장소
6. 신규 기능 우선순위와 검증 데이터(특히 스웰링 두께/압력 센서 유무)

---

## 8. 참고 자료

- Google OKF 발표: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
- OKF 스펙 저장소: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
- OKF와 LLM Wiki 관계 해설: https://themenonlab.blog/blog/google-okf-open-knowledge-format-karpathy-llm-wiki-standard
- Karpathy LLM Wiki 정리: https://blog.starmorph.com/blog/karpathy-llm-wiki-knowledge-base-guide
- PyBOP (BSD-3): https://github.com/pybop-team/PyBOP , JOSS: https://joss.theoj.org/papers/10.21105/joss.07874.pdf
- 배터리 시뮬레이터 베이지안 파라미터 추정 입문: https://arxiv.org/pdf/2512.10055
- SUNDIALS 라이선스(BSD-3, KLU 주의): https://computing.llnl.gov/projects/sundials/license
- PyBaMM IDAKLU: https://www.mintlify.com/pybamm-team/PyBaMM/api/solvers/idaklu
- foxBMS 상태추정(SOC/SOE/SOH, BSD-3): https://iisb-foxbms.iisb.fraunhofer.de/foxbms/docs/latest/software/modules/application/algorithm/state-estimation/state-estimation.html
- ISC 모델-프리 감지(pseudo-OCV 차분): https://arxiv.org/pdf/2506.13394
- 셀 평균차 기반 ISC 진단(Batteries 2022): https://doaj.org/article/9b6420f6bad04af5906a0a7a9df76962
- 파우치셀 가스 팽창 모델: https://arxiv.org/pdf/2411.13197
- 스웰링 현상학 모델(Oh et al., JPS 2016): https://public.websites.umich.edu/~annastef/papers_battery\Oh2016JPS.pdf
- asammdf(LGPL): https://libraries.io/pypi/asammdf
- BoTorch(MIT)/Optuna BoTorch sampler: https://hub.optuna.org/samplers/botorch_sampler/
- 고차원 BO 벤치마크(SAASBO 구현 라이선스 이슈): https://arxiv.org/pdf/2406.04739
- PySide6 라이선스 비교: https://www.pythonguis.com/faq/not-an-open-source-application-which-one-to-use-pyqt5-or-pyside2/
- Claude Code/OpenCode 스킬 호환(커뮤니티): https://www.mdskills.ai/skills/opencode
- tree-sitter(MIT): https://en.wikipedia.org/wiki/Tree-sitter_(parser_generator)
