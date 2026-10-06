# "인위적인 슬릿(artificial slits)" 재발 — 2026-10-06 조사

작업 중 파일. 턴이 끊겨도 여기서 이어갈 것.

## 신고

원석님, 2026-10-06:
> https://www.instagram.com/reel/DeIOmzNkYbd/
> artificial slits happening again. not good

## 대상 특정 (완료)

| 항목 | 값 |
|---|---|
| 게시물 ID | 18632946685003547 |
| 구절 | 디모데전서 2:4 |
| 게시 시각 | 2026-10-06T06:59:07+09:00 (= 2026-10-05T21:59:07Z) |
| permalink | https://www.instagram.com/reel/DeIOmzNkYbd/ |
| **scene** | **`forest_path`** |
| CI 실행 | 37378026334 (2026-10-05T21:45:46Z, success) |
| 원본 mp4 | `post-37378026334.mp4` (release tag `media`, 8,591,118 B, 업로드 21:57:58Z) |
| 규격 | 7.67s, 1080x1920, 30fps, h264 |

metrics.json 기록:
```
clip_novelty    29.03
clip_spoiled    true        ← 검사가 "상했다"고 판정했는데도 게시됨
gate_passed     false
gate_ran        9 / skipped 0
motion          12.879  (sky 6.128)
motion_attempts 3
segments        1
veo_calls       6   veo_seconds 48.0
text_contrast   10.92  text_spread 6.9
likes           9
```

반응 비교 (같은 주):
```
10-04 이사야 43:21   41
10-03 이사야 42:12   38
10-02 예레미야 20:13 37
10-05 요한삼서 1:2   23
10-06 디모데전서 2:4   9   ← 이번 건
```

## 측정 결과 (완료)

프레임을 뜯어 재보니 **y=617에 화면 전폭을 가르는 수평 절단선**이 있다.

```
t=0.2s  seam_y=617  jump=72.7   (위 212.0 / 아래 139.3)
t=2.0s  seam_y=617  jump=72.2
t=4.0s  seam_y=617  jump=67.8
t=6.0s  seam_y=617  jump=65.9
t=7.4s  seam_y=617  jump=63.7
→ 5프레임 전부 1픽셀도 안 움직임
```

행 평균 (급락 구간):
```
615  230.9
616  234.4
617  212.2
618  143.5   ← 두 줄 만에 91 레벨 추락
```

- 위쪽 밴드를 대비 보정해 보니 **진짜 하늘(구름 질감)** — 우리가 덧씌운 scrim 아님.
- 즉 **생성된 배경 이미지 자체가 숲 수관을 수평으로 잘라낸 것.** 나무줄기가 그 선에서 뚝 끊김.

### 결정적 숫자

```
617 / 1920 = 32.1%  ≈ "a third of the way up"
```

`OUTDOOR_TOP` 프롬프트의 문구와 정확히 일치한다. 절단선 위치가 **장면이 아니라 지시문**을 따라갔다.

## 원인 (확정)

### ① 프롬프트가 불가능한 걸 요구한다

`fetch_higgsfield.py:533` `OUTDOOR_TOP`:
> "the horizon LOW, **roughly a third of the way up** ... **Everything with detail or
> texture sits along the bottom and nothing rises into the sky.**"

`SCENES["forest_path"]`:
> "a narrow path winding into a green forest between **tall slender trees**"

숲에는 낮은 수평선이 없고 나무는 반드시 하늘로 솟는다. 두 지시를 동시에 만족시키는
유일한 길이 **수관을 1/3 지점에서 일직선으로 잘라내는 것**이다. 모델은 시킨 대로 했다.

