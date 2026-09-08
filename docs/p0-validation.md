# P0 검증 기록

- 실행일: 2026-09-08 (Asia/Seoul)
- 실행 당시 상태: **부분 완료**. Linux 개발 검증만 수행했으며 당시 목표 OS의 P0 완료 조건은 미충족.
- 후속 범위 변경 (2026-09-08): 사용자 요청으로 실환경 테스트를 배포 후로 이관해 P0 로컬 결과로 P1 착수가 가능해졌다. 아래 로그와 미검증 사실은 그대로 보존한다.
- 제품 코드가 아닌 최소 프로브이다. 결과 `.md` 저장은 P1, 제품 CLI는 P2, 변환 GUI는 P3 범위다.

## 시험 범위와 환경

| 항목 | 값 / 결과 |
|---|---|
| 개발 호스트 | Rocky Linux 9.8, x86_64, glibc 2.34 |
| Python | uv 관리 CPython 3.12.13 (시스템 Python 3.9는 사용하지 않음) |
| uv | 0.11.8 |
| 엔진 | MarkItDown 0.1.7, `pdf,docx,pptx,xlsx` extras |
| 패키저 | PyInstaller 6.22.2, hooks-contrib 2026.7 |
| Tcl/Tk | Tcl 9.0.3 / Tk 헤더 버전 9.0; 실제 Tk 창은 미검증 |
| 입력 | 자체 제작 PDF, DOCX, PPTX, XLSX, HTML, CSV, TXT |
| 크기 제한 | 제안값 100 MiB; 실제 대형 문서 성능 검증은 미실행 |
| 잠금 | `uv.lock`: 직접·전이 의존성 버전/해시 포함; 목표 OS 호환성 확정은 아님 |

| 목표 환경 | 환경 가용성 | 빌드 | Python 미설치 GUI/CLI·7포맷 |
|---|---|---|---|
| Windows 11 x64 | 없음 | 미실행 | 미실행 |
| macOS 14+ Apple Silicon | 없음 | 미실행 | 미실행 |
| Linux x86_64 (개발 참고용) | 있음, 디스플레이 없음 | CLI/GUI onedir 성공 | CLI 7포맷 성공; GUI 창/깨끗한 호스트 미검증 |

이 표의 Windows/macOS 버전과 CPU는 시험 대상 제안값이다. 정식 지원 선언이 아니다.

## 실행과 증거

아래 명령은 저장소 루트에서 실행했다. `uv` 명령은 `.venv` 환경을 사용한다.
최종 의존성·잠금·ignore·문서 링크·별도 CWD 검사 요약은 [최종 검사 기록](evidence/p0-final-checks.json)에 있다.

| 명령 | 종료 코드 / 결과 | 증거 |
|---|---|---|
| `uv sync --group build` | 0, Python 3.12 환경과 의존성 설치 | `uv.lock` |
| `uv pip check` | 0, 설치된 45개 패키지 호환성 검사 통과 | 아래 요약 |
| `uv run --locked everythingmarkdown-p0 --fixtures tests/fixtures` | 0, 7포맷 핵심 문자열 포함 | [소스 결과](evidence/p0-source-smoke.json) |
| `uv run --locked python -m unittest discover -s tests -v` | 0, 15개 통과 | [테스트](evidence/p0-tests.log) |
| `uv run --locked python -m compileall -q src tests scripts packaging` | 0, 문법 컴파일 검사 | 별도 출력 없음 |
| `uv run --locked --group build python packaging/build_p0.py` | 0, CLI/GUI onedir 생성 | [빌드 로그](evidence/p0-build-linux.log) |
| `dist/everythingmarkdown-p0/everythingmarkdown-p0 --fixtures tests/fixtures` | 0, frozen=true, 7포맷 성공 | [동결 결과](evidence/p0-frozen-smoke.json) |
| `dist/everythingmarkdown-p0-gui/everythingmarkdown-p0-gui` | 3, 디스플레이 없음 | [GUI 결과](evidence/p0-gui-linux.log) |
| `unshare --user --map-root-user --net .venv/bin/python -m unittest discover -s tests -v` | 0, 15개 통과 | [네트워크 격리 테스트](evidence/p0-tests-network-isolated.log) |
| `unshare --user --map-root-user --net dist/everythingmarkdown-p0/everythingmarkdown-p0 --fixtures tests/fixtures` | 0, 7포맷 성공 | [격리 동결 결과](evidence/p0-frozen-network-isolated.json) |

`unshare`는 관리자 권한 상승 없이 현재 사용자의 namespace에서 실행했다.
Python socket 연결/DNS 호출 감시와 별도 OS 네트워크 격리를 병행했다. 이 샘플 범위의 증거이지
임의 문서·네이티브 코드의 모든 네트워크 시도 부재나 전체 A21 통과를 보장하지 않는다.
외부 참조 HTML, 악성·대형 문서, 전체 저장 오류 행렬은 후속 범위다.

