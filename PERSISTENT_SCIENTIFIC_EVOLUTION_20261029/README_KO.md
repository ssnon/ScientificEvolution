# Persistent Population Scientific Evolution V1

## 목표

기존 ScientificEvolution Journal/V3-V4 NVT·PMI·OPP·Controller와 실제 연구 Worker를 재사용해, **여러 독립 연구 집단의 판단 → Population-level 과학적 SYN → 실제 연구 → 후속 세대의 독립 판단**을 수동 G0/G1/G2 분기 없이 반복한다. 특정 가설, 기작, FUSE, 생성 Work 수, positive result를 강제하지 않는다. P0는 원문 그대로 유지된다. 이 패키지는 운영 연결이며 물리적 신규성이나 Level II 달성을 인증하지 않는다.

## 포함 파일

- `persistent_population.py`: 연속 Population 실행기 (init / preflight / run / status)
- `population_run.py`: 이전 실험에서 검증한 독립 peer 연구 이관/근거 원형 기록
- `generational_run.py`: 기존 V3/V4 long-run 과학 엔진 호출
- `population_resume.py`: E2 역사적 peer-asset `ref` 호환성 (이번 패키지에서 peer-decision 기록도 처리)
- `test_offline.py`: 독립적인 Fake Journal 계약 테스트. **실제 사용자 WSL의 runtime end-to-end 검증은 아님.**

## 이전 연구를 그대로 재사용하는 안전한 첫 실험

압축 해제된 전체 폴더가 `~/ScientificEvolution/PERSISTENT_SCIENTIFIC_EVOLUTION_20261029`에 있게 한다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

KIT="$PWD/PERSISTENT_SCIENTIFIC_EVOLUTION_20261029"
POP="$HOME/ScientificEvolution_runs/SCIENTIFIC_POPULATION_FIRST_20261029"
SOURCE="$POP/G2_SYN"
NEXT="$HOME/ScientificEvolution_runs/PERSISTENT_POPULATION_V1_20261029"

python "$KIT/test_offline.py"
python "$KIT/persistent_population.py" init \
  --source-root "$SOURCE" --out "$NEXT"
python "$KIT/persistent_population.py" preflight --experiment "$NEXT"
```

`SOURCE`는 이전 G2 실제 Journal ROOT여야 한다. `ls "$SOURCE/manifest.json"`이 실패하면 경로를 확인하고 처음부터 별도 새 ROOT를 만들어야 한다. `init`은 이미 존재하는 목적지를 덮어쓰지 않는다. 기존 G0/SYN/G1/G2 원본은 수정하지 않는다. 유료 API는 `init`, `preflight`, `status`, `test_offline.py`에서 호출하지 않는다.

### 첫 실제 Population 주기 (유료, 호출 상한 명시)

```bash
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  python "$KIT/persistent_population.py" run \
    --experiment "$NEXT" --paid \
    --model openai/gpt-5.6-luna \
    --max-cycles 1 --peer-count 2 \
    --peer-calls 16 --population-calls 24 \
    --max-total-new-calls 56 \
    --slice-budget 8 --checkpoint-iterations 12 \
    --max-parallel 2 --max-tokens 16000 \
    --science-cpu-seconds 120 --science-wall-seconds 160 \
    2>&1 | tee "$NEXT/PERSISTENT_FIRST_RUN.log"
)
unset FAKG_RESEARCH_ALLOW_PAID

python "$KIT/persistent_population.py" status \
  --experiment "$NEXT" --out "$NEXT/PERSISTENT_STATUS.json"
