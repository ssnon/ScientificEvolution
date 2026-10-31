# G14 DOI 공개 PDF 읽기 확장 — 2026-10-30

## 범위

이 패키지는 기존 `ScientificEvolution` 소스·E2 Journal을 수정하지 않고 **한 번의 실행 프로세스에서만** `literature_research`의 `read_open_pdf`를 추가한다. G14 `SYN_01`의 기존 연구는 보존되고, 모든 이후 PEER Worker는 DOI 조회 기능을 자율적으로 사용할 수 있다. **주의:** 기존 Population 스케줄러는 미사용 모델 호출이 적은 Peer를 우선하므로 다음 연구 구간은 `SYN_01`이 아닌 `SYN_02`에서 먼저 진행될 가능성이 높다. 새로운 기능은 두 독립 Peer 모두에 동일하게 제공되지만 SYN_02에 SYN_01의 비공개 연구 결과를 전달하지 않는다. 기존 OpenAlex/Europe PMC/다른 과학 도구는 그대로 작동한다. 새로운 Controller·새 연구 목표·평가 정책·가설을 생성하지 않는다.

**새 모델 입력의 도구 문법**:

```json
{"kind":"literature_research","arguments":{"action":"read_open_pdf","doi":"10.1021/jp034632u","page":1}}
```

직접 PDF URL을 모델에서 받지 않는다. DOI를 OpenAlex로 조회하여 **DOI 일치** 확인 → OpenAlex가 DOI에 연결한 공개 PDF 후보를 찾는다. 현재 SYN_01이 자율적으로 이미 선택한 정확한 DOI `10.1021/jp034632u`에 한해서는 검토된 저자 공개본 `www.columbia.edu/cu/chemistry/groups/brus/pdf2/jp034632u.pdf`를 추가 locator 후보로 사용한다. 이 후보는 **검색 위치만** 제공하는 운영자 검토 링크이며 과학적 해석·원문 확인·실험 근거를 미리 주입하지 않는다. PDF를 실제 내려받아 식별 검사를 통과해야만 본문 근거로 인정한다. 검토된 정확한 host 목록 외의 OpenAlex PDF는 자동 접근하지 않는다.

성공한 실행의 `TOOL_RECORDED` + `TOOL_RESULT`는 정상 E2 기록으로 보존되고, `SOURCE_REGISTERED`로 `OA_PDF_TEXT`를 기록한다. 반환 필드는 실제 다운로드 PDF의 `source_sha256`, 공개 URL, 페이지, 페이지별 발췌·해시, DOI와 제목 대조 결과, 접근 경로, 미검증 한계. PDF 텍스트는 **과학적 주장 자체의 검증이 아니며**, 그림/수치·저자 해석에는 별도 검증이 필요하다. 라이선스도 별도 검증되지 않았다.

## 운영체제·준비

WSL Linux + `graphAgent311` conda 환경, `pypdf` 필요. 테스트는 포함된 소형 PDF fixtures를 사용하며 `reportlab` 설치가 필요하지 않다. Python 3.10 이상. 소스 보존을 위해 이 폴더 전체를 `~/ScientificEvolution/` 밑에 압축 해제한다. 기존 `KIT`, `FRONTIER`, `AUT`, `EXP` 경로는 변경하지 않는다.

```bash
conda activate graphAgent311
cd "$HOME/ScientificEvolution"
AUD="$PWD/G14_DOI_OPEN_PDF_BRIDGE_20261030"
KIT="$PWD/SCIENTIFIC_EVOLUTION_LEVEL2_RUNTIME_REPAIR_20261030"
FRONTIER="$PWD/SCIENTIFIC_EVOLUTION_FRONTIER_V1_20261030"
AUT="$PWD/AUTONOMOUS_SCIENTIFIC_EVOLUTION_20261029"
EXP="$HOME/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029"
export PYTHONPATH="$AUD:$KIT:$FRONTIER:$AUT:$PWD/runtime"
unset FAKG_RESEARCH_ALLOW_PAID
touch "$EXP/STOP_REQUESTED"
python "$AUD/test_pdf_bridge_offline.py"
python "$AUD/verify_g14_offline.py" --experiment "$EXP" \
  | tee "$HOME/G14_PDF_BRIDGE_PREFLIGHT.json"
```

예상 결과: 테스트 9건 통과 + `G14_PDF_EVIDENCE_EXTENSION_READY_NO_PAID` / `target_next_worker_step: 9`. 원본 SYN_01 head가 **1058 events** / `695187b5ab98...`와 정확히 일치해야 한다. 한 번 연구가 진행된 후에는 이 체크포인트 전용 스크립트를 재사용하지 말고 Journal을 검증한 다음 새로운 체크포인트를 정해야 한다. `target_next_worker_step: 9`는 SYN_01이 **다시 배정될 때의** 단계이며, 다음 실행이 SYN_01을 즉시 배정한다는 보장은 아니다.

