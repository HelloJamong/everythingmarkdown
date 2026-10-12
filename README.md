# EverythingMarkdown

Microsoft MarkItDown으로 업로드한 문서를 Markdown으로 변환하는 **개인용 웹 서비스**를 준비하고 있습니다.
Docker 이미지 하나로 배포하며, 본인만 로그인해 파일을 올리고 Markdown을 확인·복사·다운로드합니다.

> 현재는 **변환 코어만 구현된 상태**입니다. 웹 서버·로그인·업로드 화면과 Docker 이미지는 아직 없습니다.
> 단계별 계획은 [웹 서비스 전환 계획](docs/web-service-plan.md), 남은 작업은 [TODO](TODO.md)를 참고하세요.

## 목표

- 개인 도메인에서 `.env`에 설정한 비밀번호로 로그인해 문서 한 개씩 업로드·변환
- 지원 포맷: 텍스트 PDF, DOCX, PPTX, XLSX, HTML, CSV, TXT
- 결과 Markdown 원문 확인·복사·다운로드·삭제
- 원본/Markdown 보관 여부와 보관 일수를 `.env`로 각각 설정
- 서버가 관찰할 수 있는 접근·인증·변환·정리 이벤트를 `./logs`에 기록
- HTTPS는 앱이 아닌 nginx 등 리버스 프록시에서 처리. 앱은 HTTP만 제공

## 구성

```text
브라우저 → HTTPS → nginx 등 리버스 프록시 → 웹 앱 컨테이너 (HTTP)
                                             ├─ 비밀번호 로그인·서명 쿠키
                                             ├─ 업로드·작업 상태·다운로드
                                             ├─ SQLite (/data)
                                             └─ 변환 자식 프로세스 → 변환 코어
```

| 경로 | 내용 | 상태 |
|---|---|---|
| `src/everythingmarkdown/{models,service,markitdown_adapter}.py` | 변환 코어: 입력 검증, MarkItDown 호출, UTF-8/LF 저장 | 구현 완료 |
| `src/everythingmarkdown/web/` | 웹 앱 (FastAPI) | 인증·작업 API·변환·보관·로그·화면 완료 |
| `Dockerfile`, `compose.yaml` | 통합 웹 서비스 이미지·실행 구성 ([배포 문서](docs/web-deployment.md)) | 완료 |
| `.github/workflows/build.yml` | 버전 태그 푸시 시 Docker Hub 이미지 빌드·푸시 | 완료(첫 실행 전) |

## 개발 환경

Python 3.12와 [uv](https://docs.astral.sh/uv/)를 사용합니다.

```sh
uv sync --locked --group dev
uv run --locked --group dev pytest -q      # 전체 테스트
uv run --locked --group dev ruff check .    # lint
uv run --locked --group dev mypy            # 타입체크 (src)

# 로컬 실행 (프록시 없이 http로 접속할 때만 COOKIE_SECURE=false)
APP_PASSWORD='12자 이상 비밀번호' COOKIE_SECURE=false DATA_DIR=./data LOG_DIR=./logs \
  uv run --locked uvicorn --factory everythingmarkdown.web.app:create_app --port 8000
```

## 변환 코어 사용 예

웹 앱은 이 공통 서비스를 호출합니다.

```python
from pathlib import Path
from everythingmarkdown import ConversionRequest, ConversionService

result = ConversionService().convert(
    ConversionRequest(input_path=Path("report.docx"), launch_dir=Path("/data/work/job-id"))
)
print(result.output_path)  # <launch_dir>/convert_result/report.md
```

일반 로컬 파일만 허용하며 기존 결과는 덮어쓰지 않습니다. 오류는 `ConversionError.code`로 확인하고,
메시지에 문서 내용이나 파서 원문 예외를 넣지 않습니다. 상세 검증: [P1 검증 기록](docs/p1-validation.md).

## 범위와 한계

- 100 MiB 제한은 초기 제안값이며 악성 문서 격리나 자원 사용량 보장이 아닙니다.
- OCR, 이미지·오디오, URL 변환, 일괄 변환, 회원가입·다중 사용자, 공개 API는 범위 밖입니다.
- Markdown은 텍스트/구조 추출 결과이며 원본 레이아웃의 완전 재현을 보장하지 않습니다.

## 릴리즈 정책

- 배포물은 Docker Hub 이미지 `<DOCKERHUB_USERNAME>/everythingmarkdown`입니다. `latest`와 버전 태그를 함께 푸시합니다.
- [changelog.md](changelog.md)를 릴리즈 노트의 단일 원본으로 사용하고, 같은 노트를 annotated tag와 GitHub Release에 씁니다.
- 첫 배포는 `26.1.0`, 이후 `YY.메이저.마이너`. 배포 요청 전에는 버전·태그·Release를 만들지 않습니다.
- 상세: [릴리즈 정책](docs/releasing.md).

## 라이선스

이 프로젝트의 자체 코드는 [MIT License](LICENSE)를 따릅니다.
MarkItDown 및 전이 의존성 라이선스 목록은 [docs/third-party-licenses.md](docs/third-party-licenses.md)에 정리했고, 원문은 이미지의 `/usr/share/doc/everythingmarkdown/`과 각 패키지 `dist-info`에 들어 있습니다.
`.omx/`와 `.omc/`는 로컬 작업 기록으로 Git 추적 대상에서 제외합니다.
