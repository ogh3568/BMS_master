---
type: Plan
title: 아키텍처와 데이터 계약
description: 계층 구조, 저장소 구조, 표준 로그 스키마, 파라미터 레지스트리, 실행 기록, MCP 도구 목록, 지식 위키 frontmatter 확장, Claude/OpenCode 배치 방식
tags: [plan, architecture, schema, mcp, okf]
status: draft
version: 0.2
timestamp: 2026-10-15T00:00:00Z
---

# 아키텍처와 데이터 계약

## 1. 계층 구조

```
┌──────────────────────────────────────────────────────────────────────┐
│ 입구(Front-ends)                                                      │
│  GUI(로컬 웹)   Claude Code   OpenCode   CLI(`bms ...`)   CI 작업     │
└──────┬──────────────┬─────────────┬──────────────┬───────────────────┘
       │HTTP/JSON     │MCP stdio    │MCP stdio     │함수 호출
┌──────▼──────────────▼─────────────▼──────────────▼───────────────────┐
│ Agent 계층: AGENTS.md · Skills · Subagents · Commands                 │
│ bms-mcp 서버: 도구 목록(§6), 권한 등급, 감사 로그, 토큰 예산          │
└──────┬───────────────────────────────────────────────────────────────┘
       │Python API
┌──────▼───────────────────────────────────────────────────────────────┐
│ Core 엔진 bmskit (Python ≥3.10)                                       │
│ codeintel │ logs │ metrics │ viz/report │ knowledge │ optim │ models  │
│ features  │ synth │ sil │ eval │ security │ provenance │ license      │
└──────┬─────────────────────────────┬─────────────────────────────────┘
       │ctypes                       │파일
┌──────▼──────────────┐   ┌──────────▼──────────────────────────────────┐
│ bmscore (C99)        │   │ 저장소                                       │
│ x86 · Android · FW   │   │ knowledge/(OKF) · runs/(실행 기록) · cache/  │
└─────────────────────┘   │ data/(Parquet) · params/(YAML)               │
                          └─────────────────────────────────────────────┘
```

**의존 규칙**
- 위 계층은 아래 계층만 호출한다.
- `bmskit`는 LLM SDK에 의존하지 않는다. LLM 호출은 Agent 계층과 GUI의 "AI 실행기"에서만 한다.
- GUI가 AI 작업을 할 때는 `claude -p` 또는 `opencode run`을 헤드리스로 실행한다. 그래서 GUI가 특정 LLM에 묶이지 않는다.

## 2. 저장소 구조 (목표)

```
BMS_master/
├── AGENTS.md                 # 에이전트 공통 지침 (단일 소스)
├── CLAUDE.md                 # "@AGENTS.md" import + Claude 전용 보충
├── .claude/
│   ├── skills/<name>/SKILL.md  # Claude Code와 OpenCode가 함께 인식
│   ├── agents/               # Claude 서브에이전트
│   └── commands/             # Claude 슬래시 명령
├── .opencode/                # tools/sync_agents.py로 생성 (직접 편집 금지)
├── .mcp.json                 # Claude Code용 MCP 설정
├── opencode.json             # OpenCode용 MCP 설정 ("mcp": {"bms": {"type":"local", ...}})
├── plugin/                   # Claude Code 플러그인 패키지 (.claude-plugin/plugin.json)
├── python/bmskit/            # Core 엔진
├── python/bms_mcp/           # MCP 서버
├── bmscore/                  # C99 코어와 포트
├── gui/                      # 웹 GUI (server.py + static/)
├── knowledge/                # 제품 지식 위키 (OKF 번들)
├── docs/                     # 프로젝트 계획·조사 (OKF 번들)
├── schemas/                  # JSON Schema (log, params, run, okf-ext)
├── tests/ (unit, golden, equivalence, eval, smoke_agents)
├── tools/                    # 개발 스크립트 (sync_agents, sbom, license_gate)
└── pyproject.toml
```

## 3. 표준 로그 형식 → SBL v1

> **v0.3에서 대체됨.** 표준 로그 형식은 [SBL v1 규격](/spec/sbl_v1.md)으로 확정했다(텍스트 TSV/CSV + 엑셀, `name[unit]` 헤더, 계층형 채널 이름, 적합 등급 L0~L3/+R/+S). 참조 구현은 `python/bmskit/logs/`. 아래 표는 v0.2 초안으로, 이름 규칙이 SBL과 다르다(예: `cell_v_{k}` → `cell.v.NN`, `soc_bms` → `bms.soc`). Parquet은 대용량 내부 캐시용 표현으로 남긴다.

<details><summary>v0.2 초안 (참고용)</summary>


