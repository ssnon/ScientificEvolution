# D78 source-and-pause forensic check (no paid calls)

이 kit는 V4 Journal을 읽기 전용으로 조사하고, 공개 논문 1편의 외부 full-text 획득을 확인한다. 기존 ROOT, 과학 자산, 모델 기록, 도구 기록, Git 저장소는 수정하지 않는다. API 키나 raw model response도 출력하지 않는다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
export PYTHONPATH="$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
python /path/to/read_tail_reasons.py --root "$HOME/ScientificEvolution_runs/V4_REPO_SMOKE_20261029" --limit 50 > "$HOME/V4_D78_TAIL_REASONS_20261029.json"
python /path/to/check_pmc_source.py --out "$HOME/PMC4129422_PUBLIC_SOURCE_AUDIT_20261029.json"
```

- 첫 번째 결과는 seq 1869, 1870의 OPERATIONAL_PAUSE reason 등 최근 committed event의 안전한 메타데이터를 제공한다. `REJECTED_PROBLEM_IMPACT` 등 validator rejection이면 재실행/중복 유료 요청 전에 평가해야 한다.
- 두 번째 결과는 사용자 WSL에서 공개 Europe PMC XML과 Nature HTML을 받아 실제 본문의 존재와 SHA256, 소수의 탐색 구절을 기록한다. 차단될 경우 `error` 상태를 그대로 기록한다. 인용·진위에 대한 인증 절차가 아니다.
- 생성한 두 JSON 파일만 전달하면 다음 행동을 판단할 수 있다. API 키, model request blobs, full journal directory는 보내지 않아도 된다.
- D00078 이후의 근거 평가가 rejected라면 과학적 HOLD로 해석하지 않는다. 이전 UNCERTAIN call은 기록대로 유지한다.
