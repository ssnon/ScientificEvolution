# V4 D78 결정 이유 추출 (읽기 전용)

목적: 동일 시점의 두 Controller가 왜 새 Work를 선택하지 않았는지, 실제 기회 평가(OPA/OPP)와 Controller 원문을 확보한다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID

KIT="$PWD/V4_D78_DECISION_RATIONALE_AUDIT_20261029"
PAIR="$HOME/ScientificEvolution_runs/D78_MATCHED_DECISION_20261029"
python "$KIT/extract_rationale.py" \
  --control "$PAIR/V4_D78_CONTROL_20261029" \
  --evidence "$PAIR/V4_D78_OPERATOR_EVIDENCE_20261029" \
  --out "$HOME/V4_D78_MATCHED_EXACT_RATIONALES_20261029.json"
```

새 모델 호출이 없고 원본 Journal을 변경하지 않음. `MODEL_CALL_SAVED` raw responses, validated Controller plan, saved opportunity advisory, NVT/PMI, selected Controller input fields만 출력한다. 생성된 JSON 파일을 업로드하면 연구 선택이 합리적인 보류인지, 실행 정책 편향인지 직접 검토한다. 포함된 LLM 원문은 연구 결과를 *증명하는* 자료가 아니다.
