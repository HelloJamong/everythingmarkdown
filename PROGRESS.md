# EverythingMarkdown 진행 현황

- 최종 정리일: 2026-10-12
- 현재 단계: **26.1.0 릴리즈 완료(2026-10-12)**
- 다음 작업: 테스트 서버 사용자 확인, 실서버·nginx 구성, 부분 충족 수용 기준 보완

## 프로젝트 목표

Microsoft MarkItDown으로 업로드한 문서를 Markdown으로 변환하는 **개인용 웹 서비스**를 만든다.
본인만 로그인해 파일을 올리고 결과를 확인·복사·다운로드한다. 배포물은 Docker Hub의 통합 웹 서비스 이미지 하나이며,
HTTPS는 nginx 등 리버스 프록시에서 처리한다. 설계 기준: [웹 서비스 설계·계획](docs/web-service-plan.md).

## 현재 구성

| 영역 | 상태 |
|---|---|
| 변환 코어 `models`·`service`·`markitdown_adapter` | 완료. 7개 포맷, 입력 검증, UTF-8/LF 저장, 네트워크 미사용 |
| 웹 앱 `src/everythingmarkdown/web/` | 인증, 작업 API(업로드·상태·미리보기·다운로드·삭제), 자식 프로세스 변환, 보관·정리, JSON 로그 완료. 업로드·결과 화면 완료 |
| Docker `Dockerfile`·`compose.yaml` | 완료. 로컬 build/up/health·재시작 검증 |
| CI `ci.yml` | ruff·mypy·pytest, `main` push마다 실행, `build.yml`에서도 재사용 |
| 배포 `build.yml` | 버전 태그 푸시 시 검사 → 버전 일치 확인 → `latest`·버전 이미지 푸시. `26.1.0`에서 첫 실행 성공 |
| Docker Hub | 공개 저장소, `linux/amd64` 단일 이미지. 시크릿 `DOCKERHUB_USERNAME`·`DOCKERHUB_TOKEN` 등록 확인 |

## 이력 요약

| 기간 | 내용 |
|---|---|
| 2026-09-08 | 요구사항 정리, P0 기술 검증, 변환 코어(P1) 구현. 근거: [P1 검증 기록](docs/p1-validation.md) |
| 2026-09-08~09 | 데스크톱 CLI·Tkinter GUI·PyInstaller 패키징 초안 구현(126개 테스트 통과) |
| 2026-09-11 | 개인용 웹 서비스 전환 계획 작성 |
| 2026-10-12 | Docker Hub 시크릿 등록, `build.yml`에 Docker job 추가. MIT 저작권자를 HelloJamong으로 지정 |
| 2026-10-12 | **웹 서비스 중심으로 재정의.** 데스크톱 GUI·CLI·패키징 폐기 승인, 웹 의존성 기본 의존성 승인, 릴리즈를 Docker 이미지로 전환. HTTPS는 리버스 프록시 담당 |

데스크톱 앱 코드와 설계·검증 문서는 Git 이력(`f4cb598` 이전)에 남아 있다.

## 웹 P1 완료 내용 (2026-10-12)

- README·릴리즈 정책·웹 계획·TODO·PROGRESS를 웹 서비스 기준으로 재작성.
- `pyproject.toml`: CLI/GUI 진입점, PyInstaller `build` 그룹, 로고 패키지 데이터 제거. `uv.lock` 갱신.
- `build.yml`: Windows/macOS 빌드 job 제거, Docker job만 유지.
- 통합 테스트의 GUI/CLI 결과 일치 테스트 제거.
- 데스크톱 GUI·CLI·P0 프로브·패키징 코드와 관련 테스트·설계·검증 문서 삭제.
- 서로 다른 launch_dir 동명 파일 독립 변환 회귀 테스트 추가.
- 웹 P4 화면 목업 `docs/web-mockup.html` 작성.

## 웹 P2 완료 내용 (2026-10-12)

- 웹 의존성(FastAPI·Uvicorn·Jinja2·python-multipart·itsdangerous)과 테스트용 `httpx2` 추가.
- `web/config.py`: `APP_PASSWORD`(12자 이상, 예제 값 거부)·`COOKIE_SECURE` 검증, 잘못되면 시작 거부.
- `web/auth.py`·`web/app.py`: 로그인/로그아웃, 시작마다 새 키로 서명한 쿠키(로그인 후 8시간 절대 만료), 상태 변경 요청 Origin 검사, IP당 1분 5회 실패 제한, 인증 감사 이벤트 stderr 출력.
- 업로드 화면 전까지 `/`는 로그인 확인용 임시 페이지.
- 테스트 77개 통과(웹 16개), 실제 uvicorn 스모크 확인.

## 웹 P3 완료 내용 (2026-10-12)

