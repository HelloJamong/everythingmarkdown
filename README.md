# EverythingMarkdown

Microsoft MarkItDown으로 로컬 파일을 Markdown으로 변환하는 Windows/macOS 앱을 준비하고 있습니다.

> 현재는 **P1 공통 코어·P2 CLI·P3 GUI 구현 완료** 단계입니다. 터미널과 데스크톱 창에서 실제 파일을 변환·저장할 수 있으며, 정식 배포판(Windows/macOS 서명 빌드)은 준비 중입니다.

## 목표

- GUI 파일 선택 및 터미널 파일 입력 지원
- 원래 파일명을 유지하고 확장자만 `.md`로 변경
- 실행 시작 작업 디렉터리(CWD)의 `convert_result`에 저장, 기존 결과 보존
- 초기 검증 포맷: 텍스트 PDF, DOCX, PPTX, XLSX, HTML, CSV, TXT

## 개발 환경

Python 3.12와 [uv](https://docs.astral.sh/uv/)를 사용합니다.

```sh
uv sync --locked --group dev --group build
uv run --locked everythingmarkdown ./report.docx      # CLI
uv run --locked everythingmarkdown-gui                # GUI 창
uv run --locked everythingmarkdown-p0 --fixtures tests/fixtures   # P0 환경 프로브
```

첫 설치에는 인터넷이 필요합니다. GUI 실행에는 Tcl/Tk와 그래픽 디스플레이가 필요합니다.
`everythingmarkdown-p0*`는 CWD/Tcl/Tk 확인용 프로브이며 `.md`를 저장하지 않습니다.

## GUI 사용법 (P3)

```sh
uv run --locked everythingmarkdown-gui
```

- 한 개의 창에서 **찾아보기**로 파일을 고르고 **변환**을 누릅니다. 서버 업로드가 아닙니다.
- 창에 항상 **예상 저장 경로**(`<시작 CWD>/convert_result/<원래 이름>.md`)를 표시하고, **복사** 버튼을 제공합니다.
- 상태 줄에 준비/변환 중/성공/실패를 색·기호·한국어 텍스트로 함께 표시합니다.
- 변환 중에는 버튼이 잠기고, 그때 창을 닫으면 변환이 끝난 뒤 닫힙니다. 변환 중 강제 취소는 없습니다.
- 기존 결과가 있으면 그대로 두고 실패합니다. CLI와 동일한 저장 규칙·오류 코드를 씁니다.
- 시작 폴더에 쓰기 권한이 없으면 변환을 막고 안내합니다. 다른 폴더로 몰래 저장하지 않습니다.
- 화면 레이아웃·문구·상태 흐름의 기준: [DESIGN.md](DESIGN.md) · 시각 목업: [docs/gui-mockup.html](docs/gui-mockup.html).

상세 상태 기계와 스레드 모델은 [DESIGN.md](DESIGN.md)를 참고하세요.

> GUI가 창 없이 즉시 종료되면(코드 3) Tcl/Tk 또는 그래픽 디스플레이가 없는 환경입니다.
> 배포판에서 이 현상이 보이면 번들에 Tcl/Tk가 빠진 것이므로, 터미널에서
> `everythingmarkdown-cli`로 실행해 원인 메시지를 확인하세요.

## CLI 사용법 (P2)

```sh
uv run --locked everythingmarkdown ./report.docx
uv run --locked everythingmarkdown "./회의 자료.pdf"
uv run --locked everythingmarkdown                  # 터미널에서 파일 경로 입력
uv run --locked python -m everythingmarkdown ./report.docx
uv run --locked everythingmarkdown --help
uv run --locked everythingmarkdown --version
```

- 결과는 **시작 작업 디렉터리**의 `convert_result/<원래 이름>.md`에 UTF-8/LF로 저장됩니다.
- 기존 결과는 덮어쓰지 않습니다. 성공 시 stdout에는 결과 절대 경로 한 줄만 출력합니다.
- 프롬프트·경고·오류는 stderr로 출력합니다. 터미널이 아닌 환경에서 인자를 생략하면 대기하지 않고 종료합니다.
- 대화형 입력은 경로 바깥의 짝지어진 따옴표를 제거합니다. 인자 방식의 따옴표 처리는 셸에 맡깁니다.
- `--version`은 현재 `EverythingMarkdown (개발 중; 정식 릴리즈 없음)`을 표시합니다. 배포 버전을 새로 부여하지 않습니다.
- 종료 코드: 성공 `0`, 입력/사용법 오류 `2`, 변환 실패 `3`, 저장 실패 `4`, Ctrl+C/EOF 취소 `130`.
- GUI는 `everythingmarkdown-gui`입니다. `everythingmarkdown-p0-gui`는 변환 앱이 아닌 환경 확인용 창입니다.

상세 검증: [P2 검증 기록](docs/p2-validation.md).

## P1 공통 코어 사용 예

프로젝트 환경에서 Python API로도 변환·저장할 수 있습니다. P2 CLI는 이 공통 서비스를 사용합니다.

```python
from pathlib import Path
from everythingmarkdown import ConversionRequest, ConversionService

launch_dir = Path.cwd()  # 프로그램 시작 시 한 번 캡처
result = ConversionService().convert(
    ConversionRequest(input_path=Path("report.docx"), launch_dir=launch_dir)
)
print(result.output_path)  # <launch_dir>/convert_result/report.md
```

일반 로컬 파일만 허용하며 기존 결과는 덮어쓰지 않습니다. 결과는 UTF-8/LF로 저장하고,
오류는 `ConversionError.code`, `exit_code`, `path`, `warnings`로 확인합니다.
실패 후 정리가 불가능한 경우 `path`와 `warnings`에 확인할 결과 위치와 경고를 제공합니다.
자세한 구현·검증 범위: [P1 검증 기록](docs/p1-validation.md).

## 검증 및 시험 빌드

```sh
uv run --locked --group dev pytest -q          # 전체 테스트
uv run --locked --group dev ruff check .        # lint
uv run --locked --group dev mypy                # 타입체크 (src)
uv run --locked --group build python packaging/build_release.py   # 현재 OS 배포물 + zip
```

빌드는 실행 중인 OS용으로만 생성합니다. Windows `.exe`와 macOS `.app`은 각 OS(또는 CI:
`.github/workflows/build.yml`)에서 따로 빌드해야 하며, Linux 빌드는 배포물이 아닙니다.
수용 기준 현황은 [A01~A26 매트릭스](docs/acceptance-matrix.md), 패키징 규칙은
[릴리즈 정책](docs/releasing.md)을 참고하세요.

## 범위와 한계

- Windows 11 x64 / macOS 14+ Apple Silicon은 **지원 목표**이며 아직 검증되지 않았습니다.
- Linux는 현재 개발 검증 환경이지 배포 지원 약속이 아닙니다.
- 100 MiB 제한은 초기 제안값이며 악성 문서 격리나 자원 사용량 보장이 아닙니다.
- OCR, 이미지·오디오, URL, 일괄 변환, 덮어쓰기, 강제 취소는 현재 범위 밖입니다.
- Markdown은 텍스트/구조 추출 결과이며 원본 레이아웃의 완전 재현을 보장하지 않습니다.
- 현재 P0 프로브는 신뢰할 수 있는 자체 제작 샘플을 위한 도구입니다.

## 진행 계획

P0 로컬 검증·P1 공통 코어·P2 CLI·P3 GUI 완료 → **P4 패키징·배포 준비 (진행 중)**.
P4의 설정·문서·빌드 스크립트·CI 초안은 작성했고, Windows/macOS 실제 배포물 빌드와 서명은 각 OS/CI에서 수행합니다.
실제 Windows/macOS 환경 테스트는 사용자 요청으로 배포 후 별도 진행하며 현재 개발 선행 조건에서 제외합니다.
라이선스 고지 초안: [docs/third-party-licenses.md](docs/third-party-licenses.md).

- [진행 현황](PROGRESS.md)
- [남은 작업](TODO.md)

## 릴리즈 정책

- [changelog.md](changelog.md)를 버전별 변경 기록과 릴리즈 노트의 단일 원본으로 사용합니다.
- 배포 요청 전에는 버전 항목을 작성하지 않으며, 첫 배포 시 `26.1.0`으로 기록합니다.
- 이후 버전은 `YY.메이저.마이너`, 태그는 `v` 없이 같은 버전명으로 지정합니다.
- 해당 버전의 노트를 annotated tag 주석과 GitHub Release 본문에 동일하게 사용합니다.
- 최종 배포는 Windows/macOS 모두 `.zip`입니다. Windows는 GUI/CUI 실행 파일과 리소스를 담은 폴더,
  macOS는 GUI/CUI를 포함한 단일 `.app`입니다. 별도 설치기는 만들지 않습니다.
  파일명과 실행 방식, 검증 조건은 [릴리즈 정책](docs/releasing.md)에 정리했습니다.
- 현재는 P4 개발 단계이며 정식 태그·릴리즈·최종 배포 파일은 없습니다.

## 라이선스

이 프로젝트의 자체 코드는 [MIT License](LICENSE)를 따릅니다.
MarkItDown 및 전이 의존성 라이선스 목록은 [docs/third-party-licenses.md](docs/third-party-licenses.md)에
정리했으며(초안), 모두 허용형입니다. 배포물에 각 원문 고지를 포함하는 작업이 남아 있습니다.
`.omx/`와 `.omc/`는 로컬 작업 기록으로 Git 추적 대상에서 제외합니다.
