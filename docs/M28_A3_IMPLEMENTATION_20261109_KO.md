# ScientificEvolution — M28-A3 지속 실행·복구·과학적 재심 실행 계약

**일자:** 2026-11-09 KST
**기준 커밋:** `21a37b5` / `dev/meta-research-autonomy-v1`
**범위:** 새 M28 A1+A2 실험에서만 유효한 A3 실행 계약. 기존 M26/M27 Journal·과거 Source Pin 수정 금지.

## 1. 목적

원래의 범용 AI Scientist 목표는 연구자를 정해진 수만큼 생성하고 고정 세대별로 합성하는 것이 아니라, 연구의 필요에 따라 연구자·조직·방법·협력·지속·중단을 **모델이 과학적으로 판단**하는 것이다. A1은 독립 ROOT 생성을, A2는 자식 연구의 관찰·선택적 결과 반입·모델 기반 전역 판단을 구현했다. A3는 그 기능들을 **장기 실행 가능한 운영 경계**로 연결한다. 이 단계의 성공은 과학적 성과 향상을 입증하지 않는다.

## 2. A3에서 추가한 구체적인 능력

### A. 동적 반복 스케줄링

`meta_research_autonomy.py run`은 `meta_scheduler.run_dynamic`으로 연결된다. 기존 A2 실행기의 `seen` 집합은 한 실행에서 각 ROOT를 단 한 번 방문하게 했다. A3는 다음 조건을 적용한다.

- ROOT가 최초 판단을 내리기 전이거나, 실제 Work가 `QUEUED/ACTIVE`이거나, 마지막 Controller 결정 뒤 새로운 과학적 결과/협력 보고가 생긴 경우 실행 대상으로 고려한다.
- 연구자가 새로운 ROOT를 요청하면 A1 방식으로 생성한 다음, 그 ROOT 역시 다음 가능한 실행 대상으로 포함한다. 연구자의 수나 세대 수는 고정하지 않는다.
- 여러 실행 가능 ROOT를 순환 방문한다. 이 순서는 **운영상 공정성**에 관한 것이지, 과학적 중요도나 연구자의 능력을 점수화한 것이 아니다.
- 실행 시간, 각 방문의 최대 호출 수, ROOT 수, 총 방문 수 등은 운영상 제한일 뿐 연구 종료의 과학적 이유가 아니다.
- 더 이상 실행 가능한 Work나 새 과학적 자극이 없다면 이번 실행만 중단한다. `P0`가 해결 불가능하거나 연구가 실패했다는 판정으로 해석하지 않는다.

### B. 크래시와 중복 실행에 대한 보수적 복구

`M28_A3_SCHEDULER_CHECKPOINT.json`은 전체 실험 디렉터리에 놓이는 **운영상** 체크포인트다. 마지막 방문 ROOT와 진행 중인 방문의 시작 Journal head를 기록하며, 파일은 원자적으로 교체·fsync한다.

- 방문 직전 체크포인트에 `in_flight`를 기록한다. 정상 종료되면 완료 ROOT와 순서를 갱신한다.
- 크래시 뒤 해당 ROOT의 Journal head가 바뀌지 않았다면 동일 ROOT의 방문을 다시 시도한다.
- head가 바뀌었다면 유료 호출/연구를 다시 수행했다고 단정하거나 무조건 재실행하지 않는다. 방문을 진행이 있었던 것으로 기록하고 다른 ROOT로 진행한다. 동일 ROOT는 후속 순환에서 재방문 가능하다.
- 재실행은 A1/A2의 기존 결정·ROOT 생성·자식 보고·선택 반입의 멱등성 검사를 계속 거친다.
- 확인된 `UNCERTAIN/INTENT` 호출이나 `CONTROLLER_DECISION` 이후 `PROGRAM_REVIEWED`/`PROGRAM_OBJECTIVE_ASSESSED`/Work 계획이 누락된 흔적은 자동으로 복원하지 않고 **명시적으로 중단**한다. 임의로 결정을 재구성하거나 유료 호출을 재사용한 것처럼 기록하지 않는다.

**복구 한계:** Journal 갱신 직후의 크래시에서 해당 방문의 실제 완료 여부와 중단 정확한 시점은 체크포인트만으로 알 수 없다. A3는 이를 '방문 중 Journal 변화'로만 인지한다. 이미 승인된 A1/A2 메타 결정은 무유료로 복구할 수 있으나 **일부 적용된 기본 Controller Work 계획 전체를 자동 재구성하는 기능은 포함하지 않았다.** 모델 응답이나 계산을 발명하지 않는 것이 우선이다.

### C. 새 증거가 들어왔을 때 전역 HOLD에 대한 재심 허용