- `web/jobs.py`: SQLite 작업 저장소(`/data/app.db`), 단일 변환 스레드가 자식 프로세스(`web/worker.py`)로 변환, 120초 초과 시 종료·회수, `.work`에서 `markdown/<id>/input.md`로 게시, 재시작 시 interrupted 처리, 보관 만료 정리.
- `web/routes.py`: `POST/GET /api/jobs`, `GET /api/jobs/{id}`, `/preview`(64 KiB), `/download`, `DELETE`. 모두 로그인 필요.
- `web/logs.py`: audit/access JSON Lines 파일, 크기 회전.
- 보류한 계약은 TODO 웹 P3 "미구현으로 남긴 계약"에 기록.
- 테스트 94개 통과(웹 33개), 실제 uvicorn에서 docx 업로드→변환→한글 파일명 다운로드→보관 N 재다운로드 410 확인.

## 웹 P4 완료 내용 (2026-10-12)

- 목업(`docs/web-mockup.html`)을 `web/templates`·`web/static`으로 옮기고 실제 API에 연결. 목업 전용 상태 막대와 예시 데이터는 제외.
- 보관 정책과 업로드 한도는 서버 설정에서 화면에 표시.
- 웹폰트 대신 시스템 글꼴을 사용해 외부 요청이 없다.
- 테스트 98개 통과(웹 37개), Playwright로 데스크톱·모바일 흐름과 HTML 삽입 무해화 확인. 개발 서버에 한글 글꼴이 없어 스크린샷의 한글은 깨져 보였고 텍스트 내용은 DOM으로 확인함.

## 웹 P5 완료 내용 (2026-10-12)

- `Dockerfile`·`.dockerignore`·`compose.yaml`·`.env.example`, [배포 문서](docs/web-deployment.md) 작성.
- 배포 트리거를 수동 실행에서 **버전 태그 푸시**로 변경. 태그와 `pyproject.toml` 버전·`changelog.md` 항목이 다르면 이미지를 푸시하지 않는다.
- 로컬 Docker로 빌드·실행·재시작·보안 설정·이미지 내용 검사 완료. Docker Hub 푸시는 첫 릴리즈 태그에서 처음 실행된다.

## 웹 P6 완료 내용 (2026-10-12)

- 수용 기준 A01~A25 판정과 근거를 [검증 기록](docs/web-validation.md)에 정리: 충족 17, 부분 8. 부분 항목은 남은 범위를 명시.
- 보완: OOXML 압축 폭탄 제한, 재시작 시 기록 전 결과·고아 폴더 정리, 보완 테스트 9개.
- 컨테이너로 변환 중 재시작(interrupted), 재생성 후 데이터·로그 유지, forwarded 헤더 위조 무시, 보안 설정 확인.
- 라이선스 고지 확정, 누락 원문 4개 보충.

## 26.1.0 릴리즈 (2026-10-12)

- 릴리즈 커밋·annotated tag `26.1.0` 푸시 → `build.yml` 성공 → Docker Hub `igor0670/everythingmarkdown`의 `26.1.0`·`latest` digest 일치.
- GitHub Release `26.1.0` 게시, 본문은 태그 주석·changelog 섹션과 동일.
- 테스트 서버 `~/everythingmarkdown`에서 Docker Hub 이미지 실행(LAN http `:8000`, nginx 없음, `COOKIE_SECURE=false`): healthy, 로그인·xlsx 변환·삭제 확인.

## 남은 위험

- 실제 도메인·nginx 위치·호스트 자원이 미확인이다. 웹 P5 전까지 정한다.
- Docker Hub 저장소가 공개라 이미지 내용은 누구나 볼 수 있다. 비밀·데이터가 이미지에 들어가지 않게 검사한다.
- 인증을 붙여도 업로드 문서가 안전해지는 것은 아니다. 크기·압축·시간·프로세스 한도로 완화하며 강한 격리는 보장하지 않는다.
- 100 MiB 제한과 동시 변환 1개는 초기 제안값이다. 실제 서버에서 측정 후 조정한다.

## 공유 문서

- [README](README.md): 서비스 개요·구성·개발 환경
- [TODO](TODO.md): 단계별 체크리스트
- [웹 서비스 설계·계획](docs/web-service-plan.md): 구조·인증·보관·로그·단계·수용 기준
- [릴리즈 정책](docs/releasing.md): Docker 이미지 배포, 버전·태그·노트 규칙
- [changelog](changelog.md): 릴리즈 노트. 최신 `26.1.0`
- [P1 검증 기록](docs/p1-validation.md): 변환 코어 검증
- [서드파티 라이선스](docs/third-party-licenses.md): 의존성 라이선스 초안

원본 대화와 검토 기록은 로컬 `.omx/`에만 보관한다.
