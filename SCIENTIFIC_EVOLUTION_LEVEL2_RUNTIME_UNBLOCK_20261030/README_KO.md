# Level-II First — G13 Runtime Unblock (2026-10-30)

## 목적

**목표는 Level II 후보 한 개의 완성**이다. 이는 새롭고, 물리적으로 방어 가능하며, 강한 경쟁 설명과 구별되는 예측을 갖춘 가설이다. 실험적 입증은 Level II의 필요조건이 아니다. 이 패키지는 Level II 달성이나 새로운 과학적 결과를 주장하지 않는다. G13 연구를 다시 시작하기 전에 드러난 공통 런타임 결함을 최소 범위에서 개선한다.

기준: `ssnon/ScientificEvolution`, `debug/g13-runtime-20261030`, 커밋 `8e80586f0708a7eb72e5afb042f1a03ba88f6f02`와 동일한 Attention Guard 소스.

## 변경 파일 (3개)

1. `memory_bridge.py` — 모든 Problem ID·부모를 객체 배열로 계속 재압축하다 고정 최소 크기와 충돌하는 경우, 활성 문제 및 조상의 설명과 전체 ID·부모 관계를 구분한 **밀집 참조 카탈로그**로 재구성한다. `all_problem_ids_newline_delimited`와 `parent_indices_semicolon_delimited`가 존재하면 ID i에 대응하는 부모의 인덱스를 정확히 보존한다. 카탈로그 전체가 들어가지 않는 극단적 경우에는 `all_problem_ids_in_this_view=false`와 총 개수·해시·미확장 개수를 명시하고 원본 E2 Journal을 보존한다. P0 원문, 활성 Work, NVT/PMI의 claim/evidence 관계, 원본 입력 SHA를 변경하지 않는다. FRESH 경계와 도구 실행 근거는 변경하지 않는다.
2. `safe_attempt.py` — 모든 세대에서 `OPP_D00007`이라는 역사적 호출이 존재해야 하는 요구를 없앤다. SAVED 평가 요청과 확정 Controller ID를 모두 예약하여 새 평가 ID를 선택한다. 이미 저장된 응답을 다른 과학/프롬프트 입력에 재해석하지 않는다. 현재 V4 프롬프트가 과거 프롬프트와 다르면 *새 시도임을 기록*하며, 새로운 호출을 기존 저장 응답으로 재생하지 않는다.
3. `evolution_memory.py` — G13 D00008에만 적용되던 무과금 다음-OPP 검사를 **모든 Population 주기**로 확장한다. 사전에 실제 다음 요청을 구성하고, 입력 무결성·제한을 확인한다. 신규 NVT/PMI 요청이 첫 요청인 경우는 OPP 검사에서 제외하되 기존 provider 유료 호출 게이트는 그대로 유지한다. 운영 비용 관찰 경계는 과학적 HOLD가 아니다.

추가: `test_level2_runtime_offline.py` (긴 ID·부모 계보·1,700개 문제·P0/claim/Work 보존 회귀). G13 전용 가정이 달라진 기존 테스트 하나는 새 범용 계약으로 바꾸었다. 기존 부속 테스트는 삭제하지 않았다.

## 설치 및 무료 검증

ZIP을 `$HOME/ScientificEvolution/` 아래 압축 해제하고 아래를 실행한다. 기존 KIT, runtime, 연구 Journal은 덮어쓰지 않는다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
KIT="$PWD/SCIENTIFIC_EVOLUTION_LEVEL2_RUNTIME_UNBLOCK_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
touch "$EXP/STOP_REQUESTED"

python "$KIT/test_level2_runtime_offline.py"
python "$KIT/test_long_horizon_attention.py"
python "$KIT/test_memory_offline.py"
python "$KIT/test_attention_regression.py"
python "$KIT/test_receipt_boundary_offline.py"
python "$KIT/test_replay_compat_offline.py"
python "$KIT/test_metadata_replay_offline.py"
python "$KIT/test_safe_attempt_offline.py"

python "$KIT/attention_probe.py" \
  --experiment "$EXP" --model openai/gpt-5.6-luna --max-tokens 16000 \
  | tee "$HOME/G13_LEVEL2_UNBLOCK_PROBE.json"
```

`NEXT_ATTENTION_READY_NO_PAID`, `provider_requests_sent:0`, `journal_unchanged:true`, `integrity` 모두 true가 확인되어야 한다. 다음 호출 ID는 Journal의 진척에 따라 D00010 이후가 될 수 있다. 더 이상 하드코딩하지 않는다. 실제 OPP 응답을 받기 전에는 후속 Controller 응답 내용과 크기를 확정할 수 없다.

**주의:** 새 패키지의 오프라인 테스트 통과는 사용자 WSL의 최신 G13 실험 복구를 보증하지 않는다. 실제 최신 ROOT는 로컬에 남아 있고 GitHub 브랜치에는 포함되지 않았다. Probe가 실패하면 유료 실행하지 말고 그 출력부터 검토한다.

## 승인 후 실제 실행

무료 Probe의 일치/무결성이 확인되어 의도적으로 한 운영 구간을 재개할 때만 `rm -f "$EXP/STOP_REQUESTED"`를 실행하고, 기존의 `evolution_memory.py run` 명령에서 KIT을 이 패키지로 바꾼다. `--max-operational-segments 1`을 유지한다. 이는 엄격한 금액 상한이 아니므로 계정 측 사용량 제한을 별도로 적용한다. 불확실한 유료 요청은 절대 자동 재시도하지 않는다.

## 남은 과제 / 한계

- 매우 많은 문제(예: 1,700개 장문 ID)에서 전체 ID 카탈로그 자체가 attention budget을 초과할 수 있다. 그 경우 조회 가능한 원본 Journal을 유지하면서 한 페이지의 계보를 제시한다. 이는 장기적으로 Controller의 읽기 전용 archive-query 인터페이스가 필요하다는 뜻이지, 과학적 기각이 아니다.
- Probe는 신규 첫 모델 요청까지 재현한다. 아직 존재하지 않는 OPP 응답을 사전에 가상으로 만들어 후속 Controller 판단을 인증하지 않는다. 대신 실제 모든 OPP/CTRL 요청에는 동일한 `bound_advisor_payload`가 적용된다.
- 기존 G13의 과거 유료 응답과 원본 기록은 절대 편집/삭제하지 않는다.
- 이 릴리스는 Level II를 위해 **과학 실행을 재개하는 기반**일 뿐이다. 이후 연구에서 실제 계산·물리적 실현 가능성·기존 연구 대비 신규성·Null 대비 구별 예측을 검토해야 한다.
