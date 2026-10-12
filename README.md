# EverythingMarkdown

문서를 올리면 Markdown으로 변환해 주는 **개인용 웹 서비스**입니다. Microsoft [MarkItDown](https://github.com/microsoft/markitdown)으로 변환하며,
Docker 이미지 하나로 배포됩니다. `.env`에 정한 비밀번호로 로그인해 파일을 올리고 결과를 확인·복사·다운로드합니다.

- 지원 형식: 텍스트 PDF, DOCX, PPTX, XLSX, HTML, CSV, TXT (한 번에 한 개, 최대 25 MiB)
- 원본과 Markdown의 보관 여부·보관 일수를 각각 설정
- 접근·인증·변환·정리 기록을 `logs/`에 JSON Lines로 남김
- HTTPS는 앱이 아닌 nginx 등 리버스 프록시에서 처리하고, 앱은 HTTP만 제공
- 이미지: Docker Hub [`igor0670/everythingmarkdown`](https://hub.docker.com/r/igor0670/everythingmarkdown) (`linux/amd64`), 변경 이력: [changelog.md](changelog.md)

## 설치 (처음 구성)

필요한 것: `linux/amd64` 서버, Docker Engine과 Compose 플러그인(`docker compose`).

### 1. 구성 디렉터리 만들기

```sh
mkdir -p ~/everythingmarkdown/data ~/everythingmarkdown/logs
cd ~/everythingmarkdown
```

`data/`에는 업로드·변환 결과와 작업 DB(`app.db`)가, `logs/`에는 감사·접근 로그가 쌓입니다.

### 2. 설정 파일 내려받기

[최신 GitHub Release](https://github.com/HelloJamong/everythingmarkdown/releases/latest)에 첨부된 두 파일을 받습니다.
브라우저로 받아 옮겨도 되고, 서버에서 바로 받으려면:

```sh
curl -fsSLO https://github.com/HelloJamong/everythingmarkdown/releases/latest/download/docker-compose.yml
curl -fsSL -o .env https://github.com/HelloJamong/everythingmarkdown/releases/latest/download/env.example
chmod 600 .env
```

- GitHub는 점(`.`)으로 시작하는 첨부 파일 이름을 바꾸기 때문에 `.env.example`은 `env.example`로 올라가 있습니다. 받을 때 `.env`로 저장합니다.
- 특정 버전을 쓰려면 `latest/download` 대신 `download/26.1.1`처럼 버전을 넣습니다.

구성이 끝나면 디렉터리는 다음과 같습니다.

```text
~/everythingmarkdown/
├── docker-compose.yml
├── .env            # 비밀번호 등 설정 (권한 600, 외부 공유 금지)
├── data/
└── logs/
```

### 3. `.env` 수정

```sh
# 컨테이너가 data/·logs/에 쓸 수 있도록 현재 사용자 ID 지정
sed -i "s/^EMD_UID=.*/EMD_UID=$(id -u)/; s/^EMD_GID=.*/EMD_GID=$(id -g)/" .env
```

그다음 편집기로 `.env`를 열어 최소한 아래를 정합니다.

| 항목 | 설명 |
|---|---|
| `APP_PASSWORD` | 로그인 비밀번호. **12자 이상**, 예제 값 그대로면 시작하지 않음 |
| `EMD_BIND`, `EMD_PORT` | 앱 포트. 기본 `127.0.0.1:8000`(nginx가 같은 서버에서 연결) |
| `COOKIE_SECURE` | HTTPS 뒤에서는 `true`(기본). nginx 없이 http로 시험할 때만 `false` |
| `UPLOAD_KEEP`, `MARKDOWN_KEEP` | 원본·결과 보관 `Y`/`N`. `Y`면 `*_RETENTION_DAYS` 일수 필수 |
| `FORWARDED_ALLOW_IPS` | nginx 주소(실제 접속 IP를 믿을 프록시) |

나머지 항목은 `.env` 안의 설명을 참고하세요.

### 4. 실행과 접속

```sh
docker compose up -d
docker compose ps          # STATUS가 healthy가 되면 준비 완료
```

- **운영:** nginx에서 HTTPS를 받아 `127.0.0.1:8000`으로 넘깁니다. 아래 [nginx 연결](#nginx-연결-https)을 참고하세요.
- **LAN 시험(nginx 없음):** `.env`에 `EMD_BIND=0.0.0.0`, `COOKIE_SECURE=false`를 넣고 `docker compose up -d` 후 `http://<서버 IP>:8000`으로 접속합니다. 방화벽에서 포트를 열어야 할 수 있으며, 시험이 끝나면 되돌립니다.

### 운영 명령

```sh
docker compose pull && docker compose up -d   # 새 이미지로 갱신
docker compose logs -f                          # 컨테이너 출력
docker compose down                             # 중지 (data/·logs/는 남음)
```

비밀번호를 바꾸면 `.env` 수정 후 `docker compose up -d`로 다시 시작합니다(모든 로그인이 풀림).

### nginx 연결 (HTTPS)

```nginx
server {
    listen 443 ssl;
    server_name md.example.com;
    # ssl_certificate / ssl_certificate_key 는 서버 정책대로

    client_max_body_size 27m;      # 앱 한도: 요청 26 MiB, 파일 25 MiB
    client_body_timeout 120s;      # 업로드 수신 시간 제한(앱에는 없음)

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;                    # 필수: 없으면 모든 POST가 403
        proxy_set_header X-Forwarded-For $remote_addr;  # 로그인 횟수 제한·로그의 실제 IP
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- 앱은 `.env`의 `FORWARDED_ALLOW_IPS`에 적힌 주소가 보낸 `X-Forwarded-*`만 믿습니다. 같은 서버의 nginx는 컨테이너에서 Docker 브리지 게이트웨이(예: `172.17.0.1`)로 보이므로 `docker compose logs`의 접속 주소를 확인해 넣습니다.
- 운영에서는 `EMD_BIND=127.0.0.1`, `COOKIE_SECURE=true`(기본값)를 유지합니다.

### 자동 갱신 (digest 기반, Watchtower 미사용)

새 버전이 배포되면 `latest`의 digest가 바뀝니다. 아래 스크립트를 cron에 등록하면 바뀐 경우에만 다시 띄웁니다.

```sh
#!/bin/sh
# ~/everythingmarkdown/update.sh — cron 예: */10 * * * * ~/everythingmarkdown/update.sh
set -eu
cd "$(dirname "$0")"
before=$(docker compose images -q everythingmarkdown)
docker compose pull -q everythingmarkdown
after=$(docker image inspect -f '{{.Id}}' "$(docker compose config --images)")
[ "$before" = "${after#sha256:}" ] || docker compose up -d
```

갱신 중 진행하던 변환은 "중단됨"이 될 수 있으며, 다시 올리면 됩니다.

### 되돌리기·백업

- **되돌리기:** `.env`의 `EMD_IMAGE`를 이전 버전(예: `igor0670/everythingmarkdown:26.1.0`)으로 바꾸고 `docker compose up -d`. 그동안 자동 갱신은 멈춥니다.
- **백업:** `data/app.db`와 보관(Y)으로 설정한 `data/uploads`·`data/markdown`. `data/.work`는 제외합니다. 멈춘 상태에서 복사하는 것이 안전합니다: `docker compose stop && cp -a data data.bak && docker compose start`.
- **로그:** `logs/audit.log`·`logs/access.log`(JSON Lines, 10 MiB마다 회전·10개 보관)는 파일 보관 정책과 별개로 남습니다.

## 구성

```text
브라우저 → HTTPS → nginx 등 리버스 프록시 → 웹 앱 컨테이너 (HTTP :8000)
                                             ├─ 비밀번호 로그인·서명 쿠키
                                             ├─ 업로드·작업 상태·미리보기·다운로드
                                             ├─ SQLite (/data/app.db)
                                             └─ 변환 자식 프로세스 → 변환 코어(MarkItDown)
```

## 개발 환경

Python 3.12와 [uv](https://docs.astral.sh/uv/)를 사용합니다.

```sh
uv sync --locked --group dev
uv run --locked pytest -q        # 전체 테스트
uv run --locked ruff check .      # lint
uv run --locked mypy              # 타입체크 (src)
```

### 로컬에서 실행

```sh
# 프록시 없이 http로 접속하므로 COOKIE_SECURE=false
APP_PASSWORD='12자 이상 비밀번호' COOKIE_SECURE=false DATA_DIR=./data LOG_DIR=./logs \
  uv run --locked uvicorn --factory everythingmarkdown.web.app:create_app --port 8000
```

`http://localhost:8000`으로 접속합니다. `./data`·`./logs`는 Git에서 제외됩니다.

### 로컬 이미지로 실행

```sh
docker build -t everythingmarkdown:local .
# .env에 EMD_IMAGE=everythingmarkdown:local 을 넣고
docker compose up -d
```

### 저장소 구조

| 경로 | 내용 |
|---|---|
| `src/everythingmarkdown/{models,service,markitdown_adapter}.py` | 변환 코어: 입력 검증, MarkItDown 호출, UTF-8/LF 저장 |
| `src/everythingmarkdown/web/` | 웹 앱(FastAPI): `config`·`auth`·`jobs`·`worker`·`routes`·`logs`, `templates/`, `static/` |
| `tests/unit`, `tests/integration` | 변환 코어 테스트 |
| `tests/web` | 인증·작업·보관·로그·화면·수용 기준 테스트 |
| `Dockerfile`, `.dockerignore` | 이미지(비루트, healthcheck, TLS 미포함) |
| `docker-compose.yml`, `.env.example` | 실행 구성(Release에도 첨부) |
| `.github/workflows/ci.yml` | `main` 푸시·PR마다 ruff·mypy·pytest |
| `.github/workflows/build.yml` | 버전 태그 푸시 시 검사 → 이미지 푸시 → GitHub Release 게시 |
| `licenses/` | wheel에 원문이 없는 의존성 라이선스 보충본 |
| `docs/third-party-licenses.md` | 의존성 라이선스 목록(이미지에도 포함) |

### 변환 코어 사용 예

웹 앱은 이 공통 서비스를 별도 프로세스에서 호출합니다.

```python
from pathlib import Path
from everythingmarkdown import ConversionRequest, ConversionService

result = ConversionService().convert(
    ConversionRequest(input_path=Path("/data/uploads/<id>/input.docx"), launch_dir=Path("/data/.work/<id>"))
)
print(result.output_path)  # <launch_dir>/convert_result/input.md
```

일반 로컬 파일만 허용하며 기존 결과는 덮어쓰지 않습니다. 오류는 `ConversionError.code`로 확인하고,
메시지에 문서 내용이나 파서 원문 예외를 넣지 않습니다.

### 릴리즈

버전은 `YY.메이저.마이너`입니다. 새 기능은 메이저를 올리고 마이너를 0으로, 버그·문서 수정은 마이너를 올립니다. 연도가 바뀌면 `YY.0.0`부터 시작합니다.
변경 이력과 릴리즈 노트는 [changelog.md](changelog.md) 하나로 관리합니다.

1. `changelog.md` 맨 위에 `## [YY.메이저.마이너] - 날짜` 항목(Added/Changed/Fixed/Removed 중 해당 섹션)을 쓰고, `pyproject.toml` 버전을 맞춘 뒤 `uv lock`.
2. 릴리즈 커밋(`chore: <버전> 릴리즈`) 후 해당 changelog 섹션을 메시지로 annotated tag를 만들어 푸시합니다(`v` 접두사 없음).
3. `build.yml`이 검사 → 태그·버전·changelog 일치 확인 → Docker Hub `latest`·버전 이미지 푸시 → GitHub Release(같은 노트 + `docker-compose.yml`·`env.example`)를 처리합니다.

공개된 태그와 Release는 덮어쓰지 않고, 고칠 것이 있으면 새 버전으로 냅니다.

## 범위와 한계

- 스캔 이미지 PDF의 OCR, 이미지·오디오, URL 변환, 일괄 변환, 회원가입·다중 사용자, 공개 API는 지원하지 않습니다.
- Markdown은 텍스트·구조 추출 결과이며 원본 레이아웃을 완전히 재현하지 않습니다.
- 크기·압축·시간·자원 한도로 위험을 줄이지만 악성 문서에 대한 완전한 격리를 보장하지는 않습니다.
- 아직 확인하지 않은 것: nginx를 거친 HTTPS 동작, 디스크 부족, 다운로드 도중 만료·동시 다운로드. 로그 날짜 기준 회전은 없습니다.

## 라이선스

이 프로젝트의 코드는 [MIT License](LICENSE)를 따릅니다.
의존성 라이선스 목록은 [docs/third-party-licenses.md](docs/third-party-licenses.md)에 있고, 원문은 이미지의 `/usr/share/doc/everythingmarkdown/`과 각 패키지 `dist-info`에 들어 있습니다.
