# EverythingMarkdown 구현 설계

- 작성일: 2026-09-08
- 상태: 승인된 설계 기준선. P0 착수 현황은 [P0 검증 기록](p0-validation.md) 참고.
- 입력 근거: 기존 사용자 요구사항 R1~R7. 원본 대화·검토 기록은 Git에서 제외한 로컬 `.omx/`에 보관.
- 검증 계약: [테스트 명세](test-spec.md)
- 범위: MVP 설계 기준선. 아래 구현 미착수·설계-only 서술은 작성 당시의 역사적 범위이며, 이후 P0 작업 요청에 따른 실제 상태는 PROGRESS.md를 따른다.

## 1. 요구사항과 설계 기본값

| ID | 사용자 확정 요구사항 | 설계 대응 |
|---|---|---|
| R1 | Microsoft MarkItDown 활용 | 하나의 Python 어댑터에서 MarkItDown 호출 |
| R2 | Windows/macOS 모두 지원 | 공통 Python 코드, OS별 별도 빌드·실행 검증 |
| R3 | GUI와 CUI 모두 제공 | 같은 제품에 GUI/CLI 진입점 2개, 변환 서비스 공유 |
| R4 | 터미널 실행 후 파일명 입력 | 파일 인자 방식과 인자가 없을 때 대화형 입력 모두 제공 |
| R5 | GUI 파일 업로드 창 및 변환 버튼 | 로컬 파일 선택 대화상자 + 변환 버튼. 서버 업로드 아님 |
| R6 | 파일명을 유지한 `.md` 변환 | `Path(input).stem + '.md'`, 예: `report.v2.docx` → `report.v2.md` |
| R7 | 실행 경로의 `convert_result` 저장 | 시작 CWD를 고정해 `<launch_dir>/convert_result/<stem>.md`로 저장 |

다음은 **사용자 확정 사항이 아닌 제안 기본값**이다.

- 로컬 파일 단건 처리. 폴더·일괄 처리·URL 입력·드래그앤드롭은 후속 범위.
- 첫 지원 범위는 텍스트 기반 PDF, DOCX, PPTX, XLSX, HTML, CSV, TXT. 암호화/손상 문서는 정상 변환을 보장하지 않는다.
- 스캔 PDF OCR, 이미지 설명, 오디오 전사, ZIP, 구형 DOC/PPT/XLS, 클라우드 API, 플러그인은 MVP에서 제외.
- 기존 결과가 있으면 실패한다. 자동 접미사와 덮어쓰기는 원래 이름 보존/데이터 안전과 충돌하므로 넣지 않는다.
- 입력 크기 상한은 초기 100 MiB 제안. 실행 시간·메모리 보장은 아니며 실제 샘플 측정 후 조정한다.
- UI는 한국어 우선, 단일 창, OS 기본 테마. 앱은 사용자의 로컬 문서를 수정하지 않는다.

## 2. 핵심 결정 요약 (ADR / RALPLAN-DR)

### 원칙

1. GUI/CLI에서 변환·저장·오류 규칙을 공유한다.
2. 원본과 기존 결과를 보존한다.
3. 사용자에게 결과 저장 위치를 사전에 보여준다.
4. 작은 로컬 도구에 필요한 범위만 구현하고 배포 가능성을 먼저 검증한다.

### 상위 결정 요인

1. Python 기반 MarkItDown과의 통합 비용.
2. Windows/macOS에서 GUI와 터미널 사용성을 함께 제공하는 배포 구조.
3. 적은 의존성·운영 부담과 테스트 가능한 공통 로직.

| 대안 | 장점 | 비용/단점 | 판단 |
|---|---|---|---|
| Python + Tkinter/ttk | Python 표준 GUI 인터페이스, 작은 단일 창에 충분, 별도 JS 런타임 불필요 | Tcl/Tk 번들 확인 필요, 복잡한 UI/디자인 자유도 제한 | **MVP 권장안** |
| Python + PySide6 | 풍부한 위젯, 복잡한 작업 목록·확장에 적합 | 추가 의존성, Qt 배포 크기와 라이선스 준수 검토 | UI 확대가 확정될 때 재검토 |
| Tauri/Electron + Python 프로세스 | 웹 UI 활용 가능 | 프런트엔드·Python 이중 빌드, IPC 및 플랫폼별 sidecar 관리 | 현재 1개 화면에는 비용 과다 |

