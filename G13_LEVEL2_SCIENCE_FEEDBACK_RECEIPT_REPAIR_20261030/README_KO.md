# G13 Scientific Audit — 도구 영수증 경로 수정판 (2026-10-30)

이 폴더는 `G13_LEVEL2_SCIENCE_FEEDBACK_20261030`의 **대체 패키지**입니다. 기존 패키지를 덮어쓰지 말고 새 폴더를 사용하세요.

## 수정 이유

이전 `audit_bridge.py preview`는 `ACTUAL_EXECUTED_TOOL_RECEIPT_INCONSISTENT`로 종료했습니다. 실제 E2 WORK_STEP 구조는 `step["result"]={"status":"EXECUTED", "code_sha256":"...", "result":{계산값}, ...}`인데, 이전 코드는 계산값 내부 `step["result"]["result"]["code_sha256"]`에서 SHA를 찾는 오류가 있었습니다.

이번 판은 `step["result"]["code_sha256"]`를 확인하고, `State.tool_results`의 `TOOL_RECORDED` 요청·응답 Blob을 모델이 제출한 도구 요청 및 Work Step과 교차 검증합니다. `EXECUTED` 외 상태, 비영(非零) 종료코드, SHA 불일치, 기록 누락은 차단합니다. 원본 과학 결과, 패킷 및 연구 프롬프트는 수정하지 않았습니다.