| 열 | 타입 | 단위 | 필수 | 설명 |
|---|---|---|---|---|
| `t` | float64 | s | ● | 기준 시각부터의 경과 시간 (단조 증가) |
| `pack_v` | float32 | V | ● | 팩 전압 |
| `pack_i` | float32 | A | ● | 팩 전류. **방전이 +**(부호 규약은 메타에 기록) |
| `cell_v_{k}` | float32 | V | ○ | 셀 전압 k=1..N |
| `temp_{k}` | float32 | °C | ○ | 온도 센서 k |
| `soc_bms` | float32 | % | ○ | BMS가 출력한 SOC |
| `soh_bms` | float32 | % | ○ | BMS가 출력한 SOH |
| `state` | int16 | - | ○ | BMS 상태머신 코드 (메타에 코드표) |
| `flag_*` | bool | - | ○ | 보호·고장 플래그 |
| `bal_{k}` | bool | - | ○ | 셀 밸런싱 활성 여부 |
| `ref_*` | float32 | - | ○ | 기준값(충방전기 전류, 실험실 SOC 등) |
| `x_*` | any | - | ○ | 제조사·프로젝트 고유 신호 |

</details>

**메타 (v0.2 초안, SBL §5로 대체)**: `schema_version`, `source_file`, `source_hash`(sha256), `fw_version`, `param_set_id`, `cell_model`, `chemistry`(NCM/NCA/LFP/LMFP/Na-ion), `topology`(예: 14S2P), `nominal_capacity_Ah`, `sample_rate_hint`, `current_sign`, `timezone`, `state_codes`, `channels_map`(원본 신호명 → 표준 열), `quality`(결측률, 시간 역행 횟수, 포화 횟수).

## 4. 파라미터 레지스트리 (`params/registry.yaml`, `schemas/params.v1.json`)

```yaml
- id: soc.ekf.q_process
  name_in_code: SOC_EKF_Q          # 코드상 식별자
  source: src/soc/soc_ekf.c#L42@a1b2c3d
  kind: calibration                 # calibration | physical | model | threshold | timing
  dtype: int16                      # C 타입
  qformat: Q12                      # 고정소수점이면 표기, 아니면 null
  unit: "-"
  default: 0.0005
  range: [1.0e-6, 1.0e-2]
  scale: log                        # 최적화 탐색 스케일
  used_by: [soc_ekf_predict, soc_ekf_update]
  modules: [soc]
  sensitivity: {morris_mu_star: null, sobol_st: null}
  identifiable: null                # 식별성 분석 결과
  optimize: false                   # 최적화 대상 여부 (자동 제안, 사람 확정)
  owner: soc-team
  notes: ""
```

물리·모델 파라미터(PyBaMM 셀 파라미터 등)도 같은 형식에 `kind: physical`로 넣는다. 그래야 "코드 캘리브레이션"과 "셀 모델 파라미터"를 한 곳에서 선별할 수 있다.

## 5. 실행 기록 (`runs/<run_id>/run.json`)

모든 도구 실행과 최적화는 실행 기록을 남긴다.

```json
{
  "run_id": "2026-10-15T10-22-01_metrics_7f3a",
  "tool": "metrics.compute", "tool_version": "0.1.0",
  "inputs": [{"path": "data/log_0012.parquet", "sha256": "..."}],
  "params": {"window_s": 600},
  "seed": 42, "git_rev": "a1b2c3d", "python": "3.11.9",
  "outputs": ["runs/.../metrics.json", "runs/.../events.json"],
  "started": "...", "duration_s": 12.3,
  "llm": {"agent": "claude-code|opencode|none", "tokens_in": 0, "tokens_out": 0}
}
```

리포트와 위키 페이지에서 근거를 남길 때 `run_id`를 인용한다(예: `[근거](runs/<run_id>)`).

## 6. MCP 도구 목록 (`bms-mcp`) v1

굵은 단위로 설계한다. 비-Claude 모델도 한두 번 호출로 결과를 얻을 수 있게 하기 위해서다.
권한 등급: **R** 읽기 / **C** 계산(파일 생성) / **W** 저장소 쓰기(승인 필요)