권장 기술: Python 3.12를 초기 검증 기준으로 두고, Tkinter/ttk, `argparse`, MarkItDown, OS별 PyInstaller 패키징을 검토한다. 이는 **추가 의존성 설치가 아닌 설계 제안**이다. MarkItDown은 조사로 API를 확인한 0.1.7을 초기 고정 버전으로 제안하며, PyInstaller 버전과 전이 의존성 잠금 파일은 패키징 스파이크 통과 후 확정한다. `[all]` 대신 `pdf,docx,pptx,xlsx` extras를 선택한다. 초기 의존성 명세 제안은 `markitdown[pdf,docx,pptx,xlsx]==0.1.7`이다. 이는 설치·플랫폼 실행 검증을 완료했다는 뜻이 아니다.

## 3. 구성과 책임

```text
GUI (Tkinter/ttk) ──┐
                   ├── ConversionService ── MarkItDownAdapter ── MarkItDown
CLI (argparse) ─────┘           │
                               └── 경로 검증 / 출력 저장 / 공통 오류
```

제안 디렉터리 — 현재는 존재하지 않으며 구현 시 생성한다.

```text
pyproject.toml
src/everythingmarkdown/
  __init__.py
  __main__.py            # python -m everythingmarkdown → CLI
  cli.py                # 인자/대화형 입력, 출력 스트림, 종료 코드
  gui.py                # 파일 선택, 상태 표시, 작업 스레드 결과 수신
  service.py            # 요청 검증, 어댑터 호출, 출력 저장
  markitdown_adapter.py # 외부 라이브러리 API와 예외 정규화
  models.py             # 요청·결과·오류 코드의 작은 데이터 모델
tests/
  unit/
  integration/
  fixtures/             # 자체 제작·개인정보 없는 최소 문서
packaging/
  windows.spec
  macos.spec
README.md
DESIGN.md               # P3 GUI 구현 스펙 (이 문서 §6 계약을 구체화)
```

- `ConversionRequest(input_path: Path, launch_dir: Path)` → `ConversionResult(output_path: Path, warnings: tuple[str, ...])`.
- `launch_dir`는 진입점 시작 시 절대 경로로 한 번 캡처한다. 서비스에서 `chdir()`하지 않는다.
- 어댑터는 요청별 `MarkItDown(enable_builtins=False, enable_plugins=False)` 인스턴스를 만들고, 허용 확장자에 대응하는 컨버터 하나만 `register_converter()`로 등록한다. PDF→PdfConverter, DOCX→DocxConverter, PPTX→PptxConverter, XLSX→XlsxConverter, HTML→HtmlConverter, CSV→CsvConverter, TXT→PlainTextConverter의 고정 매핑을 사용한다. 로컬 경로를 `convert_local()`에 전달하고 Markdown 문자열을 반환한다. `convert()`의 URL/URI 자동 처리는 사용하지 않는다. v0.1.7 태그에서 확인한 `result.markdown`을 사용한다. `text_content`는 호환 alias이므로 새 구현에서 사용하지 않는다. GUI/CLI에 외부 라이브러리 객체를 노출하지 않는다.
- 별도 웹 서버·DB·REST API·플러그인 시스템·범용 저장소 추상화는 만들지 않는다.

## 4. 경로와 저장 계약

예: `/work`에서 실행하고 `/docs/report.v2.docx`를 선택하면 `/work/convert_result/report.v2.md`에 저장한다. 입력 파일 폴더 `/docs`나 설치 폴더가 기준이 아니다.

