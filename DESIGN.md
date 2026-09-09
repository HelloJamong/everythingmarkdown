# EverythingMarkdown GUI 설계 (P3)

- 작성일: 2026-09-09
- 상태: P3 착수. [구현 설계](docs/design.md) §3~§7의 GUI/UX 계약을 구현용으로 구체화한다.
- 상위 계약: [design.md](docs/design.md) · [검증 명세](docs/test-spec.md) A02 / A05 / A17 / A18
- 시각 기준: [docs/gui-mockup.html](docs/gui-mockup.html)
  — 레이아웃·문구·상태 흐름의 기준. 최종 렌더링은 네이티브 Tkinter/ttk 위젯이며
  목업의 둥근 모서리·그림자·색상은 OS 기본 테마 안에서 근사치로만 따른다.

## 1. 범위

- GUI는 P1 `ConversionService`를 감싸는 **얇은 단일 창**이다. 변환·경로·저장·오류 규칙을 다시 구현하지 않는다.
- 단건 로컬 파일 → `<launch_dir>/convert_result/<stem>.md`.
- **범위 밖(design.md §1·§6과 동일):** 드래그앤드롭, 폴더/일괄 입력, 출력 형식·품질 선택, 작업 폴더 선택,
  네트워크·계정·로그인, 정확한 진행률(%), 변환 중 취소, 강제 스레드 종료.
- "업로드"가 아니라 "파일 선택/찾아보기"를 쓴다. 서버 전송이 아니다.

## 2. 진입점

- 파일: `src/everythingmarkdown/gui.py`, `main() -> int`.
- `pyproject.toml`의 `[project.gui-scripts]`에 `everythingmarkdown-gui = "everythingmarkdown.gui:main"` 추가.
  기존 `everythingmarkdown-p0-gui`(P0 환경 프로브)와 별개로 유지한다.
- 시작 시 `Path.cwd()`를 **한 번** 캡처해 `launch_dir`로 고정한다. 프롬프트·변환 이후 재계산하지 않는다.
- `tkinter` 임포트 실패 또는 `tk.Tk()`가 `TclError`(디스플레이/Tcl·Tk 없음): stderr에 안내 후 코드 3 반환.
- `Path.cwd()`가 `OSError`(시작 폴더 삭제 등): stderr 안내 후 코드 3. `cli.py`와 동일하게 처리한다.
- 정상 종료 코드 0. CLI와 달리 GUI는 종료 코드로 변환 결과를 구분하지 않는다(오류는 창 안에서 안내).

### 아이콘

원본: `assets/logo.ico`(사용자 제공, 256×256 RGBA). 파생 자산은 여기서 생성한다.

| 파일 | 용도 | 로딩 방식 |
|---|---|---|
| `src/everythingmarkdown/logo.png` | GUI 창 아이콘(런타임) | `importlib.resources.files("everythingmarkdown") / "logo.png"` → `tk.PhotoImage(file=...)` → `root.iconphoto(True, img)`. Tk 8.6는 PNG를 직접 읽는다. `.ico`는 `PhotoImage`가 못 읽으므로 PNG를 쓴다 |
| `assets/logo.ico` | Windows 실행 파일 아이콘(P4) | PyInstaller `--icon assets/logo.ico` |
| `assets/logo.icns` | macOS `.app` 아이콘(P4) | PyInstaller `--icon assets/logo.icns` |

- `pyproject.toml`의 `[tool.setuptools.package-data]`에 `logo.png`를 포함해 설치·frozen 양쪽에서 찾히게 한다.
- 아이콘 로딩 실패(리소스 누락 등)는 조용히 무시하고 기본 아이콘으로 진행한다 — 변환 기능과 무관하다.
- `PhotoImage` 객체 참조를 창이 살아 있는 동안 유지한다(GC되면 아이콘이 사라짐).

## 3. 창 레이아웃

```
┌ EverythingMarkdown ─────────────────────────────┐
│  EverythingMarkdown                              │
│  로컬 파일을 Markdown으로 변환합니다.              │
│                                                 │
│  파일                                            │
│  [ /docs/report.v2.docx            ] [ 찾아보기 ] │
│                                                 │
│  저장 위치                                        │
│  [ /work/convert_result/report.v2.md ] [ 복사 ]  │
│                                                 │
│  상태                                            │
│  ● 변환할 준비가 되었습니다.                       │
│                                                 │
│  지원 형식  PDF · DOCX · PPTX · XLSX · HTML · CSV · TXT │
│                                                 │
│  [        변환        ] [ 초기화 ]  ( [진행바] )  │
└─────────────────────────────────────────────────┘
```

