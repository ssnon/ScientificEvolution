# Scientific Evolution G13 — 실제 진입점 복구 (2026-10-30)

## 확인된 실패

이전 `SCIENTIFIC_EVOLUTION_LEVEL2_RUNTIME_UNBLOCK_20261030`에는 `page_problem_context()`가 구현됐지만 `memory_bridge.bound_base()`가 구형 `bound_problems()`를 직접 호출했다. 실제 G13에 긴 문제 계보가 누적되면 `bound_base()`가 `PROBLEM_IDENTITIES_EXCEED_ATTENTION_BUDGET_NOT_SILENTLY_OMITTED`를 발생시켜, NVT/PMI 저장 응답 재생 전 단계에서 중단될 수 있다. 실제 Probe는 `saved_replays=[]`를 출력했다.

## 변경 범위

- `memory_bridge.py`: `bound_base()`의 기존 `bound_problems` 성공 경로는 유지한다. 크기 한도로만 실패할 때 명시적 `page_problem_context()`로 전환한다. 다른 모든 예외는 원칙적으로 전달한다. `problem_attention_info`는 원본 문제 수/원본 해시, 별도 `problem_attention_catalog`는 참조 표현을 기록한다.
- `memory_bridge.py`: 이미 페이지화된 맥락을 재압축할 때 **절대로 현재 보이는 일부 문제를 전체 문제로 오인하지 않고**, 기존 원본 문제 수·해시를 보존한다. 원본 참조 인덱스가 크면 그 인덱스의 본문 표시를 제거하되 `all_problem_ids_in_this_view=false`로 공개하고 Journal 원본을 유지한다.
- `test_real_entrypoint_offline.py`: 이전에 검증하지 않았던 실제 `bound_base()` 진입점, 17k/13k/10k 재압축에서 총 문제 수·원본 SHA 보존, 통합 payload 압축을 검증하는 3개 회귀 테스트 추가.

이 패키지는 기존 코드의 새로운 폴더 복사본이다. E2 Journal 원본, FRESH 격리, 계산 도구, 과학 상태, 과거 SAVED 호출은 변경하지 않는다. 기존 연구를 강제로 새 판단에 연결하거나 저장 응답을 다른 요청에 재사용하지 않는다.

## 설치 및 무과금 확인

ZIP을 `$HOME/ScientificEvolution/`에 압축 해제한다. 기존 KIT과 실험 Journal은 덮어쓰지 않는다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
KIT="$PWD/SCIENTIFIC_EVOLUTION_LEVEL2_RUNTIME_REPAIR_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
touch "$EXP/STOP_REQUESTED"
python "$KIT/test_real_entrypoint_offline.py"
python "$KIT/test_level2_runtime_offline.py"
python "$KIT/test_memory_offline.py"
python "$KIT/test_safe_attempt_offline.py"
python "$KIT/attention_probe.py" \
  --experiment "$EXP" --model openai/gpt-5.6-luna --max-tokens 16000 \
  | tee "$HOME/G13_LEVEL2_REPAIR_PROBE.json"
```

필요하면 `python "$KIT/test_long_horizon_attention.py"`, `test_attention_regression.py`, `test_receipt_boundary_offline.py`, `test_replay_compat_offline.py`, `test_metadata_replay_offline.py`도 실행한다.

### 판정 기준

성공 시: `status=NEXT_ATTENTION_READY_NO_PAID`, `journal_unchanged=true`, `provider_requests_sent=0`, 모든 `integrity` true. 다음 호출 ID는 반드시 현재 Journal 상태를 따른다. 특정 D00011을 요구하지 않는다.

실패 시: `STOP_REQUESTED`를 유지하며 절대 유료 실행하지 않는다. `PROBE_REJECTED`, `MODEL_REPLAY_SCIENCE_INPUT_CHANGED` 등 새 오류는 원인 구분 없이 우회하지 않는다.

`bound_base`가 참조 카탈로그로 전환되면 **과거 SAVED 요청을 생성할 때의 입력 맥락과 달라질 가능성**이 있다. 이런 경우 Replay 시스템은 해당 모델 응답을 정확히 재생할 수 없는 것으로 차단해야 하며, 로그를 통해 구분·분리할 필요가 있다. 이번 코드가 실제 최신 사용자 G13에서의 모든 후속 모델 호출을 성공시킨다고 주장하지 않는다.

## 로컬 검증

2026-10-30 개발 컨테이너의 합성 데이터 기반 40개 오프라인 회귀 테스트 및 Python 컴파일 통과. 최신 G13 Journal(1233 이벤트)은 사용자 WSL에만 있으므로 실물 검증은 위 Probe가 담당한다. 과학적 Level II 달성 주장은 하지 않는다.