1. **GUI와 CLI 모두 시작 CWD만 저장 기준으로 사용하며 MVP에는 작업 폴더 선택 기능이 없다.** 상대 입력 경로는 시작 `launch_dir` 기준으로 해석한다. CLI 인자의 셸 따옴표 처리는 셸에 맡기고, 대화형 입력은 바깥쪽 짝지어진 따옴표만 제거한다.
2. 파일 존재·일반 파일 여부·지원 확장자(대소문자 무시)·100 MiB 상한을 확인한다. URL과 디렉터리는 거부한다. `zipfile.is_zipfile()`로 일반 ZIP의 확장자 위장을 검사하고, DOCX/PPTX/XLSX만 OOXML 컨테이너 구조(`[Content_Types].xml`과 각각 `word/document.xml`, `ppt/presentation.xml`, `xl/workbook.xml`)를 확인해 허용한다. 다른 확장자의 ZIP이나 OOXML 구조가 아닌 ZIP은 INVALID_INPUT으로 거부하고, 임의 ZIP 컨버터로 우회하지 않는다.
3. 결과 이름은 입력 파일명의 마지막 확장자만 바꾼다. 입력 심볼릭 링크는 초기 MVP에서 거부해 이름/대상 혼동을 피한다.
4. `convert_result`가 없으면 생성한다. 동일 이름의 일반 파일이거나 심볼릭 링크이면 실패한다. 결과 경로가 기존 파일·디렉터리·끊어진 링크여도 충돌로 처리한다.
5. 출력 가능성을 사전 확인하되 실제 생성/쓰기 오류도 처리한다. 읽기 전용 경로에서는 다른 위치로 몰래 우회하지 않는다.
6. MarkItDown 결과가 비었거나 공백뿐이면 `EMPTY_RESULT`로 실패하고 결과 파일을 만들지 않는다. OCR 수행으로 가장하지 않는다.
7. 결과는 UTF-8(애플리케이션이 BOM을 추가하지 않음)과 LF 개행으로 저장한다.
8. 출력은 배타적 생성(`open(..., 'x', encoding='utf-8', newline='\n')`)으로 덮어쓰기를 방지한다. 사전 존재 확인만으로 경쟁 상태를 막았다고 간주하지 않는다.
9. 생성 후 쓰기/닫기 실패 시 이번 요청이 만든 불완전한 결과만 정리한다. 기존 파일은 삭제하지 않는다. 정리 실패 시 경로와 경고를 함께 알린다.
10. 성공 메시지는 파일 닫기까지 성공한 후에만 표시한다. 시스템 종료/전원 장애에 대한 원자적 저장·완전 복구는 MVP 보장 범위가 아니다.

**데스크톱 실행 주의:** Finder/Explorer 바로가기는 터미널과 다른 CWD를 줄 수 있다. GUI에 실제 저장 절대 경로를 항상 표시한다. 기본 실행 경로에 쓰기 권한이 없으면 변환을 막고, 원하는 작업 폴더를 시작 위치로 지정하는 실행 방법을 안내한다. 입력 폴더나 홈으로 자동 변경하지 않는다. Finder 더블클릭만으로 임의의 작업 폴더에 저장하는 UX는 현재 요구에서 확정되지 않았으며 별도 검토 항목이다.

## 5. CLI 계약

P2 구현과 현재 실행 근거는 [CLI 검증 기록](p2-validation.md)을 따른다. 첫 배포 전 `--version`은 숫자 대신 개발 상태를 표시한다. `everythingmarkdown-gui`는 P3에서 구현했다([GUI 설계](../DESIGN.md)).

```text
everythingmarkdown ./report.docx
everythingmarkdown "./회의 자료.pdf"
everythingmarkdown                 # 터미널일 때 파일 경로 1회 입력 요청
everythingmarkdown --help
everythingmarkdown --version
everythingmarkdown-gui             # GUI 별도 진입점
```

- 인자가 없고 stdin이 TTY이면 프롬프트를 표시한다. 빈 입력은 입력 오류, EOF는 취소, Ctrl+C는 종료 코드 130으로 처리한다.
- stdin이 TTY가 아닌데 파일 인자가 없으면 대기하지 않고 사용법 오류로 종료한다. 파일 목록 파이프 처리는 지원하지 않는다.
- 성공: stdout에 결과 절대 경로 1줄, 종료 코드 0. 프롬프트·경고·오류는 stderr. 입력 문서 본문은 stdout/로그에 출력하지 않는다.
- 오류는 사용자용 설명과 안정적인 내부 코드로 통일한다. 기본 화면에 traceback을 노출하지 않는다.