A2는 최초 PRIMARY의 프로그램 수준 `PAUSE_WITH_RATIONALE`, `SCOPED_NEGATIVE`, `REVIEW_WORTHY_CANDIDATE`를 별도 기록한다. 이전에는 그 후 새 자식 보고가 들어오면 `stale`로 표시하고 실행을 수동 중단했다. A3는 **새로운 자식의 과학적 보고가 이전 종결 판단보다 나중에 나타났음**을 확인하면 `PROGRAM_REASSESSMENT_REQUESTED`를 기록한다.

- 이 이벤트는 **과학적 CONTINUE가 아니다**. 원래 모델 판단·HOLD/부정 결과·근거는 모두 Journal에 남는다.
- 이 이벤트가 있을 때에만 종료 ROOT가 새로운 Controller 판단을 내릴 수 있도록 기존 `Engine`과 `generational_run.drive`의 종료 가드를 좁게 확장한다.
- PRIMARY는 재심 시 **새 `program_portfolio_review`를 반드시 제시**해야 하며, 기존 A2의 모든 직계 자식·최신 report ID 고려 조건을 그대로 준수한다.
- 새로운 모델 판단이 내려지기 전에는 자식 연구를 무단 재개하지 않고 PRIMARY의 재심을 우선한다. 새 데이터에 반응한 재심이 필요하다는 절차적 판단과, 어떤 과학적 결론이 타당하다는 판단을 명확히 분리한다.
- 과거에 기록된 `SCOPED_NEGATIVE`나 후보 결론의 범위가 자동으로 취소·반증되는 것은 아니다. 재심 후에도 새 과학적 모델 판단이 근거를 평가해야 한다.
- **실제로 달라진 자식 연구 보고**가 없는 운영 일시정지·호출 한도 변화는 재심을 생성하지 않는다.

### D. 장기 실행의 경계

- 새로운 A3 실험 생성 시 `meta_research_autonomy.py init`이 실행 시점 코드를 새 Source Pin에 기록한다. **A1/A2에서 이미 생성된 이전 실험의 Source Pin을 소급 갱신하지 않는다.**
- `run`에는 여전히 명시적 `--paid`와 `FAKG_RESEARCH_ALLOW_PAID=YES`가 모두 필요하다. 테스트는 모델 provider를 호출하지 않는다.
- 실험 단위 잠금(`.meta-research-run.lock`)이 `run`/`sync` 동시 실행을 막는다. 다른 도구가 실험 잠금을 무시하고 ROOT 내부 Journal을 직접 수정하는 경우까지 완전히 차단한다고 주장하지 않는다.
- 모든 새 과학적 주장은 이전과 동일하게 모델/원본 증거/계산의 진실성 검증 대상이다. 생성된 ROOT나 체크포인트는 연구 성과가 아니다.

## 3. 변경 파일

| 파일 | 책임 |
|---|---|
| `runtime/e2core/meta_scheduler.py` | 스케줄러·공정한 반복 방문·운영 체크포인트·재심 요청·fail-closed 미완료 판단 검출 |
| `runtime/meta_research_autonomy.py` | 기존 A1/A2 CLI `run`을 동적 실행기로 연결 |
| `runtime/e2core/core.py` | `PROGRAM_REASSESSMENT_REQUESTED` append-only 검증 및 상태 보존 |
| `runtime/e2core/engine.py` | 재심 시 모델의 새 전역 판단 강제, 재심 전에는 이전 종료 보존, 불완전 재심 후 Worker 무단 실행 방지 |
| `AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029/generational_run.py` | 종료된 ROOT의 새로운 재심이 정당하게 요청된 경우에 한해 실행 허용 |
| `checks/m28/test_m28_a3.py` | 실제 Journal 기반 무유료 재심·스케줄러 순환·중단 복구·운영/과학 상태 분리 |
| 기존 A2 문서와 코드 | `git diff --check`의 Markdown 후행 공백·EOF 공백 정리만 수행 |

## 4. 검증과 아직 남은 과제

A3 무유료 테스트는 실제 모델을 모의 `SAVED` Controller 응답으로 대체해 실행 계약을 검증한다. **실제 유료 장기 실행, 독립 과학자의 과제 선택 품질, 비식별성 판단의 과학적 정확성, 실제 수치 계산의 진전은 A4에서 별도로 검토**해야 한다.

A3는 완전히 임의적인 여러 ROOT의 상호간 데이터 동기화를 자동으로 수행하거나, 이미 완료된 옛 Source Pin 실험을 새 코드로 재실행하지 않는다. 또한 과학적으로 필요한 도구/데이터에 대한 모델의 판단 품질을 보장하지 않는다. 특히 '크래시 후 임의의 부분적 기본 Controller 계획을 자동 복구' 기능은 **포함하지 않으며**, 불명확한 상태를 발견하면 중단해 원본을 보존한다.
