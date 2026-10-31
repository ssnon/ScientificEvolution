# Scientific Evolution — Safe Attempt Resume (G13) · 2026-10-30

## 해결하려는 실제 문제

G13 현재 상태: 여섯 개 Controller 결정(D00001–D00006), `OPP_D00007` SAVED, `CTRL_D00007` 없음, active INFORMED Work `W_develop_selective_intervention_boundary_001`. 과거 OPP_D00007은 V1.1 메모리 입력과 V4 opportunity prompt(3,894자)로 저장되었지만 재구성 요청에서는 V1.2 입력과 짧은 opportunity prompt(1,933자)를 사용했다. 실제 진단에서 system prompt 해시와 압축 전 science input 해시 모두 불일치. 따라서 D00007을 같은 요청으로 간주하여 재생하면 안 된다.

**이 패키지는 기존 연구를 재시작하지 않고 미완료 호출 ID를 버전 관리하여 새 Controller 시도에서 이어간다.** 이전 모델 응답·Journal·연구 자산을 삭제·변경·재해석하지 않는다.

## 변경된 구조

1. `safe_attempt.py`는 모든 SAVED `OPP_Dxxxxx`와 `CTRL_Dxxxxx`, 확정 Controller 결정 ID를 예약한다. `_next_controller_id()`는 과거 유료 호출이 연결된 미완료 D00007을 선택하지 않고 D00008을 선택한다. 이후의 불완전한 기회 평가도 같은 원칙으로 처리한다.
2. **실제 연구 드라이버는 `mods.v4.runtime()`에서 V4 opportunity prompt를 추가한다.** 이전 무료 진단기가 그 컨텍스트를 누락하여 1,933자 프롬프트를 비교한 점은 별도의 진단 오류였다. 새로운 코드는 `v4.runtime()`의 정확한 시스템 프롬프트가 과거 OPP의 시스템 프롬프트와 일치하는지 읽기 전용으로 검사한다. 프롬프트를 덧붙이거나 재구성하여 억지로 이전 응답을 재생하지 않는다.
3. NVT/PMI는 기존 immutable replay 보호장치를 그대로 통과해야 한다. 예상되는 다음 신규 요청은 `OPP_D00008`이고, `CTRL_D00008`은 OPP 결과가 검증된 뒤에만 생성된다.
4. 모델 호출의 정확한 request SHA, append-only Journal, FRESH/INFORMED 분리, 실제 도구 실행 provenance는 기존 방식을 유지한다. Controller 과학적 정책을 강제하지 않는다.
5. 첫 유료 관찰은 `--max-operational-segments 1`로 기본 설정해, **하나의 운영 세그먼트가 완료된 뒤 `STOP_REQUESTED`를 자동 생성**한다. 이는 과학적 종결이 아니라 운영상의 비용 관찰 경계다. 기존 내부 `--slice-budget 8` 외에 Steering 추가 호출이 발생할 수 있어 **정확한 8-호출 또는 달러 상한을 뜻하지 않는다**.

## 1. ZIP 설치

`~/ScientificEvolution/` 위치에서 ZIP을 풀어 다음 디렉터리가 있어야 한다.

`~/ScientificEvolution/SCIENTIFIC_EVOLUTION_SAFE_ATTEMPT_RESUME_20261030/`

기존 V1.4·Frontier·Autonomous·런타임 디렉터리를 삭제하지 않는다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
KIT="$PWD/SCIENTIFIC_EVOLUTION_SAFE_ATTEMPT_RESUME_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
# 무료 진단 동안 일시정지 유지
touch "$EXP/STOP_REQUESTED"
```

## 2. 무료 테스트 및 실제 G13 무과금 재개 Probe

```bash
for t in test_memory_offline.py test_attention_regression.py test_receipt_boundary_offline.py test_replay_compat_offline.py test_metadata_replay_offline.py test_safe_attempt_offline.py; do
  python "$KIT/$t" || exit 1
done

python "$KIT/safe_resume_probe.py" \
  --experiment "$EXP" --model openai/gpt-5.6-luna --max-tokens 16000 \
  | tee "$HOME/G13_SAFE_ATTEMPT_PROBE.json"
```

**반드시 다음 결과 확인:**

- `status: SAFE_NEW_OPPORTUNITY_READY_NO_PAID`
- `controller_attempt_id: D00008`
- `next_call_id: OPP_D00008`
- `previous_saved_calls_replayed`에 `NVT_014f30d89ea5bfb2a0a23c1`, `PMI_ede5a8558471f09cff0fa6e` 두 ID 포함
- `provider_requests_sent: 0` / `journal_unchanged: true`
- `opportunity_prompt_provenance.reason: EXACT_MATCH` (정상 V4 연구 컨텍스트와 저장 프롬프트 일치)

이 외 결과가 나오면 **유료로 재실행하지 않는다**. 원본 Journal을 수정하지 않는 진단이므로 다음 오류 문자열만 공유하면 된다.

## 3. Probe 통과 후에만 1 운영 구간 유료 실행

```bash
# 중복 프로세스가 없을 때만 진행
pgrep -af '[e]volution_memory.py run' || true
rm -f "$EXP/STOP_REQUESTED"
python "$KIT/evolution_memory.py" preflight --experiment "$EXP"
# paid_run_ready:true, unresolved_model_intents:[], meta_check_error:null 확인

(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  trap 'unset FAKG_RESEARCH_ALLOW_PAID' EXIT
  python "$KIT/evolution_memory.py" run \
    --experiment "$EXP" --paid --model openai/gpt-5.6-luna \
    --bootstrap-peers 2 --slice-budget 8 \
    --checkpoint-iterations 12 --max-parallel 2 \
    --max-tokens 16000 --science-cpu-seconds 120 \
    --science-wall-seconds 160 --notice-every-segments 1 \
    --max-operational-segments 1 \
    2>&1 | tee -a "$EXP/SAFE_ATTEMPT_RESUME_RUN.log"
)
```

정상 완료 시 `OPERATOR_COST_OBSERVATION_BOUNDARY` 로그와 `STOP_REQUESTED` 파일이 남으며, 새 유료 연구를 추가로 계속하기 전에 중간 결과·비용을 검토한다. 이미 서명/과금된 OPP_D00007 응답은 변경되지 않고 비공식 미완료 시도로 남는다. D00008은 새로운 모델 입력으로서 실제 과금될 수 있다.

## 오프라인 검증 범위

V1.4의 기존 테스트 21개 및 이번 새 테스트 11개 = **총 32개 통과**. 테스트는 단순 가짜 Journal 기반으로 ID 예약·프롬프트 복원·예외 시 원복·중간 일시정지 등을 검사한다. **실제 G13 연결은 위 `safe_resume_probe.py`를 WSL에서 실행해야 검증 가능. 이 Probe는 실제 `population_science_bridge`·`historical_input_compat`·`v4.runtime()`·`v3_runtime()`·`cohort_context_bridge`를 적용한 뒤 새 요청 직전에 멈춘다**하다.

본 패키지는 G13의 특정 미완료 기회 평가를 복구하는 실행 보완이다. 이것만으로 가설의 물리적 타당성이나 Level II 도달을 보증하지 않는다. 원래의 범용 AI Scientist 과학 연구 목표와 평가 기준은 변경하지 않는다.
