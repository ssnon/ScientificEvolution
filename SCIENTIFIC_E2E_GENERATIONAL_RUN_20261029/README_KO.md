# Scientific Evolution: 첫 다연구자–세대 계승 통합 실행

## 목적

최종 목표는 범용 AI Scientist이며, SERS는 첫 도메인이다. 이 패키지는 새로운 과학 정책이나 모델을 만들지 않고 현재 `ssnon/ScientificEvolution` 저장소의 기존 실행기를 연결한다.

1. 같은 원래 문제 P0만 가진 **독립 FRESH ROOT 3개**를 생성한다. 서로의 AI 가설·요약·근거를 보지 않고 자율 연구한다.
2. 각 ROOT의 실제 모델 실행, 도구 결과, 가설·반례·부정 결과를 **원본 Journal을 변형하지 않고** 새 SYN ROOT에 이관한다. 개별 원본 ROOT가 HOLD하여도 그 상태를 기록한다.
3. SYN은 기존 `scientific_closed_loop_v3` + `scientific_research_readiness_v4`의 *동일한* 과학 판단 계층(NVT → PMI → Opportunity → Controller)을 사용한다. 새 Work를 만들도록 강제하지 않는다.
4. SYN이 INFORMED Work를 생성하면 기존 실행기가 그것을 실제로 실행하며, 새로운 자산이 발표되면 Controller가 이를 다시 검토한다. 별도의 임의 세대 카운터로 연구를 종결하지 않는다.
5. 읽기 전용 감사 파일을 생성하여 실질적인 부모 계승·실행된 도구·재평가 결정을 확인한다.

**이번 실행의 엄격한 한계:** 초기 FRESH 연구 집단의 크기 3은 운영자가 정한 실험 설계이며 AI가 선택한 수가 아니다. 이 실행은 기존 가설 123개를 G0 연구자에게 주입하지 않는다. P0 텍스트만 원본 V4에서 가져온다. 과거 V4/P6L/M32 자산은 원래 ROOT에 그대로 남는다. SYN은 **이번 신규 FRESH 결과**를 계승한다. 통합 SYN에서 생성한 새 FRESH Work는 informed Controller가 질문을 작성할 수 있어, 그것까지 독립적·완전 무정보 FRESH라고 부르지 말아야 한다. 이 패키지는 모델들이 알아서 멋진 가설을 만들거나 Level II가 달성됨을 보증하지 않는다.

## 설치

ZIP을 `~/ScientificEvolution`에 압축 해제한 뒤:

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
KIT="$PWD/SCIENTIFIC_E2E_GENERATIONAL_RUN_20261029"
EXP="$HOME/ScientificEvolution_runs/SCIENTIFIC_E2E_GEN_FIRST_20261029"
python "$KIT/generational_run.py" --help
```

실제 소스는 수정·덮어쓰지 않는다. Git working tree를 변경하지 않는다. 기존 V4 ROOT도 읽기만 한다.

## 1. 독립 FRESH 집단 구성 — 무료

```bash
python "$KIT/generational_run.py" init \
  --source-root "$HOME/ScientificEvolution_runs/V4_REPO_SMOKE_20261029" \
  --out "$EXP" \
  --cohorts 3

python "$KIT/generational_run.py" preflight --experiment "$EXP"
```

`source-root`는 **P0 문자열만** 읽는다. 코호트의 seed 가설, 논문, 이전 AI 평가를 읽지 않는다. 기존 `experiment.json`이나 ROOT가 있으면 덮어쓰지 않고 중단한다.

## 2. 독립 FRESH 연구 — 유료, 각 ROOT당 최대 36 신규 호출

```bash
for I in 1 2 3; do
  echo "===== FRESH $I ====="
  (
    set -o pipefail
    export FAKG_RESEARCH_ALLOW_PAID=YES
    python "$KIT/generational_run.py" run-fresh \
      --experiment "$EXP" --index "$I" \
      --paid --model openai/gpt-5.6-luna \
      --max-new-calls 36 --checkpoint-iterations 12 \
      --max-parallel 2 --max-tokens 16000 \
      --science-cpu-seconds 120 --science-wall-seconds 160 \
      2>&1 | tee "$EXP/FRESH_${I}_RUN.log"
  ) || break
