# EverythingMarkdown To-do

- 최종 정리일: 2026-09-09
- 현재 상태: P0 로컬 검증·P1 공통 코어·P2 CLI·**P3 GUI 완료**, 진행 중은 **P4 패키징·배포 준비**. 실환경 테스트는 배포 후 별도 단계로 이관했다.
- 관련 문서: [진행 현황](PROGRESS.md) · [구현 설계서](docs/design.md) · [GUI 설계](DESIGN.md) · [검증 명세](docs/test-spec.md) · [A01~A26 현황](docs/acceptance-matrix.md)
- 순서: P3 GUI(완료) → **P4 설정·문서·빌드 초안(진행 중)** → OS/CI 배포물 빌드·서명 → 배포 후 실환경 테스트.
- 기준 커밋: `ae9dac6` 이후 P3/P4 작업분(미커밋).
- 검증 근거: `uv run --group dev pytest` 전체 126개 통과(unittest subTest 포함), `ruff check`·`mypy` 통과 (2026-09-09 실행).
- 배포 요청 전에는 버전 항목·태그·Release를 만들지 않는다. 첫 배포 시 `26.1.0`으로 기록한다.
- 2026-09-09 결정: Windows도 설치기 없이 **ZIP 배포**로 통일. lint=`ruff`, typecheck=`mypy` 채택.

## 단계별 상태

| 단계 | 상태 | 다음 조치 |
|---|---|---|
| 준비·저장소·정책 | 완료 | 배포 요청 전 버전 미작성 유지 |
| P0 로컬 기술 검증 | 완료 | 목표 OS 빌드는 P4, 실환경 실행은 배포 후로 이관 |
| P1 공통 코어 | 완료 | P3 GUI에서도 동일 서비스 사용 |
| P2 CLI | 완료 | GUI 구현 후 공통 동작 회귀 검증 |
| P3 GUI | **완료** | `gui.py`·헤드리스 테스트·`everythingmarkdown-gui` 진입점·아이콘 연결 완료 |
| P4 통합·패키징 | **진행 중** — 설정·문서·spec·CI 초안 완료 | OS/CI에서 실제 Windows `.exe`·macOS `.app` 빌드, 서명·공증, 라이선스 원문 포함 |
| 릴리즈 게시 | 사용자 배포 요청 대기 | 첫 릴리즈 노트·버전·태그·배포 파일 게시 |
| 실환경 테스트 | 배포 후 이관 | 현재 개발 선행 조건에서 제외 |

## 완료한 준비 작업

- [x] 이전 대화의 프로젝트 요구사항 R1~R7 정리.
- [x] 기술 대안 비교와 공식 MarkItDown API 근거 조사.
- [x] GUI/CLI 공통 구조, 저장·오류·배포 정책 설계.
- [x] 수용 기준 A01~A26 및 계층별 검증 방식 작성.
- [x] Architect 보완 검토와 후속 Critic 검토 완료.
- [x] 진행 현황 및 단계별 To-do 문서 작성.
- [x] README·MIT LICENSE·Git ignore 규칙 작성; `.omx/`·`.omc/`·가상환경·빌드 결과 제외.
- [x] GitHub 비공개 저장소 생성, `origin` 연결 및 P1/P2 구현 커밋·`main` 푸시.
- [x] 배포 형태 정의. (2026-09-09 개정: Windows도 설치기 없이 ZIP, macOS는 `.app` ZIP.)
- [x] 배포 시에만 버전 기록, 첫 버전 `26.1.0`, changelog와 태그/Release 노트 동일성 정책 정의.

## P0. 최소 배포 검증 — 로컬 완료, 실환경 항목 이관

현재 P0 범위는 로컬 환경에서 검증한 기술 골격이다. 아래 완료 표시는 Linux 검증에만 해당하며, 목표 OS 실행 호환성 확인을 의미하지 않는다.