| 영역 | 위젯 | 동작 |
|---|---|---|
| 창 제목 | `root.title("EverythingMarkdown")` | 고정 |
| 파일 | `ttk.Entry`(readonly) + `ttk.Button` "찾아보기" | 버튼 → `filedialog.askopenfilename`, 필터 `[("지원 형식","*.pdf *.docx *.pptx *.xlsx *.html *.csv *.txt"),("모든 파일","*.*")]`. 선택 경로 전체를 Entry에 표시 |
| 저장 위치 | `ttk.Entry`(readonly) + `ttk.Button` "복사" | 파일 선택 전엔 `<launch_dir>/convert_result/`, 선택 후엔 예상 결과 절대 경로. "복사" → 클립보드에 전체 경로 |
| 상태 | `ttk.Label` (기호 + 텍스트) | 색만으로 구분하지 않음. §4·§8 참조 |
| 지원 형식 | 정적 `ttk.Label` | `PDF · DOCX · PPTX · XLSX · HTML · CSV · TXT` |
| 액션 | `ttk.Button` "변환"(기본) + `ttk.Button` "초기화" | §4의 활성 규칙 |
| 진행 | `ttk.Progressbar(mode="indeterminate")` | RUNNING에서만 표시·`start()`, 그 외 `stop()`·숨김 |

- 저장 경로 계산은 서비스와 동일하게 `launch_dir / "convert_result" / (stem + ".md")`.
  UI 표시는 미리보기이며, 실제 충돌·권한 판정은 변환 시 서비스가 한다.

## 4. 상태 기계

| 상태 | 진입 | 파일 Entry / 찾아보기 / 초기화 | 변환 버튼 | 진행바 | 상태 텍스트 |
|---|---|---|---|---|---|
| IDLE | 시작, 초기화 | 활성 | **비활성** | 숨김 | `변환할 파일을 선택해 주세요.` |
| READY | 찾아보기 성공, 새 파일 선택 | 활성 | **활성** | 숨김 | `변환할 준비가 되었습니다.` |
| RUNNING | 변환 클릭 | **비활성** | **비활성** | 표시·구동 | `변환 중입니다…` |
| SUCCESS | 워커 결과 `ok` | 활성 | 활성 | 숨김 | `변환 완료 · <결과 경로>` (+ 경고) |
| ERROR | 워커 결과 `error` | 활성 | 활성 | 숨김 | `<메시지> (코드: <CODE>)` (+ 경로·경고) |

- **버튼 활성 규칙:** `변환` = 파일 선택됨 **and** not RUNNING. `찾아보기`·`초기화`·`복사` = not RUNNING.
- **찾아보기 취소:** 반환값이 빈 문자열이면 아무 것도 바꾸지 않는다(이전 선택·상태 유지).
- **선택 시 사전 안내(best-effort):** 파일 선택 후 예상 결과 경로가 이미 존재하면(`output.exists()` 또는 dangling link)
  상태에 `이미 같은 이름의 결과가 있습니다. 변환 시 기존 결과를 보존하고 실패합니다.`를 표시한다.
  변환 버튼은 막지 않는다 — 충돌의 최종 판정과 경쟁 방지는 서비스의 배타적 생성이 담당한다(중복 구현 금지).
- **SUCCESS 이후:** 선택 파일을 유지하므로 그대로 다시 "변환"하면 `OUTPUT_CONFLICT`가 나는 것이 정상이다.
  새 파일을 고르면 READY로, "초기화"는 IDLE로.
- **ERROR 이후:** 선택 유지, 즉시 재시도 가능(READY와 동일 활성). 원문·traceback은 표시하지 않는다.

## 5. 스레드 모델

- "변환" 클릭 → RUNNING 진입 → `threading.Thread(target=worker, daemon=True)` **1개만** 시작.
  RUNNING 가드 플래그로 중복 시작을 막는다(버튼 비활성 + 플래그 이중).
- 워커: `ConversionService().convert(ConversionRequest(input_path, launch_dir))` 실행 후
  결과를 `queue.Queue`에 넣는다. **워커는 Tk 위젯을 절대 만지지 않는다.**
  - `("ok", ConversionResult)`
  - `("error", ConversionError)`
  - `("error", None)` — 예상 밖 예외(메시지는 `CONVERSION_FAILED` 문구로 대체)
- 메인 스레드: `root.after(100, _poll)`로 큐를 비우고 상태 전이. 큐가 비어 있으면 `after`를 다시 예약.
- 서비스 호출부(`worker`)와 위젯 갱신부(`_apply_*`)를 분리해, 이벤트 루프 없이 상태 로직만 테스트할 수 있게 한다.

## 6. 창 닫기 (`WM_DELETE_WINDOW`)