```

**비용 경계:** `--max-total-new-calls 56`은 이번 `run` 명령 전체에서 새로 수행할 외부 유료 호출의 상한이며, peer 당 16 + population 24와 일치한다. 다음 `run`을 새로 실행하면 새로운 유료 승인과 새 상한을 적용한다. `--peer-count`는 독립 판단 샘플 수를 제한하는 **운영 옵션**이지, AI에게 반드시 그 수만큼 과학적 Work를 만들라는 명령이 아니다.

### 자동 후속 주기

첫 주기 완료 후, 과학적으로 종료한 상태가 아니고 새 자산이 생성되었다면 다음 명령은 **수동 prepare-G2 없이** 다음 독립 peer 연구와 Population SYN을 만든다. 기존 주기의 완료 기록은 재호출하지 않는다.

```bash
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES
  python "$KIT/persistent_population.py" run \
    --experiment "$NEXT" --paid \
    --model openai/gpt-5.6-luna \
    --max-cycles 2 --peer-count 2 \
    --peer-calls 16 --population-calls 24 \
    --max-total-new-calls 112 \
    --slice-budget 8 --checkpoint-iterations 12 \
    --max-parallel 2 --max-tokens 16000 \
    --science-cpu-seconds 120 --science-wall-seconds 160 \
    2>&1 | tee "$NEXT/PERSISTENT_CONTINUATION.log"
)
unset FAKG_RESEARCH_ALLOW_PAID
```

`--max-cycles 2`는 이 명령에서 완주할 최대 주기 수이지 물리적인 세대 수나 과학적 성과 수가 아니다. peer가 과학적으로 HOLD해도 다른 peer의 탐색은 계속할 수 있다. Population Controller가 정당한 HOLD/리뷰 후보/부분 부정 결과를 선언하면 다음 주기를 강제 생성하지 않는다. 호출 예산 소진은 과학적 HOLD가 아니다.

## 재개와 오류

- 매 ROOT의 모델 호출은 기존 append-only Journal에 저장된다. 같은 명령을 다시 호출하면 **현재 저장된 외부 호출 수**와 운영 예산을 대조한다. 이미 완료한 peer/Population 단계는 재실행하지 않는다.
- `OPERATIONAL_ERROR_NOT_SCIENTIFIC_HOLD`는 과학적 연구 종료가 아니다. 미확정 `INTENT`/`UNCERTAIN` 유료 호출은 자동 재시도하지 않는다.
- `CYCLE_000/cycle.json`에 `PEERS`, `COMBINE`, `POPULATION`, `COMPLETE` 진행 단계가 기록된다. 동일 실험 폴더를 삭제하거나 새로운 init/combine을 중복 실행하지 않는다.
- 세대 경계에서 ACTIVE/QUEUED/DEFERRED Work의 **연구 질문과 미완료 상태는 기록으로 보존**하지만, 다음 ROOT에 이미 실행 중인 Work처럼 복제하지는 않는다. 다음 연구자는 그 상태와 산출물을 보고 연속 연구 여부를 새로 선택한다. 따라서 정확히는 '지속 연구 자산과 지속적인 과학적 선택을 갖는 Population'이지 동일 Worker 프로세스가 무중단으로 이어지는 것은 아니다.
- 기존 Journal의 `SRC_INHERITED_TOOL_...` 과거 문헌 근거와 새 실제 TOOL_RESULT의 출처를 구별한다. 이전 원문을 새로 읽었다고 기록하지 않는다. SOURCE가 외부 경로로 연결된 경우에는 원본 ROOT들을 계속 보존한다.
- 세대를 다시 만들 때 G0 및 이전 peer 자산의 실제 부모 관계를 재매핑한다. 향후 Audit는 부모 ID 존재뿐 아니라 원래 ROOT 및 직전 세대에서 온 후손을 보여준다.

## 결과 제출

```bash
python "$KIT/persistent_population.py" preflight --experiment "$NEXT"
python "$KIT/persistent_population.py" status \
  --experiment "$NEXT" --out "$NEXT/PERSISTENT_STATUS.json" \
  > "$NEXT/PERSISTENT_STATUS.log"

# 최초 실행 보고용 요약 패키지 (거대한 원본 events/blobs 제외)
tar -czf "$HOME/PERSISTENT_POPULATION_FIRST_RESULTS_20261029.tar.gz" \
  -C "$NEXT" persistent.json PERSISTENT_STATUS.json PERSISTENT_STATUS.log \
  PERSISTENT_FIRST_RUN.log CYCLE_000/cycle.json
```

이 tar는 **실행 상태와 가설 계보 요약을 검토하기 위한 것**이다. 수학·문헌 근거의 독립 재검토가 필요하면 해당 원본 ROOT의 실제 Journal event/blobs/모델 도구 응답을 추가로 추출해야 한다.

## 아직 구현하지 않았거나 검증되지 않은 것

1. 전체 Population의 규모나 independent peer 판단 개수를 AI가 동적으로 제어하는 기능은 아직 없다. `--peer-count`는 운영 상한/표본 수다. 실제 과학적 연구 Work 수·종류는 기존 Controller가 선택한다.
2. ACTIVE Work를 정확히 동일한 실행 상태로 다른 ROOT에 '마이그레이션'하지 않는다. 의도적으로 출처를 보존한 뒤 다음 연구 여부를 재판단한다.
3. 완료된 후속 자산에 새로운 인과 내용이 있는지, Level II인지 자동 인증하지 않는다. 재검토는 별도 필요하다.
4. 테스트는 코드 문법, 이전 버전의 호환성 변환, Fake Journal 상속·상태 보존, 유료 guard를 확인했지만 실제 `graphAgent311`/OpenRouter에서의 실행은 사용자가 실행해야 검증된다.
5. 장기 반복으로 자산 수가 증가하면 프롬프트 길이, 평가 비용, source-size 관리가 병목이 될 수 있다. 과학적 내용을 손실 없이 요약하는 장기 메모리 정책은 이 버전에 포함되지 않는다.
