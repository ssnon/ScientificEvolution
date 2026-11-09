# M28-A4-0: HISTORICAL_AI Worker 입력 호환성 수정

기준 커밋: `d0912eb` / `dev/meta-research-autonomy-v1`.

## 재현된 결함

A2 `import_selected`가 생성한 `HISTORICAL_AI` Source는
`original_asset`, `origin_root`, `original_asset_id`, `selected_report_id` 등
출처 필드를 가진다. 반면 기존 `engine._worker_input`은 모든
`HISTORICAL_AI` Source가 레거시 `ref`, `science`, `tool_result`,
`science_sha256` 필드를 갖는다고 가정한다. 반입된 자산으로
INFORMED CHALLENGE를 실행하면 `KeyError: 'ref'`가 발생한다.
A1 표적 독립 비판의 초기 역사적 AI Source도 다른 형태이므로
같은 결함이 생길 수 있다.

## 해결

읽기 시점에 레거시 스키마는 기존 표현을 유지한다. A1 표적
스키마와 A2 선택적 반입 스키마만 명시적으로 지원하며,
원본 Source blob이나 Journal 이벤트는 재기록하지 않는다.
M28 표시 시 `original_source_record`, 원래 Asset, 출처 정보와
source blob SHA-256을 그대로 전달한다. `tool_status`는
`HISTORICAL_AI_IMPORT_NOT_NEW_TOOL_EXECUTION`으로 표시한다.
모든 AI 주장은 인증되지 않았으며, 반입은 새 실험 실행이 아니다.
알 수 없는 스키마는 임의 보정하지 않고 실패한다.

## 검증

`checks/m28/test_m28_historical_wire.py`는 실제 A1/A2 Journal fixture를
활용해 A2 결과 선택 → HISTORICAL_AI 반입 → INFORMED Worker가
반입된 Asset을 부모로 삼아 새 반증 Asset을 출판하는 실제
`Engine.worker_step` 경로를 테스트한다. A1 표적 Source, 레거시
표현 유지, 미지 스키마 오류도 테스트한다. 모두 무유료 MOCK이다.

이 문서는 실제 모델의 과학적 판단 품질을 인증하지 않는다.
A4-0 종단 테스트 및 나머지 전체 회귀가 WSL에서 통과하기 전에는
결함 해결이 완전히 검증됐다고 선언하지 않는다.
