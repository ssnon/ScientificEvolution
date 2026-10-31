# Scientific Evolution — Memory & Tool Truth V1 (2026-10-30)

## 의도

이 패키지는 Frontier V1에서 실제 G12–G13 실행 후 발견된 **(a) 저장하지도 실행하지도 않은 도구 호출을 모델이 요청/실패로 서술하는 문제**, **(b) 누적된 문제·독립 SYN·이전 Population·기존 평가를 OPP와 Controller에 매번 재전송해 호출당 40만 자 안팎으로 팽창하는 문제**를 대상으로 한다.

P0/가설/계보의 연구 내용이나 자율 선택 정책을 강제 수정하는 패치는 아니다. 기존 `runtime/`, Frontier V1, Autonomous 패키지의 소스를 **직접 수정하지 않는 외부 런타임 어댑터**이다. 유료 호출이 가능한 코드는 `evolution_memory.py run`뿐이다. `test_memory_offline.py`, `preflight`, `inspect`는 무료.

### 변경한 실행 경로

1. `frontier_runtime`의 모델 관찰용 context에 bounded problem index, peer judgement digest, recent history, archived source hash, active Works, historical candidate summaries, `verified_execution_provenance`를 덧붙인다. 전체 문제 ID를 유지하고 P0 원문은 `program`에 남긴다. `Journal` 원문에는 손대지 않는다.
2. 이전에 `v3.controller_v3`가 만들어 전달하던 거대한 `augmented` 딕셔너리를 `DurableModel.call` 진입 직전, `OPP_` 및 `CTRL_` **신규 요청에 한해서** 분량 제한이 있는 모델 attention view로 변환한다. `claim_assessments`의 각 ID·novelty relation·evidence ID, P0의 state·unresolved requirements를 유지한다. 나머지 상세 원문은 원래 Journal의 저장된 NVT·PMI 응답과 원본 과학 자산에 남는다. 변환 전 SHA-256 및 입력 길이를 새 request receipt에 포함한다.
3. 이미 `SAVED`된 동일 call ID는 새 view로 소급 재작성하지 않고 기존 원래 입력으로 replay한다. `INTENT` 및 `UNCERTAIN`은 원래 안전 규칙을 유지하며 자동 재호출하지 않는다. 입력이 달라 replay 해시 불일치가 발생하면 fail-closed한다.
4. Worker에게 문장/독립 JSON 블록에 도구 사용 의도를 적는 것은 호출이 아님을 알려준다. **실행된 도구의 존재는 `TOOL_RECORDED` ledger만으로 판단**한다. 원문 과학 asset의 주장 자체를 몰래 수정하지 않고, 도구 호출이 없는 실패/문헌 부정 주장에는 모델 입력 내 `unverified_model_execution_report`를 표시하고, `inspect/preflight`에서 `MODEL_WRITTEN_TOOL_PREAMBLE_NOT_DISPATCHED` 유형을 검출한다.
5. `inspect --asset-id ...`에서 현재 검증된 Journal에 등록된 자산의 원문과 부모 계보/근거 ID·출처 유형을 직접 조회한다. `inspect --problem-id ...`는 전체 문제 원문을 제공한다. 이는 원문을 재구성하는 읽기 전용 조회다. Frontier V1의 INFORMED-only `scientific_archive` 도구도 유지된다.

### 제한과 정직한 해석

- 이번 버전의 OPP/Controller 연구 조회는 **활성 연구, 계보, 관련 출처에 대한 결정론적 관련성 선별**이다. AI가 임의의 원본 자산을 여러 차례 인터랙티브하게 검색·읽고 판단하는 전용 controller-side tool-call round-trip까지 구현한 것은 **아니다**. `inspect`로 사람은 임의의 정확한 ID를 조회할 수 있고, INFORMED Worker는 허가된 부모 계보를 조회한다. 장기 후속 버전에서 LLM 제어형 on-demand 조회를 별도로 평가할 수 있다.
- 오류가 있었던 과거 자산을 지우거나 `SCOPED_NEGATIVE`를 자동 삭제/기각하지 않는다. 실행 근거가 없다는 경고로 다운스트림 오인을 방지하지만 기존 모델의 근거 없는 표현을 사실로 고치지는 못한다.
- 원본 과학 기록이나 출처를 압축해 삭제하지 않는다. 연구를 재개하면 기존 E2 런타임이 정상적인 신규 모델 호출과 Work 결과를 원래 Journal에 append하는 것은 허용된다. 다만 모델에게 제공되는 작은 view는 비선택된 자료의 세부 내용을 포함하지 못한다. **원본 Journal에 존재한다는 것과 모델이 이번 판단에서 전부 읽었다는 것은 다르다.**
- 86,000자는 `OPP_/CTRL_` 파생 model payload의 상한이다. 실제 provider wire, 시스템 prompt 및 출력 token은 별개다. 입력 상한 초과나 동일 ID replay 충돌은 운영상 중단한다.
- 유료 WSL 종단 실행은 아직 수행하지 않았다. 사용자 ROOT의 `INTENT/UNCERTAIN` 상태는 자동 복구하지 않는다.

