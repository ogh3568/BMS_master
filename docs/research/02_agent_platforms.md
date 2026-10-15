---
type: Source
title: 에이전트 플랫폼 조사 — Claude Code와 OpenCode
description: 요구 R11(Claude 기본 + OpenCode 호환) 설계 근거
tags: [research, claude-code, opencode, mcp, skills]
timestamp: 2026-10-15T00:00:00Z
---

# Claude Code와 OpenCode

## 1. OpenCode

| 항목 | 내용 | 검증 |
|---|---|---|
| Skill 탐색 경로 | 프로젝트: `.opencode/skills/`, **`.claude/skills/`**, `.agents/skills/`<br>전역: `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/` | ✅ OpenCode 저장소 문서(skills.mdx) |
| Skill frontmatter | 필수 `name`, `description`. 선택 `license`, `compatibility`, `metadata`(문자열 맵). `metadata`의 `opencode/slash`는 `/name` 명령으로 노출, `opencode/autoinvoke: false`는 자동 선택에서 숨김 | ✅ |
| 규칙 파일 | 공식 문서: AGENTS.md 우선. AGENTS.md가 없을 때만 프로젝트 CLAUDE.md를 폴백으로 사용. 전역은 `~/.config/opencode/AGENTS.md` → `~/.claude/CLAUDE.md` 순 | 🟡 공식 문서 검색 결과 |
| 폴백 제거 주장 | 2026-08-21 이후 로더가 AGENTS.md만 본다는 블로그(소스 확인 주장) | 🟡 공식 문서와 충돌 → **AGENTS.md를 원본으로 쓰면 어느 쪽이든 안전** |
| Claude 호환 끄기 | 환경변수 `OPENCODE_DISABLE_CLAUDE_CODE=1`(전체), 프롬프트 파일·스킬만 끄는 세부 변수도 있음 | 🟡 |
| 추가 지침 | `opencode.json`의 instructions에 파일·glob·URL 지정, AGENTS.md와 병합 | 🟡 |
| MCP 설정 | `opencode.json` → `"mcp": {"<name>": {"type": "local", "command": [..], "environment": {..}, "enabled": true, "cwd": "..", "timeout": 5000}}` | ✅ 저장소 문서(mcp-servers.mdx) |
| 에이전트 정의 | `opencode.json`의 `agent` 키 (디렉터리 경로는 이번 조사에서 미확인) | 🟡 |
| 헤드리스 | `opencode run` | ⚪ |

## 2. Claude Code

| 항목 | 내용 | 검증 |
|---|---|---|
| 지침 | CLAUDE.md (`@path` import 지원) | ⚪ |
| Skills | `.claude/skills/<name>/SKILL.md` (프로젝트), `~/.claude/skills/` (전역) | 🟡 |
| 플러그인 구조 | `.claude-plugin/plugin.json`(필수 필드는 kebab-case `name`), 루트에 `skills/`, `agents/`, `commands/`, `hooks/hooks.json`, `.mcp.json` | 🟡 |
| 마켓플레이스 | git 저장소의 `.claude-plugin/marketplace.json`. `/plugin marketplace add`, `/plugin install`. 출처는 GitHub, git URL, 로컬 경로, URL | 🟡 (사설 저장소 인증은 미확인) |
| MCP | 프로젝트 `.mcp.json` | ⚪ |
| 헤드리스 | `claude -p` | ⚪ |

## 3. 사내 LLM gateway 연결 (2026-10-15 추가)

| 항목 | 내용 | 검증 |
|---|---|---|
| Claude Code | LLM gateway는 조직이 운영하는 Claude Code와 모델 제공자 사이의 프록시. `ANTHROPIC_BASE_URL`로 지정하고 조직 발급 자격증명으로 인증. 사내 HTTP 프록시(`HTTPS_PROXY`)와는 별개이고 함께 쓸 수 있음 | 🟡 공식 문서 검색 결과 (code.claude.com llm-gateway-connect, 엔터프라이즈 개요) |
| 설정 위치 | 셸 export와 settings 파일 env 블록이 같으면 settings 값이 우선. 자격증명은 커밋되는 프로젝트 `.claude/settings.json`에 넣지 말 것 | 🟡 |
| OpenCode | 내장 provider의 `options.baseURL`로 gateway 지정(`provider.anthropic.options.baseURL`). OpenAI 호환이면 `npm: "@ai-sdk/openai-compatible"` 사용자 정의 provider + `models` 정의 + `/connect` | ✅ OpenCode 저장소 문서(providers.mdx) |
| 확인할 것 | 사내 gateway가 Anthropic Messages API 형식인지, 도구 호출·스트리밍·프롬프트 캐시를 그대로 전달하는지 | - |

## 4. 설계 결론

1. AGENTS.md를 원본으로 두고, CLAUDE.md는 `@AGENTS.md` import와 Claude 전용 보충만 담는다.
2. Skills는 `.claude/skills/`에 둔다. 양쪽 모두 공식 경로다. frontmatter는 공통 필드만 쓴다.
3. 도구는 MCP 서버 하나로 제공하고 설정 파일 2개(`.mcp.json`, `opencode.json`)를 생성 스크립트로 맞춘다.
4. 서브에이전트·명령은 형식이 다르므로 원본 1벌에서 변환한다.
5. 야간 스모크 테스트로 양쪽 동작을 계속 확인한다. 호환 경로는 자주 바뀐다.

## 출처

- https://raw.githubusercontent.com/sst/opencode/dev/packages/web/src/content/docs/skills.mdx
- https://raw.githubusercontent.com/sst/opencode/dev/packages/web/src/content/docs/mcp-servers.mdx
- https://opencode.ai/docs/rules/
- https://blog.devgenius.io/opencode-agents-md-opencode-jsonc-architecture-precedence-and-workflow-9cb668e501e9
- https://www.mdskills.ai/skills/opencode
- https://www.morphllm.com/claude-code-marketplace
- https://skills.sh/aiskillstore/marketplace/plugin-structure
- https://code.claude.com/docs/en/llm-gateway-connect.md
- https://docs.anthropic.com/en/docs/claude-code/bedrock-vertex
- https://raw.githubusercontent.com/sst/opencode/dev/packages/web/src/content/docs/providers.mdx
