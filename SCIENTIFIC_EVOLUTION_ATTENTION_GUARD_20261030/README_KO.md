# G13 Next-Opportunity Attention Guard — 2026-10-30

## 용도 및 근거

G13의 `D00008` 새 Opportunity 평가 시도가 `MODEL_ATTENTION_BUDGET_UNSATISFIED_NO_SILENT_TRUNCATION`으로 시작 전에 중단됨. 기존 `evolution_memory.py preflight`는 **기존 SAVED 모델 요청**만 평가했기 때문에 NEXT `OPP_D00008`의 실제 입력 크기를 확인하지 못했음. 이번 패키지는 이전 Safe Attempt Resume를 보존하면서 두 가지를 추가.

1. `memory_bridge.py`의 세 차례의 **참조형 추가 압축**. 오래된 포트폴리오·SYN·심사 문장과 `assets`의 과도한 재전송을 우선 줄이고, 본문의 P0, 모든 문제 ID, NVT 및 PMI의 주장–근거 reference, 활성 Work의 원문 계약, 원본 입력 해시를 보존함. 과학적 참 또는 거짓, 후보 우선순위, 실험 성공/실패 등을 결정하지 않음. 그럼에도 한도를 넘으면 그대로 FAIL-CLOSED.
2. `attention_probe.py`가 **실제 V4/V3/Population/Frontier 컨텍스트와 이미 SAVED된 NVT·PMI를 사용해** 새 `OPP_D00008` 입력을 무과금으로 생성, 모델에 전달하기 전 수치 및 불변식을 검증함. 추가로 실행기 `run`에 이 검사를 통합해 실패하면 **유료 요청 전 차단**함. 기존 Journal은 읽기 전용으로 유지.

이 패키지는 알고리즘이나 물리적 새 발견을 인증하지 않으며, 오프라인 테스트만으로 실제 최신 G13의 성공이 확정되지 않음. 본문에 축약 표시가 붙은 이전 자산의 전체 내용은 E2 Journal에만 있으며, 현재 Controller가 자동으로 원문을 조회하는 도구가 되는 것은 아님. 장기적으로 실제 조회형 메모리 인터페이스가 필요함.

## 설치

기존 패키지를 지우지 말고 ZIP을 `$HOME/ScientificEvolution` 아래에 압축 해제.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
KIT="$PWD/SCIENTIFIC_EVOLUTION_ATTENTION_GUARD_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
touch "$EXP/STOP_REQUESTED"

python "$KIT/test_long_horizon_attention.py"
python "$KIT/test_memory_offline.py"
python "$KIT/test_attention_regression.py"
python "$KIT/test_receipt_boundary_offline.py"
python "$KIT/test_safe_attempt_offline.py"

python "$KIT/attention_probe.py" \
  --experiment "$EXP" \
  --model openai/gpt-5.6-luna \
  --max-tokens 16000 \
  | tee "$HOME/G13_D00008_ATTENTION_PROBE.json"
```

### 필수 조건

Probe가 **`status: NEXT_ATTENTION_READY_NO_PAID`**, `next_call_id: OPP_D00008`, `journal_unchanged: true`, `provider_requests_sent: 0`를 출력해야 함. 특히 `integrity`의 모든 항목이 true여야 함. `NEXT_ATTENTION_BLOCKED_NO_PAID` 등 다른 status면 `STOP_REQUESTED`를 제거하지 말고 JSON 출력 파일을 검토.

Probe가 통과한 뒤에만 기존 `run` 명령의 `KIT`을 위 새 폴더로 설정해 실행. `evolution_memory.py run` **자체가 Probe를 다시 수행**하므로 상태가 중간에 바뀌면 유료 실행 전 중단함. `--max-operational-segments 1`은 관찰 경계이며 총 과금액을 보장하는 절대 상한이 아님. 여러 모델 호출이 한 구간에 포함될 수 있음.

```bash
pgrep -af '[e]volution_memory.py run' || true
rm -f "$EXP/STOP_REQUESTED"
python "$KIT/evolution_memory.py" preflight --experiment "$EXP"
# paid run은 Probe 성공 및 사용자 의도적 승인 후 기존 명령 재사용
```

### 복구·계보 보장

- 기존 `OPP_D00007`의 SAVED 원문 및 G13 전체 기존 Journal은 변경하지 않음.
- 새로운 Controller 평가 시도는 `D00008`; 과거 NVT·PMI는 정확한 원 요청 해시 검사 후에만 재생.
- 프롬프트·과학적 입력이 달라지면 과거 평가를 다른 요청에 연결하지 않음.
- 과도한 입력 길이 또는 불변식 불일치 시 유료 실행 차단.
- 최초 새 OPP 호출 뒤의 실제 모델 응답과 후속 Controller 요청까지 성공한다는 보장은 없음.

## 개발 환경 검증

서버 컨테이너에서 합성 장기 입력 및 기존 오프라인 회귀 **34개** 통과. `py_compile` 통과. 최신 사용자의 G13 Journal(1186+ 이벤트)은 이 컨테이너에 없어 해당 ROOT의 실제 Probe는 사용자 WSL에서만 검증 가능.
