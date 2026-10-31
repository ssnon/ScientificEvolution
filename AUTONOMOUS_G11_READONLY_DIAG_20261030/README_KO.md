# Autonomous Generation 11 — 읽기 전용 진단

이 도구는 기존 Autonomous Science Journal을 **읽기만** 합니다. 유료 API를 호출하지 않고, 기존 ROOT 안에 새 파일이나 이벤트를 추가하지 않습니다.

중요: 현재 `INVALID_PROBLEM_IMPACT_JSON`의 직접 원인은 G11 Population의 PMI 모델 응답 형식 오류지만, 실제 응답이 잘린 것인지 다른 JSON 문제인지는 저장된 응답을 조사하기 전에는 확인할 수 없습니다. 따라서 현재 ROOT에 무작정 `run`을 다시 실행하지 마세요.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"

EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
DIAG="$HOME/ScientificEvolution/AUTONOMOUS_G11_READONLY_DIAG_20261030/audit_autonomous.py"

python "$DIAG" --experiment "$EXP" --out "$HOME/AUTONOMOUS_G11_FORENSICS_20261030"
```

출력 파일 `~/AUTONOMOUS_G11_FORENSICS_20261030.tar.gz`를 채팅에 업로드하세요. 도구는 각 세대의 peer 및 Population의 신규 live assets, 실제 inherited parent 연결, Controller 판단 및 HOLD, 실행 오류, 마지막 PMI의 저장된 provider finish_reason/usage/JSON 오류 위치/응답 일부를 기록합니다. 원문 과학적 판단 요약도 포함하지만, 논문 신규성이나 과학적 정확성을 자동 인증하지 않습니다.

**주의:** 출력에는 모델이 생성한 연구 주장과 일부 모델 응답이 포함됩니다. 공개하거나 공유하기 전에 필요한 경우 내용을 확인하세요. 기존 실행 연구 ROOT에는 쓰기 작업을 수행하지 않습니다.

PMI 출력의 `finish_reason=length`라면 출력 토큰 제한에 의한 절단 가능성이 있으며, 그렇지 않다면 JSON 형식 또는 provider의 구조를 별도로 확인해야 합니다. 어느 경우든 기존 응답을 수정 없이 보존하고, 이후 복구는 새 모델 호출의 출처를 기록하는 방식으로 진행해야 합니다.
