# ScientificEvolution — M28-A2 동적 과학 협력과 프로그램 수준 판단

**기준:** `ssnon/ScientificEvolution`, `d4f4c28` / `dev/meta-research-autonomy-v1` (2026-11-09 KST).  
**성격:** M28-A1의 새 ROOT 기반 메타 자율성에 대한 추가 수직 통합. 기존 M26 ROOT, 기존 Source Pin, 기존 과학적 주장의 검증 상태를 변경하지 않음. 실제 유료 연구 및 과학적 유익성 비교를 수행했다는 뜻이 아님.

## 1. 목표와 실행 의미

이번 개발의 목적은 **고정 Population을 재도입하지 않고**, 연구자가 자신이 생성한 독립 연구 단위의 실제 결과를 보고, 유용한 부분만 명시적으로 선택하고, 기존 Work로 후속 비판/비교/합성을 수행하거나, 과학적 근거로 프로그램 전반의 보류/종료를 판단할 수 있게 하는 것이다.

* **독립 연구 관찰:** 자식 ROOT에 실제 SAVED Worker 응답을 기반으로 작성된 Asset 또는 실질적인 Work/Controller 진행이 발생하면 원본 과학적 계보와 스냅샷 해시를 담아 부모에게 알린다. `CHILD_RESEARCH_OBSERVED`는 보고서 수신이며 부모의 과학적 수용이나 검증을 의미하지 않는다. 원래 질문만 받은 `ORIGINAL_P0_BLIND_INDEPENDENT` 자식은 최초 연구 문맥이 격리된 채 연구하고, 자신의 결과가 후속 연구에 전달되는 시점에서만 정보가 부모에게 넘어간다.
* **선택적인 결과 반입:** 부모 Controller가 저장된 모델 결정 안에서 `collaboration_requests`로 정확한 자식 report ID와 asset ID를 선택한다. 실제 `COLLABORATION_ASSET_IMPORTED`는 별도로 실행된다. 선택되지 않은 자식 결과를 자동 합성·상속·증명하지 않는다. 가져온 자산은 `HISTORICAL_AI` 출처와 원본 child/Work/model/source/parent ID를 가진 **미검증 역사적 주장**이며, 실제 Worker의 새 결과로 위장하지 않는다.
* **기존 연구 기능 재사용:** 연구자는 기존 `DEVELOP`, `CHALLENGE`, `FUSE`, `VERIFY` 등의 Work를 동적으로 선택할 수 있다. 합성·비판은 언제나 모델이 선택하는 후속 **실제 연구 행동**이지 가져오기만으로 달성된 결과가 아니다.
* **프로그램 판단:** `PROGRAM_PORTFOLIO_REVIEWED`는 첫 `PRIMARY`의 모델이 작성한 **별도 전역 검토**다. 개별 자식의 `HOLD`나 운영 예산 소진은 전역 P0 실패/종료로 자동 변환되지 않는다. 전역 판단은 모든 등록된 직계 자식과 최신 보고서를 명시적으로 고려해야 하며, 잔여 연구 기회와 미해결 조건을 남긴다. 기록상 `REVIEW_WORTHY_CANDIDATE`도 독립적인 과학 인증이 아니다.
* **동적 조직 유지:** 연구자 수·세대·통합 파동을 고정하지 않는다. 독립 자식이 아직 Work를 진행 중인 경우 부모가 추가 Work/동료 생성 없이 `ONGOING`을 판단할 수 있다. 운영 비용/병렬성/ROOT 수 제한은 별도 운영 경계다.

## 2. 코드와 새로운 실험의 경계

