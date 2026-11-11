# M28 Terminal Judgment / Native Runtime Successor (2026-11-11)

## 관찰된 실패

DAC M28 `M28_DAC_NO3RR_20261111_02`에서 Journal 231 SAVED, Controller 29 committed, Assets 28, Works 19 DONE, organization requests 0. 마지막 과학 검토 ONGOING. 마지막 4개의 Controller 수리 실패가 `META_A2_PRIMARY_TERMINAL_REQUIRES_PROGRAM_REVIEW` 및 `R5_CANDIDATE_DISPOSITION_MISMATCH`를 반복하고 `SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED`, `NO_ACTIONABLE_ROOT_OR_SCIENTIFIC_STATE_CHANGE`로 운영상 정지. 인간이 부정·완료 결론을 삽입해서 해결해서는 안 됨.

## 수정 범위

1. `META_A2` 프롬프트/실행 계약: PRIMARY terminal decision에서 `program_portfolio_review` 필수, CONTINUE일 때만 선택; 실제 자식 0개면 목록 `[]`. 프로그램 검토는 모델 작성. 검증기 약화·자동 형식 채우기 없음.
2. M28 한정 `REVIEW_WORTHY_CANDIDATE`에서 실제 P0 완료와 `SUBPROBLEM_ONLY`·`PAUSED_EVIDENCE/PAUSED_LOW_INFORMATION`의 *검토 가치가 있는 조건부 후보*를 구분. 후보에 실존하는 지원 Asset 필수; 코어 `PROGRAM_OBJECTIVE_ASSESSED`의 `COMPLETED` → ORIGINAL_PROBLEM + 근거 조건 보존. 기존 R5 비-M28 적용 변경 없음.
3. 원본 연구 ROOT는 보존. `M28_NATIVE_RESEARCH_SUCCESSOR.json`에 parent path/source pin SHA/Journal head/prefix events/원본 blob names/누적 비용/P0 SHA 기록. 새 experiment는 기존 `ROOTS/PRIMARY`를 바이트 그대로 복사하고 새 Source Pin을 생성. 복사 직후 **운영** 마커 `OPERATIONAL_PAUSE` 1개만 append (과학적 사건 아님). 원본 메타/과학 자산/논문 출처를 합성하지 않음.
4. **해당 successor만** 최근 복구 실패 window를 재설정하고, 새로운 합법적 Controller 판단을 요청할 수 있게 스케줄러 및 Engine를 수정. 과거 거부 원문은 기존 Journal에 그대로 있음. 확정된 과학적 종료가 없으면 시스템이 임의로 종료·중단을 과학적 HOLD로 표시하지 않음.
5. 이전 $10 예산에서 원본 *정산 완료* 실제 청구액을 빼 새 실험의 **나머지 예산**으로 설정. 옛 레코드는 새 실험 DB로 옮겨 가짜 신규 사용으로 저장하지 않음. 두 실험은 `upstream_accounted_usd` + successor 신규 ledger 합계로 회계. 다른 병렬 successor는 지원하지 않음.

## 제한 및 회귀 조건

- 기존 Source Pin의 해시가 Git 원본 `9487b96`의 실제 Python 파일 내용과 맞을 때만 승계. 옛 ROOT에 자식 ROOT/열린 Work/uncertain call이 있으면 거부. 신규 목적지는 미사용 경로만 허용.
- 원본 Root의 **exact event prefix**를 보존하지만, 후속 연구의 실행은 새 런타임 코드 하에 수행된다. 따라서 이전 연구를 이전 런타임에서 계속 수행한 것과 동일하다고 주장하지 않는다. 구간 경계는 manifest에 명시.
- 연구자 수, 과학적 방향, 연구 단계 수, 강제 FRESH/합성/종료를 추가하지 않는다.
- 인과적인 DAC 협력 기작 발견이나 Level-II scientific certification과는 무관한 운영 코드 수정.
- M28/m25/continuity/v3/v4/clean No-paid 회귀와 기존 원본이 변경되지 않았는지 확인 후에만 커밋·새 ROOT 생성. 실제 유료 실행은 별도의 사용자 승인 단계.
