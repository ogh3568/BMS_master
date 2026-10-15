---
type: Specification
title: SBL v1 — Standard BMS Log 형식
description: BMS 시계열 로그의 사내 표준 형식. 텍스트(TSV/CSV)와 엑셀 두 가지 표현, 채널 이름 규칙, 단위, 메타데이터, 적합 등급, 기존 로그 변환 규칙
tags: [spec, log, sbl, standard]
status: draft
version: 1.0
timestamp: 2026-10-15T00:00:00Z
resource: /python/bmskit/logs/sbl.py
---

# SBL v1 — Standard BMS Log 형식

## 1. 목적과 설계 원칙

- 사내 로그는 엑셀과 txt 형식이 섞여 있고, 열 이름과 단위가 제각각이다. SBL은 이를 하나로 맞춘 **표준 시계열 형식**이다.
- 설계 원칙
  1. **사람이 읽을 수 있다.** 메모장과 엑셀로 바로 열린다. 전용 도구가 필요 없다.
  2. **자기 설명적이다.** 단위, 전류 부호, 셀 구성, FW 버전이 파일 안에 있다.
  3. **기계가 검증할 수 있다.** 이름 규칙과 단위 표가 고정돼 있어 검증기(`python -m bmskit.logs.sbl validate`)로 바로 확인한다.
  4. **손실이 없다.** 표준 이름이 없는 신호도 `x.` 접두사로 보존한다.
  5. **분석에 필요한 것을 강제한다.** 파라미터 최적화에 필요한 BMS 내부 모델 상태(`model.*`)와 기준 측정값(`ref.*`)의 자리를 미리 정해 둔다.

## 2. 표현 형식

세 가지 표현은 서로 손실 없이 변환된다.

| 표현 | 확장자 | 용도 |
|---|---|---|
| 텍스트 | `.sbl.tsv` (권장), `.sbl.csv` | 기본 교환 형식, 장비·스크립트 출력, git 보관 |
| 엑셀 | `.sbl.xlsx` | 사람이 보고 편집할 때 |
| Parquet (향후) | `.sbl.parquet` | 대용량 분석용 내부 캐시 |

### 2.1 텍스트 형식

```
#SBL 1.0                                  ← 1행 고정 (형식과 버전)
#@current_sign=discharge_positive         ← 메타데이터: #@키=값
#@t0=2026-10-15T09:00:00+09:00
#@pack.series=4
#!channel=bms.state;unit=-;desc=상태 코드 (0=rest,2=discharge);source=BMS_State   ← 채널 설명(선택)
t[s]	pack.v[V]	pack.i[A]	cell.v.01[V]	...   ← 헤더: 이름[단위]
0	16.42	0	4.1052	...                    ← 데이터
```

| 규칙 | 내용 |
|---|---|
| 인코딩 | UTF-8 (BOM 허용). 기존 CP949 로그는 변환기로 바꾼다 |
| 1행 | `#SBL 1.0` |
| 메타데이터 | `#@키=값`. 키는 소문자, 점으로 구분. 헤더 앞에만 올 수 있다 |
| 채널 설명 | `#!channel=이름;unit=단위;desc=설명;source=원본 신호명` (선택) |
| 헤더 | `이름[단위]`를 구분자로 나열. 단위를 생략하면 표준 단위로 간주 |
| 구분자 | 탭(권장) 또는 쉼표. 헤더 행에 탭이 있으면 탭 |
| 소수점 | `.`만 허용. 천 단위 구분 기호 금지 |
| 결측 | 빈 칸 또는 `NaN` |
| 첫 열 | 반드시 `t` (초, 기준 시각 `t0`부터의 경과 시간, 감소하면 안 됨) |
| 샘플링 | 고정·가변 모두 허용. 신호마다 주기가 다르면 공통 시간축에 두고 해당 행만 비운다 |

### 2.2 엑셀 형식