- [x] 초기 포맷 7개·100 MiB·Windows/macOS OS/CPU 제안 범위를 시험 대상으로 기록.
- [x] 목표 OS 환경 가용성 확인 및 Windows/macOS 실행 환경 부재 기록.
- [x] Python 3.12 가상환경과 최소 패키지 설정 준비.
- [x] MarkItDown 0.1.7·선택 extras·PyInstaller 6.22.2의 Linux 설치 및 변환 확인.
- [x] 개인정보 없는 PDF/DOCX/PPTX/XLSX/HTML/CSV/TXT fixture와 생성 스크립트 준비.
- [x] 최소 Tk 창 코드·터미널 프로브·단일 컨버터 어댑터 및 Linux onedir CLI/GUI 시험 빌드 작성.
- [x] Linux 소스/동결 CLI에서 7포맷 변환 확인, Tcl/Tk 번들 누락 보완.
- [x] `uv.lock` 초기 의존성 잠금과 명령·실패 원인·검증 로그 기록.

**이관한 미완료 항목:** Windows/macOS 빌드·번들 포함 여부는 P4, 실제 Tk 창·Python 미설치 실행·Finder/Explorer CWD·권한·최종 플랫폼 호환성 확정은 배포 후 실환경 테스트에서 관리한다. 초기 잠금 파일을 목표 OS 호환성 확정으로 취급하지 않는다.

### 이번 P0 진행 증거 (2026-09-08)

- Python 3.12.13 가상환경, MarkItDown 0.1.7, PyInstaller 6.22.2 설치 및 `uv.lock` 생성.
- 7개 자체 제작 fixture, 명시 컨버터 프로브, 최소 Tk 창, OS별 실행 가능한 빌드 스크립트 작성.
- Linux에서 소스/동결 CLI 7개 포맷 변환, 테스트 15개 통과. 네트워크 격리 환경에서도 재검증.
- Linux GUI 패키징의 Tcl/Tk 라이브러리 누락을 보완. 창 표시는 디스플레이 부재로 미검증.
- `uv.lock`은 현재 환경의 재현용 초기 잠금이다. 목표 OS 검증 전 최종 호환 버전 확정이 아니다.
- Windows/macOS 빌드·Python 미설치 실행·Finder/Explorer CWD 검증은 환경 부재로 미실행.
- 위 지원 범위 체크는 **제안 범위를 시험 대상으로 기록한 것**이며 정식 지원 확정이 아니다.

## P1. 공통 변환 코어 — 완료

선행 조건: P0 로컬 검증 완료(충족). 실환경 검증은 착수 조건에서 제외. 구현 파일: `src/everythingmarkdown/{models,service,markitdown_adapter}.py`, `tests/unit/`.

- [x] 요청·결과 데이터 모델과 안정적인 공통 오류 코드를 작성한다.
- [x] 시작 CWD 고정, 상대 경로 해석, basename 보존 및 `convert_result` 경로 계산을 구현한다.
- [x] 일반 파일·확장자·크기·심볼릭 링크·ZIP 위장·OOXML 구조 검증을 구현한다.
- [x] 자동 builtins/plugins 비활성화, 포맷별 단일 컨버터 등록, `convert_local()`/`result.markdown` 어댑터를 구현한다.
- [x] 빈 결과 거부, UTF-8·LF 정규화, 배타적 생성, 기존 결과 보존을 구현한다.
- [x] 쓰기·닫기 실패 시 이번 요청의 미완성 결과만 정리하고 정리 실패 경고를 제공한다.
- [x] 입력 경계와 파일 안전성 테스트를 우선 작성·실행한다(A06~A16, A22~A26).

**완료 기준:** 가짜 엔진을 사용한 코어 단위 테스트 통과, 실제 엔진과의 최소 통합 확인, 기존 파일 손상 없음. GUI/CLI에 저장 로직을 중복 구현하지 않는다.

