# 서드파티 라이선스 고지 (초안)

- 갱신일: 2026-09-09
- 상태: **초안.** 배포 파일 게시 전 각 패키지의 실제 LICENSE 본문을 배포물에 포함하고 이 목록을 최종 확정한다.
- 범위: frozen 배포물에 **번들되는 런타임 의존성**. 개발·빌드 전용 도구(pytest, ruff, mypy)는 번들되지 않으므로 제외한다.
- 근거: `uv tree --no-dev`, `pip-licenses` (2026-09-09 기준 잠금 버전).

## EverythingMarkdown 자체

MIT License — 저장소 루트 [`LICENSE`](../LICENSE).

## 번들 런타임 의존성

| 패키지 | 버전 | 라이선스 |
|---|---|---|
| markitdown | 0.1.7 | MIT |
| beautifulsoup4 | 4.15.0 | MIT |
| soupsieve | 2.9.2 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| charset-normalizer | 3.5.1 | MIT |
| defusedxml | 0.7.1 | PSF |
| magika | 0.6.3 | Apache-2.0 |
| click | 8.5.0 | BSD-3-Clause |
| numpy | 2.5.3 | BSD-3-Clause (일부 파일 0BSD/MIT/Zlib/CC0-1.0) |
| onnxruntime | 1.20.1 | MIT |
| python-dotenv | 1.2.3 | BSD-3-Clause |
| markdownify | 1.2.3 | MIT |
| six | 1.17.0 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| certifi | 2026.7.22 | MPL-2.0 |
| idna | 3.19 | BSD-3-Clause |
| urllib3 | 2.7.0 | MIT |
| lxml | 6.1.3 | BSD-3-Clause |
| mammoth | 1.11.0 | BSD-2-Clause |
| cobble | 0.1.4 | BSD-2-Clause |
| pdfminer.six | 20260107 | MIT |
| cryptography | 50.0.1 | Apache-2.0 OR BSD-3-Clause |
| pdfplumber | 0.11.10 | MIT |
| pillow | 12.3.0 | MIT-CMU |
| pypdfium2 | 5.13.0 | BSD-3-Clause / Apache-2.0 (PDFium: BSD-3-Clause) |
| python-pptx | 1.0.2 | MIT |
| xlsxwriter | 3.2.9 | BSD-2-Clause |
| openpyxl | 3.1.5 | MIT |
| et-xmlfile | 2.0.0 | MIT |
| pandas | 3.0.5 | BSD-3-Clause |
| python-dateutil | 2.9.0.post0 | Apache-2.0 / BSD-3-Clause |

모두 배포에 조건 없는 허용형(permissive) 라이선스다. copyleft(GPL/LGPL) 런타임 의존성은 없다.
`certifi`(MPL-2.0)는 원본 고지 유지 조건으로 번들 가능하다.

## 빌드 도구 (번들 안 됨)

- **PyInstaller 6.22.2** — GPLv2. PyInstaller의 bootloader 예외 조항에 따라 생성된 실행 파일은
  임의 라이선스로 배포할 수 있으며, PyInstaller 자체 소스는 배포물에 포함되지 않는다.

## 배포 전 체크리스트

- [ ] 각 패키지의 LICENSE/NOTICE 원문을 배포물 `licenses/` 폴더 또는 앱 번들 리소스에 포함.
- [ ] Apple 공증·Windows SmartScreen용 서명 자격증명 확보 여부 확인 → [releasing.md](releasing.md) §5.
- [ ] 잠금 버전이 바뀌면 이 목록을 재생성.