| 시트 | 내용 |
|---|---|
| `meta` | A열 key, B열 value. 첫 행은 `key`, `value` 머리글 |
| `channels` (선택) | name, unit, desc, source |
| `data` | 1행은 텍스트 헤더와 같은 `이름[단위]`, 2행부터 숫자. **시간은 엑셀 날짜 서식이 아니라 초 단위 숫자** |

## 3. 채널 이름 규칙

- 문법: `^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$` (소문자, 점으로 계층 구분)
- 셀·센서 번호는 **1부터 시작하는 두 자리 이상 0채움** (`cell.v.01`, `cell.v.112`)

| 계열 | 이름 | 표준 단위 | 등급 | 설명 |
|---|---|---|---|---|
| 시간 | `t` | s | L0 | 경과 시간 |
| 팩 | `pack.v`, `pack.i`, `pack.p` | V, A, W | L0/L1 | 팩 전압·전류·전력 |
| 셀 전압 | `cell.v.NN` | V | L1 | 셀(직렬 블록) 전압 |
| 온도 | `temp.cell.NN`, `temp.module.NN`, `temp.pack.NN`, `temp.busbar.NN`, `temp.fet.NN`, `temp.shunt.NN`, `temp.amb`, `temp.coolant_in`, `temp.coolant_out`, `temp.board` | degC | L1 | 온도 센서 |
| BMS 출력 | `bms.soc`, `bms.soh`, `bms.soe`, `bms.soc_raw`, `bms.soc_min`, `bms.soc_max` | % | L2 | 추정값 |
| | `bms.sop_chg`, `bms.sop_dchg` / `bms.sop_i_chg`, `bms.sop_i_dchg` | W / A | L2 | 가용 전력·전류 |
| | `bms.ttf` | s | L2 | 만충 예상 시간 |
| | `bms.capacity` | Ah | L2 | 추정 용량 |
| | `bms.state`, `bms.mode`, `bms.fault_code` | - | L2 | 상태·코드 (코드표는 `#!` desc 또는 메타) |
| | `bms.<기타>` | 자유 | L2 | 그 밖의 BMS 출력 |
| 플래그 | `flag.<이름>` (예: `flag.ov`, `flag.uv`, `flag.oc_chg`, `flag.ot`) | - (0/1) | L2 | 보호·고장 플래그 |
| 밸런싱 | `bal.NN` | - (0/1) | L2 | 셀별 밸런싱 활성 |
| 충전기 | `chg.v_req`, `chg.i_req`, `chg.<기타>` | V, A | L2 | 충전 요구값 |
| **BMS 내부 모델** | `model.<이름>` (예: `model.v_pred`, `model.ocv`, `model.eta_neg`, `model.soc_surf_neg`, `model.cs_avg_pos`) | 자유 | **L3** | 경량 전기화학 모델(SPM 계열) 내부 상태·예측값. **파라미터 최적화와 잔차 진단에 핵심** |
| **기준 측정** | `ref.v`, `ref.i`, `ref.soc`, `ref.ah`, `ref.<기타>` | V, A, %, Ah | **R** | 충방전기·정밀 계측 등 BMS와 독립된 참값 |
| 스웰링 | `swell.thickness[.NN]`, `swell.pressure[.NN]` | mm, kPa | S | 두께·압력 센서 |
| 사용자 정의 | `x.<이름>` | 자유 | X | 표준 이름이 없는 신호 (손실 방지) |

## 4. 단위

| 차원 | 표준 단위 | 허용 단위 (읽을 때 자동 환산) |
|---|---|---|
| 시간 | s | ms, min, h |
| 전압 | V | mV |
| 전류 | A | mA |
| 전력 | W | kW |
| 온도 | degC | (K는 별도 차원, 변환기에서 처리) |
| 비율 | % | - |
| 전하량 | Ah | mAh |
| 에너지 | Wh | kWh |
| 저항 | Ohm | mOhm |
| 길이 | mm | um |
| 압력 | kPa | Pa |
| 개수 | cycle | - |
| 무차원 | - | - |

