# Autonomous Scientific Evolution — 로컬 과학적 HOLD 정상 경계 처리 (2026-10-29)

## 관찰된 실제 오류

Cycle 1 Population의 마지막 모델 Controller가 `HOLD_WITH_RATIONALE`와 `PAUSED_LOW_INFORMATION`을 append-only Journal에 확정하고 기존 Work가 모두 DONE으로 전환됐습니다. 하지만 기존 `generational_run.drive`는 `AUTONOMOUS_RESEARCH_PAUSED_NOT_OBJECTIVE_COMPLETED`를 반환했고, 외부 `autonomous_population.py`가 이를 운영 오류로 잘못 분류하며 `POPULATION_OPERATIONAL_STOP_REQUIRES_REVIEW`를 출력했습니다.

**이것은 과학적 의미의 목표 달성이 아닙니다.** 해당 연구 ROOT의 **로컬 HOLD는 실제 확정됐지만**, 전체 Population 차원의 종료는 아직 독립적인 판단·비판·최종 판정이 필요합니다. 마지막 실행기의 에러 표시는 잘못된 종료 분류입니다.

## 수정 내용

- `autonomous_population.py`만 교체합니다. 기존 `persistent_population.py`와 전체 E2 런타임은 건드리지 않습니다. 이전 schema-quarantine 패치는 유지됩니다.
- 연구 ROOT의 마지막 **검증된 Journal** 과학적 상태가 terminal이고, 연구 엔진이 알려진 정상 종료 사유를 반환하면 `LOCAL_SCIENTIFIC_TERMINAL`로 구분합니다. 원래 `engine_stop_reason`도 출력합니다.
- 연구 ROOT가 HOLD를 확정했더라도 전체 Population을 자동으로 HOLD하지 않습니다. Population Council에 연구 요약과 로컬 HOLD를 전달합니다.
- 같은 ROOT에서 연구할 수 없는 상태이므로 Council이 선택할 수 있는 실제 운영상 가능한 행동은 `NEXT_GENERATION` 또는 독립 재검토가 필요한 전역 종료 제안입니다. 종료 제안이 나오면 기존 `INDEPENDENT_TERMINAL_REVIEW`와 `FINAL_TERMINAL_ADJUDICATION`이 실행됩니다.
- 실제 schema, provider, tool 실패는 로컬 HOLD로 변환하지 않습니다.
- 기존 Journal을 재작성하거나 이전 유료 호출을 다시 실행하지 않습니다.

## WSL 설치

압축 파일에는 폴더 구조 `AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029/`가 들어 있으므로 **기존 프로젝트 루트** `~/ScientificEvolution`에 압축을 풀어 덮어쓰면 됩니다. **새로운 bootstrap / init은 수행하지 마세요.**

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
KIT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
NEXT="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"

python "$KIT/test_local_science_hold_offline.py"
python "$KIT/test_autonomous_offline.py"
python "$KIT/test_schema_quarantine_offline.py"
python "$KIT/autonomous_population.py" preflight --experiment "$NEXT"
python "$KIT/autonomous_population.py" status --experiment "$NEXT" \
  --out "$NEXT/LOCAL_HOLD_BEFORE_COUNCIL_STATUS.json"
```

## 연구 계속 / 자율적 종료 재개

기존 연구 ROOT가 이미 HOLD를 저장했기 때문에 다음 실행은 동일 ROOT에서 8회의 Worker 호출을 반복하지 않고 **Population Council 결정**을 먼저 요청합니다. 독립 Council이 전역 HOLD를 제안하면 skeptical review와 최종 판정이 진행됩니다. 반대로 새 연구 기회가 유효하다고 판단하면 `NEXT_GENERATION`을 생성하고 연구를 다시 시작할 수 있습니다. **모델 호출/세대의 총 상한이 없으므로 무제한 과금 위험이 있습니다.**

```bash
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  python "$KIT/autonomous_population.py" run \
    --experiment "$NEXT" \
    --paid \
    --model openai/gpt-5.6-luna \
    --bootstrap-peers 2 \
    --slice-budget 8 \
    --checkpoint-iterations 12 \
    --max-parallel 2 \
    --max-tokens 16000 \
    --science-cpu-seconds 120 \
    --science-wall-seconds 160 \
    --notice-every-segments 3 \
    2>&1 | tee -a "$NEXT/AUTONOMOUS_RUN.log"
)
unset FAKG_RESEARCH_ALLOW_PAID
```

실행 중 중단은 **다른 WSL 터미널**에서 `touch "$NEXT/STOP_REQUESTED"`로 요청합니다. 진행 중인 호출은 끝날 수 있으며, 모델 Provider 응답 중 `Ctrl+C`는 불확실한 호출 상태를 남길 수 있습니다.

## 주의 및 검증 범위

- 오프라인 모의 Journal에서 종료 경계/독립 Council 인계/기존 결정 캐시 테스트 및 기존 회귀 테스트 통과.
- 사용자 WSL 실Journal 재개는 **아직 확인하지 못함**.
- 기록된 로컬 `HOLD_WITH_RATIONALE`는 실제 연구자의 과학적 판단이지 과학적 정답·발견·Level II 인증이 아닙니다. 전역 종료 판단도 모델 판단이며 별도 인간 검증이 필요합니다.
