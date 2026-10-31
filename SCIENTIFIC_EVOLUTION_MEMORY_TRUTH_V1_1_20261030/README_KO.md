# Scientific Evolution — Memory & Tool Truth V1.1 (2026-10-30)

## 왜 V1.1이 필요한가

V1의 무료 Preflight에서 `OPP_D00003`의 `MODEL_ATTENTION_BUDGET_UNSATISFIED_NO_SILENT_TRUNCATION`이 발견됐다. 실제 G13 `POPULATION`의 저장된 모델 입력으로 확인한 결과, `v3_science_work_options` 안에 다시 중첩된 `v4_scientific_delta_handoff`가 4만 자를 넘었다. V1은 탑레벨 `v4_scientific_delta_handoff`만 압축했고, 이 중첩된 이전 과학적 판단은 빠뜨렸다. `OPP_D00002` 등에서 이미 같은 문제가 발생할 수 있었다.

이는 **이미 저장된 SAVED 호출을 바꾸는 문제가 아니며, 과거 조회에 대한 무료 반사실적 입력 변환에서 나타난 경고**다. 그러나 이후 신규 OPP/CTRL 호출에도 같은 문제가 발생할 수 있으므로, 유료 재개 전 수정한다.

## 정확히 바꾼 것

- `v3_science_work_options` 내의 `v4_scientific_delta_handoff`를 별도 압축. 원래의 **모든 개별 asset ID와 근거 evidence IDs**, 컨트롤러의 직전 결정 ID, 활성 Work의 ID·상태·질문을 보존하고, 과학적 판단 장문만 명시적 원본 해시가 붙은 excerpt로 전환한다.
- `prior_program_reviews`, `objective_assessments`, `prior_art_delta` 등 누적 리뷰 문구에 주의 예산을 적용. 원래 E2 Journal의 SAVED 모델 입력 및 과학 자산은 그대로 남는다.
- 허용 가능한 모델 view의 길이에 **영수증/원본 해시가 포함된 후에도** 86,000자 이하여야 한다는 검사 추가. 참조를 유지할 수 없으면 조용히 잘라내지 않고 운영상 일시정지한다.
- 오래된 SAVED 호출을 대상으로 한 Preflight 진단에서 attention 오류가 남아 있으면 `attention_reference_checks_passed: false`로 표시하고, 유료 재개 가능 상태로 표시하지 않는다. `STOP_REQUESTED`도 그대로 존중한다.

## 오프라인 검증

실제 G13 POPULATION Journal의 과거 SAVED 입력 6개로 재현 (문자 수; 실제 토큰/비용이 아님):

| 호출 | 원래 입력 | V1.1 모델 view | 체크 |
|---|---:|---:|---|
| `OPP_D00001` | 398,013 | 69,422 | PASS |
| `OPP_D00002` | 443,841 | 81,438 | PASS |
| `OPP_D00003` | 470,737 | 82,871 | PASS |
| `CTRL_D00001` | 404,491 | 75,900 | PASS |
| `CTRL_D00002` | 448,000 | 85,597 | PASS |
| `CTRL_D00003` | 475,782 | 85,707 | PASS |

G13의 전체 `problems` ID, 활성 Work, nested handoff의 개별 claim ID/evidence IDs를 대조해 동일함을 확인했다. 원래 SAVED 모델 입력은 새 요청으로 재실행하거나 변경하지 않았다.

**한계:** 85.7k자는 상한 86k자에 가까워 다음 세대에서 데이터가 더 증가할 수 있다. 이 패치는 안전한 오류 처리와 해당 누락 경로 수정이며, 지속 가능한 장기 문헌/계보 메모리의 완전한 해법이나 실제 유료 운영 통과 보장이 아니다. 향후에는 실제 Controller의 요청 기반 원본 조회와 분산·계층형 기억이 필요할 수 있다.

## 설치/사용

V1 원본 디렉터리는 보존한다. 이번 ZIP을 `~/ScientificEvolution`에 풀면 `SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_1_20261030` 폴더가 생긴다. 기존 연구 Journal은 **절대로 삭제·재초기화하지 않는다**.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
KIT="$PWD/SCIENTIFIC_EVOLUTION_MEMORY_TRUTH_V1_1_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

python "$KIT/test_memory_offline.py"
python "$KIT/test_attention_regression.py"
python "$KIT/evolution_memory.py" preflight --experiment "$EXP"
python "$KIT/evolution_memory.py" inspect --experiment "$EXP" --out "$HOME/EVOLUTION_MEMORY_INDEX_V1_1.json"
```

검사에서 `attention_reference_checks_passed: true`, `unresolved_model_intents: []`, `autonomous_meta_check_error: null`, `journal_modified: false`를 확인한다. `operator_stop_requested: true`이고 `paid_run_ready: false`인 것은 이전에 사용자가 요청한 정상적인 일시정지다. **바로 재개하지 않는다**. 비용과 과학적 결과를 따로 검토한 후 원할 때에만 STOP 파일을 직접 해제한다.

추가 유료 연구를 하기로 결정했다면 기존 V1 README의 `run` 명령을, 위 **V1.1 KIT 경로**로 바꿔 실행한다. V1.1 ZIP의 테스트·Preflight·Inspect는 유료 호출이 없다. 모든 기존 유료 호출의 replay/provenance 규칙은 유지한다.
