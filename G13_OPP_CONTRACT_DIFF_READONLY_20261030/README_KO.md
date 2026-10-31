# G13 OPP_D00007 계약 차이 읽기 전용 진단

V1.4 무료 probe가 `MODEL_REPLAY_CONTRACT_CHANGED:OPP_D00007`을 반환했다. 이 오류는 요청 본문의 과학적 내용 비교 **이전에** 발생한다. 그래서 기존 모델 요청과 현재 요청의 **actor, work_id, model, max_tokens, temperature, response_format, system prompt**를 하나씩 비교하고, 원본/현재/메타데이터 정규화 후 해시도 함께 출력한다.

## 실행 (무료, Journal 읽기 전용)

패키지 폴더 `G13_OPP_CONTRACT_DIFF_READONLY_20261030`을 `~/ScientificEvolution/`에 두고 다음을 실행한다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
KIT="$PWD/SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_4_20261030"
DIAG="$PWD/G13_OPP_CONTRACT_DIFF_READONLY_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$DIAG:$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
touch "$EXP/STOP_REQUESTED"
python "$DIAG/test_contract_diff_offline.py"
python "$DIAG/opp_contract_diff.py" --experiment "$EXP" --model openai/gpt-5.6-luna --max-tokens 16000 | tee "$HOME/G13_OPP_CONTRACT_DIFF.json"
```

이 스크립트는 `pending_replay_probe.py`와 마찬가지로 실행기의 NVT/PMI 호출을 **저장 응답에서만** 재생해 OPP 입력을 구성한다. OPP에서 네트워크 요청을 보내지 않고 비교 결과로 종료한다. 보고서는 실제 미결 호출이 있다면 이를 알리고 중단하며, `journal_unchanged: true` 및 `provider_requests_sent: 0`을 출력한다.

`mismatched_contract_fields`에서 정확한 불일치 항목을 확인한다. 특히 `system_prompt`가 거짓이면 `prompt_changed_line_previews`로 과거/현재 프롬프트가 어떤 부분에서 달라졌는지 확인한다. `only_normalized_metadata_matches_archived_precompaction`이 참인지도 확인하지만 **시스템 프롬프트가 달라졌다면 이 값만으로 과거 응답을 재사용해서는 안 된다.**

이 진단 패키지는 어떤 모델의 호출 ID도 변경하지 않으며 실행 패치가 아니다. 결과를 본 뒤 (1) 단순 실행환경 문제면 원래 실행 계약을 복원해 정확 재생하거나, (2) 실제 요청 계약 변경이면 기존 OPP를 이력에 남기고 별도 Controller 시도 ID로 이동하는 두 경로 중 하나를 선택한다. Journal 삭제·수정·기존 응답 덮어쓰기는 금지한다.
