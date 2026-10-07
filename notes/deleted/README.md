# 삭제된 게시물 — 측정값은 남긴다

인스타그램에서 지운 게시물은 `metrics.prune_deleted()`가 원장에서 뺍니다(RULES C4b).
그 순간 **그 게시물이 받은 숫자도 같이 사라집니다.** 2026-10-07 §17 이후 원장은 조회·공유를
83건 들고 있고, 비용 결정(E-0c·E-0d)이 그 위에 서 있습니다. 한 건이라도 증거는 증거입니다.

그래서 삭제는 **지우는 것이 아니라 옮기는 것**입니다 → `metrics_deleted.json`.
`metrics.json`에서는 빠지므로 리포트·선택 로직에는 영향이 없고, 증거는 남습니다.

이 디렉터리에는 **삭제 직전 손으로 뜬 API 스냅샷**이 들어갑니다(원장보다 더 많은 필드).

## 18632946685003547 — 디모데전서 2:4 (2026-10-06 아침)

```
permalink  https://www.instagram.com/reel/DeIOmzNkYbd/
조회 321  좋아요 19  댓글 1  공유 0  리포스트 0     (삭제 직전 2026-10-07)
duration 7.67s  segments 1  scene forest_path  theme 사랑
gate_passed false  gate_ran 9        ← 게이트가 9번 거부한 렌더가 그대로 나갔다
```

**삭제 사유 — 화면을 가로지르는 직선(ruled line).** 원석님이 지적하셨고, 게시된 영상을
받아 프레임을 뽑아 확인했습니다. 스크린샷 로딩 artifact가 아니라 **파일 안에 있습니다**:
720×1280 프레임의 **y=411px(32%)** 에서 폭 전체가 끊기고, 위는 평평한 회색 하늘, 아래는 숲.
구절 두 줄이 정확히 그 띠 안에 앉아 있습니다.

원인은 `test_clearance.py`에 기록된 2주짜리 사고입니다 — 여백 게이트의 한계값이 **게시된**
프레임에서 읽은 절대 edge-energy였는데 그걸 **원본 렌더**(더 선명하고 큼)에 적용해서
09-22~10-06 내내 `clearance below the verse: -0.0%`만 찍혔습니다. 아무것도 통과하지 못하니
`generate_checked`는 매번 예산을 소진하고 **거부한 렌더를 그대로 게시**했습니다.
최근 30건 중 26건이 `gate_passed=false`입니다. forest_path는 고른 게 아니라 시계가 멈췄을 때
순번이 여섯 번째였을 뿐입니다.

**게이트는 지금 이 프레임을 잡습니다** — 게시된 파일로 직접 돌려 확인(2026-10-07):

```
has_ruled_line → True   ruled line: 97% of columns break at 411px (limit 55%) → RULED
too_cramped    → True   clearance below the verse: -0.0% (need 18%)
has_seam       → False  jump 8.4 (limit 7.0), 17x typical (limit 30x) → ok   ← 이것만으로는 못 잡았다
```

`has_seam`은 **톤 점프**를 보고 이 그림은 톤이 아니라 **직선**이 문제라, `has_ruled_line`이
따로 필요했던 것이 수치로 확인됩니다(17x < 30x로 통과).
