# 배포 형태와 릴리즈 정책

- 작성일: 2026-09-08 (2026-10-12 개정: 데스크톱 ZIP 배포를 폐기하고 Docker 이미지 배포로 전환)
- 범위: 릴리즈 규칙 정의. 버전 메타데이터 변경, 태그 생성, 외부 배포는 이번 작업에 포함하지 않는다.
- 근거: 로컬 Jamong-Harvest의 `skills/versioning/SKILL.md`와 설치된 `versioning` 스킬, Jamong 배포 규칙.
- 사용자 지정 파일명에 따라 **루트 `changelog.md`(소문자)** 하나만 사용한다. `CHANGELOG.md`를 중복 생성하지 않는다.

## 1. 확정 요구

- 제품은 개인용 웹 서비스이며 **배포물은 통합 웹 서비스 Docker 이미지 하나**다. Windows/macOS 앱·CLI 배포물은 만들지 않는다.
- 모든 버전의 변경 이력과 릴리즈 노트는 `changelog.md`에 기록한다.
- 릴리즈 태그의 주석과 GitHub Release 본문은 해당 버전의 노트를 그대로 사용한다. GitHub Release에는 바이너리를 첨부하지 않는다.
- HTTPS는 이미지에 포함하지 않는다. nginx 등 리버스 프록시에서 종료한다([웹 서비스 전환 계획](web-service-plan.md)).

## 2. Docker 이미지 배포

| 항목 | 규칙 |
|---|---|
| 저장소 | Docker Hub `<DOCKERHUB_USERNAME>/everythingmarkdown` — **공개 저장소**(2026-10-12 확인) |
| CPU 아키텍처 | `linux/amd64` 단일 이미지(2026-10-12 결정) |
| 태그 | `latest`와 버전 태그(`YY.메이저.마이너`)를 **같은 빌드에서 함께** 푸시 |
| 빌드 | **버전 태그 푸시**로 `.github/workflows/build.yml` 실행(2026-10-12 결정): `ci.yml` 검사 → 태그·`pyproject.toml` 버전·`changelog.md` 항목 일치 확인 → 푸시. 시크릿 `DOCKERHUB_USERNAME`·`DOCKERHUB_TOKEN` |
| 서버 갱신 | `latest` digest 변경 감지 후 `docker compose pull && docker compose up -d`. **Watchtower는 사용하지 않는다** |

- 이미지 버전 태그는 Git 태그 이름을 쓴다. 워크플로가 `pyproject.toml`의 `version`과 다르면 중단하므로 릴리즈 커밋의 버전과 이미지 태그가 항상 일치한다.
- `YY.메이저.마이너` 형식이 아닌 태그(`v26.1.0`, `26.1.0-rc1` 등)는 워크플로를 시작하지 않는다. 운영 절차는 [배포 문서](web-deployment.md).
- digest 감지 방식(diun, cron 폴링 스크립트 등)은 배포 서버 구성 시 결정한다.
- 이미지에는 `.env`·`data/`·`logs/`·비밀 값을 포함하지 않는다(`.dockerignore`). 공개 저장소이므로 누구나 이미지 레이어를 내려받아 볼 수 있다는 전제로 검사한다.

## 3. 버전 규칙

Jamong-Harvest의 versioning 규칙을 따른다. SemVer의 호환성 의미와 혼동하지 않는다.

| 항목 | 규칙 | 예시 |
|---|---|---|
| 형식 | `YY.메이저.마이너` | `26.1.0` |
| 새 기능 | 메이저 증가, 마이너 0 | `26.1.3` → `26.2.0` |
| 버그/내부/문서 수정 | 마이너 증가 | `26.1.3` → `26.1.4` |
| 연도 변경 | 새 YY, 메이저·마이너 0 | `26.3.2` → `27.0.0` |
| 태그 | 버전 문자열과 동일, `v` 접두사 없음 | `26.1.0` |

