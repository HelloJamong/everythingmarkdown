# EverythingMarkdown To-do

- 최종 정리일: 2026-10-12
- 제품: **개인용 웹 서비스**. 배포물은 Docker Hub의 통합 웹 서비스 이미지 하나다.
- 현재 상태: 변환 코어·웹 P1~P5 완료. **다음은 웹 P6(통합 검증·운영 문서)**. 배포는 버전 태그 푸시로 시작한다.
- 관련 문서: [진행 현황](PROGRESS.md) · [웹 서비스 설계·계획](docs/web-service-plan.md) · [릴리즈 정책](docs/releasing.md) · [P1 코어 검증](docs/p1-validation.md)
- 2026-10-12 결정:
  - 데스크톱 GUI·CLI·P0 프로브·PyInstaller 패키징 폐기(Git 이력에 보존).
  - 웹 런타임 의존성(FastAPI·Uvicorn·Jinja2·python-multipart·itsdangerous)을 기본 의존성으로 승인, 웹 P2에서 추가함. 테스트 클라이언트는 dev 그룹 `httpx2`.
  - 인증 간소화: `.env`의 `APP_PASSWORD` 하나로 제3자 접근 차단. DB 계정·bcrypt·서버 세션·reset 명령·CSRF 토큰 없음.
  - 릴리즈는 Docker 이미지 + changelog·annotated tag·GitHub Release 노트.
  - HTTPS는 자체 구현하지 않고 nginx 등 리버스 프록시에서 처리. 앱은 HTTP만 제공.
  - Docker 이미지는 `linux/amd64` 단일 아키텍처. Docker Hub 저장소는 공개 상태.
- 배포 요청 전에는 버전 항목·태그·Release를 만들지 않는다. 첫 배포 시 `26.1.0`으로 기록한다.

## 단계별 상태

| 단계 | 상태 | 다음 조치 |
|---|---|---|
| 변환 코어 | 완료 | 웹 P3에서 자식 프로세스로 호출 |
| 웹 P1 구조 재정의 | 완료 | |
| 웹 P2 인증 | 완료 | |
| 웹 P3 업로드·변환·보관 | 완료 | 일부 계약 보류(아래) |
| 웹 P4 화면 | 완료 | |
| 웹 P5 Docker | 완료 | Docker Hub 첫 푸시는 첫 릴리즈 태그에서 |
| 웹 P6 통합 검증·운영 문서 | **다음** | |
| 릴리즈 | 사용자 배포 요청 대기 | |

## 변환 코어 — 완료

- [x] 요청·결과 모델과 안정적인 오류 코드(`models.py`).
- [x] 입력 경로·크기·심볼릭 링크·ZIP 위장·OOXML 구조 검증, UTF-8/LF 배타적 저장, 실패 시 미완성 결과 정리(`service.py`).
- [x] 포맷별 단일 컨버터 등록, 기본 컨버터·플러그인 비활성(`markitdown_adapter.py`).
- [x] 7개 포맷 실제 엔진 변환, 네트워크 미사용, 손상·빈 결과 안전 처리 테스트. 근거: [P1 검증 기록](docs/p1-validation.md).

## 웹 P1 — 구조 재정의 (완료)

- [x] README·릴리즈 정책·웹 계획·TODO·PROGRESS를 웹 서비스 기준으로 재작성.
- [x] `pyproject.toml`에서 CLI/GUI 진입점, `build` 그룹(PyInstaller), 로고 패키지 데이터 제거, `uv.lock` 갱신.
- [x] `build.yml`에서 Windows/macOS 빌드 job 제거, Docker job만 유지.
- [x] 통합 테스트에서 GUI/CLI 결과 일치 테스트 제거.
- [x] 데스크톱 자산 파일 삭제: `gui.py`·`cli.py`·`__main__.py`·`p0.py`·`logo.png`, 관련 테스트, `packaging/`, `scripts/sha256sums.py`, `assets/logo.icns`, `DESIGN.md`, `docs/{design,test-spec,acceptance-matrix,p0-validation,p2-validation}.md`, `docs/gui-mockup.html`, `docs/evidence/{p0,p2}-*`.
- [x] 서로 다른 launch_dir에서 동명 파일 변환이 독립적이라는 회귀 테스트 추가(`test_same_name_in_different_launch_dirs_is_independent`, 61개 테스트 통과).