done
unset FAKG_RESEARCH_ALLOW_PAID
```

이는 **최대** 108회 추가 모델 호출의 비용 승인이 필요하다는 뜻이다. 36은 개별 연구의 STEP 수나 세대 수가 아니다. 중단 시 같은 명령으로 이어갈 수 있으나, `MODEL_CALL_UNCERTAIN`은 자동 재시도하지 않는다. 최초에는 12회씩 더 작은 비용으로 실행한 뒤 재실행해도 된다. 다만 너무 짧은 실행은 SYN이 평가할 과학 자산을 충분히 생성하지 못할 수 있다.

`run-fresh`는 원래 E2 `long_campaign.drive()`를 사용한다. FRESH 연구자가 실제 발견·요청한 도구만 실행한다. 인간이 S02/S04/charge 등의 질문을 배정하지 않는다.

## 3. 전체 FRESH 결과 통합 — 무료

```bash
python "$KIT/generational_run.py" integrate --experiment "$EXP"
python "$KIT/generational_run.py" preflight --experiment "$EXP"
```

예상 결과: `SYN_INTEGRATED` ROOT, `integration.json`.

- `transfer_isolated_fresh()`로 모든 실행된 FRESH 과학 자산을 이관한다. 암묵적 상위 후보 필터는 없다.
- `FEEDBACK_PREPARE_MANIFEST.json`에 **모든 이관 자산**을 기록해 기존 NVT 평가가 이를 실제 대상으로 삼도록 한다.
- 실제 원문 반환이 입증된 direct text/figure/method/supplement tool source만 `SRC_INHERITED_TOOL_*`로 복사하여 원본 TOOL 결과와 SHA를 기록한다. 단순 검색 메타데이터, 실패한 조회를 직접 원문 증거로 승격하지 않는다. 그 기록들은 FRESH 원본 Journal에 남는다.
- 각 코호트의 종료·HOLD 여부, 실행된 출처 원본 해시, 이관 자산 목록을 `SRC_COHORT_RECEIPT_*`로 남긴다. 이는 역사적 AI 작업 기록이지 새로운 과학 발견이 아니다.
- 원래 FRESH ROOT는 변형하지 않는다. 재통합은 새로운 EXP 이름으로 해야 한다.

**주의:** 한 코호트가 모델 호출에 성공했더라도 FRESH 과학 작업을 수행하지 않았다면, 해당 코호트에 가상의 과학 결과를 넣지 않고 `integrate`를 중단한다. 종료한 코호트의 모델 판단과 연구 상태가 원본에서 확인되면 그대로 보존한다.

## 4. 자율 SYN + 실제 후속 연구 — 유료

```bash
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  python "$KIT/generational_run.py" run-syn \
    --experiment "$EXP" \
    --paid --model openai/gpt-5.6-luna \
    --max-new-calls 72 --slice-budget 12 \
    --checkpoint-iterations 12 --max-parallel 2 \
    --max-tokens 16000 \
    --science-cpu-seconds 120 --science-wall-seconds 160 \
    2>&1 | tee "$EXP/SYN_RUN.log"
)
unset FAKG_RESEARCH_ALLOW_PAID
```

72는 이 실행의 신규 유료 호출 상한이다. SYN에 FUSE/MUTATE 또는 추가 Worker 생성 의무는 없다. 과학적 HOLD, 오류, 운영상 호출 예산 종료는 서로 다르게 기록된다. 새로운 계산이 필요한지, 신규 가설을 내야 하는지는 AI가 판단한다. 필요하면 `run-syn`을 같은 ROOT에서 추가 호출 예산으로 이어갈 수 있다(과학적 종료 상태가 아니며 미해결 호출이 없어야 함).

**작동 원리:** 새 SYN ROOT는 V4 역사적 `NVT` uncertain/reissue 사건이 없으므로, 특정 과거 fork에만 적용되는 `v3.run()`의 역사적 receipt 검증을 사용하지 않는다. 대신 **기존 V4 `runtime()` + V3 `v3_runtime()` + 기존 `spe.run_feedback()`을 그대로 연결**해 연구를 실행한다. 런타임의 source-code guard는 그대로 호출한다.

## 5. 세대 계보 및 실제 결과 Audit — 무료

```bash
python "$KIT/generational_run.py" audit \
  --experiment "$EXP" \
  --out "$EXP/SCIENTIFIC_E2E_AUDIT.json"

tar -czf "$HOME/SCIENTIFIC_E2E_GEN_FIRST_RESULTS_20261029.tar.gz" \
  -C "$HOME/ScientificEvolution_runs" \
  SCIENTIFIC_E2E_GEN_FIRST_20261029/experiment.json \
  SCIENTIFIC_E2E_GEN_FIRST_20261029/integration.json \
  SCIENTIFIC_E2E_GEN_FIRST_20261029/SCIENTIFIC_E2E_AUDIT.json \
  SCIENTIFIC_E2E_GEN_FIRST_20261029/FRESH_1_RUN.log \
  SCIENTIFIC_E2E_GEN_FIRST_20261029/FRESH_2_RUN.log \
  SCIENTIFIC_E2E_GEN_FIRST_20261029/FRESH_3_RUN.log \
  SCIENTIFIC_E2E_GEN_FIRST_20261029/SYN_RUN.log
```

우선 이 압축본을 전달하면 과학적 결과를 검토한다. **완전한 과학적 검산**에 Journal 원본 또는 selected blob이 추가로 필요하면, 실제 후속 분석에서 최소 원본만 해시와 함께 추출한다. 민감한 API 키는 전달하지 않는다.

## 판단 기준

코드/실행 성공과 과학 성공을 분리한다.

- **구조적 성공:** 독립적 실제 FRESH 모델 실행, 원본 FRESH 입력 검증, 원본 출처 보존, 과학 SYN 결정, 실제 INFORMED Work 및 새 science asset, 그 이후 다시 Controller 판단.
- **과학적 진전:** 부모에 없던 인과·물리·예측·범위·반례의 변화와 도구 근거. 단순한 문구 변경, 자산 수, 수식의 존재는 성과 아님.
- **Level II:** 신규성 관련 범위와 강한 Null을 명시하고, 물리적으로 방어 가능한 새로운 기작과 독립 검토 가능한 구별 예측 및 반증 설계. **추후 독립 과학 검토가 필요하다.**
- **정당한 HOLD:** 실제로 종료한 연구 집단이 더 진행할 가치가 없다고 판단하면 기록한다. 운영 종료나 예산 도달을 불가능 판정으로 바꾸지 않는다.

## 검증 범위

이 패키지는 Python 문법 검사·CLI 도움말·정적 불변 조건 테스트를 수행했다. **사용자의 실제 WSL `ScientificEvolution` 저장소와 유료 OpenRouter 모델에 대한 통합 실행은 아직 검증되지 않았다.** 특히 `long_campaign.transfer_isolated_fresh`의 도구 원문 반환 스키마가 설치된 최신 소스와 일치하는지는 `integrate`와 `preflight` 실행에서 확인해야 한다. 실패하면 가짜 실행 결과를 만들지 말고 해당 오류와 Journal을 전달한다.