| 파일 | 변경 책임 |
|---|---|
| `runtime/e2core/meta_collaboration.py` | 자식 보고의 실재/출처 검사, 과학적 보고 fingerprint, 선택된 역사적 주장 반입, 프로그램 판단 조회·복구 |
| `runtime/e2core/core.py` | A2 opt-in Journal 필드와 `CHILD_RESEARCH_OBSERVED`, `COLLABORATION_REQUESTED`, `COLLABORATION_ASSET_IMPORTED`, `PROGRAM_PORTFOLIO_REVIEWED`의 불변 기록 검증 |
| `runtime/e2core/engine.py` | 동일 Controller 모델 결정에서 선택·전역 판단 입력 검증, 보고를 후속 판단의 계기로 인식 |
| `runtime/scientific_problem_evolution.py` | 기존 NVT→PMI→Opportunity→Controller 경로에도 동일한 A2 선택/보고 계약 전달. 새로운 필수 평가 호출 없음 |
| `runtime/e2core/meta_autonomy.py` | A2가 활성화된 부모의 새 자식에만 A2 정책 계승, 기존 A1 영수증 개수와 구별 |
| `runtime/meta_research_autonomy.py` | 새 실험의 A2 opt-in, `sync` 무유료 동기화, 실제 연구 중 자동 보고·선택 실행, 프로그램 수준 중단 확인 |
| `checks/m28/test_m28_a2.py` | 실제 `EvolutionJournal` + 모의 SAVED 모델로 무유료 계약 검증 |

**새 A2 실험에만 활성화:** `META_RESEARCH_COLLABORATION_ACTIVATED` 이벤트를 생성하고, 기존 A1 정책 위에 활성화한다. 과거 A1/M26 연구 ROOT를 자동 업그레이드하거나 재실행하지 않는다. 새 런타임 Source Pin은 새로운 연구 실험에만 적용하며, 옛 Source-Pinned 실험이 변경된 코드를 사용하도록 몰래 재지정하지 않는다.

## 3. 실행과 상태 구분

1. `meta_research_autonomy.py init`으로 **새** A2 연구를 초기화한다. 현재 CLI의 `init`은 새 ROOT에 A1+A2를 함께 opt-in한다.
2. A1 Controller가 필요한 경우만 별도 연구자를 요청하고, 실행기가 ROOT를 생성한다.
3. 자식이 연구를 실제로 수행한 뒤 `sync` 또는 `run`이 원본 Journal을 확인하고 부모에 보고를 기록한다. 운영 일시정지 기록만 추가됐다면 중복 보고하지 않는다.
4. 부모 Controller가 보고서를 보고 필요한 자산 ID만 선택한다. 다음 `sync`/`run`에서 선택된 미검증 AI 주장을 역사적 자산으로 등록한다.
5. 필요한 경우 기존 Controller가 이 자산을 근거로 새로운 비판·발전·계산·합성 Work를 생성한다. 조직 변경과 실제 과학 연구 수행을 계속 구별한다.
6. 부모 `PRIMARY`가 모든 알려진 직계 자식과 현 보고서를 고려해 전역 과학적 종결/보류를 결정할 수 있다. 후속 자식 보고서가 달라지면 기존 전역 판단은 **stale**로 표시되어 자동 유효 판정하지 않는다. 그 경우 보수적으로 중단하여 수동 검토가 필요하다(A3에서 자율 재개 규약 확대).

## 4. 무유료 검증 범위와 미완료 과제

A2 무유료 테스트는 결과 미선택·선택적 반입·원본 Work/모델 출처·추가 실험 조작 없이 FUSE 미생성·후속 Work 선택 가능·국소 HOLD와 전역 HOLD 분리·전역 자식 고려 범위 검사·저장된 모델 결정 복구·새 결과 발생 시 stale 감지·운영 로그만으로 재보고 금지를 검증한다.

**입증하지 못한 것:** 실제 유료 LLM이 올바른 자식 연구를 선택하는지, 가져온 자산이 실질적으로 다른 과학적 결론에 이르는지, 수학적 신뢰성이나 P0 해결 여부, 모델 외부의 완전한 동시 수정 방지. 의도·실제 실행·외부 과학적 평가를 따로 보아야 한다. 또한 고급 형태의 상호 동료간 피드백·원본 데이터 완전 이전·전역 중단 이후 완전 자율 재개 등은 A3 이후에 별도 설계가 필요하다.

**운영 진실:** 이 문서는 A2 패치와 테스트의 의도된 계약을 설명한다. 사용자의 실제 WSL에서 회귀 테스트가 성공했다는 확인 전에는 `INTEGRATED_VERIFIED` 또는 과학적 성공으로 기록하지 않는다.