## 우선 무료 Preview만 실행

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
AUD="$PWD/G13_LEVEL2_SCIENCE_FEEDBACK_RECEIPT_REPAIR_20261030"
KIT="$PWD/SCIENTIFIC_EVOLUTION_LEVEL2_RUNTIME_REPAIR_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
touch "$EXP/STOP_REQUESTED"
python "$AUD/test_feedback_offline.py"
python "$AUD/audit_bridge.py" preview --experiment "$EXP" | tee "$HOME/G13_AUDIT_RECEIPT_REPAIR_PREVIEW.json"
```

기대: `SCIENTIFIC_AUDIT_SAFE_PREVIEW_NO_PAID`, `journal_unchanged: true`, `provider_requests_sent: 0`, `target_next_step: 4`, `audit_registered: false`. 다른 상태가 나타나면 STOP을 유지하고 해당 로그를 확인하세요. 최신 G13 원본 Journal은 이 패키지에 포함되어 있지 않으므로 이 기대값은 실제 WSL에서 아직 검증되지 않았습니다.

**중요:** Preview 이후의 `register`, `verify-disclosure`, `run`은 사용자가 미리보기 결과와 과학적 피드백 내용에 동의했을 때만 실행하세요. `register`는 기존 이벤트를 수정하지는 않지만 append-only `SOURCE_REGISTERED`를 새로 추가하는 비가역적인 행위입니다. `run`은 명시적 유료 호출입니다. 순서는 원본 README의 해당 단계가 적용됩니다.

## 기존 패키지의 전체 설명

# G13 — 과학적 반례 전달 및 Level II 연구 재개

기준: 2026-10-30 G13/POPULATION, 1268 Journal events, 사용자가 제공한 `G13_LEVEL2_SCIENCE_REVIEW.json`.

## 목표

1. G13에서 실제 `EXECUTED`된 Monte Carlo를 **별도의 독립 계산**으로 감사한다.
2. 계산 오류를 기존 결과를 수정하지 않고 **EXTERNAL_AUDIT**로 append-only Journal에 등록한다(사용자 명시적 실행 시에만).
3. 이 감사 결과를 오직 `W_develop_finite_exposure_adversarial_model_001`의 **다음 INFORMED Worker 호출(step 4)** 에 전달한다. 모델은 동의·반박·수정·중단을 자율적으로 선택한다. FRESH Worker에는 전달하지 않는다.
4. redox가 제안했지만 `BAD_ASSET_PARENTS`로 거절된 두 자산은 원래 모델 응답의 미등록 내용이라는 사실만 정확히 보존한다. 과거 모델의 ID를 고치거나 자산을 창작하지 않는다.

**과학적 주장과 별개로:** 이 패키지는 Level II를 인증하지 않는다. 독립 감사는 기존 G13의 실행된 도구를 대체하지 않고, G13 Journal에 수행된 새로운 도구 실행으로 위장하지 않는다.

## 실질적인 검산 내용

- 잘못된 이산 Telegraph 전이확률: `1-exp(-2*dt/tau)`.
- 상관시간이 `tau`인 대칭 CTMC의 **정확한 간격 끝점 전이확률**: `(1-exp(-dt/tau))/2`. 정확한 CTMC 경로 시뮬레이션은 지수 분포 대기시간 평균 `2*tau`를 사용.
- Poisson mixture의 2차 factorial cumulant = 적분된 잠재강도의 분산: `(rate*contrast)^2 * 2*tau*[T-tau*(1-exp(-T/tau))]`.
- G13 실행 결과 예: rate 1000/s, contrast .3, tau .1s, exposure .1s에서 Telegraph K2^F 328.08 vs Gaussian K2^F 663.48. 의도한 covariance-matched 값은 662.183. 독립 event-driven 재계산은 약 659.83 (40,000 trace, seed 고정).
- 부정 강도 clipping 없는 **양의 연속 잠재강도 Null**: Jacobi diffusion의 정규화된 stationary Beta 상태. Telegraph와 평균 및 전체 지연 공분산이 정확히 같아도 고차 통계가 달라질 수 있고, a→0에서 4차 cumulant 차이는 0으로 접근. 따라서 적어도 약한 clipped-Gaussian Null에 대한 높은 separation만으로 discrete mechanism을 인증하지 않는다.
- 기존 G13 결과의 `standardized_separation`은 유의수준이 보정된 실제 검정력이 아니다. 유효한 power 비교에는 수정된 모형, finite-sample bias, 외부 nuisance 범위, size calibration, 독립 Monte Carlo가 필요하다.

관련 파일: `verify_mc.py`, `INDEPENDENT_MC_CHECK.json`, `SCIENTIFIC_AUDIT_PACKET.json`. `make_packet.py`는 사용자가 제공한 export 파일로 정합성을 다시 계산하는 선택적 도구다.

## 설치·독립 검증 (항상 무과금)

ZIP을 `$HOME/ScientificEvolution`에 풀어 `G13_LEVEL2_SCIENCE_FEEDBACK_20261030` 폴더를 만든다. **이전 런타임 패키지를 덮어쓰지 않는다.**

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
AUD="$PWD/G13_LEVEL2_SCIENCE_FEEDBACK_20261030"
KIT="$PWD/SCIENTIFIC_EVOLUTION_LEVEL2_RUNTIME_REPAIR_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
touch "$EXP/STOP_REQUESTED"

python "$AUD/test_feedback_offline.py"
python "$AUD/verify_mc.py" --draws 40000 --out "$HOME/G13_INDEPENDENT_MC_CHECK.json"
python "$AUD/audit_bridge.py" preview --experiment "$EXP" \
  | tee "$HOME/G13_AUDIT_PREVIEW.json"
```

`SCIENTIFIC_AUDIT_SAFE_PREVIEW_NO_PAID`, `audit_registered: false`, `journal_unchanged: true`, `provider_requests_sent: 0`을 확인한다. 만약 `TARGET_WORK_ADVANCED_OR_RESET`, `UNRESOLVED_CALL`, `SHA_MISMATCH` 등이 나오면 **등록하지 말고 결과를 검토**한다. 최초 이벤트 수가 1268과 같을 것으로 예상하나, 변경됐다면 자동으로 역사적 결과를 추정하지 않는다.

## 기존 Journal에 감사 기록 등록 (명시적 조치, 무료)

미리보기 결과와 패킷을 확인하고, 연구자가 외부 감사를 입력받는 것에 동의할 때에만 다음을 실행한다. **이 단계는 E2 Journal에 SOURCE_REGISTERED 이벤트를 1개 새로 기록하는 비가역적인 append-only 변경이다.** 기존 이벤트와 자산은 수정하지 않는다.

