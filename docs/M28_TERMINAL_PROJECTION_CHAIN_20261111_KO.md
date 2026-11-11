# M28 DAC 종료 판단의 구조 투영 및 연쇄 후속 연구 (2026-11-11)

## 왜 이 패치가 필요한가

원본 `_02`에서는 `program_portfolio_review:null`로 종료 판단이 거부됐다. `d931063`의 `_03`에도 동일 현상이 반복됐다(8회 신규 호출, 4개의 Controller 거부, 0개의 승인된 Controller 결정). **이전 패치는 새로운 판단 기회만 열었지, 모델이 문서를 누락하는 문제를 제거하지 못했다.** `_03`은 소스 핀이 `d931063`이므로 새 코드를 동일 ROOT에서 바로 실행할 수 없다.

## 변경 사항

1. `runtime/e2core/engine.py` — **자식 연구가 전혀 없는 PRIMARY**가 종료를 제안했고 `program_portfolio_review`를 빠뜨렸을 때, 그 **동일 응답에서 모델이 직접 작성한** `disposition`, `rationale`, `objective_assessment.remaining_questions`를 정확히 대응시키는 프로그램 검토 기록을 작성한다. `M28_TERMINAL_PROGRAM_REVIEW_STRUCTURED_FROM_AUTHORED_JUDGMENT` 감사 사건을 함께 커밋한다. 원본 Controller 응답은 수정하지 않는다. 별도의 과학적 판단, 근거, 결과를 생성하지 않는다. 자식 연구·조직 요청이 하나라도 존재하면 기존대로 모델이 명시적으로 작성해야 한다. R5 과학적 상태 불일치는 자동 변환하지 않고 거부한다.
2. `runtime/e2core/meta_collaboration.py` — 모델 프롬프트에서 위 제약과 복구 경로를 명시한다.
3. `runtime/e2core/m28_successor.py` — 최초 후속 실험 `_03`을 검증된 다음 후속 실험 `_04`로 이어받는다. 원래 231회 호출은 `_03`의 장부에 재청구되지 않았고, 이번 8회 신규 호출만 후속 차감 대상이다. 두 번의 소스 핀과 Journal 접두 해시 및 예산 보존성을 검증한다. 무제한 깊이 계승은 지원하지 않으며 `_02→_03→_04`만 지원한다.
4. 무유료 테스트 — 누락 검토의 감사 가능한 투영, 잘못된 후보상태의 엄격한 거부, 2차 후속 계보·비용 연속성, 누락된 SQLite 비용 기록 거부.

## 적용 (유료 호출 없음)

```bash
cd "$HOME"
unzip -n SCIEVO_M28_TERMINAL_PROJECTION_CHAIN_20261111.zip -d "$HOME"
cd "$HOME/ScientificEvolution_M25"
KIT="$HOME/SCIEVO_M28_TERMINAL_PROJECTION_CHAIN_20261111"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/runtime:$PWD:$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
unset FAKG_RESEARCH_ALLOW_PAID OPENROUTER_API_KEY
python "$KIT/self_test.py"
python "$KIT/apply.py" --repo "$PWD" --check
python "$KIT/apply.py" --repo "$PWD" --apply

# 중요: 모든 기존 회귀 검사에서는 DAC 전용 환경변수를 제거한다.
unset M232_CONTROLLER_DETAIL_MODE M232_NAMESPACE_MODE M233_MODEL_METADATA_MODE
unset M232_CACHE_POLICY M232_SYN_PMI_MODE M232_BUDGET_REQUIRED
for suite in m28 continuity m25 v3 v4 clean; do
    echo "=== $suite ==="
    python -m unittest discover -s "checks/$suite" -p 'test_*.py' -q
done
git diff --check
git status --short
```

모든 테스트 통과 전 커밋하지 말 것. 실패 시 출력 전체를 확인할 것. 기존 `_02`, `_03`은 건드리지 않는다.

## 커밋 후 `_04` 생성 (유료 호출 없음)

```bash
cd "$HOME/ScientificEvolution_M25"
unset FAKG_RESEARCH_ALLOW_PAID OPENROUTER_API_KEY
export PYTHONPATH="$PWD/runtime:$PWD:$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
export PYTHONDONTWRITEBYTECODE=1
export M232_CONTROLLER_DETAIL_MODE=ON_DEMAND
export M232_NAMESPACE_MODE=COMPACT
export M233_MODEL_METADATA_MODE=SEPARATE
export M232_CACHE_POLICY=SELECTIVE_NO_WRITE
export M232_SYN_PMI_MODE=FULL
export M232_BUDGET_REQUIRED=YES

git add runtime/e2core/engine.py runtime/e2core/meta_collaboration.py \
  runtime/e2core/m28_successor.py \
  checks/m28/test_m28_terminal_projection_chain.py \
  docs/M28_TERMINAL_PROJECTION_CHAIN_20261111_KO.md
git diff --cached --check
git commit -m 'fix(m28): project zero-child terminal review and chain audited successor'
git push origin dev/meta-research-autonomy-v1

test -z "$(git status --porcelain)"
OLD="$HOME/ScientificEvolution_runs/M28_DAC_NO3RR_20261111_03"
NEXT="$HOME/ScientificEvolution_runs/M28_DAC_NO3RR_20261111_04"
test ! -e "$NEXT"
python "$KIT/resume.py" --parent "$OLD" --out "$NEXT" --check
python "$KIT/resume.py" --parent "$OLD" --out "$NEXT" --create
python runtime/meta_research_autonomy.py preflight --experiment "$NEXT"
```

## 후속 실제 연구

이후 `_04`에서 **새로운 유료 실행을 별도로 승인**한다. 복구 진입점이 있다고 해서 반드시 추가 연구를 만들어야 하는 것은 아니다. 모델이 유효한 프로그램 종료를 제출하면 즉시 종료할 수 있다. 자동 종료 처리의 정당성은 별도로 과학 감사한다. 내부 예산은 제공자 비용의 절대 상한이 아니므로 OpenRouter 키·계정 잔액도 점검한다.

## 제한사항

- `SCOPED_NEGATIVE`, `REVIEW_WORTHY_CANDIDATE`, `HOLD_WITH_RATIONALE` 자체의 **과학적 진위**는 이 패치가 인증하지 않는다.
- 자식 연구가 존재하는 경우에는 자동 프로그램 검토 투영을 허용하지 않는다.
- R5 상태가 모순되는 경우에는 여전히 거부한다. 그때는 원래 모델이 작성한 JSON을 읽고 판단을 감사해야 한다.
- `_02`, `_03`의 기존 Journal 및 Source Pin을 수정하지 않는다.
