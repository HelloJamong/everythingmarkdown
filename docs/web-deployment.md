# 웹 서비스 배포·운영

- 작성일: 2026-10-12
- 대상: Docker Hub 공개 이미지 `<DOCKERHUB_USERNAME>/everythingmarkdown`(`linux/amd64`)을 한 서버에서 compose로 실행하고, 같은 서버의 nginx가 HTTPS를 종료하는 구성.
- 실제 도메인·서버·nginx 위치는 아직 정하지 않았다. 아래 값은 예시다.

## 1. 이미지 배포 (태그 푸시)

배포는 **버전 태그 푸시**로 시작한다. `.github/workflows/build.yml`이 다음을 순서대로 수행한다.

1. `ci.yml`과 같은 검사(ruff·mypy·pytest).
2. 태그가 `pyproject.toml`의 `version`과 같은지, `changelog.md`에 `## [<태그>] - <날짜>` 항목이 있는지 확인. 다르면 중단.
3. `linux/amd64` 이미지를 한 번 빌드해 `latest`와 `<태그>`를 함께 Docker Hub에 푸시.

```sh
# 사용자 배포 요청 후에만. 버전·노트 규칙은 docs/releasing.md
git tag -a 26.1.0 -F <노트 파일>
git push origin 26.1.0
```

- 태그 형식은 `YY.메이저.마이너`이며 `v` 접두사를 붙이지 않는다. 형식이 다른 태그는 워크플로를 시작하지 않는다.
- 이미지 푸시 후 같은 워크플로가 GitHub Release를 만든다. 본문은 `changelog.md`의 해당 버전 섹션이고, 첫 설치용 `docker-compose.yml`과 `env.example`(= `.env.example`)을 첨부한다. Release가 이미 있으면 첨부 파일만 갱신한다.

## 2. 서버 준비

```sh
mkdir -p ~/everythingmarkdown/{data,logs} && cd ~/everythingmarkdown
curl -fsSLO https://github.com/HelloJamong/everythingmarkdown/releases/latest/download/docker-compose.yml
curl -fsSL -o .env https://github.com/HelloJamong/everythingmarkdown/releases/latest/download/env.example
chmod 600 .env
sed -i "s/^EMD_UID=.*/EMD_UID=$(id -u)/; s/^EMD_GID=.*/EMD_GID=$(id -g)/" .env
# .env: APP_PASSWORD(12자 이상) 등 수정
docker compose pull && docker compose up -d
docker compose ps        # STATUS가 healthy인지 확인
```

- 컨테이너는 `EMD_UID:EMD_GID` 사용자로 실행된다. `./data`·`./logs`를 같은 사용자가 소유하면 sudo 없이 쓸 수 있다. 쓸 수 없으면 앱이 시작을 거부한다.
- 앱 포트는 기본적으로 `127.0.0.1:${EMD_PORT}`에만 열린다. 외부에 직접 노출하지 않는다.
- nginx 없이 LAN에서 http로 시험할 때만 `.env`에 `EMD_BIND=0.0.0.0`, `COOKIE_SECURE=false`를 넣는다. 방화벽에서 해당 포트를 열어야 할 수 있다. 시험이 끝나면 되돌린다.
- 루트 파일시스템 읽기 전용, 모든 capability 제거, no-new-privileges, 메모리 2 GB·CPU 2개·PID 256 한도(실측 후 조정).
- `.env`는 Git·이미지에 넣지 않는다. 비밀번호가 `.env`와 컨테이너 환경에 평문으로 남는다.
- 비밀번호 변경: `.env` 수정 후 `docker compose up -d`. 모든 로그인이 풀린다.

## 3. nginx 리버스 프록시 (HTTPS 종료)

```nginx
server {
    listen 443 ssl;
    server_name md.example.com;
    # ssl_certificate / ssl_certificate_key 는 서버 정책대로

    client_max_body_size 27m;      # 앱 한도: 요청 26 MiB, 파일 25 MiB
    client_body_timeout 120s;      # 업로드 수신 시간 제한(앱에는 없음)

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;                       # 필수: 없으면 Origin 검사에서 모든 POST가 403
        proxy_set_header X-Forwarded-For $remote_addr;     # 로그인 횟수 제한·로그의 실제 IP
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

- 앱은 `X-Forwarded-*`를 `FORWARDED_ALLOW_IPS`에 적힌 주소에서 온 것만 믿는다. 호스트 nginx가 publish된 포트로 들어오면 컨테이너에서는 Docker 브리지 게이트웨이(예: `172.17.0.1`, compose 네트워크면 `172.18.0.1` 등)로 보인다. `docker compose logs`의 접속 주소로 확인해 `.env`에 넣는다.
- `COOKIE_SECURE=true`(기본)는 HTTPS에서만 로그인 쿠키가 저장된다. nginx 없이 LAN에서 `http`로 시험할 때만 `false`.
- nginx를 다른 서버에 둘 경우 포트 바인딩과 방화벽 규칙을 따로 정한다.

## 4. 업데이트 (digest 기반, Watchtower 미사용)

새 이미지가 푸시되면 `latest`의 digest가 바뀐다. 서버는 이를 감지해 갱신한다.

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

- 갱신 중에는 진행 중인 변환이 중단(interrupted)될 수 있다. 재시작 후 다시 올리면 된다.
- 되돌리기: `.env`의 `EMD_IMAGE`를 이전 버전 태그(예: `...:26.1.0`)로 바꾸고 `docker compose up -d`. 이 동안 자동 갱신 스크립트는 멈춘다.

## 5. 백업·로그

- 백업 대상은 `data/app.db`(작업 메타데이터)와 보관 Y로 설정한 `data/uploads`·`data/markdown`이다. `data/.work`는 제외한다.
- 서비스를 멈춘 상태에서 복사하는 것이 안전하다: `docker compose stop && cp -a data data.bak && docker compose start`.
- 로그는 `logs/audit.log`·`logs/access.log`(JSON Lines, 10 MiB마다 회전·10개 보관). 파일 보관 정책과 별개로 남는다.