표준 이름 채널에 차원이 다른 단위를 쓰면 오류다(예: `pack.v[A]`). 같은 차원의 다른 단위(예: `cell.v.01[mV]`)는 허용하고 정보로 알린다. `--normalize`로 표준 단위로 바꾼다.

## 5. 메타데이터

| 키 | 필수 | 예시 | 설명 |
|---|---|---|---|
| `current_sign` | **필수** | `discharge_positive` / `charge_positive` | 전류 부호 규약 |
| `t0` | 권장 | `2026-10-15T09:00:00+09:00` | `t=0`의 절대 시각 (ISO 8601, UTC 오프셋 포함) |
| `source` | 권장 | `rig3_2026-10-15.txt` | 원본 파일명 |
| `cell.chemistry` | 권장 | NCM, NCA, LFP, LMFP, LCO, Na-ion | 셀 화학 |
| `cell.capacity_ah` | 권장 | 50 | 정격 용량 |
| `cell.model` | 선택 | | 셀 모델명 |
| `pack.series`, `pack.parallel` | 권장 | 14, 2 | 직렬·병렬 수 |
| `fw.version` | 권장 | | BMS FW 버전 (FW 비교·추적성) |
| `param_set` | 권장 | | 캘리브레이션·모델 파라미터 세트 ID |
| `test.type` | 권장 | drive, charge, fast_charge, hppc, ocv, gitt, calendar, field, pulse_discharge_rest | 시험 종류 |
| `test.temp_degc` | 선택 | 25 | 챔버 온도 |
| `sampling` | 선택 | `fixed:0.1`, `variable` | 샘플링 방식 |
| `device`, `operator`, `project` | 선택 | | 장비·작성자·프로젝트 |
| `legacy.*` | 자동 | | 변환기가 원본 파일 머리말에서 옮긴 값 |

모르는 키가 있어도 오류가 아니다(확장 가능).

## 6. 적합 등급

검증기가 자동 판정한다.

| 등급 | 조건 | 가능한 분석 |
|---|---|---|
| **L0** | `t`, `pack.v`, `pack.i` | 기본 통계, 에너지·용량 계산 |
| **L1** | L0 + `cell.v.*` + `temp.*` | 셀 편차, 밸런싱, 열 분석, ISD 징후 |
| **L2** | L1 + `bms.*` | SOC·SOH 성능, 보호 동작, 상태머신 분석 |
| **L3** | L2 + `model.*` | 내장 모델 잔차 진단, **파라미터 추론·최적화** |
| `+R` | `ref.*` 존재 | 참값 기반 정확도 평가 |
| `+S` | `swell.*` 존재 | 스웰링 모델 검증 |

예: `L3+R`은 파라미터 최적화와 정확도 평가에 가장 좋은 로그다.

## 7. 검증 규칙 (검증기 코드)

| 코드 | 수준 | 내용 |
|---|---|---|
| E001 | 오류 | 지원하지 않는 버전 |
| E010 | 오류 | 첫 열이 `t`가 아님 |
| E011 | 오류 | 채널 이름 중복 |
| E012 | 오류 | 이름 규칙 위반 |
| E013 | 오류 | 알 수 없는 단위 |
| E014 | 오류 | 표준 채널에 차원이 다른 단위 |
| E015 | 오류 | 셀·밸런싱 번호가 0채움 두 자리 이상이 아님 |
| E020/E021/E022 | 오류 | 필수 메타 누락 / `current_sign` 값 오류 / `t0` 형식 오류 |
| E030/E031 | 오류 | `t` 결측 / `t` 역행 |
| E032 | 오류 | 숫자가 아닌 값 |
| E040 | 오류 | L0 필수 채널 없음 |
| W010 | 경고 | 표준 이름이 아닌 채널 (`x.` 권장) |
| W020/W021 | 경고 | `t0`에 오프셋 없음 / `pack.series`와 셀 채널 수 불일치 |
| W030/W031/W032 | 경고 | 시간 중복 / 결측 20% 초과 / 범위 밖 값 |
| I010/I020 | 정보 | 비표준 단위 / 권장 메타 누락 |

## 8. 기존 로그 변환 (엑셀·txt → SBL)

