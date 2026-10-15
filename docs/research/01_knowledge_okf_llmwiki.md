---
type: Source
title: 지식 관리 조사 — Google OKF와 Karpathy LLM Wiki
description: 요구 R6(LLM Wiki + OKF) 설계 근거
tags: [research, okf, llm-wiki, knowledge]
timestamp: 2026-10-15T00:00:00Z
---

# Google OKF와 Karpathy LLM Wiki

## 1. Google Open Knowledge Format (OKF)

| 항목 | 내용 | 검증 |
|---|---|---|
| 발표 | Google Cloud, 2026-06-12. Karpathy LLM-wiki 패턴을 벤더 중립 스펙으로 정리 | 🟡 |
| 버전 | v0.1, "완성된 표준이 아니라 출발점", 하위 호환 확장을 목표로 설계 | ✅ 공식 블로그 |
| 구조 | 디렉터리 = 번들, **마크다운 파일 1개 = 개념 1개**, 파일 경로가 개념의 식별자 | ✅ |
| 예약 파일 | `index.md`(점진적 공개용 목차), `log.md`(시간순 변경 이력). 둘 다 선택 | ✅ |
| frontmatter | **필수는 `type` 하나**. 흔히 쓰는 필드: `title`, `description`, `resource`, `tags`, `timestamp` | ✅ |
| 본문 | 자유 형식 마크다운 | ✅ |
| 관계 | 표준 마크다운 링크, 예시는 루트 기준 경로(`/tables/customers.md`). 링크가 디렉터리 계층 너머의 그래프를 만든다 | ✅ |
| 원칙 | 최소한의 규정 / 생산자·소비자 분리 / "플랫폼이 아니라 형식" (클라우드·DB·SDK 불필요) | ✅ |
| 저장소 | `github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf`: 스펙, 레퍼런스 구현(BigQuery 개념 초안 생성 에이전트, **정적 HTML 그래프 뷰어**), 샘플 번들 3개 | ✅ 링크 확인 / 내용은 ⚪ |
| 라이선스 | 2차 출처는 Apache 2.0이라고 함. 공식 블로그에는 명시 없음 | 🟡 → 저장소 LICENSE 확인 필요 |
| 생태계 | Nowledge Mem 등이 OKF 내보내기 지원 발표 | 🟡 |

**설계에 반영한 점**
- `type` 외 필드는 선택이므로 우리 확장 필드(`relations`, `status`, `evidence`, `hot`)를 넣어도 적합성이 유지된다.
- `index.md` 계층을 L1으로, 최상위 `_hot.md`를 L0으로 쓴다. `_hot.md`는 OKF 예약 파일이 아니므로 일반 개념(`type: Index`)으로 취급한다.
- 레퍼런스 그래프 뷰어와 호환되도록 링크는 루트 기준 경로를 쓴다.

**주의**: v0.1 초기 스펙이다. 교차 링크 세부 규칙과 적합성 기준은 스펙 원문 확인 후 lint 규칙에 반영해야 한다.

## 2. Karpathy LLM Wiki 패턴

| 항목 | 내용 | 검증 |
|---|---|---|
| 출처 | Karpathy GitHub gist, 2026-04 | 🟡 |
| 핵심 | 질문할 때마다 원문을 검색(RAG)하는 대신, 에이전트가 **지속적으로 관리하는 구조화된 마크다운 위키**를 만들어 지식을 누적 | 🟡 |
| 구성 | `raw/`(불변 원천), `wiki/`(LLM 생성 페이지), 스키마 문서(CLAUDE.md 등) | 🟡 |
| 연산 | ingest(새 원천 처리), query(질의), lint(상태 점검) | 🟡 |
| 한계 | 정기 유지보수 필요. 위키가 커지면 컨텍스트 한계로 품질 저하 (실사용자 후기) | 🟡 |

**설계에 반영한 점**
- 한계(규모)에 대응하려고 계층화(L0~L3), FTS 검색, 핫스팟, 요약 캐시를 넣었다.
- lint를 CI에 넣어 유지보수를 자동화한다.

## 출처

- https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
- https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
- https://themenonlab.blog/blog/google-okf-open-knowledge-format-karpathy-llm-wiki-standard
- https://nowledge.co/blog/open-knowledge-format
- https://blog.starmorph.com/blog/karpathy-llm-wiki-knowledge-base-guide
- https://www.kunalganglani.com/blog/llm-wiki-karpathy-local-knowledge-base.md
