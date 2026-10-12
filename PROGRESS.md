# EverythingMarkdown 진행 현황

- 최종 정리일: 2026-10-12
- 현재 단계: **변환 코어·웹 P1(구조 재정의) 완료 / 웹 P2~P6 미착수**(P4 화면 목업 작성)
- 다음 작업: 웹 P2(인증) 착수

## 프로젝트 목표

Microsoft MarkItDown으로 업로드한 문서를 Markdown으로 변환하는 **개인용 웹 서비스**를 만든다.
본인만 로그인해 파일을 올리고 결과를 확인·복사·다운로드한다. 배포물은 Docker Hub의 통합 웹 서비스 이미지 하나이며,
HTTPS는 nginx 등 리버스 프록시에서 처리한다. 설계 기준: [웹 서비스 설계·계획](docs/web-service-plan.md).

## 현재 구성

| 영역 | 상태 |
|---|---|
| 변환 코어 `models`·`service`·`markitdown_adapter` | 완료. 7개 포맷, 입력 검증, UTF-8/LF 저장, 네트워크 미사용 |
| 웹 앱 `src/everythingmarkdown/web/` | 미착수 |
| Docker `Dockerfile`·`compose.yaml` | 미착수 |
| CI `ci.yml` | ruff·mypy·pytest, `main` push마다 실행 |
| 배포 `build.yml` | Docker Hub 빌드·푸시 job(수동). `Dockerfile` 전까지 실패 |
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
- [changelog](changelog.md): 배포 시 작성할 릴리즈 노트. 첫 배포는 `26.1.0`
- [P1 검증 기록](docs/p1-validation.md): 변환 코어 검증
- [서드파티 라이선스](docs/third-party-licenses.md): 의존성 라이선스 초안

원본 대화와 검토 기록은 로컬 `.omx/`에만 보관한다.
