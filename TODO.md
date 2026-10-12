# EverythingMarkdown To-do

- 최종 정리일: 2026-10-12
- 제품: **개인용 웹 서비스**. 배포물은 Docker Hub의 통합 웹 서비스 이미지 하나다.
- 현재 상태: 변환 코어 완료. **웹 P1(구조 재정의) 진행 중**, 웹 P2~P6 미착수.
- 관련 문서: [진행 현황](PROGRESS.md) · [웹 서비스 설계·계획](docs/web-service-plan.md) · [릴리즈 정책](docs/releasing.md) · [P1 코어 검증](docs/p1-validation.md)
- 2026-10-12 결정:
  - 데스크톱 GUI·CLI·P0 프로브·PyInstaller 패키징 폐기(Git 이력에 보존).
  - 웹 런타임 의존성(FastAPI·Uvicorn·Jinja2·python-multipart·bcrypt·itsdangerous)을 기본 의존성으로 승인. 웹 P2에서 추가한다.
  - 릴리즈는 Docker 이미지 + changelog·annotated tag·GitHub Release 노트.
  - HTTPS는 자체 구현하지 않고 nginx 등 리버스 프록시에서 처리. 앱은 HTTP만 제공.
  - Docker 이미지는 `linux/amd64` 단일 아키텍처. Docker Hub 저장소는 공개 상태.
- 배포 요청 전에는 버전 항목·태그·Release를 만들지 않는다. 첫 배포 시 `26.1.0`으로 기록한다.

## 단계별 상태

| 단계 | 상태 | 다음 조치 |
|---|---|---|
| 변환 코어 | 완료 | 웹 P3에서 자식 프로세스로 호출 |
| 웹 P1 구조 재정의 | **진행 중** | 데스크톱 자산 삭제, 동명 파일 회귀 테스트 |
| 웹 P2 인증 | 미착수 | 웹 의존성 추가부터 |
| 웹 P3 업로드·변환·보관 | 미착수 | |
| 웹 P4 화면 | 미착수 | |
| 웹 P5 Docker | 미착수 | `Dockerfile` 작성 후 Docker Hub 첫 푸시 |
| 웹 P6 통합 검증·운영 문서 | 미착수 | |
| 릴리즈 | 사용자 배포 요청 대기 | |

## 변환 코어 — 완료

- [x] 요청·결과 모델과 안정적인 오류 코드(`models.py`).
- [x] 입력 경로·크기·심볼릭 링크·ZIP 위장·OOXML 구조 검증, UTF-8/LF 배타적 저장, 실패 시 미완성 결과 정리(`service.py`).
- [x] 포맷별 단일 컨버터 등록, 기본 컨버터·플러그인 비활성(`markitdown_adapter.py`).
- [x] 7개 포맷 실제 엔진 변환, 네트워크 미사용, 손상·빈 결과 안전 처리 테스트. 근거: [P1 검증 기록](docs/p1-validation.md).

## 웹 P1 — 구조 재정의 (진행 중)

- [x] README·릴리즈 정책·웹 계획·TODO·PROGRESS를 웹 서비스 기준으로 재작성.
- [x] `pyproject.toml`에서 CLI/GUI 진입점, `build` 그룹(PyInstaller), 로고 패키지 데이터 제거, `uv.lock` 갱신.
- [x] `build.yml`에서 Windows/macOS 빌드 job 제거, Docker job만 유지.
- [x] 통합 테스트에서 GUI/CLI 결과 일치 테스트 제거.
- [x] 데스크톱 자산 파일 삭제: `gui.py`·`cli.py`·`__main__.py`·`p0.py`·`logo.png`, 관련 테스트, `packaging/`, `scripts/sha256sums.py`, `assets/logo.icns`, `DESIGN.md`, `docs/{design,test-spec,acceptance-matrix,p0-validation,p2-validation}.md`, `docs/gui-mockup.html`, `docs/evidence/{p0,p2}-*`.
- [ ] 서로 다른 launch_dir에서 동명 파일 변환이 독립적이라는 회귀 테스트 추가.

## 웹 P2 — 웹 기반과 단일 계정 인증