- **사용자 배포 요청 전에는 버전을 작성·증가시키지 않는다.** 이 프로젝트의 최신 사용자 지침이 Jamong 스킬의 작업 완료 시 즉시 버전 기록 규칙보다 우선한다.
- 첫 배포는 `26.1.0`으로 기록한다. 이후 배포 요청 시 `changelog.md`의 최신 배포 버전을 확인하고 위 증가 규칙을 적용한다. `Unreleased` 항목은 사용하지 않는다.
- 최신 버전을 파일 상단에 `## [YY.메이저.마이너] - YYYY-MM-DD` 형식으로 작성한다.
- Added/Changed/Fixed/Removed 중 변경이 있는 섹션만 작성한다.
- 이미지 태그·지원 CPU 아키텍처, 검증 결과, 알려진 제한·호환성 주의사항도 해당 버전 섹션에 기록한다.
- 현재 릴리즈 이력은 없다. 이전에 작성했던 미배포 버전 항목은 사용자 요청으로 제거했으며 개발 이력은 PROGRESS/TODO와 Git 이력에 보존한다.
- 최초 버전 항목은 배포 시점에 `## [26.1.0] - <실제 배포 날짜>`로 작성한다.
- 현재 `pyproject.toml`의 `0.0.0`은 임시 메타데이터다. 태그와 다르면 `build.yml`이 중단하므로
  릴리즈 커밋에서 버전을 맞추고 `uv.lock`을 갱신한다.

## 4. 태그 주석과 GitHub Release 노트의 동일성

1. 사용자 배포 요청 후 최초 또는 다음 배포 버전의 노트를 작성한다. 태그가 가리킬 커밋의 `changelog.md`에서 해당 버전 헤더부터 다음 버전 헤더 직전까지 추출한다.
   파일 제목·서문·다른 버전 기록은 포함하지 않는다. 섹션 본문은 요약·번역·재작성하지 않는다.
2. 동일한 UTF-8/LF 노트 파일을 **annotated tag의 메시지**와 **GitHub Release 본문**에 사용한다.
   일반 lightweight tag에는 노트 본문을 보관할 수 없으므로 사용하지 않는다.
3. GitHub 자동 생성 노트나 커밋 목록으로 본문을 대체하거나 별도 문구를 덧붙이지 않는다.
4. 게시 전 태그 주석과 Release 본문을 원본 섹션과 비교한다. 말미 개행 외 차이가 있으면 게시를 중단한다.
5. 릴리즈 제목은 버전으로 통일한다. Docker 이미지도 동일 태그의 커밋에서 빌드한다.
6. 공개된 태그·기존 노트를 강제로 덮어쓰지 않는다. 수정이 필요하면 새 버전과 별도 승인으로 처리한다.

`git tag -a <version> -F <노트 파일>` 및 `gh release create <version> --verify-tag --notes-file <노트 파일>`
방식을 사용한다. **이 문서는 해당 명령 실행 요청이 아니다.** 향후 자동화 시 추출·일치 검사를 구현한다.

## 5. 현재 배포 준비 완료 조건

- [ ] 웹 P1~P6 구현과 자동 테스트·정적 검사·컨테이너 smoke 근거 확보. 미검증 항목을 명시.
- [x] `Dockerfile`·`compose.yaml`·`.dockerignore`·`.env.example` 작성, 이미지 build/up/health 확인(2026-10-12 로컬).
- [ ] MIT 및 이미지에 포함되는 의존성의 라이선스 고지 포함.
- [x] `changelog.md`, `pyproject.toml` 버전, 태그, 이미지 태그 일치 검사(`build.yml`이 자동 확인).
- [ ] 사용자 명시 요청 후 릴리즈 커밋(`chore: <version> 릴리즈`), annotated tag와 push 수행. 태그 push가 이미지 배포를 시작한다.
- [ ] 태그 push로 실행된 `build.yml` 성공 후 Docker Hub의 `latest`·버전 태그 digest가 같은지 확인.
- [ ] 동일한 노트로 GitHub Release 게시.

실서버 배포(DNS, nginx, 서버의 compose 갱신)는 별도 명시 요청 범위다.
GitHub 저장소는 비공개, Docker Hub 저장소는 공개다. 공개 범위 변경은 이 문서로 하지 않는다.