실행 근거: [P1 검증 기록](docs/p1-validation.md). 전체 테스트 74개(P1 신규 59개 + 기존 P0 15개) 통과,
네트워크 격리 재실행 통과. 새 의존성 없이 구현했으며 제품용 GUI/CLI와 OS 실환경 검증은 포함하지 않았다.

## P2. CLI — 완료

선행 조건: P1 완료. 구현 파일: `cli.py`, `__main__.py`, 패키지 진입점.

- [x] 파일 인자, `--help`, `--version` 및 GUI와 구분된 CLI 진입점을 제공한다.
- [x] 인자 없는 TTY 실행에서 파일 경로 입력을 받고 비TTY에서는 즉시 사용법 오류로 종료한다.
- [x] 성공 경로는 stdout, 프롬프트·경고·오류는 stderr로 분리한다.
- [x] 종료 코드 0/2/3/4/130, Ctrl+C·EOF·빈 입력 처리를 구현한다.
- [x] 인자/대화형 입력, 한글·공백 경로, CWD, 스트림·종료 코드 테스트를 실행한다(A03/A04/A06/A07/A19).

**완료 기준:** 동일 공통 서비스로 인자/대화형 변환이 동작하고 자동화 환경에서 입력 대기에 걸리지 않음.

실행 근거: [P2 검증 기록](docs/p2-validation.md). P2 신규 29개를 포함한 전체 103개 테스트 통과.
실제 모듈/설치된 콘솔 진입점, 7포맷, 한글 경로, Linux PTY 대화형 입력 검증 포함.
`--version`은 첫 배포 전 개발 상태만 표시하며 버전 항목·태그는 만들지 않는다.

## P3. GUI — 완료 (2026-09-09)

구현 파일: `src/everythingmarkdown/gui.py`, `DESIGN.md`, `docs/gui-mockup.html`, `tests/unit/test_gui.py`.
`tests/integration/test_conversion.py`에 A02 병렬 테스트 추가.

- [x] GUI 계약을 구체화한 `DESIGN.md`와 시각 목업 `docs/gui-mockup.html` 작성.
- [x] `gui.py`와 `everythingmarkdown-gui` 진입점 추가, P1 `ConversionService`에 연결. P0 환경 창과 분리.
- [x] 파일 선택(찾아보기), 예상 결과 절대 경로 + 복사, 상태 줄, 변환/초기화 버튼 구현.
- [x] IDLE/READY/RUNNING/SUCCESS/ERROR 상태 기계와 버튼 활성 규칙 구현. `ConversionController`(Tk 비의존)로 분리.
- [x] 단일 작업 스레드 + `queue.Queue` + `after()` 폴링. 중복 요청 무시, 워커는 큐만 접근.
- [x] 선택 취소 시 기존 선택 유지, 오류 후 재시도, 변환 중 창 닫기 예약 구현.
- [x] Tab 탐색·복사 가능한 경로·`minsize`/`columnconfigure` 배율 대응. 상태는 색+기호+텍스트 3중 표현.
- [x] `test_gui.py` 16개: 상태 전이·중복 방지·워커 격리·닫기 예약·모든 ErrorCode 안전 매핑·no-Tk/no-display 폴백.
- [x] A02: `test_gui_and_cli_produce_identical_result_for_same_input` — 같은 입력의 GUI/CLI 결과 바이트·상대 경로 일치.
- [x] `assets/logo.ico`에서 `src/everythingmarkdown/logo.png` 생성, `iconphoto`로 창 아이콘 연결(실패 시 무시).

**완료 기준 충족:** 상태 전이·스레드 경계·중복 요청·닫기 처리를 자동 테스트로 검증했다.
실제 창의 키보드/배율/OS 이벤트(A05/A17/A18의 일부)는 배포 후 실환경 테스트로 이관한다.

## P4. 통합·패키징·배포 준비 — 진행 중 (설정·문서·초안 완료)

