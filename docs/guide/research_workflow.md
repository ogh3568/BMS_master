---
type: Guide
title: 연구 워크플로 — 사용자 C 코드 분석·개선 도구 사용법
description: 사용자의 C 모델(SPM)을 수정하지 않고 파라미터를 추출하고, SIL로 실행하고, 최적화 대상 파라미터를 추론·검증하고, 세트 단위 SOC·SOH·ISD 정확도를 평가하는 절차
tags: [guide, workflow, sil, inference, accuracy]
status: draft
timestamp: 2026-10-15T00:00:00Z
---

# 연구 워크플로

> 원칙: **분석·개선 대상은 사용자의 C 코드다.** 이 도구들은 새 모델을 만들지 않는다. 사용자 코드를 그대로 읽고, 그대로 실행하고, 무엇을 바꾸면 좋아지는지 근거와 함께 제안한다. 사내 빌드·개발 환경과 별개로 연구용으로 쓸 수 있다.

## 두 단계 평가

| 단계 | 목표 | 도구 |
|---|---|---|
| **셀** | 모델 전압과 실측 전압의 차이 최소화 | ①~⑤ (`codeintel.cparams` → `sil` → `optim.infer`) |
| **세트 탑재** | 여러 환경에서 SOC·SOH·ISD 정확도 | ⑥ (`metrics.accuracy`) |

## 준비

```bash
pip install numpy tree-sitter tree-sitter-c openpyxl   # 모두 MIT/BSD
export PYTHONPATH=<저장소>/python
```

C 컴파일러(gcc/clang, Windows는 MinGW 또는 clang)가 필요하다. 사내 빌드 시스템을 써도 되고, 맞춰야 할 것은 `bms_sil_api.h`의 함수 규약뿐이다.

## ① 로그를 SBL로

```bash
python -m bmskit.logs.legacy suggest 셀시험.txt > map.json   # 매핑 초안 검토·수정
python -m bmskit.logs.legacy convert 셀시험.txt cell.sbl.tsv --mapping map.json --current-sign discharge_positive
```

## ② C 코드에서 파라미터 후보 추출

```bash
python -m bmskit.codeintel.cparams <SPM 소스 폴더> -o registry.json --md params.md
```

- `#define`, 전역·static 변수, 구조체 초기화, 테이블(배열)을 찾는다. 함수 안 매직 넘버도 찾는다.
- 각 후보에 물리 묶음(확산, 반응속도, 저항, OCP, 화학양론, 온도 등)을 추정해 붙인다.
- 어느 함수가 그 파라미터를 쓰는지 기록한다.
- `params.md`의 "함수에서 직접 참조되지 않은 후보"는 실제로 안 쓰이는 값일 수 있다. 코드 정리 후보로 본다.

## ③ SIL 라이브러리 만들기 (사용자 코드는 수정하지 않음)

1. **파라미터 접근 코드 자동 생성**

   ```bash
   python -m bmskit.sil.wrapgen registry.json -o build/bms_sil_params.c [--only Ds_n Ds_p ...]
   ```
   - 생성 파일은 모델 소스를 `#include`하는 unity build라서 `static` 변수도 이름으로 읽고 쓸 수 있다.
   - `#define`과 `const` 객체는 실행 중에 바꿀 수 없다. 생성기가 목록을 보고하므로 SIL 빌드에서만 바꿀 수 있게 할지 검토한다.
2. **글루 파일 1개 작성** (모델마다 한 번, 수십 줄): `bms_sil_reset/step/output_*`가 기존 모델의 초기화·주기 함수를 호출하게 한다. 예시는 `tests/fixtures/sil_toy/toy_glue.c`. AI가 사용자 코드를 읽고 초안을 써 줄 수 있다.
3. **빌드**: 사내 빌드로 공유 라이브러리를 만들거나 다음을 쓴다.
   ```python
   from bmskit.sil.runner import build_shared, SilModel
   lib = build_shared(["build/bms_sil_params.c", "glue.c"], "build/libspm.so", include_dirs=["<소스 루트>"])
   model = SilModel(lib)   # model.param_names, model.output_names, model.run(t, i, temp, soc0, params)
   ```

## ④ 최적화 대상 추론과 검증 (셀 단계)

```python
import json, numpy as np
from bmskit.logs import sbl
from bmskit.optim import infer

log = sbl.read("cell.sbl.tsv")
t = np.array(log.data["t"]); i = np.array(log.data["pack.i"]); T = np.array(log.data["temp.cell.01"])
v = np.array(log.data["pack.v"])
params = infer.params_from_registry(json.load(open("registry.json")))   # 후보 전체 (테이블 원소 포함)
sim = model.simulator(t, i, T, soc0=0.95)                              # 사용자 C 모델
masks = infer.regimes(t, i, capacity_ah=5.0, temp_c=T)
res = infer.pipeline(sim, params, v, masks, noise=1e-3)
open("inference.md", "w").write(infer.pipeline_markdown(res))
```

리포트에 들어가는 것
1. 선택 순서와 각 단계의 예측 RMSE
2. 공선성 지수: 함께 식별할 수 있는지
3. 파라미터별로 어느 운전 영역의 오차를 줄이는지
4. 운전 영역별 잔차 전후 비교
5. 제외된 후보와 이유: 영향 없음 / 함께 식별 불가 / 이득 미미
6. 최적화 후 검증: 각 파라미터를 원래 값으로 되돌리면 얼마나 나빠지는지. 기여 없는 것은 자동 제외

**AI(Claude)의 역할**: 이 리포트와 `params.md`, 코드를 함께 읽고 해석한다. "이완 구간 오차가 줄었으니 확산 쪽 문제였다", "고율 잔차가 남는 것은 SPM 구조 한계로 보인다" 같은 판단을 하고, 다음 실험과 코드 개선안을 제안한다. 수치는 모두 도구 결과를 근거로 인용한다.

## ⑤ 결과를 사용자 코드에 반영

- 최적화된 값은 사용자의 파라미터 정의 위치(`registry.json`의 `source`)에 대한 패치 제안으로 만든다.
- 사람이 검토한 뒤 사내 저장소에 반영한다. 도구가 사용자 코드를 직접 수정하지 않는다.

## ⑥ 세트 탑재 정확도 (SOC·SOH·ISD, 여러 환경)

```bash
python -m bmskit.metrics.accuracy soc  set_*.sbl.tsv     # 로그별 + 온도·C-rate·SOC 구간별 오차
python -m bmskit.metrics.accuracy soh  set_*.sbl.tsv     # meta ref.soh 대비
python -m bmskit.metrics.accuracy isd  set_*.sbl.tsv     # 혼동행렬, 감지 지연, 셀 위치, 저항 추정 오차, 환경별
```

SBL에 필요한 채널과 메타는 [SBL v1 §3·§5](/spec/sbl_v1.md)의 ISD·SOH·기준값 항목을 따른다. 예: `bms.isd_flag`, `meta label.isd`, `ref.soc` 또는 `ref.soc0`, `env`.

## 검증 상태

- 도구 체인 전체(추출 → 생성 → 빌드 → 실행 → 추론 → 검증)는 테스트용 C 픽스처로 확인했다([실험 기록](/research/07_experiment_toolchain_check.md)).
- 실제 SPM 코드에 적용하려면 글루 파일 하나가 필요하다.