```bash
EXPECTED_HEAD="$(python - <<'PY'
import json,os
p=os.path.expanduser('~/G13_AUDIT_PREVIEW.json')
print(json.load(open(p))['journal_head']['head_sha256'])
PY
)"

python "$AUD/audit_bridge.py" register \
  --experiment "$EXP" --expected-head "$EXPECTED_HEAD"

python "$AUD/audit_bridge.py" verify-disclosure --experiment "$EXP" \
  | tee "$HOME/G13_AUDIT_DISCLOSURE_PROBE.json"
```

성공 조건: `SCIENTIFIC_FEEDBACK_WORKER_DISCLOSURE_VERIFIED_NO_PAID`, `fresh_worker_unexposed: true`, `journal_unchanged: true`, `provider_requests_sent: 0`. 실패하면 STOP 파일을 그대로 유지한다.

이 감사 원문은 오직 `W_develop_finite_exposure_adversarial_model_001`의 다음 Worker 프롬프트에 **별도 외부 감사로 명시**되며, redox 미등록 후보는 해당 finite-exposure Worker에게 주입하지 않는다. 그 후보의 원문은 이전 WORKER MODEL_RESPONSE와 새 감사 레코드에 미등록으로 남아 있다.

## 실제 자율 연구 구간 재개 (유료, 검증 후 선택적으로)

위의 모든 무료 검증이 통과했고 다른 실행 프로세스가 없을 때, 명시적으로 비용 승인한 운영 구간에 한해 다음을 사용한다. 이 호출은 기존 `evolution_memory.py run`을 래핑하면서 **추가 과학적 입력을 INFORMED Work step 4에 한 번만 제공**한다. 현재 G13 복구 코드의 안전 검사·실제 Journal 저장·과금 게이트는 그대로 사용한다.

```bash
pgrep -af '[e]volution_memory.py run|[a]udit_bridge.py run' || true
rm -f "$EXP/STOP_REQUESTED"
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  trap 'unset FAKG_RESEARCH_ALLOW_PAID' EXIT
  python "$AUD/audit_bridge.py" run \
    --experiment "$EXP" --paid \
    --model openai/gpt-5.6-luna \
    --bootstrap-peers 2 --slice-budget 8 \
    --checkpoint-iterations 12 --max-parallel 2 \
    --max-tokens 16000 --science-cpu-seconds 120 \
    --science-wall-seconds 160 --notice-every-segments 1 \
    --max-operational-segments 1 \
    2>&1 | tee -a "$EXP/SCIENTIFIC_AUDIT_CONTINUATION.log"
)
```

`--max-operational-segments 1`은 **금액 상한이 아니다**. 운영상 STOP은 과학적 HOLD가 아니다. 특정 INFORMED Work가 다음 구간에 선택되는 것은 보장할 수 없으며, 아무 과학적 주장도 강제로 생성하지 않는다. 완료 또는 추가 진행 후에는 실제 호출 원문과 새 Tool Result 및 자산들을 독립적으로 평가한다.

## 제약 및 진실성 경계

- **중요:** 현재 G13 Journal 원본은 패키지에 포함되어 있지 않다. 본 패키지는 user-provided science export와 공개 GitHub 브랜치의 코드 계약을 바탕으로 제작되었고, 실제 최신 ROOT의 preview/registration/disclosure 검증은 사용자 WSL에서 수행되어야 한다.
- 모델이 미등록 자산을 다시 제안하더라도 과거 실패한 자산을 자동 소급 등록·수정하지 않는다.
- `SRC_AUDIT_G13_MC_*`는 EXTERNAL_AUDIT이며 새로운 E2 Python tool execution도, 독립 실측 자료도 아니다.
- 시스템에 기존 SAVED Worker step 4가 있거나 Work가 이미 진행된 경우 패키지는 실패한다. **절대 호출 재생을 강제하거나 오래된 응답을 재사용하지 않는다.**
- 과학적으로 경쟁 Null에 이겼다는 결론은 아직 없다. Jacobi는 하나의 수학적으로 허용되는 연속 Null 예시이지, 해당 SERS 실험에서 그 확산이 실제로 발생한다는 근거는 아니다.
