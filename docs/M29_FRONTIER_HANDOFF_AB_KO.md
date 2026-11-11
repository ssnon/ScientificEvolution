# ScientificEvolution M29 — HOLD 시 후속 식별 연구 경계 보존 및 DAC 동일 출발점 A/B

상태: source patch / no-paid tests prepared. 검증 기준: 기존 `a1458c3` 깨끗한 Git 작업 트리.

## 목적과 기존 체계 재사용

- 원래 문제 P0는 모델이 해결하지 못했으면 UNRESOLVED 상태 그대로 둔다.
- 문헌/계산/실험의 미확보가 **수행 가능성의 제약**인지 **과학적 가설의 정식화 불가능성**인지 구별한다.
- 이미 존재하는 `new_problems` / `PROBLEM_CREATED` / `State.problems` 경로를 사용해 *후속 과학적 문제*를 P0의 계보에 보존한다.
- 등록된 `research_frontier`는 `PROPOSED_NOT_EXECUTED`: 실행된 실험/계산, 사실, 완료된 Work가 아니다.
- `HOLD_WITH_RATIONALE`와 `new_problems`는 함께 사용할 수 있고 `actions=[]`여도 된다.
- 적절한 후속 과제가 없으면 모델은 `NO_ADDITIONAL_VALUE` 또는 `CANNOT_YET_SPECIFY`를 택할 수 있다. 강제로 과제를 만들거나 HOLD를 거부하지 않는다.
- `research_frontier_assessment`는 과학자가 명시적으로 작성한 경우에만 기존 `PROGRAM_REVIEWED`의 `m29_research_frontier_assessment`에 보존한다. 누락 시 과학적으로 자동 추론하지 않는다.
- 기존 임의 연구 ROOT에 소급 적용하거나 기존 Journal을 편집하지 않는다.

## 구현

1. `runtime/e2core/m29_frontier.py`: 현재 M28 opt-in Controller의 연구 경계 프롬프트/형식 검증. 가설/경쟁 설명/변별 조작·관측/조건부 예측/필요 문헌·계산·실험/미확보 자원/해석 한계를 포함한다.
2. `runtime/e2core/engine.py`: M28 Controller 프롬프트에만 위 계약을 전달하고, 구조화한 모델 응답을 기존 `new_problems`와 `PROGRAM_REVIEWED`에 귀속. 존재하는 연구 경계는 재생성하지 않도록 Controller context에서 읽게 한다.
3. `runtime/e2core/m28_successor.py`: `_03` 상태에서 `_05`를 분기할 때 원래 `_04`가 지출한 비용도 동일 최초 $10 한도에서 빼도록 영수증/후속 계보 연결 추가. `_04`는 과학적 입력으로 복사되지 않음.
4. `compare.py`: `_03` 과학적 입력으로부터 `_05`를 새 실험으로 생성, 기존 `_04`와 모델 결정을 비교하는 감사 출력.
5. `checks/m28/test_m29_frontier_handoff.py` / `test_m29_comparator_budget.py`: 과제 등록·종료 상태 보존·무중복·모의 원가 차감 확인. 모든 기존 회귀 검사와 함께 사용.

## 동일 출발점 DAC 실험 비교

- 기존 기준군: `.../M28_DAC_NO3RR_20261111_04`, 승인된 `D00042` HOLD. 자료는 READ ONLY.
- 기존 마지막 사전종료 상태: `.../M28_DAC_NO3RR_20261111_03`, 239 SAVED 모델 호출, 29 Controller 결정, 28 자산, 19 DONE Work, 마지막 ONGOING 및 거부된 판단 원문.
- 새 실험군: `.../M28_DAC_NO3RR_20261111_05`, 동일 `_03` Journal 접두 복사 후 새 코드 Source Pin.
- 비용: 최초 $10에서 `_02` 실제 1.94022499, `_03` 실제 0.1326428, `_04` 실제 0.032629를 차감. 예상 `_05` 한도 $7.89450321. **이 값은 실제 장부 확인 후 결정**.
- 데이터 오염 방지: `_04`는 비교 메타데이터와 원가 검증에만 쓰이고, 새 연구 Controller에게 학습/문헌/증거 형태로 전달되지 않는다. `_05`의 모델 판단이 바뀌더라도 새 프롬프트 효과인지, 비결정적 샘플링/모델 변동인지 단일 A/B만으로 인과적으로 단정할 수 없다.

## 과학적 결과 해석

기대하는 *좋은 결과*는 **무조건 더 많은 모델 호출이 발생하는 것이 아니다.** 모델이 가능한 구별 가설을 `P...`에 조건부로 등록하고 과학적으로 타당한 HOLD를 유지해도 좋은 결과다. 반대로 모델이 기존 자산을 바탕으로 신규 식별 가설이 정말 중복이라고 정당화한다면 HOLD와 `NO_ADDITIONAL_VALUE`도 합리적일 수 있다. 과학적 정확성은 별도 검증이 필요하다.

주의: 모델 응답이 새 구조를 빠뜨려도 런타임은 과학적 판단을 왜곡해 채우지 않는다. 그 경우 비교 보고서에 해당 구조의 미작성 여부를 명시한다.

## 안전성

기존 `_02` `_03` `_04`는 절대 수정하지 않는다. Source Pin은 새로운 `_05`에만 기록. 일단 모든 회귀 검사를 유료 호출 없이 실행한 다음 별도의 사용자 승인/키가 있을 때만 재실행한다. 라이브 OpenRouter 지출은 예약/정산 방식을 사용하므로 키 자체에 별도 지출 상한을 유지한다.
