# P2 CLI 검증

- 실행일: 2026-09-08 (Asia/Seoul)
- 상태: CLI 구현·로컬 검증 완료. 목표 Windows/macOS 실환경 테스트는 배포 후 별도 진행.
- 환경: Rocky Linux 9.8 x86_64, CPython 3.12.13, MarkItDown 0.1.7, 기존 `uv.lock`.
- 첫 배포 전 버전 항목은 작성하지 않는다. 패키지 임시 `0.0.0`은 유지하고 `--version`은 개발 상태만 표시한다.

## 구현 내용

| 파일 | 내용 |
|---|---|
| `src/everythingmarkdown/cli.py` | 인자/TTY 입력, 시작 CWD 캡처, 공통 서비스 호출, 결과·오류·경고 표시 |
| `src/everythingmarkdown/__main__.py` | `python -m everythingmarkdown` 진입점 |
| `pyproject.toml` | `everythingmarkdown` 콘솔 명령 등록; P0 진입점 보존 |
| `tests/unit/test_cli.py` | CLI 단위 테스트 21개 |
| `tests/integration/test_cli.py` | 실제 subprocess·콘솔 진입점·Linux PTY 테스트 8개 |

동작 계약:

- `everythingmarkdown <file>` 및 `python -m everythingmarkdown <file>`은 같은 서비스를 사용한다.
- 파일 인자가 없고 stdin이 TTY이면 stderr 프롬프트를 출력하고 한 번 입력받는다.
  비TTY이면 입력 대기 없이 사용법 오류로 종료한다.
- CWD는 도움말/버전 처리 후, 입력 프롬프트 전에 한 번 캡처한다. 입력이나 변환 후 재계산하지 않는다.
- 대화형 입력만 바깥 공백과 짝지어진 따옴표를 제거한다. 파일 인자의 따옴표 처리는 셸에 맡긴다.
- 성공 시 stdout에 결과 절대 경로 한 줄만 출력한다. 프롬프트·오류 코드·경로·정리 경고는 stderr다.
- 종료 코드: 성공 0, 입력/사용법 2, 변환 3, 저장 4, Ctrl+C/EOF 취소 130.
- `--version`: 현재 `EverythingMarkdown (개발 중; 정식 릴리즈 없음)`.
  향후 배포 요청에 따라 패키지 메타데이터가 실제 릴리즈 버전으로 변경되면 해당 버전을 표시한다.
- P1 서비스만 변환·저장을 수행한다. CLI에 저장 정책을 중복 구현하지 않는다.

## 실행 결과

| 명령 | 결과 | 증거 |
|---|---|---|
| `.venv/bin/python -m unittest discover -s tests -v` | 종료 0, **103개 통과** | [전체 로그](evidence/p2-tests.log) |
| `unshare --user --map-root-user --net .venv/bin/python -m unittest discover -s tests -v` | 종료 0, **103개 통과** | [격리 로그](evidence/p2-tests-network-isolated.log) |
| `.venv/bin/python -m compileall -q src tests scripts packaging` | 종료 0, 문법 컴파일 | [최종 검사](evidence/p2-final-checks.json) |
| `.venv/bin/python -m tabnanny src tests scripts packaging` | 종료 0, 들여쓰기 검사 | [최종 검사](evidence/p2-final-checks.json) |
| `uv pip check` | 종료 0, 기존 패키지 호환성 확인 | [최종 검사](evidence/p2-final-checks.json) |
| `uv sync --locked --group build` | 종료 0, CLI 진입점 설치; 의존성 버전 변경 없음 | [최종 검사](evidence/p2-final-checks.json) |
| `git diff --check`, AST 중복 정의·문서 링크·미배포 버전 항목 검사 | 통과 | [최종 검사](evidence/p2-final-checks.json) |

핵심 검증:

- 실제 CLI 프로세스로 7개 포맷 변환 → 시작 CWD의 `convert_result`에 저장.
- 설치된 콘솔 진입점의 한글·공백·대문자·다중 확장자 경로, 파일명 유지.
- 실제 충돌 코드 4·원본 결과 보존, 누락 입력 코드 2, 빈 문서 코드 3, 비TTY 무인자 즉시 종료.
- Linux PTY를 stdin에 연결한 실제 프로세스에서 따옴표로 감싼 한글 파일명 입력과 저장 성공.
- Ctrl+C/EOF/빈 입력·모든 공통 오류 코드·경고와 stdout/stderr 분리는 단위 테스트로 검증.
- 전체 103개 = 기존 P0/P1 74개 + P2 신규 29개. P0/P1의 별도 과거 로그는 수정하지 않았다.

## 범위 밖 / 다음 단계

- Windows/macOS 실제 콘솔, Python 미설치 실행, GUI와 설치 EXE/macOS 앱 번들은 이번에 검증하지 않았다.
- Linux PTY는 목표 OS 검증의 대체가 아니며 Ctrl+C/EOF의 실제 키보드 조작은 후속 실환경 테스트 대상이다.
- lint/typecheck 도구·설정 미선정으로 미실행. compileall/tabnanny/AST 검사는 전체 lint/typecheck가 아니다.
- 새 의존성·릴리즈 버전·태그·GitHub Release는 생성하지 않는다. 사용자 요청에 따른 소스 커밋·푸시와 구분한다.
- 다음 작업은 P3 GUI에서 동일한 P1 서비스를 호출하는 파일 선택·변환·상태 UI 구현이다.
