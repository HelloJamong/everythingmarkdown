# EverythingMarkdown 진행 현황

- 최종 정리일: 2026-09-08
- 현재 단계: **P0 로컬 검증·P1 공통 코어·P2 CLI 완료 / P3 GUI 미착수 / 목표 OS 실환경 테스트는 배포 후 이관**
- 다음 작업: P3 파일 선택·변환 GUI 구현

## 프로젝트 목표

Microsoft MarkItDown을 사용해 Windows/macOS에서 GUI와 CLI로 로컬 파일을 Markdown으로
변환한다. 원래 파일명에서 확장자만 `.md`로 바꾸고 시작 CWD의 `convert_result`에 저장한다.
실제 출력 저장은 P1 공통 API로, 제품용 CLI는 P2로 구현했다. 제품용 GUI는 아직 구현하지 않았다.

## 완료한 준비 작업

- 원 요청을 요구사항 R1~R7로 정리.
- Python/Tkinter 및 CLI 공통 구조, 저장·오류·배포 정책 설계.
- A01~A26 수용 기준과 테스트 명세 작성.
- Architect 1차 보완 후 2차 APPROVE, Critic APPROVE 기록 확보.
- 기존 상세 계획은 로컬 `.omx/plans/`에 보존. Git 공유용 설계·검증 명세는 `docs/`에 복사.

## 이번 P0 작업

| 항목 | 결과 |
|---|---|
| 기본 문서 | README, MIT LICENSE, `.gitignore` 작성; `.omx/`·`.omc/` 제외 |
| 프로젝트 환경 | Python 3.12.13, `pyproject.toml`, `.venv`, `uv.lock` |
| 의존성 | MarkItDown 0.1.7 + pdf/docx/pptx/xlsx extras, PyInstaller 6.22.2 |
| 시험 코드 | 명시 컨버터 하나만 등록하는 프로브, CLI 파일/대화형 입력, 최소 Tk 환경 창 |
| 샘플 | 자체 생성 PDF/DOCX/PPTX/XLSX/HTML/CSV/TXT 및 재생성 스크립트 |
| 소스 검증 | 7개 포맷 변환, 테스트 15개 통과 |
| Linux 시험 빌드 | CLI/GUI onedir 생성, 동결 CLI의 7개 포맷 변환 성공 |
| 네트워크 | Python socket 시도 감시 및 Linux 네트워크 namespace 격리 재검증 |
| GUI | Tcl/Tk 번들 누락 보완; 디스플레이 부재로 실제 창 표시는 미검증 |
| 목표 플랫폼 | Windows/macOS 환경 없음; 빌드·실행 검증 미실행 |

명령·버전·로그·제약은 [P0 검증 기록](docs/p0-validation.md)에 정리했다.
P0 프로브는 변환 성공 여부와 문자 수만 보고하며 **문서 본문이나 결과 파일을 출력하지 않는다.**

## 이번 P1 작업

- `models.py`: 불변 요청/결과 모델, 공통 오류 코드·안전한 메시지·종료 코드.
- `service.py`: 시작 CWD 기준 경로, 입력·크기·ZIP/OOXML 검증, UTF-8/LF 저장, 배타적 생성과 기존 파일 보호.
- `markitdown_adapter.py`: 요청별 명시 컨버터 하나 등록, 기본 컨버터·플러그인 비활성, 외부 예외 정규화.
- 쓰기·닫기 실패 시 생성한 미완성 결과만 정리; 파일 교체/정리 실패 시 삭제하지 않고 경고.
- P1 신규 테스트 59개와 기존 P0 15개를 합쳐 74개 통과. 실제 엔진 7포맷 저장·외부 참조 HTML과 네트워크 격리 검증 포함.
- 버전 정책 수정: 미배포 changelog 항목 제거. 사용자 배포 요청 전 버전 기록 없음, 첫 배포는 `26.1.0`.
- P0 프로브는 역사적 시험 도구로 유지한다. 제품 코어에서 P0 코드에 의존하지 않는다.
- 실행 근거: [P1 검증 기록](docs/p1-validation.md).

