# AGENTS.md — BMS AI Plugin

이 파일은 Claude Code와 OpenCode가 함께 읽는 에이전트 지침의 원본이다. CLAUDE.md는 이 파일을 import만 한다.

## 프로젝트
BMS SW 성능 분석·개선용 AI Plugin. 계획과 조사는 `docs/`에 있다(OKF v0.1 형식). 시작점은 `docs/index.md`다.

## 코드
- `python/bmskit/`: 분석 엔진 (표준 라이브러리 우선). `logs/sbl.py`는 SBL v1 표준 로그(규격: `docs/spec/sbl_v1.md`), `logs/legacy.py`는 기존 엑셀·txt 로그 변환기
- 테스트: `python -m unittest discover -s tests` (Python 3.10+, 엑셀 테스트는 openpyxl이 있을 때만)
- 로그를 다룰 때는 먼저 SBL로 변환한다: `PYTHONPATH=python python -m bmskit.logs.legacy suggest <파일>` → 매핑 검토 → `convert`

## 작업 규칙
- 변경은 지정된 개발 브랜치에 커밋하고 **push만** 한다. **PR은 만들지 않는다.**
- 계획·조사·결정이 바뀌면 `docs/`의 해당 문서를 갱신하고 `docs/log.md`에 이력을 남긴다.
- 새 결정은 `docs/plan/08_decisions.md`에 ADR로 추가한다.
- `docs/` 문서는 YAML frontmatter에 `type`을 반드시 넣고, 문서 간 링크는 `docs/` 기준 루트 경로(`/plan/...`)를 쓴다.
- 조사 내용은 검증 수준(✅ 1차 확인 / 🟡 2차 출처 / ⚪ 미확인)을 표시하고 출처 URL을 남긴다.
- Python은 3.10+ 호환. 새 의존성은 `docs/research/05_licenses_dependencies.md` 정책을 따른다(GPL·무라이선스 금지, LGPL은 선택 extras만).
- **외부 MCP 서버에 의존하지 않는다**(사내 정책). 도구는 저장소의 로컬 MCP와 CLI로 제공하고, Skills는 CLI만으로도 동작해야 한다.
- 현재 최우선 목표는 SPM 모델 정확도 향상이다(`docs/plan/10_model_accuracy_track.md`). FW 저전력 모델은 연구 단계다.
- 설계 원칙: 계산은 결정론적 도구, LLM은 해석만. 수치 주장에는 근거(run_id 등)를 붙인다.
