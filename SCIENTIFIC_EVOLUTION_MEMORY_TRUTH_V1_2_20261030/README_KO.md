# Scientific Evolution — Memory & Tool Truth V1.2 (2026-10-30)

## 목적 및 수정 범위

Autonomous Population Generation 13 재개 중 다음 예외가 발생했다.

```
MEMORY_LAYER_OPERATIONAL_PAUSE_NOT_SCIENTIFIC_HOLD
MODEL_ATTENTION_RECEIPT_PUSHED_VIEW_OVER_BUDGET
```

원인은 `memory_bridge.bound_advisor_payload()`가 과학적 입력 view에 86,000자 상한을 적용한 **후**, 원본 해시·문자 수를 담는 `science_memory_request_receipt`를 추가했다는 것이다. 이전의 입력 크기는 한도 이하이더라도, 영수증을 더하면 한도를 초과할 수 있었다. 해당 예외는 `DurableModel.call()`에 진입하기 전 발생하므로, 실패한 *그 호출*의 `MODEL_CALL_INTENT`는 발행하지 않는다. 같은 실행의 선행 호출은 유료로 진행됐을 수 있으니 영수증과 실행 상태를 확인한다.

V1.2는 영수증의 직렬화 크기를 사전에 계산하여 전체 상한에서 공제한다. 공제한 실효 예산 안에 과학 입력을 구성한 뒤 실제 크기로 기록한 영수증을 마지막에 추가한다. 과학적 P0, 활성 Work, 부모 관계, 실제 도구 영수증, 모델의 기존 과학적 판단을 임의로 변경하지 않는다. 원본 Journal은 그대로 두고 모델 전용 뷰만 변경한다. 확보되지 않는 입력 예산을 숨기기 위해 과학 데이터를 침묵 삭제하지 않으며, 상한을 만족할 수 없다면 `MODEL_ATTENTION_BUDGET_UNSATISFIED_NO_SILENT_TRUNCATION`으로 명시적인 운영 중단을 반환한다.

이 수정은 **입력의 적합 판정과 실제 영수증 추가 사이의 경계 버그**에 국한한다. 장기 컨텍스트의 모든 비용 문제를 해결하거나 Level II 후보의 완성을 보장하는 것이 아니다.

## 검증

- V1.1 원형: 합성 85.6k자 입력이 영수증 이후 `MODEL_ATTENTION_RECEIPT_PUSHED_VIEW_OVER_BUDGET`으로 실패함을 재현.
- V1.2: 동일 합성 입력을 안전하게 재압축하여 86k자 이내로 통과. 원래 P0, 문제 ID, 활성 Work 보존.
- 기존 `test_memory_offline.py` 5건과 `test_attention_regression.py` 1건 통과.
- 신규 `test_receipt_boundary_offline.py` 3건 통과.
- 이전 G13 Journal의 SAVED `OPP_D00001..D00003`, `CTRL_D00001..D00003` 6건에 읽기 전용 변환 적용, 전부 86k자 이하.
- **신규 G13 유료 실행의 성공은 아직 검증하지 않았음.** 최신 Journal의 상태는 사용자의 WSL `preflight`에서 확인해야 한다.

## 설치

ZIP을 `~/ScientificEvolution/`에 압축 해제하면 `SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_2_20261030` 폴더가 생긴다. V1.1과 원본 연구 ROOT는 변경하지 않는다.

먼저 실행 중인 연구 프로세스가 없는지 확인하고 일시정지를 유지한다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
KIT="$PWD/SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_2_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

pgrep -af '[e]volution_memory.py run|[e]volution_frontier.py run|[a]utonomous_population.py run' || true
touch "$EXP/STOP_REQUESTED"

python "$KIT/test_memory_offline.py"
python "$KIT/test_attention_regression.py"
python "$KIT/test_receipt_boundary_offline.py"
python "$KIT/evolution_memory.py" preflight --experiment "$EXP"
```

Preflight에서 확인: `unresolved_model_intents: []`, `autonomous_meta_check_error: null`, `attention_reference_checks_passed: true`, `journal_modified: false`. STOP 마커를 유지하면 `operator_stop_requested: true`, `paid_run_ready: false`는 의도된 결과다. `unresolved_model_intents`가 비어 있지 않으면 **자동 재시도 금지**. 또한 원격 계정에 비용 상한/경고를 설정한다.

## 사용자 판단 후 유료 재개

검증이 정상이고 유료 실행에 다시 동의하면, 실행 중 프로세스가 없음을 확인한 뒤 STOP 마커를 해제하고 무료 Preflight로 `paid_run_ready: true` 확인한다.

```bash
rm "$EXP/STOP_REQUESTED"
python "$KIT/evolution_memory.py" preflight --experiment "$EXP"
```

그 다음 `tmux`에서 **기존 V1.1과 동일한** `evolution_memory.py run` 명령을 실행하되 KIT만 V1.2로 변경한다. 예:

```bash
(
 set -o pipefail
 export FAKG_RESEARCH_ALLOW_PAID=YES
 trap 'unset FAKG_RESEARCH_ALLOW_PAID' EXIT
 python "$KIT/evolution_memory.py" run \
   --experiment "$EXP" --paid --model openai/gpt-5.6-luna \
   --bootstrap-peers 2 --slice-budget 8 --checkpoint-iterations 12 \
   --max-parallel 2 --max-tokens 16000 \
   --science-cpu-seconds 120 --science-wall-seconds 160 \
   --notice-every-segments 3 \
   2>&1 | tee -a "$EXP/MEMORY_V1_2_RUN.log"
)
```

이 명령은 **총 호출 수/총 비용의 자동 상한이 없다.** 비용 경고/계정 한도를 별도로 마련하고, 짧게 검증할 때는 다른 터미널에서 `touch "$EXP/STOP_REQUESTED"`로 운영상 정지를 요청한다. Journal을 재초기화하거나 기존 과학 자산을 덮어쓰지 않는다.