## 설치

ZIP을 `~/ScientificEvolution/` 폴더에서 압축 해제하면
`~/ScientificEvolution/SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_20261030/` 디렉터리가 생성된다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_20261030:$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030:$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

KIT="$PWD/SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_20261030"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
python "$KIT/test_memory_offline.py"
python "$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030/test_frontier_offline.py"
python "$KIT/evolution_memory.py" preflight --experiment "$EXP"
```

`preflight`은 실제 기존 Journal을 읽으면서 `unresolved_model_intents`, `autonomous_meta_check_error`, `operator_stop_requested`를 출력한다. 하나라도 문제라면 `paid_run_ready: false`이고 먼저 원인을 해결해야 한다. 자동으로 `INTENT`를 수리하지 말 것.

## 원본 조회 / 근거 감사 (무료)

```bash
python "$KIT/evolution_memory.py" inspect --experiment "$EXP" \
  --out "$HOME/EVOLUTION_MEMORY_INDEX_20261030.json"

# 정확한 현재 root의 자산 ID를 넣는다.
python "$KIT/evolution_memory.py" inspect --experiment "$EXP" \
  --asset-id A_REDOX_IDENTIFIABILITY_BOUND_002 --depth 3
```

`A_REDOX_IDENTIFIABILITY_BOUND_002`의 ID가 현 CURRENT Population에 실제로 등록되지 않았거나 세대 이관 후 이름이 바뀌었다면, 첫 `inspect`의 `reference_ids` 또는 저장된 자산 부모 참조에서 정확한 ID를 확인한다.

## 재개 (유료, 선택 사항)

이전 연구 ROOT를 지우거나 `bootstrap`하지 않는다. 비용 계정 수준 제한을 따로 설정한다. 먼저 무료 Preflight로 **미확정 호출이나 Meta 오류가 없는지** 검사한다. `operator_stop_requested: true`는 사용자가 설정한 일시정지 표시이므로, 다른 문제가 전혀 없고 재개하기로 직접 결정한 때에만 `STOP_REQUESTED`를 지운 후 **Preflight를 다시 실행**해 `paid_run_ready: true`인지 확인한다.

```bash
rm "$EXP/STOP_REQUESTED"  # 다시 실행하기로 결정했을 때만!
python "$KIT/evolution_memory.py" preflight --experiment "$EXP"
# 위 출력이 paid_run_ready: true 인 것을 확인한 뒤에만 아래 유료 실행
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  python "$KIT/evolution_memory.py" run \
    --experiment "$EXP" --paid --model openai/gpt-5.6-luna \
    --bootstrap-peers 2 --slice-budget 8 \
    --checkpoint-iterations 12 --max-parallel 2 --max-tokens 16000 \
    --science-cpu-seconds 120 --science-wall-seconds 160 \
    --notice-every-segments 3 \
    2>&1 | tee -a "$EXP/EVOLUTION_MEMORY_TRUTH_RUN.log"
)
unset FAKG_RESEARCH_ALLOW_PAID
```

`STOP_REQUESTED`는 운영상 pause이고, 과학적 HOLD가 아니다. 유료 호출/세대 상한은 추가하지 않았다. **과금 제한이 없다면 자동 연구가 오랫동안 계속될 수 있다.**

## 테스트/근거 범위

- 기존 Frontier V1의 오프라인 4개 테스트 통과.
- 새 Memory Truth V1의 오프라인 5개 테스트 통과.
- 실제 업로드된 G13의 SAVED OPP/CTRL 요청을 변환한 결과: `OPP_D00001` 약 398,013 → 74,740자, `CTRL_D00001` 약 404,491 → 81,218자. 전체 문제 ID 125개, claim relation row 9개 유지. 이는 **과거 입력 재생이 아닌 반사실적인 크기 재현 실험**이며 토큰 사용·과금 절감의 실제 측정은 아니다.
- 실제 G13 SYN_01/02의 기록에서 각각 **0 TOOL_RECORDED + standalone literature_research JSON preamble + tool_request null** 조합을 감지. 원본 데이터의 해시·과학 자산은 수정하지 않았다.
- `runtime/` 소스 자체는 이번 테스트 환경에 연결돼 있지 않아, 실제 WSL 통합·유료 실행 안전성은 `preflight` 및 소규모 운영 관찰이 필요하다.
