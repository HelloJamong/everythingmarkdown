# 서드파티 라이선스 고지

- 갱신일: 2026-10-12
- 범위: Docker 이미지에 **포함되는 런타임 의존성** 전체(`uv sync --locked --no-dev`). 개발 도구(pytest·ruff·mypy·httpx2)는 이미지에 없으므로 제외한다.
- 근거: 이미지 안에서 `importlib.metadata`로 이름·버전·라이선스 메타데이터와 라이선스 파일 포함 여부를 수집(잠금 파일 `uv.lock` 기준).
- 잠금 버전이 바뀌면 이 목록을 다시 만든다.

## EverythingMarkdown 자체

MIT License, Copyright (c) 2026 HelloJamong — 저장소 루트 [`LICENSE`](../LICENSE).

## 이미지에서 원문을 찾는 위치

- 이 문서와 `LICENSE`: `/usr/share/doc/everythingmarkdown/`
- 각 패키지의 LICENSE/NOTICE 원문: `/app/.venv/lib/python3.12/site-packages/<패키지>-<버전>.dist-info/` (wheel에 포함된 그대로)
- wheel에 원문이 없는 4개(markitdown, magika, flatbuffers, cobble): 저장소 [`licenses/`](../licenses/) → 이미지 `/usr/share/doc/everythingmarkdown/licenses/`
  - markitdown·magika·flatbuffers는 각 프로젝트 GitHub 저장소의 `LICENSE`를 그대로 가져왔다(2026-10-12).
  - cobble은 배포물에도 저장소에도 라이선스 파일이 없고 README에 "2-Clause BSD"만 적혀 있어, 표준 BSD-2-Clause 본문에 패키지 작성자를 저작권자로 적었다.
- Python 런타임과 Debian 기반 이미지의 고지는 베이스 이미지(`python:3.12-slim`)의 `/usr/share/doc/*/copyright`에 있다.

## 런타임 의존성

| 패키지 | 버전 | 라이선스(메타데이터) | 원문 |
|---|---|---|---|
| annotated-doc | 0.0.5 | MIT | 패키지 포함 |
| annotated-types | 0.8.0 | MIT | 패키지 포함 |
| anyio | 4.15.1 | MIT | 패키지 포함 |
| beautifulsoup4 | 4.15.0 | MIT License | 패키지 포함 |
| certifi | 2026.7.22 | Mozilla Public License 2.0 (MPL 2.0) | 패키지 포함 |
| cffi | 2.1.1 | MIT-0 | 패키지 포함 |
| charset-normalizer | 3.5.1 | MIT | 패키지 포함 |
| click | 8.5.0 | BSD-3-Clause | 패키지 포함 |
| cobble | 0.1.4 | BSD License | `licenses/` 보충 |
| coloredlogs | 15.0.1 | MIT License | 패키지 포함 |
| cryptography | 50.0.1 | Apache-2.0 OR BSD-3-Clause | 패키지 포함 |
| defusedxml | 0.7.1 | Python Software Foundation License | 패키지 포함 |
| et_xmlfile | 2.0.0 | MIT License | 패키지 포함 |
| fastapi | 0.143.0 | MIT | 패키지 포함 |
| flatbuffers | 25.12.19 | Apache Software License | `licenses/` 보충 |
| h11 | 0.16.0 | MIT License | 패키지 포함 |
| humanfriendly | 10.0 | MIT License | 패키지 포함 |
| idna | 3.19 | BSD-3-Clause | 패키지 포함 |
| itsdangerous | 2.2.0 | BSD License | 패키지 포함 |
| jinja2 | 3.1.6 | BSD License | 패키지 포함 |
| lxml | 6.1.3 | BSD-3-Clause | 패키지 포함 |
| magika | 0.6.3 | Apache Software License | `licenses/` 보충 |
| mammoth | 1.11.0 | BSD License | 패키지 포함 |
| markdownify | 1.2.3 | MIT License | 패키지 포함 |
| markitdown | 0.1.7 | MIT | `licenses/` 보충 |
| markupsafe | 3.0.4 | BSD-3-Clause | 패키지 포함 |
| mpmath | 1.3.0 | BSD License | 패키지 포함 |
| numpy | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 패키지 포함 |
| onnxruntime | 1.20.1 | MIT License | 패키지 포함 |
| openpyxl | 3.1.5 | MIT License | 패키지 포함 |
| opentelemetry-api | 1.45.1 | Apache-2.0 | 패키지 포함 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | 패키지 포함 |
| pandas | 3.0.5 | BSD License | 패키지 포함 |
| pdfminer.six | 20260107 | MIT | 패키지 포함 |
| pdfplumber | 0.11.10 | MIT License | 패키지 포함 |
| pillow | 12.3.0 | MIT-CMU | 패키지 포함 |
| protobuf | 7.36.1 | 3-Clause BSD License | 패키지 포함 |
| pycparser | 3.0 | BSD-3-Clause | 패키지 포함 |
| pydantic | 2.14.1 | MIT | 패키지 포함 |
| pydantic_core | 2.50.1 | MIT | 패키지 포함 |
| pypdfium2 | 5.13.0 | BSD-3-Clause, Apache-2.0, dependency licenses | 패키지 포함 |
| python-dateutil | 2.9.0.post0 | BSD License; Apache Software License | 패키지 포함 |
| python-dotenv | 1.2.3 | BSD-3-Clause | 패키지 포함 |
| python-multipart | 0.0.32 | Apache-2.0 | 패키지 포함 |
| python-pptx | 1.0.2 | MIT License | 패키지 포함 |
| requests | 2.34.2 | Apache Software License | 패키지 포함 |
| six | 1.17.0 | MIT License | 패키지 포함 |
| soupsieve | 2.9.2 | MIT | 패키지 포함 |
| starlette | 1.7.0 | BSD-3-Clause | 패키지 포함 |
| sympy | 1.14.0 | BSD License | 패키지 포함 |
| typing-inspection | 0.4.4 | MIT | 패키지 포함 |
| typing_extensions | 4.16.0 | PSF-2.0 | 패키지 포함 |
| urllib3 | 2.7.0 | MIT | 패키지 포함 |
| uvicorn | 0.54.0 | BSD-3-Clause | 패키지 포함 |
| xlsxwriter | 3.2.9 | BSD License | 패키지 포함 |

모두 허용형(permissive) 라이선스이고 copyleft(GPL/LGPL) 런타임 의존성은 없다.
`certifi`(MPL-2.0)는 파일 단위 약한 copyleft이며, 수정 없이 원본 고지를 유지한 채 포함하므로 추가 의무가 없다.
