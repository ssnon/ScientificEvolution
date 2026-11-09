# M28 — 기존 M25 Activation Profile / M23.2 USD 예산 계약의 기본 실행 통합

2026-11-09 KST. 대상: `dev/meta-research-autonomy-v1`, 기준 `cea6d6c`.

## 개발의 이유

M23.3의 ON_DEMAND·COMPACT·SEPARATE·SELECTIVE_NO_WRITE 구현이 이전 M23.6.2–M24 실행에서 조용히 비활성화되는 재발을 겪었다. M25 Native Persistent Population은 명시적 Activation Profile, 지문, 실행 환경 드리프트 검증을 구현했으나, 새 M28 entrypoint는 이 계약을 자동 요구하지 않았다. 2026-11-09 A4-1 최초 ROOT에 프로파일·USD 예산이 저장되지 않았음을 확인했다. 이 수정은 **기능/운영 연속성**을 보장하기 위한 것이며 새로운 과학적 추론 능력을 선언하지 않는다.

## 적용된 계약

- 모든 **새** M28 `init`에서 기존 M25 스키마를 따르는 `--activation-profile` 및 기존 M23.2 스키마의 `--budget-config`를 명시적으로 요구한다. 프로파일의 `M232_BUDGET_REQUIRED=YES`를 요구한다. FULL/ON_DEMAND, COMPACT, SEPARATE, 캐시 모드와 SYN PMI 모드는 운영자가 선택한다. 과학자에게 연구 방법이나 연구자 수를 강제하지 않는다.
- `persistent.json`에는 **선언된** Activation Profile과 SHA256, 예산 파일의 SHA256를 보존하고 `meta_research.json`에도 두 지문을 기록한다. USD 설정은 실험 디렉터리 내부 `M232_DEV_BUDGET.json`에 저장한다. 기존 모델 단가·예약·정산 코드를 재사용하며, 숫자를 발명하지 않는다.
- `preflight`, `run`, `sync`, `materialize`에서 단일 `check_m28_experiment()`을 사용한다. 모든 새 M28 연구자는 같은 실험 ROOT 아래에서 공통 계약을 따른다. `run`은 선택된 모델도 비교한다.
- `DurableModel.call`의 **외부 호출 전 경계**에서도 활성 프로파일·환경·모델·예산 파일의 일치를 확인한다. PRIMARY가 아닌 자식 ROOT도 상위 실험을 찾아 동일 계약을 적용한다. 기존 `reserve_call()`과 `settle_call()`의 원래 비용 기록을 유지한다.
- M28 구버전에서 프로파일 없이 초기화된 연구는 최신 코드에서 **읽기 전용** `preflight`만 허용하며 새 `run`/`sync`/`materialize` 및 모델 호출을 차단한다. 새 코드를 기존 Source Pin에 덮어쓰거나 과거 Journal을 변경하지 않는다. 이전 코드가 필요하면 당시 pinned worktree를 사용해야 한다.

## 제한과 유의점

1. **USD 예약 한도는 실제 제공자의 절대적인 청구 한도가 아님.** 모델 단가·캐시·토큰 구조·제공자 과금 변동에 따라 추정과 실제가 다를 수 있다. 별도의 제공자 계정/키 지출 한도 확인 필요.
2. 이미 생성한 `M28_A41_LIVE_SCIENCE_20261109_01`은 원본 P0와 실험 기록을 보존하는 **프로파일 없는 구 ROOT**다. 자동으로 마이그레이션하거나 Source Pin을 바꾸지 않는다. 새로운 코드·프로파일로 새 실험을 시작한다.
3. 소프트웨어 테스트 성공, MOCK 자산, 모델 생성 주장, 실행된 Python 도구는 과학적 진리 또는 Level II 성취가 아님. 연구가 실제로 새로운 검증 가능한 주장·반례·계산·수정/근거 있는 HOLD에 도달했는지는 A4-1에서 따로 평가해야 한다.
4. 기존 M25 Native Persistent Population은 원래 `activation_contract.py`를 계속 사용한다. 공통 스키마·검증 함수를 재사용하되, M28의 새 실험 수준 예산 핀은 M28에만 추가했다. 이 변경은 모든 레거시 실행 스크립트의 전면 통합을 주장하지 않는다.
5. 모델 호출 중 불확정(`UNCERTAIN`) 응답은 자동 재청구/재시도하지 않는다. 예산 예약과 원본 Journal을 보존한다.

## 수용 조건

- 신규 M28 INIT: 프로파일 또는 예산 누락/형식 오류/환경 설정 불일치/허용되지 않는 모델/예산 정책은 거부, 새 실험 삭제 또는 변경 없음.
- M28 `preflight`: 실제 유효 프로파일/예산 지문 및 ROOT 현황 보고. 기존 구 ROOT는 읽기 전용 상태로만 보고.
- M28 `run`: 모델·환경·USD 설정 불일치에서 외부 호출 이전 거부. `sync`/`materialize`도 구 ROOT에서 실행 거부.
- 실제 `DurableModel` 경계에서 PRIMARY와 Child에 동일 계약 적용. 누락·모델/환경·예산 변경이 실제 네트워크 Provider 호출을 막는지 모의 Provider로 테스트.
- M28/M25/continuity/v3/v4/clean 회귀 테스트 통과. 실제 유료 연구 및 과학적 성과는 별도 승인/검증.

**상태:** 적용 패키지 제공. 사용자 WSL 실제 적용·회귀·새 실험 검증이 성공하기 전까지 통합 검증 완료로 표현하지 않음.