- IDLE / READY / SUCCESS / ERROR: 즉시 `root.destroy()`.
- RUNNING: `_close_requested = True`로 예약하고 창을 유지, 상태에 `변환이 끝나면 창을 닫습니다.` 표시.
  `_poll`이 워커 결과를 받으면 결과를 상태에 반영한 뒤 `root.destroy()`.
- 강제 스레드 종료·변환 중 취소는 제공하지 않는다. 라이브러리 무응답 시 OS 강제 종료가 필요할 수 있음을 README에 적는다.

## 7. 접근성 · 배율 · 좁은 창

- Tab 이동 순서: 파일 Entry → 찾아보기 → 저장 위치 Entry → 복사 → 변환 → 초기화. "변환"이 기본 버튼.
- 상태는 색 + 기호(`●` `⏳` `✓` `⚠`) + 한국어 텍스트로 3중 표현한다. 색만으로 의미를 전달하지 않는다.
- `ttk` 기본 테마·폰트를 쓰고 픽셀 폰트 크기를 고정하지 않는다(OS 배율 대응).
- `root.minsize(...)` 설정, 그리드 `columnconfigure(weight=1)`로 리사이즈 시 Entry가 늘어나게 한다.
- 경로 Entry는 readonly라 좁아져도 좌우 스크롤·전체 선택 복사가 되고, 별도 "복사" 버튼도 둔다.
- 시작 경로가 쓰기 불가면 변환이 `OUTPUT_UNWRITABLE`로 실패하고
  `쓰기 가능한 폴더에서 실행해 주세요.`를 덧붙인다. 다른 폴더로 자동 우회하지 않는다.

## 8. 문구 사전

| 키 | 문자열 |
|---|---|
| 창 제목 | `EverythingMarkdown` |
| 부제 | `로컬 파일을 Markdown으로 변환합니다. 기존 결과는 덮어쓰지 않습니다.` |
| 버튼 | `찾아보기` · `복사` · `변환` · `초기화` |
| 라벨 | `파일` · `저장 위치` · `상태` |
| 지원 형식 | `지원 형식  PDF · DOCX · PPTX · XLSX · HTML · CSV · TXT` |
| IDLE | `변환할 파일을 선택해 주세요.` |
| READY | `변환할 준비가 되었습니다.` |
| RUNNING | `변환 중입니다…` |
| 닫기 예약 | `변환이 끝나면 창을 닫습니다.` |
| SUCCESS | `변환 완료 · {output_path}` |
| 경고 | `경고: {warning}` (SUCCESS·ERROR에 이어서) |
| ERROR | `{message} (코드: {code})` — `message`는 `ConversionError`의 메시지, `code`는 `ErrorCode` |
| ERROR 경로 | `경로: {error.path}` (있을 때) |
| 쓰기 불가 보강 | `쓰기 가능한 폴더에서 실행해 주세요.` |
| Tcl/Tk 없음 | `GUI 실행에는 Tcl/Tk와 그래픽 디스플레이가 필요합니다.` (stderr) |

- 에러 메시지·코드는 `everythingmarkdown.models._ERROR_DETAILS`를 그대로 재사용한다(별도 사전 만들지 않음).

## 9. 자동 테스트 (`tests/unit/test_gui.py`, 헤드리스)

가짜 서비스/큐를 주입해 이벤트 루프 없이 상태 로직만 검증한다.

- 전이: IDLE → READY → RUNNING → SUCCESS / ERROR, 각 상태의 버튼 활성 플래그·상태 텍스트.
- 찾아보기 취소(빈 반환) 시 선택·상태 불변.
- RUNNING 중 "변환" 재요청이 무시되고 스레드가 1개만 생성됨.
- 각 `ErrorCode` 및 예상 밖 예외가 ERROR 문구로 안전하게 매핑됨(원문·traceback 없음).
- 닫기: 비RUNNING은 즉시 destroy, RUNNING은 예약 후 결과 수신 시 destroy.
- 워커가 위젯을 만지지 않음(워커는 큐에만 접근하는 구조로 보장, 리뷰로 확인).
- **A17 / A18의 실제 Tk 창·이벤트 루프·키보드·배율은 배포 후 실환경 테스트로 이관**한다.

### A02 (GUI/CLI 결과 일치)

- 통합 테스트에서 동일 fixture·동일 `launch_dir`로 GUI의 변환 함수와 CLI를 각각 실행하고
  결과 파일의 상대 위치·이름·바이트를 비교한다.

## 10. pyproject 변경 요약

- `[project.gui-scripts]`에 `everythingmarkdown-gui = "everythingmarkdown.gui:main"` 추가.
- 새 런타임 의존성 없음(`tkinter`는 표준 라이브러리).
