# EverythingMarkdown

Microsoft MarkItDown으로 로컬 파일을 Markdown으로 변환하는 Windows/macOS 앱을 준비하고 있습니다.

> 현재는 **P1 공통 코어·P2 CLI 구현 완료** 단계입니다. 터미널에서 실제 파일을 변환·저장할 수 있으며, 제품용 GUI와 정식 배포판은 준비 중입니다.

## 목표

- GUI 파일 선택 및 터미널 파일 입력 지원
- 원래 파일명을 유지하고 확장자만 `.md`로 변경
- 실행 시작 작업 디렉터리(CWD)의 `convert_result`에 저장, 기존 결과 보존
- 초기 검증 포맷: 텍스트 PDF, DOCX, PPTX, XLSX, HTML, CSV, TXT

## 개발 환경

Python 3.12와 [uv](https://docs.astral.sh/uv/)를 사용합니다.

```sh
uv sync --locked --group build
uv run --locked everythingmarkdown-p0 --fixtures tests/fixtures
uv run --locked everythingmarkdown-p0 tests/fixtures/sample.txt
uv run --locked everythingmarkdown-p0-gui
```

첫 설치에는 인터넷이 필요합니다. GUI 실행에는 Tcl/Tk와 그래픽 디스플레이가 필요합니다.
P0 CLI는 인자가 없으면 터미널에서 파일 경로를 입력받습니다. 변환 성공 여부·문자 수·시작 CWD를
JSON으로 출력하며 **문서 본문 출력이나 `.md` 저장은 하지 않습니다.** GUI는 CWD/Tcl/Tk 확인용
최소 창입니다. 실제 변환·저장 GUI는 P3에서 구현합니다.

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
- 실제 GUI는 P3에서 제공합니다. `everythingmarkdown-p0-gui`는 변환 앱이 아닌 환경 확인용 창입니다.

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
uv run --locked python -m unittest discover -s tests -v
uv run --locked python -m compileall -q src tests scripts packaging
uv run --locked --group build python packaging/build_p0.py
```

빌드는 실행 중인 OS용으로만 생성합니다. Windows/macOS는 해당 OS에서 따로 빌드해야 합니다.
자세한 실행·패키징 절차와 미검증 항목은 [P0 검증 기록](docs/p0-validation.md)을 참고하세요.

## 범위와 한계

- Windows 11 x64 / macOS 14+ Apple Silicon은 **지원 목표**이며 아직 검증되지 않았습니다.
- Linux는 현재 개발 검증 환경이지 배포 지원 약속이 아닙니다.
- 100 MiB 제한은 초기 제안값이며 악성 문서 격리나 자원 사용량 보장이 아닙니다.
- OCR, 이미지·오디오, URL, 일괄 변환, 덮어쓰기, 강제 취소는 현재 범위 밖입니다.
- Markdown은 텍스트/구조 추출 결과이며 원본 레이아웃의 완전 재현을 보장하지 않습니다.
- 현재 P0 프로브는 신뢰할 수 있는 자체 제작 샘플을 위한 도구입니다.

## 진행 계획

P0 로컬 검증·P1 공통 코어·P2 CLI 완료 → P3 GUI → P4 로컬 검증·패키징·배포 준비.
실제 Windows/macOS 환경 테스트는 사용자 요청으로 배포 후 별도 진행하며 현재 개발 선행 조건에서 제외합니다.

- [진행 현황](PROGRESS.md)
- [남은 작업](TODO.md)

## 릴리즈 정책

- [changelog.md](changelog.md)를 버전별 변경 기록과 릴리즈 노트의 단일 원본으로 사용합니다.
- 배포 요청 전에는 버전 항목을 작성하지 않으며, 첫 배포 시 `26.1.0`으로 기록합니다.
- 이후 버전은 `YY.메이저.마이너`, 태그는 `v` 없이 같은 버전명으로 지정합니다.
- 해당 버전의 노트를 annotated tag 주석과 GitHub Release 본문에 동일하게 사용합니다.
- 최종 배포는 Windows 단일 설치 `.exe`(GUI/CUI 실행 파일 포함), macOS 단일 `.app`(GUI/CUI 포함)을 담은 `.zip`입니다.
  파일명과 실행 방식, 검증 조건은 [릴리즈 정책](docs/releasing.md)에 정리했습니다.
- 현재는 P2 개발 단계이며 정식 태그·릴리즈·최종 설치 파일은 없습니다.

## 라이선스

이 프로젝트의 자체 코드는 [MIT License](LICENSE)를 따릅니다.
MarkItDown 및 전이 의존성에는 각각의 라이선스가 적용되며, 번들 배포 전 고지 검토가 필요합니다.
`.omx/`와 `.omc/`는 로컬 작업 기록으로 Git 추적 대상에서 제외합니다.