- [ ] 승인된 웹 의존성을 `pyproject.toml`·`uv.lock`에 추가, 서버 진입점 정의.
- [ ] `web/{app,config,auth,store}.py`: `.env` 최초 비밀번호 bootstrap/reset, 비밀번호 전용 로그인, SQLite 스키마, 세션·CSRF·로그인 속도 제한, 기본 키 시작 거부.
- [ ] Secure 쿠키를 프록시 없는 로컬 개발에서 끌지 결정.
- [ ] 로그 기반(access/audit JSON Lines) 착수, `tests/web/test_auth.py`.

## 웹 P3 — 업로드·변환·저장 수명주기

- [ ] `web/{routes,jobs,worker,cleanup,audit}.py`: 작업별 경로·소유권 검사, 제한된 대기열, 자식 프로세스 변환·timeout 종료, 재시작 시 interrupted 처리.
- [ ] 원본/Markdown 독립 보관 Y/N·일수, 시작/5분 주기 정리, 삭제 실패 재시도, 로그 회전.
- [ ] `tests/web/test_{jobs,upload_limits,retention,logging}.py`.

## 웹 P4 — 개인용 웹 화면

- [ ] `web/templates/{base,index,login}.html`, `web/static/`: 업로드·상태 폴링·원문 확인/복사/다운로드/삭제, 만료·실패·인증 만료 안내.
- [ ] `tests/web/test_views.py`와 데스크톱/모바일 폭 브라우저 검증.

## 웹 P5 — Docker 및 배포 구성

- [ ] `Dockerfile`(Python 3.12, 잠긴 의존성, 비루트, healthcheck, TLS 미포함), `compose.yaml`(`./data:/data`, `./logs:/logs`), `.dockerignore`, `.env.example`.
- [ ] `docs/web-deployment.md`: nginx 리버스 프록시 연결 예시(HTTPS는 프록시에서 종료)·forwarded 헤더 신뢰 범위·secret 주입.
- [ ] 이미지 build/up/health, 재시작 후 데이터 유지 검증.
- [x] `build.yml` Docker job을 `linux/amd64`로 고정.
- [ ] 공개 저장소이므로 이미지 레이어에 비밀·`.env`·데이터가 없는지 확인.
- [ ] `build.yml` 첫 실행으로 Docker Hub 로그인·빌드·푸시 확인. 버전이 `0.0.0`이면 실행 금지.
- [ ] 배포 서버의 digest 기반 자동 업데이트 구성(Watchtower 미사용).

## 웹 P6 — 통합 검증과 운영 문서

- [ ] 웹 A01~A25 수용 기준 검증 및 lint/typecheck/회귀/컨테이너 smoke 기록.
- [ ] DB 백업/복원, 이미지 rollback 절차 문서화.
- [ ] 실제 도메인·nginx 위치(같은 Docker 네트워크/호스트/다른 서버)·호스트 자원 확인(현재 미확인).
- [ ] 이미지에 포함되는 의존성 라이선스 고지 확정([목록 초안](docs/third-party-licenses.md)).

## 최초 릴리즈 — 사용자 배포 요청 후에만

- [ ] `changelog.md`에 `26.1.0`과 실제 배포 날짜·변경 내역·미검증 범위 작성, `pyproject.toml` 버전 일치.
- [ ] 릴리즈 커밋·annotated tag·push, `build.yml`로 `latest`·`26.1.0` 이미지 푸시.
- [ ] 동일 노트로 GitHub Release 게시.

## 후속 검토 — MVP 필수 작업 아님

- [ ] 일괄 업로드·변환.
- [ ] OCR, 이미지/오디오, 레거시 Office 등 지원 포맷 확대.
- [ ] 암호화 PDF 처리·fixture(pypdf/pikepdf 도입 여부).

## 완료 표시와 증거 규칙

- `[x]`는 산출물과 확인 근거가 있을 때만 표시한다.
- 테스트는 명세 작성, 코드 작성, 실제 실행 성공을 구분한다.
- 실행 환경이 없어 검증하지 못한 항목은 미실행으로 기록한다.
- 제품 계약을 바꿔야 하면 먼저 [웹 서비스 설계·계획](docs/web-service-plan.md)을 갱신한다.
