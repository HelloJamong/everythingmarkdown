# P1 공통 변환 코어 검증

- 실행일: 2026-09-08 (Asia/Seoul)
- 단계: P1 구현·로컬 검증 완료. 제품 CLI/GUI, OS별 패키징·실환경 테스트와 구분한다.
- 환경: Rocky Linux 9.8 x86_64, CPython 3.12.13, MarkItDown 0.1.7, 기존 `uv.lock` 사용.
- 버전: 새 버전 항목 없음. 첫 배포 요청 시 `26.1.0` 기록 예정; 패키지 임시 버전 `0.0.0` 유지.

## 구현 계약

| 파일 | 책임 |
|---|---|
| `src/everythingmarkdown/models.py` | 불변 `ConversionRequest`/`ConversionResult`, `ErrorCode`와 `ConversionError` |
| `src/everythingmarkdown/service.py` | 경로·입력 검증, 결과 디렉터리 사전 확인, 배타적 생성·쓰기·정리 |
| `src/everythingmarkdown/markitdown_adapter.py` | 명시 컨버터 하나 등록, 로컬 변환, Markdown 반환, 의존성/파서 오류 정규화 |
| `src/everythingmarkdown/__init__.py` | GUI/CLI가 재사용할 공통 API 공개 |

- 호출자는 프로세스 시작 시 캡처한 절대 `launch_dir`와 `Path` 타입의 입력 경로를 제공한다.
  상대 launch_dir는 INVALID_INPUT이며 서비스가 현재 CWD를 대신 선택하거나 변경하지 않는다.
- 입력 심볼릭 링크·디렉터리·URL·비허용 확장자·100 MiB 초과·위장 ZIP을 거부한다.
  DOCX/PPTX/XLSX는 ZIP과 필수 OOXML 엔트리 존재를 확인한다. 전체 XML 유효성 검사는 파서 책임이다.
- 결과는 `<launch_dir>/convert_result/<input.stem>.md`에 UTF-8/LF로 저장한다.
  빈 결과는 파일을 만들지 않는다. 준비 중 생성된 빈 `convert_result` 디렉터리는 남을 수 있다.
- 디렉터리 사전 검사와 쓰기 가능 힌트 이후에도 `open('x')`로 생성 경쟁을 처리한다.
  같은 이름의 파일·디렉터리·심볼릭 링크는 보존한다.
- 쓰기와 파일 닫기가 완료돼야 성공을 반환한다. 실패 시 열린 파일의 식별정보와 경로의 현재 파일을
  비교해 이번 요청의 파일만 정리한다. 정리 실패/파일 교체 시 `ConversionError.path`와 `warnings`로 알린다.
- 오류 메시지에 원본 문서 본문이나 외부 파서 예외 문자열을 복사하지 않는다.
  의존성 누락이 MarkItDown의 `FileConversionException.attempts`에 감싸진 경우도 구분한다.

## 실행 결과

| 명령 | 결과 | 근거 |
|---|---|---|
| `.venv/bin/python -m unittest discover -s tests -v` | 종료 0, **74개 통과** | [전체 로그](evidence/p1-tests.log) |
| `unshare --user --map-root-user --net .venv/bin/python -m unittest discover -s tests -v` | 종료 0, **74개 통과** | [격리 로그](evidence/p1-tests-network-isolated.log) |
| `.venv/bin/python -m compileall -q src tests scripts packaging` | 종료 0, 문법 컴파일 검사 | [최종 검사](evidence/p1-final-checks.json) |
| `.venv/bin/python -m tabnanny src tests scripts packaging` | 종료 0, 들여쓰기 모호성 검사 | [최종 검사](evidence/p1-final-checks.json) |
| `uv pip check` | 종료 0, 기존 의존성 호환성 검사 | [최종 검사](evidence/p1-final-checks.json) |
| `uv sync --locked --group build` | 종료 0, 잠금 파일 변경 없이 환경 확인 | [최종 검사](evidence/p1-final-checks.json) |
| `git diff --check` 및 문서 링크/버전 항목/중복 함수 AST 검사 | 통과 | [최종 검사](evidence/p1-final-checks.json) |

테스트 구성: 기존 P0 15개 + 어댑터 8개 + 서비스 기본 32개 + 서비스 경계 14개 + 실제 엔진 통합 5개.

주요 검증:

- A06~A11/A22~A26 관련: CWD 분리, 한글/공백/대문자/다중 확장자, 입력/크기/링크/OOXML,
  원본 보존, UTF-8/LF, 동시 요청 둘 중 하나만 성공 및 기존 결과 보존.
- A12/A13 관련: 파서 손상, 의존성 누락, 빈 결과, 외부 오류 내용 미노출.
- A14~A16 관련: 경로/권한 오류, 쓰기·닫기 실패, 정리 실패 경고, 교체된 파일 삭제 방지.
- 실제 엔진 7포맷을 공통 서비스를 통해 저장하고 핵심 텍스트와 원본 해시를 확인.
- 외부 참조 HTML과 전체 샘플의 Python socket 연결/DNS 호출을 감시하고 OS 네트워크 namespace로
  격리한 전체 테스트를 재실행. 관리자 권한 상승이나 시스템 네트워크 설정 변경 없음.

## 검증 경계와 다음 작업

- 사용자 요청에 따라 Windows/macOS 실환경 테스트는 배포 후로 이관했다. 이번에 새 플랫폼 빌드는 하지 않았다.
- P0의 GUI/CLI 프로브는 여전히 진단용이며 제품 CLI/GUI는 P2/P3에서 공통 서비스에 연결한다.
- lint/typecheck 도구·설정은 아직 선정하지 않아 미실행이다. 새 의존성을 추가하지 않았다.
  `compileall`/`tabnanny`/AST 검사는 완전한 lint나 정적 타입 검사를 대신하지 않는다.
- 실패는 결정적 주입과 Linux 테스트로 확인했다. 실제 디스크 부족·Windows 권한·macOS 보안 정책 검증은 아니다.
- 100 MiB 제한과 OOXML 검사는 악성 문서 샌드박스/압축 해제 폭탄 방어가 아니다.
  외부 프로세스의 디렉터리 교체 공격, 전원 장애 원자적 저장, 하드 타임아웃은 보장하지 않는다.
- 경로 교체 확인과 unlink 사이의 악의적인 추가 교체까지 방어하지 않는다. 기존 로컬 단일 사용자 범위를 유지한다.
- 다음 작업: P2 CLI 인자/TTY 입력·도움말·버전 표시·stdout/stderr/종료 코드 연결.