P1/P2/P3 검증은 완료했다. 이 환경(Linux)에서 할 수 있는 설정·문서·빌드 스크립트·CI 초안까지 작성했고,
Windows `.exe`·macOS `.app` 실제 빌드와 서명은 각 OS 또는 CI에서 수행한다.

### 이미 완료한 선행 검증

- [x] 실제 엔진으로 7개 최소 포맷 샘플의 핵심 텍스트·UTF-8/LF 저장 확인(P1/P2).
- [x] 외부 참조 HTML과 현재 테스트 샘플의 Python socket/DNS 호출 감시 및 OS 네트워크 격리 실행.
- [x] 기존 결과·원본 보존, 동시 생성 경쟁, 권한 오류, 쓰기/닫기 실패, 정리 실패 경고를 로컬 단위·통합 테스트로 확인.
- [x] 현재 구현 전체 테스트 103개와 compileall/tabnanny/AST·의존성 검사 통과 기록 확보.
- [x] README에 현재 CLI/API 사용법·저장 위치·종료 코드·지원 목표와 OCR/품질 한계 작성.

근거: [P1 검증](docs/p1-validation.md), [P2 검증](docs/p2-validation.md). 현재 샘플과 구현에 대한 완료이며 최종 GUI·OS 배포물이나 전체 A01~A26 통과를 의미하지 않는다.

### 완료한 개발·검증 (2026-09-09)

- [x] GUI 포함 전체 단위·통합 테스트 126개 통과, 네트워크 격리 테스트 유지.
- [x] 텍스트 없는 PDF 회귀 테스트 추가(A13). 암호화 문서 fixture는 라이브러리 필요 — 보류(아래 참조).
- [x] lint=`ruff`, typecheck=`mypy` 채택. `pyproject.toml`에 설정·`dev` 그룹 추가. `ruff check .`(전체 `.py`)·`mypy`(`src`) 통과. `packaging/`·`scripts/`는 mypy 범위 밖.
- [x] A01~A26 현황을 [docs/acceptance-matrix.md](docs/acceptance-matrix.md)에 매핑(통과/부분/이관).

### 완료한 패키징·배포 준비 초안 (2026-09-09)

- [x] CI 초안: `.github/workflows/ci.yml`(lint+mypy+test), `.github/workflows/build.yml`(Windows/macOS 빌드, 수동 트리거).
- [x] PyInstaller spec: `packaging/emarkdown.spec` — GUI+CLI를 한 배포 폴더에(macOS `BUNDLE`). Linux에서 빌드·frozen CLI 변환 스모크 확인(배포물 아님).
- [x] `packaging/build_release.py` — spec 빌드 후 `EverythingMarkdown-<ver>-<os>.zip` 생성. Windows도 ZIP(설치기 없음).
- [x] `scripts/sha256sums.py` — `dist/*.zip`의 `SHA256SUMS` 생성·검증.
- [x] 서드파티 라이선스 목록 초안: [docs/third-party-licenses.md](docs/third-party-licenses.md). 모두 허용형, copyleft 런타임 없음.
- [x] README에 GUI 사용법·빌드 명령·서명 상태·ZIP 배포·실환경 미검증 안내 반영. releasing.md를 ZIP 정책으로 개정.

### 남은 P4 — OS/CI 필요, 이 환경에서 불가

- [ ] Windows/macOS 러너에서 `build.yml` 실행: 실제 `.exe`/`.app` 빌드, Tcl/Tk·포맷 데이터 번들 로딩 확인.
- [ ] Windows 서명·macOS Developer ID 서명/공증 자격증명 확보(미서명 시험판과 정식판 구분).
- [ ] 각 패키지 LICENSE/NOTICE 원문을 배포물에 포함.
- [ ] (배포 요청 시) 버전/메타데이터/파일명 일치, changelog 추출·태그 동일성 검증.
- [ ] 암호화 PDF fixture — pypdf/pikepdf 도입 여부 결정 후 A12 보강.

