# Memory & Tool Truth V1.3 — SAVED Replay Compatibility

## 원인
기존 V1.1/V1.2 `memory_bridge.activate()`는 SAVED `OPP_`/`CTRL_` 호출 ID가 있으면 무조건 압축을 건너뛰고 원본 입력을 DurableModel로 넘겼다. 하지만 실제 저장된 요청이 이미 압축된 입력인 경우, `MODEL_REPLAY_INPUT_CHANGED`가 발생했다. 본문·prompt가 변경된 과거 요청을 새 응답처럼 재사용하는 것은 금지된다.

## 수정
모델에 노출되는 메모리 계약의 `VERSION`은 **V1.2 그대로** 유지한다. V1.3은 재생 동작만 바꾸며 이 버전 문자열까지 변경하면 유효한 동일 과학 입력의 해시가 달라지기 때문이다.

- SAVED 요청이면 저장된 원래 요청의 `model`, `system`, `temperature`, `max_tokens`, `actor`, `work_id` 계약을 확인한다.
- 기존 저장 요청의 `science_memory_request_receipt.original_payload_sha256`과 이번 **압축 전** 과학적 입력의 SHA-256이 동일한 경우에 한해서, 기존 요청에 사용된 **정확한 저장된 모델 입력**을 DurableModel에 넘겨 재생한다. DurableModel의 원래 바이트 단위 해시 검증을 통과해야 응답이 반환된다. 재과금 없음.
- 입력 과학 내용이나 system prompt가 변했다면 `MODEL_REPLAY_SCIENCE_INPUT_CHANGED:<call_id>` 또는 `MODEL_REPLAY_CONTRACT_CHANGED:<call_id>`로 안전하게 중단한다. 다른 호출 ID로 몰래 다시 과금하지 않는다.
- NVT/PMI/WORKER 기존 SAVED 요청은 정확한 원본 입력과 동일할 때만 재생한다. 다른 상황은 로그에 구체적인 호출 ID를 남겨 확인할 수 있다.
- 원본 Journal, 유료 사용량, 가설 선택 기준, 과학적 HOLD 등 변경 없음.

## WSL 설치
기존 V1.1, V1.2 폴더를 유지하고 이 ZIP을 `~/ScientificEvolution`에 압축 해제한다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
KIT="$PWD/SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_3_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

test -f "$EXP/STOP_REQUESTED" || touch "$EXP/STOP_REQUESTED"
python "$KIT/test_memory_offline.py"
python "$KIT/test_attention_regression.py"
python "$KIT/test_receipt_boundary_offline.py"
python "$KIT/test_replay_compat_offline.py"
python "$KIT/model_replay_inventory.py" \
  --journal "$EXP/CYCLE_013/POPULATION" \
  --out "$HOME/G13_REPLAY_INVENTORY.json"
python "$KIT/evolution_memory.py" preflight --experiment "$EXP"
```

`STOP_REQUESTED` 상태는 정상적인 수동 정지다. **실제 WSL에서 이번 충돌 호출 ID가 OPP/CTRL인지 NVT/PMI/WORKER인지 아직 확인하지 못했다.** 재개 시 충돌이 해소될지는 추가 검증이 필요하다. `MODEL_REPLAY_SCIENCE_INPUT_CHANGED` 또는 `MODEL_REPLAY_CONTRACT_CHANGED`가 나오면 유료 실행을 재시도하지 말고 해당 로그와 인벤토리를 검토한다.

현재 오류 직전 0 신규 호출이며 기존 실행에서 과거 과금이 발생한 사실과 구별된다. 실제 저장된 요청을 덮어쓰거나 충돌한 호출 ID를 지우지 않는다.

## 후속 실행
무제한 실행 전 OpenRouter 계정 단위 비용 상한을 설정하고, RUNNER가 완전히 종료되었는지 확인한다. 유료 재개는 사용자 결정. 실행 방법은 V1.2와 동일하되 KIT만 V1.3으로 변경하고 `STOP_REQUESTED`를 명시적으로 해제한다. 유료 실행 중 운영 오류가 생기면 자체 오류 메시지와 Journal은 원본 그대로 보존한다.
