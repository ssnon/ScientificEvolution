# V4 D00078 Operator-Guided Evidence Pair (2026-10-29)

## 목적
동일한 1870-event Journal 시점에서 CONTROL과 OPERATOR_EVIDENCE 두 조건을 복제한다. Evidence 조건에만 **사용자가 실행한 공개 논문 원문 검색의 정확한 문맥 발췌**를 등록한다. 새 논문을 AI가 스스로 발견했다고 주장하지 않는다. 가설 발전을 강요하지 않으며 기존 P0, FRESH, 역사적 UNKNOWN의 의미를 보존한다.

- `build_operator_packet.py`: 이미 생성된 `~/PMC4129422_PUBLIC_SOURCE_AUDIT_20261029.json`의 Europe PMC XML 매치 일곱 개를 원문 발췌 packet으로 전환. 새로운 네트워크/LLM 호출 없음. 각 원문은 제한된 context window임.
- `prepare_pair.py`: 기존 V4에 있는 단 하나의 역사적 UNCERTAIN만 기존 공식 복구 영수증으로 감사하고, 원본 ROOT를 lock+검증+복제해 두 fork를 생성. `SRC_PRIOR_...` 등록은 EVIDENCE fork에서만 수행. FRESH Worker의 실제 input payload는 두 fork에서 바이트 비교.
- `compare_pair.py`: 모델 실행 후 실제 Journal의 새 Work/Asset/문제/Controller를 읽기 전용으로 비교. 새 Work 수가 Level II 성공을 뜻하지 않음.

### 명령: 셸에서

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

KIT="$HOME/SCIENTIFIC_V4_OPERATOR_EVIDENCE_PAIR_20261029"  # 압축 해제 위치로 수정
python "$KIT/build_operator_packet.py" \
  --audit "$HOME/PMC4129422_PUBLIC_SOURCE_AUDIT_20261029.json" \
  --out "$HOME/PMC4129422_OPERATOR_EVIDENCE_PACKET_20261029.json"

python "$KIT/prepare_pair.py" \
  --source-root "$HOME/ScientificEvolution_runs/V4_REPO_SMOKE_20261029" \
  --packet "$HOME/PMC4129422_OPERATOR_EVIDENCE_PACKET_20261029.json" \
  --out-parent "$HOME/ScientificEvolution_runs"
```

두 fork가 생성되면 원본보다 이벤트 수가 많아지고 Evidence fork에만 operator source 7개가 추가된다. **두 fork 중 어느 쪽도 과학적 성과가 이미 발생했다는 의미가 아니다.**

### 별도 실행: 연구 호출은 사용자가 선택해 실행

사전검사:

```bash
for C in CONTROL OPERATOR_EVIDENCE; do
  python runtime/scientific_v4_clean_baseline.py inspect \
    --root "$HOME/ScientificEvolution_runs/V4_D78_${C}_20261029"
done
```

예산을 제한한 실제 실행(선택):

```bash
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  trap 'unset FAKG_RESEARCH_ALLOW_PAID' EXIT
  python runtime/scientific_v4_clean_baseline.py run \
    --root "$HOME/ScientificEvolution_runs/V4_D78_CONTROL_20261029" \
    --paid --model openai/gpt-5.6-luna \
    --slice-budget 12 --max-total-new-calls 12 \
    --checkpoint-iterations 12 --max-parallel 1 --max-tokens 16000 \
    | tee "$HOME/V4_D78_CONTROL_FIRST_RUN.log"
)
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  trap 'unset FAKG_RESEARCH_ALLOW_PAID' EXIT
  python runtime/scientific_v4_clean_baseline.py run \
    --root "$HOME/ScientificEvolution_runs/V4_D78_OPERATOR_EVIDENCE_20261029" \
    --paid --model openai/gpt-5.6-luna \
    --slice-budget 12 --max-total-new-calls 12 \
    --checkpoint-iterations 12 --max-parallel 1 --max-tokens 16000 \
    | tee "$HOME/V4_D78_OPERATOR_EVIDENCE_FIRST_RUN.log"
)
```

이어 실제 행동 비교:

```bash
python "$KIT/compare_pair.py" \
 --control "$HOME/ScientificEvolution_runs/V4_D78_CONTROL_20261029" \
 --evidence "$HOME/ScientificEvolution_runs/V4_D78_OPERATOR_EVIDENCE_20261029" \
 --out "$HOME/V4_D78_OPERATOR_EVIDENCE_PAIR_RESULT_20261029.json"
```

**주의**
- 본 자료는 준비용이며 사용자 로컬 ROOT에서 end-to-end로 시험하지 않았다. PIN 검증/문서화는 로컬에서 재확인해야 한다.
- 하나의 RUN에서 변화가 없다고 증거 무효를 의미하지 않는다. 양 조건에서 기존 문헌 정보가 이미 중복되었을 수도 있다.
- 임시 실험은 V4 코드 또는 ROOT의 원본에 쓰기를 수행해서는 안 된다.
- 기존 `ingest_external_evidence()`는 모든 호출 SAVED를 요구하므로 역사적 UNCERTAIN이 있는 ROOT에 그대로 적용할 수 없다. 본 kit은 그 호출의 기존 공식 감사 영수증을 보존한 **별도의 immutable branch**에만 source를 append한다.
- 원문 7개는 본문 전체가 아닌 자동 탐색한 **문자열 주변 문맥**이다. 각 논문의 완전한 Figure/SI 분석이라고 과장하면 안 된다.
