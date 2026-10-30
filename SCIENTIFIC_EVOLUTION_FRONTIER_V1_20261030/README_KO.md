# Scientific Evolution Frontier V1 — 2026-10-30

## 목적과 경계

기존 `ScientificEvolution`의 12세대 자율 실행에서 드러난 (1) PMI 약 103,525 입력 토큰 및 출력 16,000 토큰 절단, (2) 살아 있는 연구 계보가 문헌 접근/식별성 연구에 수렴하는 경향, (3) 단순한 자산 수 증가를 Level-II 진전으로 오인할 위험을 **단일 연구 입력/포트폴리오 뷰 오버레이**로 다룬다.

기존 E2 Journal, source code, 가설, 저장된 모델 응답, 도구 결과를 수정하지 않는다. 과학적 선택 정책을 강제 변경하지 않고, 모델에 전달하는 *파생 컨텍스트*의 주의 배분을 조정한다. 이것은 기존 코드 전체를 새로 만든 엔진이 아니다. 기존 V4/V3, Autonomous Population, Schema Recovery, Local HOLD Fix가 정상적으로 설치돼 있어야 한다.

- **Scoped scientific state:** 모델은 우선 활성 Work, 입력 부모, 현재 live 결과, 여러 독립 계보·반례·예측을 검토한다. 전체 아카이브는 삭제하지 않고 해시/ID/원본 경로로 추적 가능하게 남긴다. 임의의 최신 N개 잘라내기가 아니라 다중 근거 기준으로 주의 범위를 만든다. 일부 과거 자산이 이번 모델 호출에서 상세하게 검토되지 않았다는 한계를 명시한다.
- **Portfolio-level scientific choice:** Population Steering과 Controller에 활성/보류 Work, 여러 연구 계보의 주장, 부모 대비 새로운 내용, 문헌 접근 실패와 실제 실험 근거의 차이, 강한 Null 검토를 제공한다. 별도 과학적 심사 모델을 늘리지는 않는다. AI는 모든 계보를 보류하거나 한 계보에 집중해도 된다. FUSE와 MUTATE는 필수가 아니다.
- **Level-II dossiers:** 각 후보에 부모 주장, 자산이 주장한 delta, 예측, 가정, 한계, 근거 ID 및 독립 검토 질문을 남긴다. 이 도구가 신규성/물리적 실현 가능성을 자동으로 인증하지는 않는다.
- **Historical retrieval:** INFORMED Worker에 한해 자신의 부모 자산·조상 자산의 원본 `HISTORICAL_AI` 레코드를 `scientific_archive` 요청으로 확인 가능하다. FRESH Worker에서는 거부한다. 원문 조회가 새 실험 결과로 둔갑하지 않도록 분류한다.
- **Durability:** 이전 G11의 `INVALID_PROBLEM_IMPACT_JSON`을 포함한 저장된 호출 응답은 그대로 보존한다. 새로운 분량 제한과 작업 컨텍스트는 다음 호출의 *요청 내용*을 변경해 새 호출 ID를 생성할 수 있다. 확정되지 않은 호출을 덮어쓰거나 같은 호출을 강제 재시도하지 않는다.

### 파일

- `evolution_frontier.py` — `preflight`, `audit`, `run` CLI
- `frontier_runtime.py` — 기존 런타임 위에 *일시적으로* 장착하는 어댑터 (실행 종료 시 원상복구)
- `science_frontier.py` — 과학 지식의 파생 뷰, 출처 추적, 계보 및 후보 dossier
- `test_frontier_offline.py` — 오프라인 Mock 회귀 테스트

## 1. 무료 사전 점검

이 ZIP 폴더를 `~/ScientificEvolution/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030/` 아래에 놓는다. 기존 실행기는 다음 폴더에 이미 있어야 한다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"

OLD_KIT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
NEW_KIT="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"

export PYTHONPATH="$NEW_KIT:$OLD_KIT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