### 선택적 무료 공개 PDF 네트워크 Probe

외부 공개 문헌 서버 요청은 하지만 **LLM API·E2 Journal은 전혀 사용하지 않는다**.

```bash
python "$AUD/probe_open_pdf.py" --doi 10.1021/jp034632u --page 1 \
  --out "$HOME/G14_PDF_OPEN_PROBE.json" \
  | tee "$HOME/G14_PDF_OPEN_PROBE_SUMMARY.json"
```

`status=DELIVERED`면 실제 PDF 텍스트 접근 가능. `EVIDENCE_UNAVAILABLE`은 접근 제한·네트워크 오류 또는 식별 실패를 뜻하며 과학적 부정 결과가 아니다. 실패했다면 **유료 재개 전에** 오류 원인을 검토하는 것이 좋다. 공개 PDF가 다운로드되더라도 원문 텍스트·그림의 내용이 이미 과학적으로 검증됐다는 의미는 아니다.

## 선택적 유료 재개 — 성공한 Preflight를 확인하고 실행

기존 STOP 마커를 명시적으로 해제한 경우만 유료 연구를 실행한다. 아래는 1개 운영 구간이며 8은 총 결제 상한이 아니다. 메타 연구 심사 호출이 추가될 수 있다.

```bash
python - <<'PY'
import json, pathlib
j=json.loads((pathlib.Path.home()/"G14_PDF_BRIDGE_PREFLIGHT.json").read_text())
assert j['status']=='G14_PDF_EVIDENCE_EXTENSION_READY_NO_PAID'
assert j['target_next_worker_step']==9
assert j['journal_unchanged'] is True
print('BRIDGE_PREFLIGHT_VERIFIED')
PY
pgrep -af '[e]volution_pdf.py run|[e]volution_memory.py run' || true
(
  set -o pipefail
  trap 'touch "$EXP/STOP_REQUESTED"; unset FAKG_RESEARCH_ALLOW_PAID' EXIT
  rm -f "$EXP/STOP_REQUESTED"
  export FAKG_RESEARCH_ALLOW_PAID=YES
  python "$AUD/evolution_pdf.py" run \
    --experiment "$EXP" --paid --model openai/gpt-5.6-luna \
    --bootstrap-peers 2 --slice-budget 8 --checkpoint-iterations 12 \
    --max-parallel 2 --max-tokens 16000 \
    --science-cpu-seconds 120 --science-wall-seconds 160 \
    --notice-every-segments 1 --max-operational-segments 1 \
    2>&1 | tee -a "$EXP/G14_PDF_RESEARCH_CONTINUATION.log"
)
```

⚠ `pgrep`에 실시간 실행 중인 기존 실행기가 나온다면 병렬로 재개하지 않는다. `BRIDGE_PREFLIGHT_VERIFIED`가 통과하더라도 현재 상태가 바뀌었다면 먼저 검증을 다시 수행한다. 모델 호출은 사용자가 수행할 때만 발생한다.

## 보안·근거 제한

- HTTPS 필수, 명시적 호스트만 허용. 모델에 임의 URL, HTTP, IP literal, userinfo, port 전달 금지. 서버 측 리디렉션 허용하지 않음. DNS가 사설주소를 반환하면 실패. 외부 DB의 공개 URL만으로는 자동 신뢰하지 않음.
- HTML, 8 MB 초과, 암호화 PDF, DOI 색인 제목과 PDF 첫 페이지가 불일치하면 사용하지 않음. PDF parser는 subprocess에서 CPU/주소공간 제한, wall timeout으로 격리 (OS sandbox 전체를 보증하지는 않음).
- 공개 PDF가 반드시 자유 라이선스인 것은 아님. 반환 문헌은 출처 데이터를 의미하며 LLM이 주장 검증·신규성을 자동 인증하지 않음.
- 일반적인 OpenAlex `best_oa_pdf_url`은 PDF가 아닐 수 있고 권한이 필요할 수 있다. 실패는 `EVIDENCE_UNAVAILABLE`로 분류되며 Work가 다음 과학적 판단을 할 수 있다.
- 기존 `SYN_01`의 과거 네 번의 TOOL_RECORDED, 기존 G13/G14 원본 이벤트, 과거 SAVED 모델 응답은 그대로 유지한다. 새 도구 결과는 **새로 모델이 요청했을 때만** 생성한다.
- 이 확장은 텍스트가 있는 PDF 한 페이지를 읽는다. 이미지/수식/표의 시각적 검증은 대체하지 못한다.
