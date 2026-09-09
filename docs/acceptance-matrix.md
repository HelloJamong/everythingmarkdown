# A01~A26 수용 기준 현황

- 갱신일: 2026-09-09
- 대상: [검증 명세](test-spec.md)의 수용 기준
- 실행: `uv run --group dev pytest` — 전체 126개 통과(unittest subTest 포함). 근거: [P1](p1-validation.md) · [P2](p2-validation.md)
- 표기: **통과**(로컬 자동 테스트 통과) · **부분**(핵심 경로는 통과, 일부는 이관/주입) · **이관**(배포 후 실환경 테스트)

| ID | 요약 | 상태 | 근거 테스트 |
|---|---|---|---|
| A01 | 실제 엔진 7포맷 변환·핵심 문자열 보존 | 통과 | `test_conversion.test_seven_formats_save_utf8_in_launch_directory_without_network` |
| A02 | GUI/CLI 동일 입력 결과 일치 | 부분 | `test_conversion.test_gui_and_cli_produce_identical_result_for_same_input` (실제 OS 창은 이관) |
| A03 | CLI 파일 인자·TTY 대화형 입력 | 통과 | `test_cli.*`, `test_cli.test_real_tty_input_converts_quoted_unicode_path` |
| A04 | 인자 없는 비TTY 즉시 사용법 오류 | 통과 | `test_cli.test_non_tty_without_argument_is_immediate_usage_error` |
| A05 | GUI 선택→변환, 예상 경로·성공 안내 | 부분 | `test_gui.*` (상태 로직), 실제 창은 이관 |
| A06 | 다중 확장자·공백·한글·Unicode 파일명 | 통과 | `test_service.test_preserves_unicode_spaces_uppercase_and_multidot_stem`, `test_cli.test_installed_console_entry_point_matches_module` |
| A07 | CWD·입력·실행 파일 위치 분리 저장 | 통과 | `test_cli.test_module_converts_seven_formats_in_separate_cwds`, `test_service.test_absolute_input_keeps_launch_dir_as_output_base` |
| A08 | `convert_result` 자동 생성 | 통과 | `test_service.test_creates_convert_result_directory_when_missing` |
| A09 | 같은 stem·기존 결과 보존/충돌 | 통과 | `test_conversion.test_same_stem_different_formats_preserve_first_result`, `test_cli.test_collision_returns_four_and_preserves_result` |
| A10 | 동시 저장 경쟁, 최대 1개 성공 | 부분 | `test_service_edges.test_two_concurrent_requests_only_one_succeeds` (주입 기반) |
| A11 | 누락·디렉터리·URL·미지원·초과 거부 | 통과 | `test_service.test_rejects_*`, `test_cli.test_missing_input_returns_two` |
| A12 | 파서 손상·어댑터 예외의 안전 처리 | 부분 | `test_conversion.test_corrupt_pdf_is_safe_conversion_error`, `test_markitdown_adapter.test_parser_errors_are_sanitized` — 암호화 PDF fixture는 미보강 |
| A13 | 빈 결과·텍스트 없는 PDF, OCR 미주장 | 통과 | `test_conversion.test_empty_text_is_not_saved`, `test_conversion.test_text_free_pdf_fails_without_claiming_ocr` |
| A14 | read-only CWD·파일/링크인 `convert_result` | 부분 | `test_service.test_rejects_when_convert_result_is_file`/`_is_symlink`, `test_service_edges.test_output_preflight_permission_failure_avoids_engine` (권한은 주입) |
| A15 | 쓰기/닫기 실패·용량 부족, 미완성 정리 | 통과 | `test_service.test_write_failure_removes_partial_output`, `test_close_failure_removes_partial_output` |
| A16 | 정리 실패 시 경고·잔여 경로 안내 | 통과 | `test_service.test_cleanup_failure_is_reported_as_warning` |
| A17 | 느린 엔진에서 UI 유지·중복 방지·워커 격리 | 부분 | `test_gui.test_convert_runs_single_worker_and_reports_success`, `test_worker_only_touches_queue_not_view` — 실제 이벤트 루프는 이관 |
| A18 | 선택 취소·실패 후 재시도·작업 중 닫기 | 부분 | `test_gui.test_cancelled_dialog_keeps_previous_selection`, `test_close_while_running_defers_until_result` — 실제 창은 이관 |
| A19 | Ctrl+C·EOF·빈 입력 종료 코드 | 부분 | `test_cli.test_interactive_eof_and_ctrl_c_are_cancelled`, `test_ctrl_c_during_conversion_is_cancelled`, `test_p0.test_cli_cancellation` — 실제 SIGINT는 이관 |
| A20 | Windows/macOS frozen·Python 미설치 실행 | 이관 | 배포 후 실환경 테스트 |
| A21 | 네트워크 차단 + 외부 참조 HTML | 통과 | `test_conversion.test_html_external_references_do_not_fetch`, OS 네트워크 격리 재실행 로그 |
| A22 | 미관련 파일 무변경 | 부분 | `test_conversion.test_seven_formats_*` (fixture 해시 비교), `test_service_edges.test_failed_write_never_deletes_replacement_file` |
| A23 | 입력 심볼릭 링크·끊어진 결과 링크·대문자 확장자 | 통과 | `test_service.test_rejects_symlink_input`, `test_rejects_existing_broken_output_symlink`, `test_service_edges.test_broken_input_symlink_is_invalid_not_followed` |
| A24 | CRLF/CR 정규화·한글·BOM 없음 | 통과 | `test_service.test_writes_utf8_lf_without_bom` |
| A25 | 위장 ZIP·URL·이미지·오디오 입력 거부 | 통과 | `test_service.test_rejects_disguised_zip_for_plain_text_extension`, `test_service_edges.test_urls_are_rejected_before_adapter`, `test_markitdown_adapter.test_single_converter_registration_and_markdown_api` |
| A26 | 포맷별 어댑터, 지정 컨버터 1개만 등록 | 통과 | `test_markitdown_adapter.test_single_converter_registration_and_markdown_api`, `test_requests_create_independent_engines`, `test_p0.test_registers_only_selected_converter` |

## 남은 항목

- **A12 암호화 문서:** 암호화 PDF fixture 생성에는 별도 라이브러리(pypdf/pikepdf)가 필요하다. 현재는 손상 PDF·어댑터 예외로 안전 경로만 검증한다.
- **A02/A05/A17/A18/A19/A20:** 실제 창·이벤트 루프·SIGINT·frozen 실행은 [배포 후 실환경 테스트](test-spec.md#현재-실행-범위-변경-2026-09-08)로 이관. 상태·스레드·종료 로직은 위 테스트로 검증했다.
- **A10/A14/A22:** 권한·경쟁·디스크 오류는 결정적 주입으로 검증했고, 실제 OS 권한 환경 재현은 배포 후 테스트에서 보강한다.