python "$NEW_KIT/test_frontier_offline.py"
python "$NEW_KIT/evolution_frontier.py" preflight --experiment "$EXP"
```

`FRONTIER_V2_PREFLIGHT_OK_NO_PAID`가 나타나면 적용된 후보 범위/문헌 증거 수와 다음 PMI 계열의 대략적인 입력 크기를 확인한다. `scoped_nvt_input_chars`는 **글자/바이트 기반 근사치**이며 토큰 수가 아니다. 반드시 기존 `source_head`와 `paid_calls_executed: 0`을 확인한다.

**주의:** 새로운 입력을 쓰기 때문에 G11에서 마지막으로 저장된 실패 PMI 결과를 삭제하거나 수정하지 않아도 된다. 그러나 유료 실행 성공 여부는 WSL에서 아직 확인되지 않았다. 기존에 UNCERTAIN 상태의 유료 모델 호출이 있으면 진행하지 말고 수동 검토한다.

## 2. 진화 계보·Level-II 검토 패킷 Audit (무료)

```bash
python "$NEW_KIT/evolution_frontier.py" audit \
  --experiment "$EXP" \
  --out "$HOME/SCIENTIFIC_EVOLUTION_FRONTIER_AUDIT_20261030.json"
```

원래 E2 ROOT는 변경하지 않는다. 산출물은 (a) 각 세대별 새 연구 자산과 부모 연결, (b) 전체 과학 상태 중 이번 판단에 전달된 범위와 제외 범위의 출처 해시, (c) 활성 과학 연구 계보, (d) 후보별 Level-II 검토 질문을 포함한다. `--out`은 새 경로여야 하며 기존 파일 덮어쓰기를 거부한다.

이 Audit는 '새로운 인과 기작', '수식 검증 완료', '선행연구 대비 신규성'을 자동으로 인증하지 않는다. 중요한 후보는 해당 ROOT의 실제 Journal 및 도구 실행 원문을 별도로 검사해야 한다.

## 3. 자율 실행 재개 (유료)

기존 `autonomous_population.py`가 아니라 **이번 `evolution_frontier.py run`**을 사용한다. 내부적으로 이전 검증된 실행기를 그대로 재사용한다. 연구의 총 호출 수와 세대 수에는 새로운 과학적 상한을 두지 않는다.

```bash
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES

  python "$NEW_KIT/evolution_frontier.py" run \
    --experiment "$EXP" \
    --paid \
    --model openai/gpt-5.6-luna \
    --bootstrap-peers 2 \
    --slice-budget 8 \
    --checkpoint-iterations 12 \
    --max-parallel 2 \
    --max-tokens 16000 \
    --science-cpu-seconds 120 \
    --science-wall-seconds 160 \
    --notice-every-segments 3 \
    2>&1 | tee -a "$EXP/FRONTIER_V1_RUN.log"
)
unset FAKG_RESEARCH_ALLOW_PAID
```

실제 장기간 무제한 모델 호출에는 많은 비용이 발생할 수 있다. 먼저 무료 preflight 결과를 검토하고 OpenRouter 사용 한도/잔액 알림을 설정한다. 운영상 중단: `touch "$EXP/STOP_REQUESTED"` (현재 호출이 끝난 뒤 확인). 이것은 과학적 HOLD가 아니다.

### 유지되는 중요한 안전 경계

- 이전의 확정된 Controller 결정/모델 응답/도구 receipt를 지우거나 수정하지 않는다.
- 컨텍스트에 나타나지 않는 역사적 자산은 **폐기된 게 아니라 이번 평가의 주의 범위 밖**이다.
- 원본 Journal은 오직 기존 E2 엔진이 새로운 실제 연구/모델 호출을 append한다. 어댑터는 독자적으로 과학 기록을 위조하지 않는다.
- FRESH 연구자에게 부모 역사적 AI 레코드가 노출되지 않는다.
- Level-II 판정은 엄격히 과학적 검토 대상이지 자동 성공 배지가 아니다.
- `SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED` 같은 운영 오류는 여전히 실행 중단 또는 격리 정책을 따른다. 이 패치는 이를 과학적 HOLD로 바꾸지 않는다.

## 4. 현재 검증 수준

`test_frontier_offline.py` Mock에서는 파생 입력의 크기 감소, 최신 결과/활성 부모 보존, 제외 근거 ID의 추적, FRESH 차단, 전역 패치의 원상복구를 검사했다. 실사용 WSL의 실제 장기 Journal에서 동작하는지는 **사용자 preflight와 이어지는 유료 연구 결과로 검증해야 한다.**

이 패키지는 장기 문헌 재탐색 문제에 대한 과학적 정답을 하드코딩하지 않는다. 여러 세대의 새 과학적 변화, 반례 및 실제 선택이 생성되는지 전체 결과를 보고 평가해야 한다.
