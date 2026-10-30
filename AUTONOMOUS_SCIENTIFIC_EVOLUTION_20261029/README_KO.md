# Autonomous Scientific Evolution — Run Until Scientific Disposition

## 목적과 범위

G0→SYN A/B→Population G1/G2→Persistent CYCLE_000까지의 연구 결과를 출발점으로, **주기 수/호출 수를 연구 종료 조건으로 사용하지 않고** AI가 연구 계속·합성으로 넘김·다음 독립 세대·전체 연구 종료를 판단하도록 하는 V1 실행기입니다.

기존 `ScientificEvolution`의 `e2core`, `scientific_problem_evolution`, V3/V4 runtime, append-only Journal 및 문헌/계산 도구를 그대로 사용합니다. 이 패키지는 기존 런타임을 수정하지 않습니다. 과학적 종료는 모델의 **검증되지 않은 판단**이며 P0 해결이나 Level II 신규성을 자동 인증하지 않습니다. 모델이 계속 `CONTINUE`를 선택할 경우 실행 시간과 API 비용은 제한 없이 증가할 수 있습니다.

이 버전은 중앙 **Population 조정자**를 통한 실제 AI 선택이며, 각 주기 시작의 독립 SYN 수는 운영 초기값(기본 2개)입니다. AI는 추가 SYN 생성(`ADD_INDEPENDENT_PEER`)을 선택할 수 있지만 전면적으로 자유로운 population size 최적화는 아닙니다. 모든 판단은 별도 `AUTONOMOUS_META` E2 Journal에 실제 모델 호출로 보존됩니다. 한 모델의 최초 종료 제안은 독립적인 회의론적 검토와 최종 판정 호출을 거쳐야 전역 종료가 됩니다.

## 기존 연구 보존 — 권장 경로

구 패키지의 `PERSISTENT_POPULATION_V1_20261029/CYCLE_000/POPULATION`을 *읽기 전용 출발점*으로 사용하고 새 실험 ROOT를 만듭니다. 기존 Journal을 덮어쓰거나 `CYCLE_000`의 상태를 변경하지 않습니다.

ZIP을 `~/ScientificEvolution/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029` 폴더로 압축 해제했다고 가정합니다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

KIT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
OLD="$HOME/ScientificEvolution_runs/PERSISTENT_POPULATION_V1_20261029/CYCLE_000/POPULATION"
NEXT="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"

python "$KIT/test_offline.py"
python "$KIT/test_autonomous_offline.py"
python "$KIT/autonomous_population.py" bootstrap \
  --source-root "$OLD" --out "$NEXT"
python "$KIT/autonomous_population.py" preflight \
  --experiment "$NEXT"
```

이미 새 실험을 `persistent_population.py init`으로 생성했다면, `bootstrap` 대신 `python "$KIT/autonomous_population.py" init --experiment "$NEXT"`로 메타 조정자만 생성할 수 있습니다. 같은 메타 ROOT에 `init`을 두 번 실행하지 마세요.

### 실제 유료 자동 연구 — 총 호출·주기 수 상한 없음

최초에는 **tmux**에서 실행하는 것을 권장합니다. 충분히 긴 시험에서는 API 비용이 매우 커질 수 있으니 OpenRouter/계정 수준의 **별도 사용량 한도 또는 알림**을 설정하는 것을 권합니다. 아래 코드는 자체적으로 총 과금량을 제한하지 않습니다.

```bash
tmux new -s ai_scientist_auto
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
KIT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
NEXT="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"

(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  python "$KIT/autonomous_population.py" run \
    --experiment "$NEXT" \
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
    2>&1 | tee -a "$NEXT/AUTONOMOUS_RUN.log"
)
unset FAKG_RESEARCH_ALLOW_PAID
```

`--slice-budget 8`은 개별 E2 연구 호출을 8개씩 기록·검사하는 *내부 트랜잭션 경계*입니다. 8회 뒤에 연구를 끝내거나 세대를 강제하지 않습니다. 매 구간 이후 Population 조정자가 유료 모델 호출로 실제 연구 지속/전달 여부를 판단합니다. `--max-tokens`는 **개별 응답**의 최대 토큰 수이며 총 과학 작업량 상한이 아닙니다.

`tmux` 분리: `Ctrl+B` 다음 `D`. 다시 접속: `tmux attach -t ai_scientist_auto`.

### 안전한 중단과 재개

다른 터미널에서:

```bash
touch "$NEXT/STOP_REQUESTED"
```

실행기는 **현재 진행 중인 외부 호출이 반환된 후**, 다음 제어 경계에서 이 파일을 확인하고 **운영상 PAUSE**로 빠져나옵니다. 과학적 HOLD로 기록하지 않습니다. 즉시 취소하거나 이미 진행된 호출 비용을 취소할 수는 없습니다.

재개하려면 파일을 지우고 같은 `run` 명령을 다시 실행합니다.

```bash
rm "$NEXT/STOP_REQUESTED"
```

`Ctrl+C`로 네트워크 중간의 요청을 강제로 끊으면 응답 수신 여부가 불확실한 `MODEL_CALL_UNCERTAIN`이 남을 수 있으니, 가능하면 STOP 파일을 사용하세요. `UNSAVED_MODEL_CALL`, `PROVIDER_UNKNOWN_OUTCOME`, 코드 불일치, Journal 무결성 오류는 **자동 재시도하지 않고 운영상 중단**해야 합니다.

### 상태/Audit — 무료

```bash
unset FAKG_RESEARCH_ALLOW_PAID
python "$KIT/autonomous_population.py" status \
  --experiment "$NEXT" \
  --out "$NEXT/AUTONOMOUS_STATUS.json"
