# EverythingMarkdown

Microsoft MarkItDown으로 로컬 파일을 Markdown으로 변환하는 Windows/macOS 앱을 준비하고 있습니다.

> 현재는 **P0 기술·배포 검증용 골격**입니다. 완성된 GUI/CLI 변환 앱이나 정식 배포판이 아닙니다.

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

P0 최소 배포 검증 → P1 공통 코어 → P2 CLI → P3 GUI → P4 통합·배포 검증.

- [진행 현황](PROGRESS.md)
- [남은 작업](TODO.md)

## 라이선스

이 프로젝트의 자체 코드는 [MIT License](LICENSE)를 따릅니다.
MarkItDown 및 전이 의존성에는 각각의 라이선스가 적용되며, 번들 배포 전 고지 검토가 필요합니다.
`.omx/`와 `.omc/`는 로컬 작업 기록으로 Git 추적 대상에서 제외합니다.