실내는 이미 이 문제를 고쳤다(`INDOOR_TOP`, line 598~601 주석: "An interior has no sky and
no horizon"). **수평선이 없는 야외 장면은 그 수정에서 빠졌다.**

### ② 검사 프롬프트가 이 결함을 명시적으로 면제한다

`_CHECK_PROMPT` 7번은 "화면을 가르는 직선"을 거부하라고 하면서 예외를 둔다:
> "ONLY TWO EXCEPTIONS: **a true horizon where sky meets land or water**, and the line
> where a wall meets a floor."

그리고 머리말·꼬리말이 두 번 더 쐐기를 박는다:
> "do NOT flag a normal single-horizon landscape"
> "Do NOT flag: a normal single-horizon landscape/seascape"

잘린 수관 + 빈 하늘은 검사 모델에게 **"하늘이 땅을 만나는 수평선"으로 읽힌다** → 면제 → 통과.
`gate_ran: 9`, 9번 다 돌았고 9번 다 통과시켰다.

### ③ 이미 있던 측정 게이트가 **그 띠를 안 봅니다** ← 진짜 원인

`fetch_higgsfield.seam_score()` 739~740행:

```python
deltas = [(abs(rows[y+1]-rows[y]), y) for y in range(int(0.05*h), int(0.95*h)-1)
          if not (0.18 * h < y < 0.45 * h)]      # ← 18%~45% 행을 통째로 건너뜀
```

우리 이음매는 **32.1%**, 제외 구간 한가운데. 실측으로 증명:

```
현재 코드 그대로        jump  5.6   18배   74.5%   → ok, 게시됨
제외만 없애면          jump 67.8  206배   32.1%   → stacked, 반려
```

제외 이유로 적힌 건 "말씀 띠의 흰 글자가 밝기 절벽"이었는데,
**`has_seam`은 `generate_checked` 안에서 글자 올리기 전 배경에만 돌아갑니다.**
속을 글자가 애초에 이미지에 없었습니다. 순수한 사각지대.

## 계통적인가 — 게시물 29건 전수 측정

릴리즈 `media` 태그의 mp4 29개 전부 받아서 같은 측정(글자가 닿지 않는 좌우 바깥 열만,
화면 위쪽 45% 안에서 한 행에 동시에 끊기는 열의 비율):

```
10-06 디모데전서 2:4  forest_path   0.924   좋아요  9   ← 신고된 것
09-29 신명기 26:9     snowfall      0.347   좋아요 17   ← 멀쩡한 것 중 최악
10-05 요한삼서 1:2    snowfall      0.233
나머지 26건                        ≤0.217, 중앙값 0.000
```

**단독 이상치입니다. 계통적이지 않습니다.** 차순위의 2.7배.

밝기(jump/ratio)로는 못 가립니다 — 멀쩡한 식탁 모서리 48.8/431배, 진짜 밀밭 수평선 22.9/96배.
금지된 건 대비가 아니라 **선**이라, 직선성을 재야 합니다.

## 고친 것

| 파일 | 내용 |
|---|---|
| `fetch_higgsfield.py` | `ruled_line()`·`has_ruled_line()` 신설, `generate_checked`에 연결 |
| `fetch_higgsfield.py` | `OUTDOOR_TOP` — 수평선 없는 장면에 수평선 요구 금지, 경계는 들쭉날쭉 |
| `fetch_higgsfield.py` | `INTERIOR_CATS` += `cathedral`, `candle`, `flowers_vase` |
| `RULES.md` | F-2a / 2a-1 / 2a-2 신설 |
| `check_rules.py` | 7개 검사 추가 |
| `test_ruled_line.py` | 신규, 12 케이스 (실제 프레임 3장 포함) |
| `test_seam.py` | 사각지대를 "의도된 것"으로 적어둔 주석 정정 |
| `testdata/` | 실제 게시 프레임 3장 (540x960 그레이) |

보정값: 한계 `RULED_FRAC = 0.55`, 창 `0.08 ~ 0.45`, 좌우 바깥 7% 열만.
창은 훑어서 정함 — 0.34~0.40이 3.1배, 0.42~0.50이 2.6배. 넓은 쪽 택함.

**최종 검증: 29건 중 신고된 1건만 반려, 28건 통과. 통과 중 최악 0.347 (한계의 1.6배 여유).**
`./verify.sh` 16개 전부 통과.

## 진행 상황

- [x] 게시물 특정
- [x] 원본 mp4 확보
- [x] 프레임 추출 후 육안 확인
- [x] 결함 수치화 (seam y=617, 고정, jump 72)
- [x] 게이트가 왜 못 막았는지 (seam_score 제외 구간)
- [x] 계통적인지 — 전수 측정 결과 **단독 이상치**
- [x] 수정 + 테스트 + 규칙 문서
- [x] verify.sh 통과
- [ ] 커밋·푸시
- [ ] **다음 게시가 실제로 통과하는지 관측** (배포 후 확인 전엔 "고쳤다" 아님 — 규칙 H-1)

## 미해결 질문

- `clip_spoiled: true` 인데 왜 게시됐나? 폴백 경로 미확인. **이번 변경과 무관**하지만 남아 있음.
- 신고된 게시물을 지울지는 원석님 판단. 지우시면 `metrics.prune_deleted`가 원장을 정리하고
  디모데전서 2:4가 후보 풀로 돌아옵니다.