`python -m bmskit.logs.legacy`가 다음을 자동으로 추정한다.

| 항목 | 방법 |
|---|---|
| 인코딩 | UTF-8 → CP949 → EUC-KR → UTF-16 → Latin-1 순서로 시도 |
| 구분자 | 탭, 쉼표, 세미콜론, 파이프, 공백 중 행마다 개수가 일정한 것 |
| 헤더 행 | 숫자가 이어지기 직전의 글자 위주 행. 그 위의 머리말은 `legacy.*` 메타로 보존 |
| 시간 | 초 숫자, `hh:mm:ss(.fff)`, 날짜시간 문자열, 엑셀 일련번호. 없으면 행 번호 × 샘플 주기 |
| 열 매핑 | 한글·영문 별칭 표(예: 시간/Time, 팩전압/Pack Voltage, 전류/Current, 셀전압1/Cell_V_01, 온도1/Temp1, SOC) |
| 단위 | 헤더의 `(V)`, `[mV]` 표기. 없으면 값의 크기로 추정(셀 전압 중앙값 >100 → mV, SOC ≤1.5 → 비율) |
| 모르는 열 | `x.<이름>`으로 보존 (신뢰도 0.3) |

**작업 흐름**
1. `suggest`로 매핑 초안(JSON, 열마다 신뢰도와 이유)을 만든다.
2. 사람 또는 에이전트가 검토하고 고친다. 특히 전류 부호, 신뢰도 0.7 미만 열.
3. `convert --mapping`으로 변환한다. 같은 장비의 로그는 같은 매핑 파일을 재사용한다.

```bash
python -m bmskit.logs.legacy suggest raw/rig3.txt > maps/rig3.json      # 초안
python -m bmskit.logs.legacy convert raw/rig3.txt out/rig3.sbl.tsv \
       --mapping maps/rig3.json --current-sign discharge_positive         # 변환 + 검증
python -m bmskit.logs.sbl validate out/rig3.sbl.tsv                       # 단독 검증
python -m bmskit.logs.sbl convert out/rig3.sbl.tsv out/rig3.sbl.xlsx       # 엑셀로
```

## 9. 장비·FW 팀에 권고하는 출력 방식

SBL이 사내 표준이 되려면 새로 만드는 로그가 처음부터 SBL로 나오는 것이 가장 좋다.

1. 로거·HIL·시험 스크립트가 `.sbl.tsv`를 직접 쓴다. 헤더 2줄(형식, 메타)만 추가하면 된다.
2. BMS 디버그 로그에 **내장 모델 출력(`model.v_pred` 등)과 주요 내부 상태**를 포함한다. 파라미터 최적화 정확도가 크게 올라간다.
3. 가능한 시험에는 충방전기 참값(`ref.i`, `ref.ah`)을 함께 기록한다.
4. 엑셀로 공유할 때는 `.sbl.xlsx`(시트 3개) 구조를 쓴다.

## 10. 버전 정책

- `1.x`: 하위 호환 확장만 한다(새 표준 이름, 새 메타 키). 검증기는 `1.`로 시작하는 버전을 모두 받는다.
- `2.0`: 호환이 깨지는 변경. 변환 도구를 함께 제공한다.
- 표준 이름 추가 요청은 `docs/spec/`에 ADR로 기록한다.

## 11. 참조 구현

| 파일 | 내용 |
|---|---|
| `python/bmskit/logs/sbl.py` | 읽기·쓰기(텍스트, 엑셀), 검증, 단위 정규화, CLI |
| `python/bmskit/logs/legacy.py` | 기존 txt/csv/xlsx 변환, 매핑 추정, CLI |
| `examples/sbl/example_l3.sbl.tsv` | 합성 예제 (L3+R, 측정값 아님) |
| `tests/test_sbl.py` | 테스트 (표준 라이브러리 unittest) |

의존성은 표준 라이브러리뿐이다. 엑셀은 선택 의존성 `openpyxl`(`pip install .[excel]`)이 필요하다.
