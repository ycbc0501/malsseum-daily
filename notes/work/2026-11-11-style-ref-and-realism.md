# 2026-11-11 — 레퍼런스 이미지 직접 투입 + 리얼리즘 프롬프트 단순화 (진행 중)

## 지시 3개
1. 레퍼런스를 실내/실외 버킷 카운팅으로 "분석"하는 건 분석만도 못함 — @dailymayim 이미지를
   Gemini에 통째로 넣어 "이 룩앤필로" 생성 요청하고, 장소/장면은 지금처럼 단어로.
2. 모션 프롬프트에 "먼지 금지" 같은 부정 나열 넣지 말 것 — 너무 복잡해짐. "더 진짜처럼"을
   구현하는 법을 딥리서치해서 프롬프트 고수들 기법 적용.
3. 검수에이전트가 검수 안 한 파트는 0 — 법. 바뀐 모든 파일 구조+diff+qa_gate --run 다 거친다.

## 리서치 결론 (WebSearch 3회, 2026-11-11)
- 실제 카메라/렌즈 지칭("50mm f/1.8", "full-frame"), "film grain"/"raw photo"로 불완전성을
  프롬프트에 내장 — 후처리가 아니라 생성 단계에서.
- "8K", "hyperrealistic", "ultra-detailed", "masterpiece" 같은 버즈워드는 오히려 과샤픈/
  과채도의 가짜 느낌을 만든다 — 적게 쓰는 게 더 real.
- 영상: **"하지 말 것" 나열보다 "무엇이 실제로 움직이는가"를 구체적으로 말하는 게 낫다**
  (positive motion instruction > long negative list). 이게 핵심 — 어젯밤 추가한
  "no floating dust/sparkle" 식 부정 나열(D-5/E-3b)이 바로 이 반패턴이었다.

## 구현 계획
- [ ] reference_study.py: style_refs/ 디렉터리에 수동 업로드 이미지를 영구 저장(캡 적용) —
      지금까지 분류 후 버려지던 것을 fetch_image.py가 실제로 쓸 수 있게.
- [ ] fetch_image.py: style_refs가 있으면 Gemini 호출에 참조 이미지 N장을 inlineData로 첨부,
      "look/color/grain만 참고, subject/composition은 본문 단어가 결정" 지시 추가. 없으면
      현재와 동일(회귀 없음).
- [ ] content_law.py: STYLE_REF_NOTE 신설, for_image()에 조건부 추가.
- [ ] fetch_motion.py: MOTION을 "무엇이 움직이는가"를 긍정문으로 명시하는 구조로 재작성,
      어젯밤 추가된 부정 나열(먼지/반짝임/그림자) 축소.
- [ ] RULES.md: D-6(스타일 레퍼런스 직접 투입), E-3c(긍정 모션 문법), K-5(검수 0% 법 — 명문화).
- [ ] check_rules.py + tests.
- [ ] 검수 에이전트 3단계(구조/diff/qa_gate --run) 전부, 커밋/푸시/CI green.

## 상태: 연구 완료, 구현 착수

## 진행 상황 업데이트 (구현 완료, qa_gate --run 실행 중)

- content_law.py: STYLE_REF_NOTE + for_image(style_ref=) 완료.
- fetch_image.py: STYLE_REF_DIR/ATTACH_N, _style_refs/_pick_style_refs/_image_request_body
  (순수 함수로 분리, 네트워크 없이 테스트 가능), _gemini_once/_gemini/generate_background에
  style_refs 관통. 중복 indoors 계산 + 중복 model=="gemini" 분기 정리(구조 검수 지적).
- reference_study.py: save_style_ref (mtime 기준 축출로 수정 — diff 검수가 파일명 정렬 버그
  잡음), run_manual/run_try_fetch 양쪽에서 호출. send_reminder()가 "그리드 아니라 개별 사진"
  요청하도록 문구 변경(그리드 스크린샷 통째 저장 문제 — diff 검수가 잡음, 코드로 신뢰성 있게
  막을 수 없어 운영 절차로 문서화).
- fetch_motion.py: MOTION을 "무엇이 움직이는가" 긍정 목록으로 재작성, NEG에서 심볼릭 부정
  나열 제거. 구조 검수가 MOTION↔NEG 모순(moving clouds/flowing water/flickering이 허용되는데
  동시에 금지돼 있던 것) 잡음 — 수정 완료.
- RULES.md: D-6(스타일 레퍼런스), E-3b→3c 교체 기록, K-5(0% 법) 추가.
- check_rules.py: D-6 6개, E3c 3개(+모순 검사 1개 추가), K-5 1개.
- test_style_refs.py 신규 32개 체크(역테스트 다수) — 전부 통과.
- verify.sh 전체(기존 테스트 전부 + 신규) 통과 확인(샌드박스 해제, uv 캐시 문제 때문).
- 검수 에이전트 3단계: ① 구조 검수(Agent, opus) 완료 — 6개 지적, #1(모순)·#5(중복 코드) 수정,
  #2(파일명 정렬)는 diff 검수와 동일 지적이라 교차 확인됨, #3/#4/#6은 범위 밖으로 기록.
  ② diff 검수(code-review 스킬 high) 완료 — 2개 지적(정렬 버그, 그리드 스크린샷) 둘 다 수정.
  ③ 결과물 검수(qa_gate.py --run) — 백그라운드 실행 중, 로그 /tmp/qa_gate_run.log.

## 남은 것
- qa_gate --run 완료 대기 → 실제 생성물(배경+모션) 확인.
- CLAUDE.md 로그 작성, RULES.md/CONTENT_RULE.md 상호 참조 확인.
- 커밋 + 푸시 + CI green 확인.
- 사용자에게: style_refs 디렉터리가 지금 비어있다(저장된 레퍼런스 이미지 없음) — 효과를
  보려면 @dailymayim 개별 사진(그리드 아닌) 몇 장을 보내달라고 요청 필요.
