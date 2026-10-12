# Changelog

EverythingMarkdown 버전별 변경 이력과 릴리즈 노트입니다. 최신 버전이 위에 옵니다.
각 버전 섹션은 태그 주석과 GitHub Release 본문에 그대로 사용합니다. 릴리즈 절차는 [README](README.md#릴리즈).

## [26.1.2] - 2026-10-12

로그인 화면 상단 바 보강과 문서 정리.

### Added
- 상단 바의 로그아웃 왼쪽에 GitHub 저장소 아이콘(새 탭으로 열림)과 현재 버전을 표시합니다. 폭이 좁은 휴대폰에서는 로고만 남겨 한 줄에 맞춥니다.

### Changed
- 배포·운영 안내(nginx 연결, 자동 갱신, 되돌리기·백업)와 릴리즈 절차를 README로 합쳤습니다.

### Removed
- 개발 중에 쓴 설계·계획, 화면 목업, 검증 기록, 릴리즈 정책, TODO·PROGRESS 문서(Git 이력에 보존).

### 이미지
- Docker Hub `igor0670/everythingmarkdown:26.1.2`, `latest` (같은 빌드), `linux/amd64`

## [26.1.1] - 2026-10-12

결과 화면 사용성 수정과 첫 설치용 파일 배포.

### Fixed
- 미리보기에서 긴 줄이 줄바꿈되면 줄번호 칸 밖으로 밀려 나오던 문제. 넘어간 줄도 내용 칸 안에 맞춰 표시합니다.
- `http://`로 접속하면 복사 버튼이 항상 "복사하지 못했습니다"가 되던 문제. 클립보드 API가 없는 http 환경에서도 복사합니다.
- 파일 이름 길이에 따라 복사·다운로드·삭제 버튼 위치가 바뀌던 문제. 넓은 화면에서는 항상 오른쪽 위, 좁은 화면에서는 항상 제목 아래에 둡니다.
- 원본 보관 안 함(N) 설정에서 변환 완료 직후 상태 조회에 원본이 잠깐 남아 있는 것으로 보이던 처리 순서.

### Added
- GitHub Release에 첫 설치용 `docker-compose.yml`과 `env.example`(`.env.example`)을 첨부합니다. 태그 푸시 시 워크플로가 Release를 만들고 파일을 올립니다.
- `docker-compose.yml`의 기본 이미지를 Docker Hub `igor0670/everythingmarkdown:latest`로 지정해, 내려받은 파일만으로 실행할 수 있습니다.

### Changed
- 저장소의 `compose.yaml`을 `docker-compose.yml`로 이름을 바꿨습니다.
- README를 첫 설치(파일 내려받기→디렉터리 구성→실행)와 개발 환경 중심으로 정리했습니다.

### 이미지
- Docker Hub `igor0670/everythingmarkdown:26.1.1`, `latest` (같은 빌드), `linux/amd64`

## [26.1.0] - 2026-10-12

첫 릴리즈. 문서를 올리면 Markdown으로 변환해 주는 개인용 웹 서비스를 Docker 이미지 하나로 배포합니다.

### Added
- 비밀번호 로그인: `.env`의 `APP_PASSWORD`(12자 이상) 하나로 접근을 막습니다. 서명 쿠키 세션(로그인 후 8시간), 같은 사이트 요청만 허용(Origin 검사), IP당 1분 5회 로그인 실패 제한.
- 문서 변환: PDF·DOCX·PPTX·XLSX·HTML·CSV·TXT 한 번에 한 개, 최대 25 MiB. 별도 프로세스에서 변환하며 120초를 넘으면 중단합니다. 대기·실행 중 작업은 최대 3개.
- 결과 화면: 업로드(선택·끌어놓기), 진행 상태, Markdown 원문 미리보기(64 KiB), 복사·다운로드·삭제, 실패·만료 안내.
- 보관 정책: 원본과 Markdown을 각각 보관(Y, 일수 지정) 또는 미보관(N)으로 설정. 미보관 원본은 변환 직후, 미보관 결과는 첫 다운로드 후 또는 60분 뒤 삭제. 5분마다 만료 파일 정리.
- 로그: `/logs/audit.log`·`/logs/access.log` JSON Lines(10 MiB × 10개 회전). 파일명·문서 내용·비밀번호는 기록하지 않습니다.
- 배포 구성: `Dockerfile`, `compose.yaml`(비루트, 읽기 전용 루트 파일시스템, 권한 제거, 자원 한도), `.env.example`, 배포 문서. 버전 태그 푸시로 이미지를 빌드·푸시합니다.

### 이미지
- Docker Hub `everythingmarkdown:26.1.0`, `everythingmarkdown:latest` (같은 빌드)
- 아키텍처: `linux/amd64`
- HTTP 8000 포트만 제공합니다. HTTPS는 nginx 등 리버스 프록시에서 처리합니다.

### 검증
- 자동 테스트 108개, ruff, mypy 통과.
- 로컬 컨테이너에서 로그인·변환·다운로드, 변환 중 재시작, 재생성 후 데이터·로그 유지, 보안 설정 확인.
- 수용 기준 25개 중 충족 17, 부분 8. 상세: [검증 기록](docs/web-validation.md).

### 알려진 제한
- nginx를 거친 HTTPS 동작과 실서버 자원은 아직 검증하지 않았습니다.
- 로그 날짜 기준 회전·30일 정리, 실행 중 로그 쓰기 실패 처리, 업로드 수신 시간 제한(nginx로 대체)은 없습니다.
- 미보관 결과를 같은 시각에 두 번 내려받으면 두 번째가 실패할 수 있습니다.
- 스캔한 이미지 PDF의 글자 인식(OCR)은 지원하지 않습니다.
