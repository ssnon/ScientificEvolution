# Population G1 `KeyError: 'ref'` 호환성 수정

## 확인한 내용

이번 로그의 SYN_A(24회), SYN_B(24회), `combine`, `preflight`는 성공했습니다. `POP_G1` 최초 `run-population`에서 `KeyError: 'ref'`로 중단됐습니다. `HISTORICAL_AI`를 읽는 구 E2의 INFORMED Worker 입력은 `ref/science/tool_result/science_sha256` 필드를 요구하지만, 최신 `import_peer()`가 만든 `SRC_PEER_ASSET_*`는 `original_root/original_asset_id/original_asset/...`를 보존합니다. 이 스키마 불일치가 실행 중 KeyError를 일으킬 수 있습니다. 원래 형식과 새로운 이관 형식을 함께 다루는 **런타임 전용 호환 계층**을 제공합니다.

이번 수정은 다음을 하지 않습니다.
- G0, SYN_A, SYN_B, POP_BASE, POP_G1 Journal의 기존 이벤트 또는 blob을 변경하거나 삭제하지 않습니다.
- 이미 완료된 유료 호출을 취소하거나 재사용되지 않은 것으로 취급하지 않습니다.
- FRESH Worker의 입력을 수정하지 않습니다.
- 새로운 가설, 논문 발견, 계산 결과, Controller 판단을 만들어 넣지 않습니다.
- 특정 가설의 G1 선택이나 FUSE를 강제하지 않습니다.

호환 처리는 **이미 Work의 입력 부모 또는 명시적 출처로 승인된 `SRC_PEER_ASSET_*`에만** 적용합니다. 유효한 원본 해시/출처가 검증되지 않으면 중단합니다. 알려지지 않은 비표준 `HISTORICAL_AI` 유형을 묵시적으로 변환하지 않습니다.

## 설치

1. 기존 `~/ScientificEvolution/POPULATION_SCIENTIFIC_EVOLUTION_20261029` 폴더에 이번 ZIP의 `population_resume.py`를 복사합니다. 기존 `population_run.py`는 바꾸지 마세요.
2. `conda activate graphAgent311`, `cd ~/ScientificEvolution`, `export PYTHONPATH="$PWD/runtime"`를 실행합니다.
3. 아래 예제를 그대로 실행합니다. **`init`, `run-peer`, `combine`를 다시 실행하지 마세요.**

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

KIT="$PWD/POPULATION_SCIENTIFIC_EVOLUTION_20261029"
POP="$HOME/ScientificEvolution_runs/SCIENTIFIC_POPULATION_FIRST_20261029"

python "$KIT/population_resume.py" preflight --experiment "$POP"
```

정상이라면 `PEER_HISTORICAL_SOURCE_COMPAT_PREFLIGHT_OK_NO_PAID`와 `no_unsaved_model_calls: true`가 출력됩니다. 기존 `POP_G1`에 Controller 호출이 저장됐다면 `saved_model_calls`와 `controller_decisions`에 표시됩니다. 그 경우에도 **이미 저장된 응답을 임의로 삭제하거나 재발행하지 않습니다.**

## 안전한 재개

```bash
(
  set -o pipefail
  export FAKG_RESEARCH_ALLOW_PAID=YES

  python "$KIT/population_resume.py" run \
    --experiment "$POP" \
    --paid \
    --model openai/gpt-5.6-luna \
    --max-new-calls 48 \
    --slice-budget 12 \
    --checkpoint-iterations 12 \
    --max-parallel 2 \
    --max-tokens 16000 \
    --science-cpu-seconds 120 \
    --science-wall-seconds 160 \
    2>&1 | tee "$POP/POP_G1_RESUMED_RUN.log"
)
unset FAKG_RESEARCH_ALLOW_PAID
```

`--max-new-calls 48`은 **이번 재개 실행 중 새로 발생하는 최대 호출 수**입니다. 실패 이전에 이미 발생한 모델 호출이 있으면 그 호출의 비용까지 합친 전 실험 누적 호출 상한이 48이라는 뜻은 아닙니다. 비용 통제가 더 중요하다면 `--max-new-calls 12`로 시작해도 됩니다.

## G1 성공 후 G2

```bash
python "$KIT/population_run.py" preflight --experiment "$POP"
python "$KIT/population_run.py" prepare-g2 --experiment "$POP"
python "$KIT/population_resume.py" preflight --g2 --experiment "$POP"
```

G2 실행을 한다면 `population_resume.py run --g2 --experiment "$POP" --paid ...` 명령을 사용합니다. G2가 자동 생성되지는 않습니다. G1 연구 결과가 없거나 과학적 terminal이면 `prepare-g2`가 보류할 수 있습니다.

## 결과 수집

```bash
python "$KIT/population_run.py" audit \
  --experiment "$POP" --out "$POP/POPULATION_RESULT_AUDIT.json"

tar -czf "$HOME/SCIENTIFIC_POPULATION_RECOVERY_RESULT_20261029.tar.gz" \
  -C "$HOME/ScientificEvolution_runs/SCIENTIFIC_POPULATION_FIRST_20261029" \
  population.json POP_G1_RUN.log POP_G1_RESUMED_RUN.log \
  POPULATION_RESULT_AUDIT.json
```

위 `tar`는 파일 존재 여부에 따라 `POP_G1_RUN.log`를 포함할 수 있습니다. 이번 실행은 `POP_G1_RESUMED_RUN.log`가 핵심입니다.

## 테스트와 검증 범위

- `python -m py_compile population_resume.py`
- `PYTHONPATH=<기존 KIT 폴더>:<이번 패키지 폴더> python test_offline_compat.py`
- 통과한 검증: 원본 자산 해시, peer provenance, FRESH unchanged, canonical G0 source unchanged, wrapper restoration, 잘못된 출처 거부.
- 현재 환경에서 사용자의 실제 POP_G1 ROOT 또는 OpenRouter를 실행할 수 없으므로 **사용자 WSL에서 preflight + 실실행 검증 필요**.

예상치 못한 새 오류가 생기면 `POP_G1`을 삭제하거나 재생성하지 말고 오류 출력과 `preflight` JSON을 보내주세요. 새 유료 호출이 `UNCERTAIN`인 경우에는 자동 재호출하지 않습니다.