| 종료 코드 | 의미 | 내부 코드 예 |
|---|---|---|
| 0 | 성공 | — |
| 2 | 인자/입력 오류 | INVALID_INPUT, NOT_FOUND, UNSUPPORTED_FORMAT, TOO_LARGE |
| 3 | 변환 실패 | CONVERSION_FAILED, EMPTY_RESULT, MISSING_DEPENDENCY |
| 4 | 결과 경로/저장 실패 | OUTPUT_CONFLICT, OUTPUT_UNWRITABLE, WRITE_FAILED |
| 130 | 사용자 중단 | CANCELLED |

## 6. GUI/UX 계약

```text
┌ EverythingMarkdown ───────────────────────────┐
│ 파일       [선택한 파일 경로             ] [찾아보기] │
│ 저장 위치  /work/convert_result/report.md             │
│ 상태       변환할 파일을 선택해 주세요.                │
│                         [변환]                       │
└──────────────────────────────────────────────────────┘
```

- 최초 파일 미선택: 변환 비활성화. 파일 선택 취소: 기존 선택 유지.
- 선택 완료: 파일 경로와 예상 결과 절대 경로 표시. 저장 경로 오류/충돌도 명확히 안내.
- 변환 중: 파일 선택·변환 버튼 비활성화, 불확정 진행 표시. 정확한 퍼센트는 제공하지 않는다.
- 단일 작업 스레드에서 서비스 실행, `queue.Queue`와 메인 스레드 `after()` 폴링으로 결과를 전달한다. 작업 스레드에서 Tk 위젯을 직접 조작하지 않는다.
- 성공: “변환 완료”와 결과 경로. 실패: 원인과 해결 방법, 선택 파일 유지, 재시도 가능.
- 처리 중 닫기: 작업이 끝나면 창을 닫도록 예약하고 상태로 알린다. 강제 스레드 종료나 처리 중 취소는 제공하지 않는다. 라이브러리 무응답 시 OS 강제 종료가 필요할 수 있는 MVP 한계를 문서화한다.
- 키보드 Tab 이동, 파일 선택과 변환에 명확한 레이블, 색상 외 상태 텍스트, OS 기본 폰트·배율 대응. 좁은 창에서는 경로 표시 영역을 줄이고 전체 경로는 복사 가능한 형태로 유지한다.
- 외부 네트워크·계정·로그인 화면 없음. “업로드” 대신 “파일 선택”을 사용한다.

## 7. 변환 품질·오류·보안 경계

- Markdown은 텍스트/구조 추출 결과이며 원본 레이아웃의 픽셀 단위 복제가 아니다. PDF 표·다단 문서의 읽기 순서와 복잡한 Office 요소는 손실 가능성이 있다.
- 스캔 PDF는 무조건 탐지된다고 가정하지 않는다. 텍스트가 없으면 실패하고, 추출 내용이 있더라도 OCR 완전성을 보장하지 않는다.
- 로컬 경로 입력만 사용하고 기본 컨버터 일괄 등록·선택적 플러그인·LLM·Document Intelligence 설정을 활성화하지 않는다. 어댑터의 단일 컨버터 매핑 밖 ZIP/YouTube/Image/Audio/기타 컨버터를 등록하거나 실패 시 fallback으로 호출하지 않는다. HTML 포함 각 포맷은 네트워크 차단 테스트로 기본 경로를 검증한다. 이는 OS 샌드박스나 악성 문서 안전성 보장이 아니다.
- 변환기에 입력을 셸 명령 문자열로 넘기지 않는다. `convert_result` 밖 사용자 지정 출력 기능도 MVP에는 없다.
- 파일 크기 제한은 완화책일 뿐 압축 해제 폭탄·악성 파서 입력·CPU/메모리 고갈을 막는 보안 경계가 아니다. 신뢰하지 않는 문서의 강한 격리는 후속 프로세스 격리/리소스 제한 설계가 필요하다.
- 문서 내용·원문을 영구 로그에 남기지 않는다. 오류 코드와 상태만 UI/CLI로 제공하고, 원시 파서 예외의 민감 문자열을 사용자 메시지에 그대로 복사하지 않는다.
- 경로 검증과 파일 생성 사이 외부 프로세스가 디렉터리를 교체하는 공격까지 방어하는 샌드박스는 제공하지 않는다. 로컬 단일 사용자 도구를 전제로 한다.