**현재 완료 기준:** GUI 포함 로컬 검증·정적 검사·빌드 스크립트/CI 초안·미검증 범위 문서화까지 충족.
실제 OS 배포물 빌드·서명은 남았고, 빌드 성공을 실행 보장으로 표현하지 않는다.

## 최초 릴리즈 게시 — 사용자 배포 요청 후에만

- [ ] 배포 요청 시 `changelog.md`에 `26.1.0`과 실제 배포 날짜·변경 내역·미검증 범위를 작성한다.
- [ ] 패키지/앱 버전과 배포 파일명을 최초 릴리즈 버전에 맞추고 최종 파일·체크섬을 생성한다.
- [ ] 동일 커밋의 해당 changelog 노트로 annotated tag 주석과 GitHub Release 본문을 작성한다.
- [ ] 명시 요청 범위에서 릴리즈 커밋·태그 push·배포 파일 게시를 수행하고 원격 파일/노트/체크섬을 확인한다.
- [ ] 외부 공개가 필요하면 현재 비공개 저장소의 공개 전환 또는 별도 배포 채널을 명시 결정한다. 자동으로 공개 범위를 변경하지 않는다.

개발 커밋·푸시는 릴리즈가 아니다. 배포 요청 전에는 버전별 항목·`Unreleased`·태그·Release를 생성하지 않는다.

## 배포 후 실환경 테스트 — 현재 작업 범위에서 제외

- [ ] Windows/macOS Python 미설치 환경에서 설치·GUI/CUI 실행과 7포맷 변환(A20).
- [ ] 실제 콘솔 입력·파이프·종료 코드·Ctrl+C/EOF, GUI 창·키보드·배율·응답성.
- [ ] Finder/Explorer/터미널 CWD, 한글·공백 경로, 실제 쓰기 권한과 결과 일치.
- [ ] Gatekeeper/Windows 보안 경고, 서명·공증 사용자 경험, 런타임 의존성 누락.
- [ ] 실환경 결과에 따라 지원표 확정 및 필요 시 후속 수정 릴리즈.

이 목록은 추후 테스트 환경에서 수행하며 지금의 P1~P4 개발 진행을 막지 않는다.

## 후속 검토 목록 — MVP 필수 작업 아님

아래 기능은 현재 설계 범위를 자동 확장하지 않으며 별도 필요성 검토 대상이다.

- [ ] GUI 작업 폴더 선택 및 Finder 더블클릭 저장 UX 개선 검토.
- [ ] 일괄 변환, 폴더 입력, 드래그앤드롭 검토.
- [ ] 덮어쓰기 확인 또는 충돌 시 이름 변경 정책 검토.
- [ ] OCR, 이미지/오디오, 레거시 Office 등 지원 포맷 확대 검토.
- [ ] 처리 중 취소, 하드 타임아웃, 프로세스 격리·자원 제한 검토.
- [ ] macOS Intel, Windows ARM64 및 이전 OS 지원 확대 검토.

## 완료 표시와 증거 규칙

- `[x]`는 산출물과 해당 완료 기준의 확인 근거가 있을 때만 표시한다.
- 테스트는 명세 작성, 코드 작성, 실제 실행 성공을 각각 구분한다.
- 검증 기록에는 실행 명령, 날짜, OS/CPU/패키지 버전, 종료 코드, 로그·캡처 위치를 남긴다.
- 플랫폼 테스트 환경이 없으면 해당 테스트를 이관·미실행으로 기록한다. 현재 범위의 개발 완료와 실환경 검증 완료를 별도로 표시한다.
- 제품 계약을 변경해야 하면 먼저 설계서·테스트 명세를 갱신하고 변경 검토를 남긴다. 이 목록으로 기존 요구사항을 조용히 바꾸지 않는다.
