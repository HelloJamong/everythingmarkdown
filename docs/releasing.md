# 최종 배포 요구와 릴리즈 정책

- 작성일: 2026-09-08
- 범위: 릴리즈 규칙 정의. 설치기 구현, 버전 메타데이터 변경, 태그 생성, 외부 배포는 이번 작업에 포함하지 않는다.
- 근거: 로컬 Jamong-Harvest의 `skills/versioning/SKILL.md`와 설치된 `versioning` 스킬.
- 사용자 지정 파일명에 따라 **루트 `changelog.md`(소문자)** 하나만 사용한다. `CHANGELOG.md`를 중복 생성하지 않는다.

## 1. 확정 요구와 남은 검증

확정 요구:

- 모든 버전의 변경 이력과 릴리즈 노트는 `changelog.md`에 기록한다.
- 릴리즈 태그의 주석과 GitHub Release 본문은 해당 버전의 노트를 그대로 사용한다.
- Windows는 `.exe` 기반으로 GUI와 CUI(이 문서의 CLI)를 모두 제공한다.
- macOS는 `.app` 애플리케이션으로 GUI와 CUI를 모두 제공한다.
- 사용자가 Python이나 pip 의존성을 별도로 설치하지 않아도 실행할 수 있어야 한다.

사용자가 권장안을 선택한 최종 배포 형태:

- Windows는 **설치용 `.exe` 하나**에 별도 GUI/CUI 실행 파일과 리소스를 담는다.
  설치 없이 실행하는 단일 EXE의 모드 전환 방식은 채택하지 않는다.
- macOS는 GUI/CUI 진입점을 포함한 단일 `.app`을 `.zip`으로 전달한다. DMG는 배포하지 않는다.
  사용자는 압축 해제 후 앱을 실행하며 `/Applications` 이동은 선택 사항이다.
- Windows 11 x64 / macOS 14+ Apple Silicon은 기존 시험 대상 제안이며 실제 지원 확정은 검증 후다.

## 2. 채택한 배포 구성 — 아직 최종 바이너리 없음

| 플랫폼 | 다운로드 파일 명명 규칙 | 설치/실행 후 구성 | 사용 방식 |
|---|---|---|---|
| Windows | `EverythingMarkdown-<version>-windows-x64-setup.exe` | `EverythingMarkdown.exe`(GUI), `everythingmarkdown-cli.exe`(CUI), 공통 리소스 | 시작 메뉴/더블클릭 GUI; PowerShell/CMD에서 CLI 실행 |
| macOS | `EverythingMarkdown-<version>-macos-arm64.zip` | `EverythingMarkdown.app`, 앱 번들 내부의 GUI/CLI 실행 진입점 | Finder 더블클릭 GUI; 터미널에서 번들 내부 CLI 직접 실행 |

예상 사용 예이며 현재 P0 명령을 대체하지 않는다:

```powershell
# 실제 설치 위치는 설치기 정책 확정 시 안내한다.
& "<설치 경로>\everythingmarkdown-cli.exe" ".\report.docx"
```

```sh
"/Applications/EverythingMarkdown.app/Contents/MacOS/everythingmarkdown-cli" ./report.docx
```