## 8. 배포와 호환성

최종 배포 파일과 버전·태그·노트 규칙은 후속 사용자 요구를 반영한 [릴리즈 정책](releasing.md)을 따른다.
아래 onedir/분리 실행물은 P0 검증 형태이며 최종 사용자 배포 패키지와 구분한다.

- 개발 기준 Python 3.12, OS 지원 목표 Windows 11 x64 / macOS 14+ Apple Silicon. Windows ARM64·macOS Intel·이전 OS는 사용자 확정 요구가 아니며 필요 시 별도 빌드/검증을 추가한다.
- 릴리스 지원표는 실제 CI/실기기 패키징 결과를 근거로 확정한다. Linux 개발 머신의 테스트만으로 Windows/macOS 지원 완료를 선언하지 않는다.
- 초기 패키징은 PyInstaller one-directory 형태를 우선 검증한다. GUI와 console CLI는 같은 제품 배포물의 별도 실행 파일로 제공해 Windows의 stdout/stdin과 창 숨김 충돌을 피한다.
- Windows: GUI 실행 파일 + console CLI + 의존 파일을 포함한 폴더 배포. PATH 자동 변경 없음. CLI는 절대 경로나 사용자가 설정한 PATH로 실행.
- macOS: GUI `.app`과 터미널용 CLI 실행물을 포함한 배포 묶음. 앱/CLI 각각 필요한 리소스를 번들하고 개발 Python/Tcl 환경에 의존하지 않는지 확인한다.
- PyInstaller는 대상 OS에서 별도 빌드한다. Tcl/Tk, 포맷별 데이터/동적 import 수집은 실제 frozen 실행으로 검증한다.
- 코드서명·notarization·인증서는 정식 외부 배포 단계의 별도 작업이다. 이번 설계/로컬 개발에서 자격증명이나 외부 게시 작업을 수행하지 않는다. 미서명 빌드에는 OS 경고가 있을 수 있다.
- 서드파티 라이선스/고지와 포맷 extras별 의존성을 릴리스 전에 확인한다. GUI 프레임워크 변경은 기본 스택 패키징 실패 또는 제품 범위 확대 시에만 재검토한다.

## 9. 구현 단계와 완료 조건

**후속 범위 변경 (2026-09-08):** 사용자 요청으로 아래 표의 목표 OS 실환경 테스트는 배포 후 별도 단계로 이관한다. P0 로컬 검증으로 P1을 시작하며, 로컬 자동 테스트·정적 검사·목표 OS별 파일 빌드는 유지한다. 아래 표는 원래 설계 기준선이고 현재 착수/완료 조건은 [TODO](../TODO.md)와 [릴리즈 정책](releasing.md)을 따른다. 미검증 항목은 통과로 처리하지 않는다.

| 단계 | 작업/예정 파일 | 검증 및 다음 단계 조건 |
|---|---|---|
| P0 배포 스파이크 | 임시 최소 어댑터, Tk 창, `packaging/*`, 호환성 기록 | 각 목표 OS에서 Python 미설치 환경으로 GUI 창과 CLI 입출력, 7개 포맷 fixture 변환 성공. 실패 포맷/OS는 몰래 제외하지 말고 설계 수정 |
| P1 공통 코어 | `models.py`, `service.py`, `markitdown_adapter.py`, 단위 테스트 | 경로/확장자/충돌/권한/빈 결과/쓰기 실패 테스트 통과; 외부 엔진은 단위 테스트에서 대체 |
| P2 CLI | `cli.py`, `__main__.py`, 패키지 진입점 | 인자·TTY 입력·비TTY·종료 코드·한글/공백 경로 검증 |
| P3 GUI | `gui.py`, `DESIGN.md` | 상태 전이, 메인 스레드 갱신, 중복 요청 방지, 닫기 예약, 키보드 동작 검증 |
| P4 통합/배포 | OS별 번들 설정, fixtures, `README.md`, 잠금 파일 | 실제 엔진/배포물 포맷 행렬, CWD 일치, read-only·충돌·네트워크 차단 검증, 라이선스/서명 현황 문서화 |