python "$KIT/autonomous_population.py" preflight \
  --experiment "$NEXT"
```

상태에는 완료된 주기, 최신 단계, Population 조정자의 각 판단과 근거, 실제 연구 ROOT 및 메타 ROOT의 누적 유료 호출 수, 최종 종료 판정 여부가 포함됩니다. 단, 마지막 데이터만으로 물리적 타당성·신규성을 인증하지 않습니다.

결과를 공유할 때는 `AUTONOMOUS_STATUS.json`, `AUTONOMOUS_RUN.log`, 관심 있는 `CYCLE_xxx/cycle.json`과 해당 Population의 새 자산 내용을 포함한 감사자료를 주시면 됩니다. Journal의 호출 원문에는 유료 모델 응답이나 연구 중의 비공개 내용이 포함될 수 있어 외부 공개 전 확인하세요.

## 독립 상태 구분

| 상태 | 의미 |
|---|---|
| `PEER: CONTINUE_RESEARCH` | 독립 연구 구간을 계속 실행 |
| `PEER: YIELD_TO_POPULATION` | 현재 결과를 모아 Population SYN으로 인계. ACTIVE Work를 DONE으로 위조하지 않음 |
| `PEER: ADD_INDEPENDENT_PEER` | AI가 동일 원본에서 독립 SYN 분기 추가, 요청자는 인계 |
| `POPULATION: CONTINUE_RESEARCH` | 동일 Population ROOT의 연구를 계속 실행 |
| `POPULATION: NEXT_GENERATION` | 이전 연구 결과와 역사적 상태를 다음 독립 세대에 이관. 새 자산 수가 0이어도 과학적으로 정당화되면 선택 가능 |
| `POPULATION: SCIENTIFIC_HOLD` | 전역 종료 **제안**. 비판·최종 판정 전에는 종료 아님 |
| `POPULATION: REVIEW_WORTHY_CANDIDATE` | 인간 검토 가치 후보 확보 **제안**. 실제 검토/실험 인증 아님 |
| `POPULATION: SCOPED_NEGATIVE` | 한정된 부정적 결론 **제안**. P0 전체 불가능의 증명 아님 |
| `FINAL: CONFIRM_TERMINAL` | 독립 검토 후 최종 모델이 전역 종료 선택. Journal에 과학적 판단으로 보존 |
| `STOP_REQUESTED`, 미확정 유료 호출, 코드 오류 | **운영상 중단**, 과학적 종료/부정 결과 아님 |

## 과학적/실행 한계

1. 자동화가 실제 물리적 신규성이나 Level II를 보증하지는 않습니다. 실험/문헌 증거와 강한 Null을 독립 검토해야 합니다.
2. 이전 세대의 발표 자산과 보류·미완료 Work는 새 세대로 *역사적 미검증 기록*으로 전달됩니다. 이전 ACTIVE Worker의 프로세스 상태를 그대로 영구 복원하지는 않습니다. 그 Work를 다시 수행할지는 새 모델이 판단합니다.
3. 수학적 결과만 계속 재도출하거나 문헌 검색만 반복하는 과학적 정체가 발생해도 **코드가 임의 횟수에서 STOP을 강제하지는 않습니다**. 모델에게 이전 주기와의 차이를 보여주고 스스로 정체·종료·전환을 판단하게 합니다. 따라서 실제 종료는 보장되지 않습니다.
4. 최종 비판과 판정은 **별도 저장된 LLM 호출**이지만 같은 모델 ID를 사용할 수 있습니다. 통계적으로 독립된 외부 연구실의 검토와 같지 않습니다.
5. 모델 호출이 반환된 뒤에도 Journal 이벤트 저장 중 운영장애가 날 수 있습니다. 재시작 시 저장된 호출은 재사용하지만, 불확실한 호출은 자동 재시도하지 않습니다.
6. 새 실행기 자체는 오프라인 mock으로 검증했으며, 실제 WSL/유료 OpenRouter 다세대 통합 실행은 아직 검증되지 않았습니다. 초기 preflight와 첫 로그를 확인한 후 지속 실행하는 것이 안전합니다.
