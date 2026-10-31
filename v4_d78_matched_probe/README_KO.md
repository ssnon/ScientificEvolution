# V4 D78 Matched Controller Decision Probe

목적: 이미 실행한 12회/12회 paired experiment의 연구 단계 혼입을 분리한다. 원래 D00078 상태를 다시 두 분기로 복제하여, 두 Controller가 **동일 시점에서 한 번씩** 판단하도록 한다. 외부 지정 원문 7개를 제공한 차이만 유지한다.

**중요:** 이것은 연구 스케줄러를 운영자가 한 번 호출하는 결정 실험이다. **Controller의 연구 선택 자체는 모델이 결정하지만, 해당 시점에 호출하기로 선택한 주체는 운영자다.** 따라서 자율적 다음 연구 타이밍 또는 다세대 성과를 실증하지 않는다.

## 전제

- GitHub `ssnon/ScientificEvolution`의 기존 V4 런타임을 그대로 사용한다.
- 원본 ROOT는 읽기 전용이다. 새로운 두 분기만 append-only로 추가한다.
- 기록된 역사적 `UNCERTAIN`은 재발행하지 않고, 추가 UNKNOWN/PENDING이면 중단한다.
- FRESH Worker는 실행하지 않는다. 기존 FRESH 입력과 지난 작업 기록을 변경하지 않는다.
- 새 가설의 신규성이나 과학적 완성은 이 도구가 인정하지 않는다.

## 실행

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
KIT="$PWD/SCIENTIFIC_V4_OPERATOR_EVIDENCE_PAIR_20261029"
PAIR="$HOME/ScientificEvolution_runs/D78_MATCHED_DECISION_20261029"
mkdir -p "$PAIR"
python "$KIT/prepare_pair.py" \
  --source-root "$HOME/ScientificEvolution_runs/V4_REPO_SMOKE_20261029" \
  --packet "$HOME/PMC4129422_OPERATOR_EVIDENCE_PACKET_20261029.json" \
  --out-parent "$PAIR"

PROBE="/path/to/v4_d78_matched_probe/matched_controller_probe.py"
for C in CONTROL OPERATOR_EVIDENCE; do
  python "$PROBE" --preflight \
    --root "$PAIR/V4_D78_${C}_20261029"
done
```

사전 검증이 통과한 뒤 유료 호출을 실행한다. **분기별 신규 모델 호출 최대 6회**이며, 정상적인 첫 Controller 판단은 일반적으로 2–4회에 완료될 수 있으나 보장하지 않는다.

```bash
for C in CONTROL OPERATOR_EVIDENCE; do
  (
    export FAKG_RESEARCH_ALLOW_PAID=YES
    python "$PROBE" --paid \
      --root "$PAIR/V4_D78_${C}_20261029" \
      --out "$HOME/V4_D78_MATCHED_${C}_DECISION_20261029.json" \
      --model openai/gpt-5.6-luna \
      --max-new-calls 6 --max-tokens 16000
  ) 2>&1 | tee "$HOME/V4_D78_MATCHED_${C}_DECISION_20261029.log"
done
unset FAKG_RESEARCH_ALLOW_PAID

tar -czf "$HOME/V4_D78_MATCHED_DECISION_RESULTS_20261029.tar.gz" -C "$HOME" \
  V4_D78_MATCHED_CONTROL_DECISION_20261029.json \
  V4_D78_MATCHED_OPERATOR_EVIDENCE_DECISION_20261029.json \
  V4_D78_MATCHED_CONTROL_DECISION_20261029.log \
  V4_D78_MATCHED_OPERATOR_EVIDENCE_DECISION_20261029.log
```

## 해석

1. D00079 Controller가 선택한 Work의 차이 확인. 새 Work가 없어도 합리적 결정일 수 있다.
2. `SRC_PRIOR_PMC4129422_*` 인용 여부, novelty relation의 의미 있는 변화와 PMI validation quarantine 확인.
3. 별도의 기존 진행 분기에서는 Evidence 조건의 INFORMED 연구를 계속할 수 있다. 다만 이 probe의 결과를 *자율적 실행 타이밍의 검증*이라고 주장해서는 안 된다.
4. 하나의 확률적 반복은 인과 효과 추정이 아니다. 최초의 12회 실행 비교와 합쳐 탐색적 근거로만 판단한다.

실행 중 provider unknown outcome 발생 시 자동 재시도하지 않는다. 새 ROOT에서만 다음 대응을 논의한다.

## 추가: 기존 Evidence INFORMED 연구의 실제 내용 추출 (무료·읽기 전용)

이 단계는 새 matched probe와 독립적이다. **이미 수행된** Evidence Work의 모델 응답, 도구 실행 증빙, 자산을 그대로 묶어 과학적 검토에 사용한다.

```bash
python /path/to/v4_d78_matched_probe/extract_informed_work.py \
  --root "$HOME/ScientificEvolution_runs/V4_D78_OPERATOR_EVIDENCE_20261029" \
  --work-id W_decompose_gap_molecular_forward_models_001 \
  --out "$HOME/V4_D78_EVIDENCE_INFORMED_WORK_EXACT_20261029.json"
```

이 파일까지 전달하면 새로운 반례와 Jacobian 주장이 실제로 어떤 수식, 계산 및 도구 결과에 근거했는지 독립적으로 평가할 수 있다.