## 웹 P2 — 웹 기반과 비밀번호 인증 (완료)

- [x] 승인된 웹 의존성을 `pyproject.toml`·`uv.lock`에 추가, 서버 진입점 `uvicorn --factory everythingmarkdown.web.app:create_app`.
- [x] `web/{app,config,auth}.py`: `APP_PASSWORD` 검증(누락·예제·12자 미만 시작 거부), 로그인/로그아웃, 시작 시 랜덤 키 서명 쿠키(8시간), Origin 검사, IP당 5회/분 로그인 제한.
- [x] Secure 쿠키는 기본 켜고 LAN 직접 테스트용 `COOKIE_SECURE=false`만 허용(2026-10-12 결정).
- [x] `tests/web/test_auth.py` 16개 테스트, 실제 uvicorn 스모크(healthz·리다이렉트·401·403·303·쿠키 플래그) 확인.
- [x] 인증 감사 이벤트(`login_succeeded`·`login_failed`·`login_rate_limited`·`origin_rejected`·`logout`)를 JSON으로 기록(웹 P3부터 `/logs/audit.log`).

## 웹 P3 — 업로드·변환·저장 수명주기 (완료)

- [x] `web/{routes,jobs,worker}.py`: SQLite 작업 저장소, 서버 생성 작업 ID별 경로, 활성 3개 대기열(429), 자식 프로세스 변환·120초 timeout 종료, 재시작 시 interrupted 처리·`.work` 정리. 업로드는 Content-Length 필수(411)·요청 26 MiB/파일 25 MiB(413)·미지원 형식(415).
- [x] 원본/Markdown 독립 보관 Y/N·일수(작업별 스냅샷), 보관 N 원본은 변환 종료 후·결과는 첫 전송 완료 후 또는 60분 뒤 삭제, 시작/5분 주기 정리, 삭제 실패 시 다음 주기 재시도.
- [x] `web/logs.py`: `/logs/{access,audit}.log` JSON Lines, 크기 기준 회전(10 MiB × 10개). 파일명·본문·비밀번호 미기록, access는 경로 템플릿만 기록. 로그 디렉터리 쓰기 불가 시 시작 거부.
- [x] `tests/web/test_jobs.py` 17개 테스트(7개 포맷·동명·경로 탈출·손상·timeout·한도·Y/N 4조합·만료·삭제·재시작·로그), 실제 uvicorn 업로드→변환→다운로드 스모크 확인.
- [ ] 미구현으로 남긴 계약(필요 시 착수):
  - 업로드 수신 시간 120초 제한 — 웹 P5 nginx `client_body_timeout`으로 대체 검토.
  - 대기 만료 5분 — 활성 3개 × 변환 120초로 대기 상한이 이미 정해져 있어 보류.
  - 자식 프로세스 자원 제한(rlimit) — 웹 P5 컨테이너 CPU·메모리·PID 한도로 대체 검토.
  - 로그 날짜 경계 회전·회전 파일 30일 정리(`LOG_RETENTION_DAYS`), 로그 쓰기 실패 시 readiness 실패·접수 중단.
  - 보관 N 결과의 동시 다운로드 참조 계수(두 번째 동시 전송이 삭제와 경합할 수 있음).

## 웹 P4 — 개인용 웹 화면 (완료)