- Windows에서 GUI는 불필요한 콘솔 없이, CLI는 stdin/stdout/stderr·파이프·종료 코드가 정상 동작해야 한다.
  PyInstaller의 console/windowed 구분을 따른다. [공식 사용법](https://pyinstaller.org/en/stable/usage.html)
- GUI windowed 빌드에 단순히 `--cli` 인자를 추가하는 대신 console 진입점을 분리해
  콘솔 연결/숨김과 셸 대기 동작을 검증한다. 단일 무설치 EXE는 이번 배포 범위가 아니다.
- macOS CLI는 Finder나 `open`을 경유하지 않고 번들 안의 실행 파일을 직접 호출한다.
  셸 별칭/심볼릭 링크는 편의 기능이며 PATH나 시스템 경로를 자동 변경하지 않는다.
  `.app` 내부 실행 파일의 터미널 실행은 [PyInstaller 동작 설명](https://pyinstaller.org/en/stable/operating-mode.html)을 참고한다.
- 앱의 CLI helper와 런타임을 함께 패키징해야 한다. 현재 `packaging/build_p0.py`가 만드는 분리된
  P0 배포물은 최종 단일 앱 번들 구현이 아니다.
- Windows 설치 EXE를 만들기 위해 PyInstaller 결과를 담는 설치기 단계가 추가로 필요하다.
  설치기 도구·추가 의존성·자동 업데이트는 아직 선택하거나 도입하지 않는다.
- 시작 CWD를 저장 기준으로 삼는 기존 계약을 유지한다. 설치 디렉터리나 앱 내부로 CWD를 변경하지 않는다.

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
- 지원 OS/CPU, 배포 파일명, 검증 결과, 알려진 제한·호환성 주의사항도 해당 버전 섹션에 기록한다.
- 현재 릴리즈 이력은 없다. 이전에 작성했던 미배포 버전 항목은 사용자 요청으로 제거했으며 개발 이력은 PROGRESS/TODO와 P0 검증 기록에 보존한다.
- 최초 버전 항목은 배포 시점에 `## [26.1.0] - <실제 배포 날짜>`로 작성한다.
- 현재 `pyproject.toml`의 `0.0.0`은 P0 임시 메타데이터다. 배포 전 반드시 선택한 릴리즈 버전으로
  맞추고 `uv.lock`, GUI/CLI 버전 표시, Windows 파일 정보, macOS 번들 버전을 검증한다.

## 4. 태그 주석과 GitHub Release 노트의 동일성

1. 사용자 배포 요청 후 최초 또는 다음 배포 버전의 노트를 작성한다. 태그가 가리킬 커밋의 `changelog.md`에서 해당 버전 헤더부터 다음 버전 헤더 직전까지 추출한다.
   파일 제목·서문·다른 버전 기록은 포함하지 않는다. 섹션 본문은 요약·번역·재작성하지 않는다.
2. 동일한 UTF-8/LF 노트 파일을 **annotated tag의 메시지**와 **GitHub Release 본문**에 사용한다.
   일반 lightweight tag에는 노트 본문을 보관할 수 없으므로 사용하지 않는다.
3. GitHub 자동 생성 노트나 커밋 목록으로 본문을 대체하거나 별도 문구를 덧붙이지 않는다.
4. 게시 전 태그 주석과 Release 본문을 원본 섹션과 비교한다. 말미 개행 외 차이가 있으면 게시를 중단한다.
5. 릴리즈 제목은 버전으로 통일한다. 배포 파일도 동일 태그의 커밋에서 빌드한다.
6. 공개된 태그·기존 노트를 강제로 덮어쓰지 않는다. 수정이 필요하면 새 버전과 별도 승인으로 처리한다.

`git tag -a <version> -F <노트 파일>` 및 `gh release create <version> --verify-tag --notes-file <노트 파일>`
방식을 사용한다. **이 문서는 해당 명령 실행 요청이 아니다.** 향후 자동화 시 추출·일치 검사를 구현한다.

## 5. 현재 배포 준비 완료 조건

2026-09-08 사용자 요청으로 **실환경 테스트는 배포 후 별도 테스트 환경에서 진행**한다.
현재 개발·배포 전 필수 조건에서 제외하되 통과로 기록하지 않는다. 이 결정은 지금 태그·게시를 실행하라는 요청이 아니다.

- [ ] P1~P4 구현과 로컬 자동 테스트·정적 검사 근거 확보. A01~A26의 이관/미실행 항목을 명시.
- [ ] 선택한 최종 배포 형태로 목표 OS의 빌드 환경 또는 CI에서 별도 빌드.
- [ ] GUI 상태 로직, CLI 입력·스트림·종료 코드, 변환·저장 로직의 자동 테스트.
- [ ] 배포 파일 구조·필수 리소스 포함 여부 확인. 실제 GUI·콘솔 실행은 배포 후 테스트로 분리.
- [ ] Windows 서명, macOS Developer ID 서명·공증 필요사항과 자격증명 확보 여부 확인.
  미서명 시험판과 정식 배포판을 구분하고 보안 경고가 없다고 보장하지 않는다.
  macOS 기준은 [Apple 배포 전 공증 안내](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)를 따른다.
- [ ] MIT 및 모든 번들 의존성의 라이선스 고지 포함.
- [ ] `changelog.md`, 패키지/앱 버전, 태그, 파일명 일치 검사.
- [ ] 선택한 Windows/macOS 파일과 다운로드 무결성 확인용 `SHA256SUMS` 준비.
- [ ] 사용자 명시 요청 후 릴리즈 커밋(`chore: <version> 릴리즈`), annotated tag와 push 수행.
- [ ] 동일한 노트의 GitHub Release와 생성된 배포 파일을 게시하고 원격 파일·체크섬을 재확인.
  노트에는 Windows/macOS 실환경 미검증과 알려진 서명·공증 상태를 명시한다. 빌드 성공을 실행 보장으로 표현하지 않는다.

### 배포 후 별도 테스트 (현재 범위 제외)

- Windows/macOS Python 미설치 환경의 설치·GUI/CUI·7포맷 실행.
- 실제 터미널·Finder·Explorer, CWD/권한, 한글·공백 경로, 키보드/배율/응답성.
- Gatekeeper/Windows 보안 정책과 런타임 의존성, GUI/CUI 결과 일치.
- 결과 기록과 지원표 확정, 필요 시 후속 수정 릴리즈.

**빌드 환경은 여전히 필요하다.** 테스트를 이관해도 Linux 빌드만으로 Windows EXE와 macOS 앱을 생성했다고 간주하지 않는다.

현재 저장소는 비공개다. 일반 사용자 공개 다운로드는 저장소 공개 전환 또는 별도 배포 채널에 대한
명시 결정이 필요하며, 이 문서만으로 공개 범위를 변경하지 않는다.