테스트는 명시 컨버터 등록, 7포맷 내용 보존, 원본 해시 보존, 잘못된 입력/위장 ZIP/불완전 OOXML,
심볼릭 링크·크기 제한, 한글/대문자 경로, CLI 비TTY·대화형·취소·빈 입력·민감 오류 미노출을 확인한다.
CLI 대화형 분기는 단위 테스트로 검사했으며 목표 OS의 실제 콘솔 검증을 대체하지 않는다.
lint/typecheck는 도구·설정 미선정으로 미실행이다. 불필요한 개발 의존성을 추가하지 않았다.

### 발견한 실패와 조치

- 첫 Linux 동결 GUI 실행은 `libtcl9.0.so` 누락으로 실패했다.
- uv Python의 `sys.base_prefix/lib`를 **빌드 하위 프로세스에만** `LD_LIBRARY_PATH`로 전달하도록
  수정했다. 재빌드 후 Tcl/Tk 공유 라이브러리가 번들에 포함됐으며 기존 ImportError는 해소됐다.
- 이후 실행은 Tk 창 생성 단계에서 디스플레이 부재로 종료 코드 3을 반환했다. 창 성공으로 보지 않는다.
- PyInstaller의 선택 의존성 `jinja2`, Linux에 없는 Windows 라이브러리 `user32`/`msvcrt` 경고는
  남아 있다. 현재 7개 최소 샘플 변환은 통과했지만 목표 OS와 복잡한 문서에서 재검증해야 한다.
- 결과 디렉터리 쓰기 가능 여부는 `os.access` 힌트만 표시한다. 실제 쓰기 검증·저장은 하지 않는다.

## 목표 OS에서 이어서 실행할 절차

각 OS에서 Python 3.12/Tcl/Tk 및 uv를 준비한 후:

```sh
uv sync --locked --group build
uv run --locked python -m unittest discover -s tests -v
uv run --locked everythingmarkdown-p0 --fixtures tests/fixtures
uv run --locked everythingmarkdown-p0-gui
uv run --locked --group build python packaging/build_p0.py
```

- Windows CLI: `dist\everythingmarkdown-p0\everythingmarkdown-p0.exe`
- Windows GUI: `dist\everythingmarkdown-p0-gui\everythingmarkdown-p0-gui.exe`
- macOS CLI: `dist/everythingmarkdown-p0/everythingmarkdown-p0`
- macOS GUI: `dist/everythingmarkdown-p0-gui.app` (예상 경로, 이 호스트에서 미검증)
- `dist`의 실행 파일 하나가 아니라 **onedir 폴더 전체**와 fixture 폴더를 Python 미설치 시험 환경에 복사한다.
- CLI에 `--fixtures <fixture 절대 경로>`를 전달해 7개 결과를 확인한다.
- CLI 인자 없음으로 경로 입력·stdout/stderr·종료 코드·Ctrl+C/EOF를 실제 터미널에서 확인한다.
- GUI 직접 실행/Finder/시작 위치 지정 바로가기에서 창 표시와 CWD를 기록한다.
- 입력·실행 파일·CWD를 서로 다른 폴더로 설정하고 한글/공백 경로, 쓰기 불가 위치도 확인한다.
- 날짜·OS/CPU·명령·종료 코드·로그·GUI 캡처를 추가하고 TODO를 갱신한다.

로컬 시험 빌드는 미서명이며 외부 릴리스가 아니다. Python 없는 깨끗한 머신 검증 없이
개발 Python이나 설치 라이브러리에 대한 독립성을 단정하지 않는다.

## 저장소 골격과 라이선스

- `.gitignore`는 `.omx/`, `.omc/`, 가상환경·캐시·빌드·변환 결과를 제외한다.
- P0 검증 당시 프로젝트는 Git 저장소가 아니었으므로 임시 Git 저장소에서 ignore 규칙을 검사했다.
  이후 사용자 요청으로 Git/GitHub를 구성했으며 현재 저장소 정보는 [진행 현황](../PROGRESS.md)을 따른다.
- `.omx` 제외 후에도 설계 문서가 공유되도록 `docs/design.md`, `docs/test-spec.md`를 보존했다.
- MIT 저작권 표기는 `EverythingMarkdown contributors`로 두었다. 제3자 의존성의 라이선스는 별도다.

## 공식 참고 근거

- [MarkItDown 0.1.7 의존성 정의](https://github.com/microsoft/markitdown/blob/v0.1.7/packages/markitdown/pyproject.toml)
- [MarkItDown 0.1.7 변환 API](https://github.com/microsoft/markitdown/blob/v0.1.7/packages/markitdown/src/markitdown/_markitdown.py)
- [PyInstaller onedir/windowed 사용법](https://pyinstaller.org/en/stable/usage.html)
- [uv 관리 Python](https://docs.astral.sh/uv/guides/install-python/)
