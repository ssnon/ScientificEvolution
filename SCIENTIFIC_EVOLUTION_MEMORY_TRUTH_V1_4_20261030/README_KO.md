# Scientific Evolution Memory & Tool Truth V1.4 — G13 원본 모델 입력 재생 복구

## 현재 확인된 상황

- G13의 확정 Controller 결정은 6개. `OPP_D00007`은 SAVED, `CTRL_D00007`은 미생성.
- `OPP_D00007`의 저장된 입력은 `RETRIEVABLE_SCIENCE_MEMORY_AND_EXECUTED_TOOL_TRUTH_V1_1_20261030` 버전으로 기록됐으나, V1.3의 현재 모델 컨텍스트는 V1.2 버전 표기를 포함한다.
- V1.3 로그: `MODEL_REPLAY_SCIENCE_INPUT_CHANGED:OPP_D00007`. 실제 이번 시도의 신규 유료 모델 호출 0회.
- **과학적 필드까지 동일한지는 로그만으로 알 수 없다.** 원본 정보의 무조건적인 덮어쓰기, 재해석, 중복 과금 금지.

## V1.4 변경 범위

`memory_bridge.py`의 기존 V1.3 안전 재생 규칙에 *엄격한 과거 버전 호환 증명*을 추가했다.

1. 과거 저장된 모델 요청의 system/model/temperature/max_tokens/actor/work_id가 현재와 같아야 한다.
2. 보통의 경우 저장된 `original_payload_sha256`이 현재 원본 입력 해시와 정확히 같아야 한다.
3. V1.1 → V1.2 차이인 경우에만 현재 입력의 사본에서 다음 두 메타데이터 버전 필드를 V1.1로 바꿔 해시를 검사한다: `science_memory_disclosure.version`, `verified_execution_provenance.contract`. 다른 텍스트는 전혀 정규화하지 않는다.
4. 이 사본의 **전체 SHA-256이 저장된 압축 전 원본 SHA-256과 정확히 같을 때에만** E2의 저장된 요청 바이트 그대로 응답을 재생한다. 다르면 중단하면서 현재/정규화/원본 SHA 값을 표시한다.
5. `MODEL_CALL_INTENT`, `MODEL_CALL_SAVED`, Journal 파일, 실행된 도구 결과, 실제 과학적 판단은 재작성하지 않는다.
6. V1.2의 모델 출력용 메모리 버전 표시는 유지한다. 이 코드는 위 단계만 추가한다.

`pending_replay_probe.py`는 유료 호출을 수행하지 않고, **실제 다음 G13 Controller 논리**를 실행한 것처럼 저장된 NVT/PMI/OPP 응답을 검증한다. 미저장 요청에 도달하면 호출하기 직전에 종료한다. Journal의 append/blob는 프록시가 차단한다.

## 설치 및 무료 진단 (중요)

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
KIT="$PWD/SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_4_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

touch "$EXP/STOP_REQUESTED"

python "$KIT/test_memory_offline.py"
python "$KIT/test_attention_regression.py"
python "$KIT/test_receipt_boundary_offline.py"
python "$KIT/test_replay_compat_offline.py"
python "$KIT/test_metadata_replay_offline.py"

# 과거 연구의 실제 호출 경로: 새 모델 요청 바로 직전까지만 실행
python "$KIT/pending_replay_probe.py" \
  --experiment "$EXP" \
  --model openai/gpt-5.6-luna \
  --max-tokens 16000 \
  | tee "$HOME/G13_PENDING_REPLAY_PROBE_V1_4.json"
```

### 결과 해석

- `status: NEXT_MODEL_CALL_IS_NEW`, `next_call_id: CTRL_D00007`, `previous_saved_calls_replayed`에 과거 OPP 포함: 저장 응답 재생이 무료 검증을 통과한 상태. 실제 유료 재개는 사용자가 별도로 선택한다.
- `status: PENDING_REPLAY_BLOCKED`: 정확한 과거 입력과 현재 입력이 버전 표기 외에도 다르다는 뜻. **유료로 재실행하지 말고** 출력된 SHA들과 ID를 검토해야 한다. 무단으로 호출 ID를 바꾸거나 저장 결과를 버리지 말 것.
- `status: PROBE_UNEXPECTED_ERROR`: 오프라인 진단 자체의 복구가 필요. 유료 실행 금지.
- `NEXT_MODEL_CALL_IS_NEW`가 `CTRL_D00007`이 아닌 다른 ID인 경우: 그 ID와 순서를 검토하고 재개 여부를 결정한다.
- `provider_requests_sent: 0`은 진단기 자체가 네트워크 요청을 만들지 않는다는 의미이며, 과거에 사용한 비용이 0이라는 뜻은 아니다.

## 재개는 진단 이후에만

실행 전 `preflight`에서 `unresolved_model_intents: []`와 `autonomous_meta_check_error: null`을 재확인한다. `STOP_REQUESTED` 제거는 재개 의도가 있을 때만 한다. 기존 연구 ROOT와 MODEL SAVED 데이터를 절대 덮어쓰지 않는다.

현재 위 명령은 ***유료 재개가 아니라 진단 단계***이다. 다시 실행하더라도 원래의 비용 제한 및 중단/체크포인트 원칙을 적용해야 한다. 통과 판정은 Level II 물리 가설의 과학적 타당성을 뜻하지 않는다.