| 도구 | 등급 | 입력 | 출력 (요약) |
|---|---|---|---|
| `code.index` | C | 소스 루트, 빌드 정의(compile_commands.json 선택) | 심볼 수, 파서 커버리지, 인덱스 위치 |
| `code.query` | R | 심볼·파일·질의 | 정의, 호출자/피호출자, 사용 파라미터 (토큰 상한 적용) |
| `code.params` | R | 필터 | 파라미터 레지스트리 조각 |
| `code.hotspots` | R | 기간 | 복잡도 × 변경량 × 이슈 상위 목록 |
| `code.mapfile` | R | .map 파일 | 모듈별 ROM/RAM 사용량 |
| `log.ingest` | C | 원본 경로, 어댑터, 채널맵 | 표준 Parquet, 메타, 품질 리포트 |
| `log.summary` | R | 로그 ID | 기본 통계, 구간 목록, 품질 |
| `log.metrics` | C | 로그 ID, 지표 세트 | 지표 표, 이벤트 목록, run_id |
| `log.query` | R | 로그 ID, 조건식(예: `cell_spread>0.03 & t in day`) | 구간 목록 |
| `log.plot` | C | 로그 ID, 신호, 구간 | HTML/PNG 경로 |
| `sil.replay` | C | 로그 ID, 알고리즘, 변종, 파라미터 세트 | 출력 시계열, 기준 대비 오차, 실행 시간 |
| `sil.compare` | C | 두 FW/파라미터 세트, 로그 세트 | 차이 리포트 |
| `opt.screen` | C | 파라미터 목록, 모델, 데이터 | Morris/Sobol 결과 |
| `opt.identifiability` | C | 후보 파라미터 | 상관행렬, 식별 불가 묶음 |
| `opt.run` / `opt.status` | C/R | 설정 | 진행 상황, 최적값, 사후 분포 |
| `synth.generate` | C | 셀 파라미터, 프로파일, 고장 시나리오 | 표준 로그와 라벨 |
| `kb.search` | R | 질의 | 상위 페이지 (계층별 요약) |
| `kb.read` | R | 경로, 깊이 | 페이지 본문 또는 요약 |
| `kb.upsert` | W | 페이지 초안 | diff 미리보기, 승인 후 반영 |
| `kb.lint` | R | - | 깨진 링크, 고아·오래된 페이지, 근거 없는 주장 |
| `kb.graph` | R | 노드, 깊이 | 이웃 그래프(JSON) |
| `report.build` | C | 템플릿, run_id 목록 | HTML/PDF 경로 |

**공통 응답 규칙**: 응답은 기본 ≤4k 토큰으로 자른다. 결과가 더 크면 파일 경로와 요약만 돌려준다. 모든 응답에 `run_id`를 넣는다.

## 7. 지식 위키 frontmatter 확장 (`schemas/okf-ext.v1.json`)

OKF 필수 필드는 `type` 하나다. 아래 필드는 우리 프로젝트에서 쓰는 선택 확장이다.

```yaml
---
type: CodeModule            # CodeModule|Function|Parameter|Algorithm|Cell|Experiment|Finding|KnowHow|ADR|Source|Index|Log
title: SOC EKF 모듈
description: 확장 칼만 필터 기반 SOC 추정
tags: [soc, ekf]
timestamp: 2026-10-15T00:00:00Z
resource: src/soc/soc_ekf.c@a1b2c3d      # 원천 위치와 git 해시
author: ai | human | ai+human
status: draft | reviewed | deprecated
confidence: high | medium | low
evidence: [runs/2026-10-15T10-22-01_metrics_7f3a]
relations:
  - {type: uses_param, target: /code/params/soc.ekf.q_process.md}
  - {type: calls, target: /code/functions/ocv_lookup.md}
  - {type: explained_by, target: /algorithms/soc/ekf.md}
hot: {views_30d: 0, churn_90d: 0, issues: 0, score: 0.0}
---
```

**관계 타입(초안)**: `calls`, `uses_param`, `reads_signal`, `writes_signal`, `implements`, `explained_by`, `observed_in`, `caused_by`, `fixed_by`, `supersedes`, `related`.

## 8. Claude Code와 OpenCode 배치 방식 (조사 결과 반영)

| 요소 | Claude Code | OpenCode | 방식 |
|---|---|---|---|
| 지침 | CLAUDE.md | AGENTS.md (CLAUDE.md 폴백은 제거됐다는 보고가 있음) | **AGENTS.md가 원본**, CLAUDE.md는 import만 |
| Skills | `.claude/skills/` | `.claude/skills/` 공식 지원 (그 밖에 `.opencode/skills/`, `.agents/skills/`) | `.claude/skills/` 한 곳에 둔다. frontmatter는 공통 필드(`name`, `description`)만 쓴다 |
| MCP | `.mcp.json` | `opencode.json` → `mcp.<name>.{type:"local", command:[...]}` | 같은 서버, 설정 파일만 2개 (생성 스크립트로 맞춤) |
| 서브에이전트/명령 | `.claude/agents`, `.claude/commands` | `opencode.json`의 `agent` 등 | 원본 1벌, `tools/sync_agents.py`로 변환 |
| 배포 | 플러그인 (`.claude-plugin/plugin.json`, 사내 git 마켓플레이스) | 저장소 복제 또는 전역 설정 디렉터리 | 같은 git 저장소에서 둘 다 제공 |
| 헤드리스 | `claude -p` | `opencode run` | GUI의 AI 실행기가 선택 |
| **LLM 연결 (사내 gateway)** | `ANTHROPIC_BASE_URL` = gateway 주소, 조직 발급 자격증명(`ANTHROPIC_AUTH_TOKEN` 등). 자격증명은 커밋되는 `.claude/settings.json`에 넣지 않음 | `opencode.json` → `provider.anthropic.options.baseURL` (Anthropic 호환 gateway) 또는 `@ai-sdk/openai-compatible` 사용자 정의 provider | 설치 스크립트가 사용자 환경에 설정. 저장소에는 예시 파일만 |

환경변수 `OPENCODE_DISABLE_CLAUDE_CODE=1`이 설정되면 OpenCode가 `.claude/` 경로를 무시한다. 설치 가이드와 스모크 테스트에서 이 설정을 확인한다.