## 이번 P2 작업

- `cli.py`/`__main__.py` 및 `everythingmarkdown` 콘솔 진입점 추가. P1 공통 서비스로 실제 변환·저장.
- 파일 인자·TTY 대화형 입력·도움말·개발 상태 표시, stdout/stderr 분리와 종료 코드 0/2/3/4/130.
- Ctrl+C/EOF/빈 입력, 따옴표·한글/공백 경로, 오류·잔여 파일 경고와 원문 미노출 처리.
- P2 신규 29개 + 기존 74개 = 전체 103개 테스트 통과. 실제 subprocess와 Linux PTY 검증 포함.
- 의존성 추가·버전 증가·릴리즈 항목·태그 없음. 첫 배포 요청 시 `26.1.0` 정책 유지.
- 실행 근거: [P2 검증 기록](docs/p2-validation.md).

## 아직 완료하지 않은 것

- **배포 후로 이관:** Windows/macOS의 Python 미설치 환경에서 GUI/CLI 및 7개 포맷 검증. 현재 개발 선행 조건이 아님.
- Finder/Explorer/터미널 시작 CWD와 쓰기 권한의 플랫폼별 확인.
- 목표 환경 전체에서 의존성·패키저 최종 호환성 확정.
- P3 파일 선택·변환 GUI, P4 통합·최종 배포 검증.
- lint/typecheck 도구 선정·설정·실행. 현재 `compileall`은 문법 검사만 의미한다.
- 코드서명·공증, 제3자 라이선스 고지 검토, 외부 릴리스.

**P0 테스트 15개 통과는 A01~A26 전체 수용 기준 통과나 Windows/macOS 지원 완료가 아니다.**
P0 검증 당시에는 Git 작업을 수행하지 않았다. 이후 사용자 요청으로 `main` 브랜치를 초기화하고
[HelloJamong/everythingmarkdown](https://github.com/HelloJamong/everythingmarkdown) 비공개 저장소를
생성해 `origin`으로 연결했다. `.omx/`·`.omc/`와 빌드/가상환경은 추적에서 제외한다.

## 남은 계획과 위험

1. 사용자 요청에 따라 실환경 테스트를 배포 후 별도 단계로 이관했다. 로컬 자동 테스트와 배포 파일 빌드는 유지한다.
2. [TODO](TODO.md)의 P3 → P4 순으로 진행한다. Windows 설치 EXE, macOS 단일 `.app`을 담은 ZIP을 생성하는 것이 배포 목표다.
3. 7개 포맷·100 MiB·Windows 11 x64/macOS 14+ Apple Silicon은 현재 시험 대상 제안값이다.
4. OCR·레이아웃 완전 재현·악성 문서 샌드박스·하드 타임아웃은 보장하지 않는다.
5. 상태가 바뀌면 실제 실행 증거가 있는 항목만 완료로 표시한다.

## 공유 문서

- [릴리즈 정책](docs/releasing.md): 최종 Windows/macOS 배포 요구와 버전·태그·노트 계약 (구현 전 정의)
- [changelog](changelog.md): 배포 시 작성할 릴리즈 노트. 현재 버전 항목 없음; 첫 배포는 `26.1.0`
- [README](README.md): 설치·CLI 사용·프로브 실행 방법
- [TODO](TODO.md): 단계별 실행 체크리스트
- [설계 기준선](docs/design.md): 원 요구사항과 세부 동작 계약
- [검증 명세](docs/test-spec.md): A01~A26의 미래 수용 기준
- [P0 검증 기록](docs/p0-validation.md): 초기 프로브 실행과 미검증 경계
- [P1 검증 기록](docs/p1-validation.md): 공통 코어·파일 안전성·실제 변환 검증
- [P2 검증 기록](docs/p2-validation.md): CLI 단위·프로세스·대화형 실행 검증

원본 대화·Architect/Critic 검토·산출물 해시 기록은 로컬 `.omx/`에만 보관한다.
이전 RTK 환경 작업은 앱 구현과 별개이며 이번에 재검사하지 않았다.
