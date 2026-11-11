# ScientificEvolution M29.2 — 중심 Controller 계약의 단일 실행 경로 통합

**기준:** `dev/meta-research-autonomy-v1` / `303ca4b2de4cfbdea5cf3026d4bb9784e6129a17`. 2026-11-11. 

## 검증된 문제

M28 `_06`의 실제 V4+V3 실행은 `scientific_closed_loop_v3.controller_v3()`를 사용한다. 그런데 M28 A1/A2 및 M29/M29.1 프롬프트 확장은 별개의 `Engine.controller()`에만 적용되어, 공통 `controller_plan()`의 엄격한 검증기에만 도달했다. 저장된 23개 Controller 요청의 시스템 메시지에 새 계약이 없었고, 6개 HOLD는 M291 필드 누락으로 거부되었다. 이는 모델의 자율적 종료 판단 실패로 평가하지 않는다. 입력에는 생성된 자산이 존재했고 모델이 일부를 명시적으로 참조했다.

## 수정 범위 — 기존 정책 재사용, 신설 과학 규칙 없음

- `e2core.engine.effective_controller_contract(j, base_prompt, base_context)`를 공통 계약 구성기로 생성.
- `Engine.controller()`와 `scientific_closed_loop_v3.controller_v3()` 모두 해당 함수를 호출한다.
- `META_RESEARCH_AUTONOMY_ACTIVATED` 경우에만 M28-A1 지시 및 `meta_research_organization_context`를 전달한다.
- `META_RESEARCH_COLLABORATION_ACTIVATED` 경우에만 M28-A2 및 M29의 프롬프트를 추가한다.
- `m291_frontier_contract.active(j)`가 참인 **정확히 source-pinned successor**에서만 M29.1 명시적 프론티어 평가 계약을 추가한다. 현재 M291의 검증 규칙/명시적 판단 상태는 바꾸지 않는다.
- 이미 있던 V3의 NVT/PMI/OPP, V4 advisory, math claim selection 등을 제거하지 않는다. 기존 M23.2 ON_DEMAND, COMPACT, SEPARATE는 전송 전 투명한 프레젠테이션 계층으로 유지한다.
- `new_problems`, `organization_requests`, `collaboration_requests`, `program_portfolio_review`와 Journal 스키마 및 검증은 변경하지 않는다.
- 일반 비-meta 연구 ROOT는 프롬프트와 컨텍스트 동일성이 유지되어야 한다.

## 통합 검사 기준

새 `checks/m28/test_m292_controller_route_unification.py`에서 다음을 무유료 확인한다.

1. Native Engine의 모델 요청이 A1/A2/M29/M291을 조건대로 포함.
2. V4/V3 런타임을 통해 실제 `controller_v3()` 함수가 조립한 최종 Controller 요청에 동일한 텍스트와 조직 컨텍스트가 들어감.
3. M29.1 source-pin opt-in이 없으면 M291 지시 추가되지 않음. 비-meta ROOT에서는 전혀 추가되지 않음.
4. `DetailSession`의 ON_DEMAND 이후 COMPACT와 SEPARATE 처리에서 `meta_research_organization_context`가 완전 보존됨.
5. 기존 `checks/m28` 및 `continuity/m25/v3/v4/clean` 회귀 검사 모두 통과.
6. 생성한 실제 새 Source-Pinned ROOT의 모의 호출 혹은 실제 유료 첫 Controller 호출을 감사할 때 모델 **저장 wire**에서 동일 문구를 확인한다. 아래 별도의 `audit_wire_gate.py`를 사용한다.

**주의:** 모의 테스트의 모델은 실제 과학을 판단하지 않는다. 구성과 전달을 검증한 것이지 과학적 질, 신규 연구자 생성 또는 최종 HOLD의 성공을 입증하는 것은 아니다.

## 실험 계보와 지출 경계

- `_06` ROOT는 1개의 `OPP_D00065` `UNCERTAIN` 호출이 남고 기존 Source Pin과 Journal은 읽기 전용 보존 대상이다.
- `_06`에 소스를 바꿔 재실행하는 행위는 금지한다.
- 다음 유료 DAC 재검증은 원래 예산의 `_04`, `_05`, `_06` 사용액과 예약/불확정 청구를 먼저 정산하고 별도 소스 핀 및 정합한 결제 장부를 둔 새 실험에서만 실행한다.
- `build_successor(_03,...comparison_baseline=_05)`를 무비판적으로 재사용하지 않는다: 해당 경로는 `_06`의 실지출/UNCERTAIN 비용을 자동 반영하지 않는다.
- 지금 제공한 패치는 유료 모델 실행이나 재실험(ROOT 생성)을 자동으로 수행하지 않는다. 우선 코드 회귀와 실제 요청 경로를 고치는 데 한정한다.

## 과학적 성공 판정

향후 새 source-pinned DAC A/B의 평가 기준: 1) 정상적으로 승인된 HOLD 또는 조건부 후속 Work, 2) 모델 작성 `research_frontier_assessment` 및 구체적 후속 문제의 실질 과학성, 3) 모델이 원래 P0를 미해결로 정확히 유지하는지, 4) 실제 동적 조직 요청의 자율 판단, 5) 자산/근거/조건부 예측의 사용. 단순 Work 수·모델 호출 수·등록 Problem 수는 성공 기준이 아니다.
