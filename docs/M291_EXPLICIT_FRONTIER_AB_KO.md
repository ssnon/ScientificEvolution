# ScientificEvolution M29.1 — 명시적 연구 경계 평가와 DAC 동일 출발점 비교

코드 기준: `d9dba29`; 무유료 개발, 새 `_06` opt-in만 엄격한 종료 기록 계약을 사용한다.

## 동기와 실패 근거

M29 `_05`는 `HOLD_WITH_RATIONALE`을 자율적으로 승인했으나, `research_frontier_assessment`를 전혀 쓰지 않았고 `new_problems`도 없었다. 단순히 구조화 형식을 프롬프트에 제공하는 것으로는 모델의 과학적 행동이 달라지지 않았다. 이것을 과학적 실패라 확정하지는 않되, **후속 식별 문제를 등록하거나 등록하지 않는 이유를 명시적으로 판단했다는 기록이 없다**는 것은 계약 결함이다.

## 새 계약: 과학적 선택 자유, 연구 경계의 명시적인 판단

- 새 Source-Pinned `_06` successor에서 `OPERATIONAL_PAUSE`로 activation marker를 기록한다. 이 사건은 과학적 관측이 아니다.
- 해당 successor가 `HOLD_WITH_RATIONALE`을 제출하면 `research_frontier_assessment`를 반드시 **모델이 직접 작성**해야 한다. 필드 누락은 `M291_HOLD_FRONTIER_ASSESSMENT_REQUIRED`로 거부된다. 과거 원문이나 답변은 수정하지 않는다.
- `REGISTERED_NEW`: 새로운 검증 가능 하위 문제(`new_problems`의 `research_frontier`)와 ID를 명시. 경쟁 가설, 판별 관측·개입, 예측 결과, 문헌·계산·실험 필요, 미확보 자원, 한계는 기존 M29 형식을 사용한다.
- `LINKED_EXISTING`: 이미 등록된 Problem ID를 참조하고 그 문제에 연구 경계가 있음을 설명한다.
- `NO_ADDITIONAL_VALUE`: 새 하위 문제가 실질적으로 중복이거나 정보 가치가 없는 이유를 설명한다. `new_problems`나 `actions`를 억지로 만들지 않는다.
- `CANNOT_YET_SPECIFY`: 실험 **실행** 자원 부재와 조건부 실험 **가설 정식화**의 불가능을 구별하며, 무엇이 부족한지 설명한다.
- 기존 M29 코드는 네 범주 중 정확한 선택을 구조적으로 검증하며, 임의 Problem/Asset 참조를 거부한다. **모델의 서술을 과학적으로 옳다고 런타임이 인증하지 않는다.**
- HOLD가 아니라 `ONGOING` 또는 다른 상태를 선택할 경우 이 추가 종료 계약을 강제하지 않는다. 추가 Worker/연구자/과학 문제 수도 강제하지 않는다.
- 서식 오류는 기존 저장된 원본·검증 오류와 함께 기록되고 모델이 새 응답으로 복구할 기회를 갖는다. 사람이 과학적 내용을 주입하지 않는다.

## 동일 연구 상태 및 예산

- 공통 출발점: `_03`의 원본 Journal 접두(239 SAVED 호출, 29 Controller 결정, 28 자산, 19 DONE Work). 마지막 등록 상태 ONGOING.
- 기준군 A: `_04`의 기존 자율 HOLD.
- 기준군 B: `_05`의 M29 자율 HOLD(`research_frontier_assessment` 미작성).
- 신규 실험군: `_06`을 **_03에서 새 Source Pin으로 분기**. `_04`, `_05`의 모델 응답은 `_06`의 Controller 과학 입력에 들어가지 않는다.
- `_06` 예산은 기존 `_03` 잔여 8.05977501 달러에서 `_03` 실제 사용액(0.1326428)과 `_04` 실제 사용액(0.032629), `_05`의 실제 사용액을 **한 번씩** 추가 차감한다. `_05`가 `_04`의 비용을 이미 자산 메타에 기록했더라도 중복 청구하지 않는다.
- 이전 두 비교군과 부모 Journal, Source Pin, 원래 P0는 절대 수정하지 않는다. 새 모델 호출은 `_06`에서만 기록한다.

## 통합과 테스트

1. `self_test.py`, `no_paid_contract_probe.py`: 패키지 서명·Python/bash 문법과 모델 응답 계약의 오프라인 검증.
2. `apply.py --repo "$PWD" --check`: Git HEAD와 소스 Git blob 검증, 고정 앵커 검사. `--apply`로 소스 패치.
3. `checks/m28/test_m291_explicit_frontier_contract.py`: 필드 누락 거부, 유효한 NO_ADDITIONAL_VALUE HOLD 승인, 별도 Work 없이 검증 가능 하위 문제 등록, 잘못된 참조 거부, Source-Pin activation 검증.
4. `checks/m28/test_m291_nested_comparison_budget.py`: 2개 비교군의 실제 장부를 포함한 누적 예산과 동일 역사 입력 검증.
5. `checks/m28`, `checks/continuity`, `checks/m25`, `checks/v3`, `checks/v4`, `checks/clean` 전체 회귀 테스트 후 Git 커밋.
6. `compare_m291.py`로 `_06` 생성. 생성에는 모델 API 호출 없음.
7. `read_only_replay.py`로 기존 `_04`, `_05`의 필수 필드 미작성 여부를 확인(원본 변경 없음).
8. `run_06.sh`는 명시적 유료 승인 및 키 한도 확인 후 실제 M29.1 재평가. 실행 후 비교 JSON 작성.

## 결과 평가

좋은 결과는 반드시 문제를 하나 만드는 것이 아니다. 네 가지 상태 중 **과학적으로 정당한 상태를 명시적으로 선택한 것**이 최소 조건이다. 예를 들어 NO_ADDITIONAL_VALUE라도 기존 자산이 실험적 식별성을 이미 충분히 정식화했음을 구체적으로 근거 제시해야 설득력이 있다. `CANNOT_YET_SPECIFY`가 단지 장비가 없다는 말의 반복이면 과학적 판단의 질은 여전히 낮을 수 있다. 새 Problem 등록은 실행되지 않은 가설이며 발견/검증/실험 성공이 아니다. 1회 A/B는 샘플링 비결정성으로 인해 코딩 변경의 인과적 효과를 독립적으로 입증하지 않는다.