- [x] 초기 화면 목업 [docs/web-mockup.html](docs/web-mockup.html): 로그인·업로드·결과·실패·만료 등 12개 상태, 로고·파비콘 적용(2026-10-12).
- [x] `web/templates/{base,index,login}.html`, `web/static/{app.css,app.js,logo.ico}`: 목업 디자인 그대로 업로드(선택·끌어놓기)·1초 상태 폴링·원문 확인/복사/다운로드/삭제, 실패·거절·만료·인증 만료 안내, 화면에 보관 정책·한도 표시. 모든 문자열은 `textContent`로만 넣는다.
- [x] `tests/web/test_views.py` 4개 테스트, Playwright(Chromium)로 1280px·390px 전체 흐름(로그인 실패→로그인→업로드→결과→다운로드→실패→기록 삭제→거절→만료→로그아웃)과 HTML·스크립트가 든 파일명·문서가 실행되지 않음을 확인.
- [ ] 웹폰트 미사용: 목업의 IBM Plex 대신 시스템 글꼴(맑은 고딕·Apple SD 산돌고딕 Neo 등)을 쓴다. 목업과 같은 글꼴이 필요하면 OFL 폰트를 `web/static`에 넣는다(이미지 용량 증가).

## 웹 P5 — Docker 및 배포 구성 (완료)

- [x] `Dockerfile`(python:3.12-slim 2단계, `uv sync --locked --no-dev`, UID 10001 비루트, healthcheck, TLS 미포함, 728 MB), `compose.yaml`(`./data:/data`, `./logs:/logs`, 127.0.0.1 바인딩, 읽기 전용 rootfs·`/tmp` tmpfs, capability 전부 제거, no-new-privileges, 메모리 2 GB·CPU 2·PID 256), 허용 목록 방식 `.dockerignore`, `.env.example`.
- [x] [docs/web-deployment.md](docs/web-deployment.md): 태그 배포 흐름, 서버 준비, nginx 예시(`Host`·`X-Forwarded-*`·업로드 한도·수신 시간), `FORWARDED_ALLOW_IPS`, digest 갱신 스크립트, rollback, 백업.
- [x] 로컬 이미지 build → compose up → healthy, 로그인·PDF 업로드·변환·미리보기, 재시작 후 이전 쿠키 401·보관 결과 다운로드 200, 비루트·읽기 전용 확인. `APP_PASSWORD` 누락·로그 디렉터리 쓰기 불가 시 시작 거부 확인.
- [x] `build.yml` Docker job을 `linux/amd64`로 고정.
- [x] 이미지에 `.env`·`app.db`·로그 없음, `/data`·`/logs` 비어 있음, 레이어 명령에 비밀 문자열 없음 확인.
- [x] `build.yml`: `YY.메이저.마이너` 태그 푸시로 시작 → `ci.yml` 검사 → 태그·`pyproject.toml` 버전·`changelog.md` 항목 일치 확인 → `latest`·버전 태그 푸시. 수동 실행 제거.
- [ ] `build.yml` 첫 실행(첫 릴리즈 태그)으로 Docker Hub 로그인·빌드·푸시 확인.
- [ ] 배포 서버에 digest 갱신 스크립트(cron) 설치(Watchtower 미사용). 스크립트 예시는 배포 문서에 있음.

## 웹 P6 — 통합 검증과 운영 문서

- [ ] 웹 A01~A25 수용 기준 검증 및 lint/typecheck/회귀/컨테이너 smoke 기록.
- [x] DB 백업, 이미지 rollback 절차 문서화(배포 문서 4·5장). 복원 실습은 미실행.
- [ ] 실제 도메인·nginx 위치(같은 Docker 네트워크/호스트/다른 서버)·호스트 자원 확인(현재 미확인).
- [ ] 이미지에 포함되는 의존성 라이선스 고지 확정([목록 초안](docs/third-party-licenses.md)).

## 최초 릴리즈 — 사용자 배포 요청 후에만

- [ ] `changelog.md`에 `26.1.0`과 실제 배포 날짜·변경 내역·미검증 범위 작성, `pyproject.toml` 버전 일치.
- [ ] 릴리즈 커밋·annotated tag `26.1.0` push → `build.yml`이 `latest`·`26.1.0` 이미지 푸시, 두 태그 digest 일치 확인.
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
