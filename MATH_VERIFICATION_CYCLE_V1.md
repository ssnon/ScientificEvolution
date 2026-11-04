# ScientificEvolution — Native Math Verification Cycle V1

## 목적 및 한계

**범용 AI Scientist**의 기존 Native Worker/Controller/Journal에 독립적인 수학 검증을 연결합니다. 기존 루트 및 P0, A0/A1, ASER 벤치마크의 기록은 변경하지 않습니다. `--math-verification`을 선택한 **새 Persistent Population**에서만 동작합니다. 연구가 성공했다거나 수학적 주장이 참이라고 자동 인증하지 않습니다.

이 패키지는 `bdcda494f3e7d01ceaff2efc9692669289bb738c`의 정확한 Native 소스를 대상으로 작성했습니다. **기존 다른 브랜치/수정된 HEAD에는 임의로 패치하지 않습니다.** 해당 기준 GitHub 소스의 필요한 코드 지점과 계약을 조사했지만, 패키지 작성 환경에 사용자 WSL 전체 저장소가 없으므로 **전체 Native 런타임 통합 검사는 사용자 WSL에서 `native_no_paid_smoke.py`를 실행해야 합니다**. 패키지 자체의 단위 테스트(14개), 구문 검사 및 ZIP 검사는 작성 환경에서 통과했습니다.

### 실제 연결

```
새 CALCULATION/COUNTEREXAMPLE ASSET_PUBLISHED
    -> 정식 EVOLUTION_APPLIED/VERIFY Work 등록
    -> 분리된 입력으로 Native Worker 호출
    -> 반환한 수학 검토는 MATH_REVIEW WORK_STEP (프로비저널)
          -> 검증자가 새로운 수학 자산을 발표한 경우: 다시 VERIFY Work
          -> 처음 연구의 기여자에게 별도 INFORMED/DEVELOP 재평가 Work
               -> 재평가자가 새 수학 자산을 만들면 다시 VERIFY
    -> 검증 대기열 해소 후 기존 Controller 판단
```

모든 실행은 원래 `Engine.worker_step()`와 `EvolutionJournal`를 사용하며 **검증자 모델만 바꿔치는 가짜 래퍼가 아닙니다.** 실험의 과학적 끝을 강제하는 검증 depth/cycle 최대치는 없습니다. 예산 때문에 중단되면 과학적 결론이 아닌 운영 상태입니다. 모든 새 수학 주장에 대한 독립 재검증은 **등록된** ASSET_PUBLISHED에 적용됩니다. V1의 자동 선별 범위는 `CALCULATION`/`COUNTEREXAMPLE`, 그리고 Verifier/Reassessor가 새로 발표한 모든 종류의 자산입니다. 다른 종류의 자산에 숨겨진 수학은 Controller의 일반 VERIFY 결정 대상이며, **자동 탐지 커버리지를 100%라고 주장하지 않습니다.**

## 1. 로컬 적용 — 유료 호출 금지

```bash
cd "$HOME"
unzip -n SCIEVO_NATIVE_MATH_CYCLE_V1_20261104.zip -d "$HOME"

cd "$HOME/ScientificEvolution_M236_2"
unset FAKG_RESEARCH_ALLOW_PAID
export PYTHONDONTWRITEBYTECODE=1
KIT="$HOME/SCIEVO_NATIVE_MATH_CYCLE_V1_20261104"

# 소스 HEAD와 4개 anchor/교체 지점 점검: 절대 쓰지 않음
python "$KIT/integrate_native_math_cycle.py" --repository "$PWD" --check

# 정상일 때에만 별도 새 브랜치에서 Native 파일 수정
# HEAD를 바꾸지 않는 git switch -c 만 허용
git switch -c dev/native-math-verification-cycle-v1
python "$KIT/integrate_native_math_cycle.py" --repository "$PWD" --apply

# 정적 단위 테스트(유료 없음)
python "$KIT/checks/test_math_cycle_offline.py"

# **중요**: 실제 E2 Native Engine과 append-only Journal을 사용하는
# 가짜 모델 4호출 실험. 외부 Provider 모델은 절대로 호출하지 않음.
python "$KIT/checks/native_no_paid_smoke.py" "$PWD"

git diff --check
git status --short
git diff --stat
```

`native_no_paid_smoke.py`는 임시 `$HOME/SCIEVO_MATHCYCLE_MOCK_*` 루트를 생성해 모의 연구자 → 1차 VERIFY → 신규 검증 자산의 2차 VERIFY → 원저자 재평가 → 미완료 검증 없음, 총 4회 모의 Worker 호출을 검증하고 임시 루트를 삭제합니다. **모델이 과학적으로 성공했다는 의미는 아닙니다.**

권장 기존 회귀 테스트(유료 flag가 설정되지 않았는지 확인 후):