단일 구현 담당자가 순차 진행하면 충분하다. 코어 계약이 안정된 후에만 GUI/CLI를 독립 담당자로 나눌 수 있다. 검증 담당자는 소스 실행과 frozen 실행을 구분해 보고한다. 이번 작업의 종료 조건은 설계·테스트 명세와 순차 검토 결과가 저장되는 것이며, 구현 착수는 이번 요청에 포함하지 않는다.

## 10. 위험과 열린 결정

| 항목 | 기본 대응/결정 시점 |
|---|---|
| GUI 실행 CWD가 쓰기 불가 | 실제 경로 표시·명확한 오류, P0에서 Finder/Explorer 검증. 작업 폴더 선택 UX 추가는 저장 규칙 변경 검토 필요 |
| Tk/포맷 의존성 번들 누락 | P0에서 전체 7개 포맷 frozen smoke, 버전 고정은 통과 후 |
| 문서 추출 품질 편차 | 의미 중심 fixture 검사, OCR/레이아웃 충실도 보장 금지 |
| 대형/악성 파일로 긴 처리 | 100 MiB 상한, 변환 중 UI 유지; 하드 타임아웃/프로세스 격리는 후속 범위 |
| 기존 결과와 이름 충돌 | 무조건 보존·실패, 이름 변경/덮어쓰기 UX는 후속 결정 |
| OS/CPU 실제 사용자 범위 | 제안 지원표를 구현 시작 시 확인. 미검증 플랫폼을 지원 완료로 표시하지 않음 |
| 배포 신뢰와 라이선스 | 정식 배포 전에 서명/공증 및 고지 검토 |

## 11. 공식 근거

조사일 2026-09-08. 아키텍처와 제품 정책은 공식 라이브러리 기능이 아니라 이 프로젝트의 설계 제안이다. API는 v0.1.7 태그 소스로 확인했다. 문서에 나오는 플랫폼 지원은 실제 앱 배포 검증과 구분한다.

- [MarkItDown README](https://github.com/microsoft/markitdown): Python 3.10+, 포맷별 optional dependencies, 라이브러리/CLI 용도 및 데스크톱 앱 별도 프로젝트 방침. R1 및 extras 선택 근거.
- [MarkItDown PyPI](https://pypi.org/project/markitdown/): 릴리스/요구 Python/의존성 메타데이터. [v0.1.7 공식 릴리스](https://github.com/microsoft/markitdown/releases/tag/v0.1.7)와 API를 확인했으며 앱 실행 검증은 아직 하지 않았다.
- [MarkItDown 변환 진입점 소스](https://github.com/microsoft/markitdown/blob/v0.1.7/packages/markitdown/src/markitdown/_markitdown.py): `convert()`의 URI 처리와 `convert_local()` 구분. 로컬 입력 경계를 어댑터에 두는 근거.
- [MarkItDown 결과 객체 소스](https://github.com/microsoft/markitdown/blob/v0.1.7/packages/markitdown/src/markitdown/_base_converter.py): v0.1.7에서 `markdown` 필드 및 `text_content` 호환 alias 확인.
- [Python Tkinter](https://docs.python.org/3/library/tkinter.html): Tcl/Tk 인터페이스, 이벤트 루프/스레딩 모델. 표준 GUI 선택 및 메인 스레드 UI 처리 근거.
- [Python argparse](https://docs.python.org/3/library/argparse.html): 기본 CLI 인자 파싱 기능. 별도 CLI 프레임워크를 추가하지 않는 근거.
- [PyInstaller 사용법](https://pyinstaller.org/en/stable/usage.html), [공식 패키지 설명](https://pypi.org/project/pyinstaller/): console/windowed 빌드 및 대상 OS별 빌드 제약. 별도 진입점과 OS별 스파이크 근거.
- [Qt for Python](https://doc.qt.io/qtforpython-6/), [PySide6 패키지](https://pypi.org/project/PySide6/): Qt GUI 대안 및 라이선스 검토 범위.
- [Tauri sidecar](https://v2.tauri.app/develop/sidecar/), [Electron 프로세스 모델](https://www.electronjs.org/docs/latest/tutorial/process-model): Python 외부 프로세스/웹 UI 대안의 통합 비용 판단 근거.
