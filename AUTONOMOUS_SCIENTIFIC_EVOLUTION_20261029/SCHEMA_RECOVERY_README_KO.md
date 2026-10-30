# Autonomous Scientific Evolution — Schema Exhaustion Recovery (2026-10-29)

## 어떤 문제를 수정하는가

첫 Autonomous Cycle 000에서 `SYN_02`가 `CONTROLLER_PLAN_REJECTED`를 반복해
`SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED`로 멈추는 경우에 대한 **운영상 안전 복구**.
이 오류는 과학적 HOLD가 아니라 제출된 E3R1 Controller 계획의 검증 실패다.

이 패치는 Controller의 잘못된 계획을 자동 수정하거나 강제로 승인하지 않는다.
또한 정상 연구 결과를 가진 `SYN_01`의 연구를 폐기하지 않는다.

## 변경 파일

- `autonomous_population.py`: 저장된 3건 이상의 거부 계획과 관련 SAVED 호출을
  점검해 append-only `AUTONOMOUS_META`에 운영상 격리 근거를 기록한다.
  재실행 시 저장된 실패 동료는 과학적 성공/HOLD가 아닌 운영상 실패로 간주하고
  Population 합성으로 넘어갈 수 있다. 새로운 실행에서 같은 형태의 schema
  exhaustion이 일어나도 같은 복구 경로를 사용한다.
- `persistent_population.py`: 유효한 동료는 기존 엄격한 import를 유지하고,
  격리된 동료는 **실패 기록만** `SRC_PEER_DECISION_SYN_02` 형태의
  HISTORICAL_AI 출처로 등록한다. 실패한 동료의 decisions/assets는 빈 배열이다.
  모든 동료가 실패하면 합성을 중단한다.
- `test_schema_quarantine_offline.py`: mock Journal로 no-paid 영속성,
  decision/asset 미위조, 재실행, 해시 변경 감지를 검증한다.

## 원본 결과 보존

기존 G0, G1/G2, Persistent, SYN_01, SYN_02 연구 ROOT를 절대 삭제하거나
수동으로 수정하지 않는다. 이 패치는 오직 Coordinator 메타 Journal에
**새로운** 운영 기록을 하나 추가하고, 다음 combine 시 새로운 Population
ROOT를 생성한다. 기존의 Model SAVED 응답은 재호출하지 않는다.

## 설치

ZIP을 WSL에 복사했다고 가정:

```bash
cd "$HOME/ScientificEvolution"
unzip -o "$HOME/Downloads/AUTONOMOUS_SCHEMA_RECOVERY_PATCH_20261029.zip" -d "$HOME/ScientificEvolution"

conda activate graphAgent311
export PYTHONPATH="$PWD/runtime"
KIT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
NEXT="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"

python "$KIT/test_offline.py"
python "$KIT/test_autonomous_offline.py"
python "$KIT/test_schema_quarantine_offline.py"
```

압축 파일을 다른 위치에 두었다면 `unzip` 첫 번째 인자만 실제 경로로 바꿔야 한다.

## 현재 멈춘 실행을 0 유료 호출로 복구

```bash
unset FAKG_RESEARCH_ALLOW_PAID
python "$KIT/autonomous_population.py" recover-schema \
  --experiment "$NEXT" --peer SYN_02

python "$KIT/autonomous_population.py" preflight \
  --experiment "$NEXT"
```

성공하면 `SCHEMA_EXHAUSTED_PEER_QUARANTINED_NO_PAID`가 출력된다.
이 명령은 실제 거부된 SAVED Controller 응답이 3건 이상이고, 아직 이 동료의
유효 Controller 결정이나 새로운 Work가 없으며, 미확정 호출이 없을 때만
작동한다. 조건이 맞지 않으면 **절대 억지로 통과시키지 말 것**.

## 다음 실행

기존에 사용하던 `autonomous_population.py run` 명령을 그대로 다시 실행한다.
이는 누적 횟수를 다시 0으로 초기화하는 것이 아니다. `SYN_01`의
`YIELD_TO_POPULATION` 응답과 `SYN_02` 격리 기록을 확인해 Population으로
이동한다. 첫 합성은 정상 SYN_01 자산과 실패한 SYN_02 메타 정보를 별도로
전달한다. 이후 AI Population의 NEXT_GENERATION/CONTINUE/HOLD 판단은 그대로
AI가 수행한다.

## 주의

- `SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED` 기록 자체가 자동으로 과학적 결론이
  되는 것은 아니다.
- `recover-schema`는 기존 로그의 경계를 운영자가 사실로 확인한 경우에만
  호출한다. 이번 사용자 로그에서 해당 경계가 이미 확인됐다.
- 프로그램의 운영상 실패율이 높다면 유료 호출을 무제한 재개하기보다
  먼저 조정자 성능과 제약 검증의 실패 원인을 조사해야 한다.
- 단일 SYN의 결과만으로 Level II 신규 가설을 인증하지 않는다.