```bash
PYTHONPATH="$PWD/runtime:$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029" \
 python -m unittest discover -s checks/v3 -p 'test_*.py'
PYTHONPATH="$PWD/runtime:$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029" \
 python -m unittest discover -s checks/v4 -p 'test_*.py'
```

`checks/v3`/`checks/v4`가 실제 있는지 확인하십시오. 회귀 실패가 발생하면 커밋하지 않고 로그를 전달하세요. `git reset --hard`는 다른 작업물을 삭제할 수 있으므로 사용하지 마세요.

## 2. 기존 연구와 분리된 새 ROOT 준비 (무과금)

소스가 적용된 **새 브랜치**에서만 아래 신규 ROOT를 사용합니다. 새 루트의 원본 P0와 역사적 자산은 SYN_02에서 계승하지만 A0/A1의 사후 감사 정답은 전달하지 않습니다.

```bash
cd "$HOME/ScientificEvolution_M236_2"
unset FAKG_RESEARCH_ALLOW_PAID
export PYTHONDONTWRITEBYTECODE=1

export PYTHONPATH="$PWD/runtime:$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
export ROOT="$HOME/ScientificEvolution_runs/NATIVE_MATH_CYCLE_V1_PILOT_20261104_01"
export SOURCE="$HOME/ScientificEvolution_runs/M2362_FROM_M236_POPULATION_20261104_01/CYCLE_000/SYN_02"

python AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029/persistent_population.py init \
  --source-root "$SOURCE" --out "$ROOT" --math-verification

# 새 소스의 실제 .py 바이트 해시를 신규 ROOT에 영구 핀
python - <<'PY'
import os, generational_run as gen
pin=gen.pin_native_source(os.environ['ROOT'])
print('NATIVE_NEW_PIN_FILES',len(pin['files']))
PY

python AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029/persistent_population.py preflight \
  --experiment "$ROOT"
```

**다음으로 추천하는 무과금 확인:** 임시 파일/사이클을 지우지 말고 `preflight`, `git diff --stat`, Native mock smoke의 전체 출력 로그를 첨부하세요. 그때 실제 소스/계보 해시/대기열/검증자 입력 분리까지 확인한 뒤 작은 유료 Population 파일럿을 시작할 수 있습니다. 이 문서에는 자동 유료 실행 명령을 넣지 않았습니다.

## 3. 데이터/판정 신뢰성

- `VERIFY`는 기존 Native Evolution Work이며, Model answer 원문·진짜 tool result·parent asset id를 보존합니다.
- 모델이 `math_review` 구조화 필드를 반환하면 그 내용 그대로 `MATH_REVIEW` Step에 남습니다. 구조가 없으면 `UNSTRUCTURED_MODEL_REVIEW`로 기록하고 수학적 인증을 내리지 않습니다.
- Worker가 제안한 추가 `CALCULATION`/`COUNTEREXAMPLE`도 **새로운 provisional Asset**이지 인증된 결과가 아닙니다.
- 검증자는 한 대상의 `parent_assets`와 자신의 과거 step 위주로 입력받습니다. 전체 Population 판단 요약 등은 Reviewer 최초 입력에서 제거하되, 대상 자산에 이미 연결된 역사적 근거는 출처로 남습니다.
- 다른 연구자를 위한 재평가 Work는 검증자의 실제 Journal `MATH_REVIEW` 기록과 (있다면) 새로운 원문 수학 자산을 인계합니다. 무조건 동의하라는 지시는 없습니다.
- 검증 대기열이 QUEUED/ACTIVE 또는 운영상 BLOCKED로 남았는데 PEER→POPULATION 혹은 POPULATION→새 Cycle 경계에 도달했다면 진행하지 않고 `...MATH_REVIEW_INCOMPLETE_OPERATIONAL_PAUSE`를 출력합니다.
- 오래된 source-pinned Root는 변경되지 않으며, 새 코드를 설치한 브랜치에서 오래된 source pin의 가드가 거부하는 것은 정상입니다. 기존 재현 실행은 원래 HEAD에서 수행하세요.

## 4. 구현 범위와 다음 검증

**이 패키지는 Native 코드의 실험적 첫 통합본**입니다. 아직 실제 유료 Population이 이 기능을 실행한 기록은 없습니다. PASS 조건은 단순 Work 갯수가 아니라, 실제 모델 요청이 출처에 맞게 격리되고, 새 수학 claim이 재검증 대상이 되며, 연구자가 그 결과를 고려해 수정·유지·유보하고, Controller가 그 차이를 반영하는지입니다. Reviewer의 신뢰성은 벤치마크 8개만으로 일반화되지 않습니다. 무엇보다 `MATH_REVIEW`는 과학적 인증이 아닙니다.
