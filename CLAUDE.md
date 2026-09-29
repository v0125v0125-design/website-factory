# website-factory 에서 일할 때

**먼저 `문서/작업기록.md` 를 읽으십시오.**

무엇을 왜 그렇게 정했는지, 이미 확인해서 다시 할 필요가 없는 것이 거기 적혀 있습니다.
대화는 컴퓨터를 옮기면 따라오지 않지만 그 파일은 따라옵니다.

특히 이것만은 다시 하지 마십시오 — 지어 보고 브라우저로 확인해서 잡은 것들입니다.

  · HSL 채도로 무채색을 판단하지 마십시오 (크림색의 채도는 1.0 입니다).
  · 바탕색을 "가장 많이 쓰인 배경색"으로 고르지 마십시오.
  · JSON-LD 를 Jinja 자동 이스케이프에 태우지 마십시오.
  · 밝은 사진 위 히어로의 덮개를 옅게 하지 마십시오.
  · 마스터를 복사해 색만 바꾸지 마십시오 — 업종마다 사는 이유가 다릅니다.
  · 확인할 수 없는 숫자(누적 고객·만족도·업력)를 화면에 세우지 마십시오.
  · 받는 곳이 없는 문의 폼이 "접수되었습니다" 라고 말하게 하지 마십시오.
    받는 곳(storefront.json 의 submission)이 비면 버튼을 잠그고 다른 길을 안내합니다.
  · 첫 신청 화면에서 제작 자료를 다 받으려 하지 마십시오 — 두 단계로 나눠 두었습니다.

원페이지·5페이지 홈페이지를 템플릿으로 찍어 파는 공장입니다.
구조와 쓰는 법은 `README.md` 에 있습니다. 아래에는 **지켜야 할 것**만 적습니다.

## 이 공장이 지키는 것

1. **지어내지 않는다.** 주문서에 없는 사실을 원고에 쓰지 않습니다.
   재료가 없으면 섹션을 빼고, 속장의 본체가 없으면 그 장 자체를 내지 않고
   메뉴에서도 지웁니다. 사람이 채울 자리는 `[...]` 로 남기고 납품 메모에 올립니다.
2. **근거를 남긴다.** 템플릿을 왜 골랐는지, 색을 어디서 가져왔는지
   `build_report.json` 과 `납품메모.md` 에 적습니다. 고객에게 설명할 수 있어야 팝니다.
3. **색은 다시 잰다.** 팔레트를 만든 뒤 대비를 검사합니다
   (본문 7:1, 흐린 글씨·버튼 글자 4.5:1). 이 기준은 시험으로 잠겨 있습니다.
4. **레퍼런스에서 가져오는 것은 치수뿐이다.** 색·서체 이름·모서리·여백만 봅니다.
   문장·이미지·마크업을 베끼지 않습니다.

## 손대기 전에

```bash
python tools/doctor.py                    # 이 컴퓨터에 무엇이 없는지
python -m pytest -q                       # 357개
python -m factory.cli build examples/customers/a-gonggan.json -o out/a --offline --clean
python -m factory.cli serve out/a
```

## 자주 쓰는 도구

```
python tools/doctor.py [--build]        이 컴퓨터에서 공장이 도는지 본다
python tools/build_previews.py _site    견본 + 판매 홈페이지를 한 폴더에
tools/publish_preview.sh                gh-pages 로 손수 발행
python storefront/build.py _site/store  판매 홈페이지만 짓는다
python tools/shoot_sample_thumbs.py     판매 페이지 샘플 썸네일 다시 찍기
python tools/make_cleaning_photos.py    청소 견본 그림 다시 그리기
python tools/make_company_photos.py     기업 견본 그림 다시 그리기
```

`tests/test_theming.py::test_every_preset_produces_readable_tokens` 와
`tests/test_build.py` 의 링크·문법 검사는 상품 품질을 지키는 그물입니다.
새 템플릿이나 업종 기본값을 넣으면 여기서 먼저 걸립니다.

## 스타일이 정해지는 순서

주문서에 못 박은 값 → 레퍼런스에서 읽어 낸 값 → 업종 기본값(`factory/theming.py` 의 `PRESETS`).
앞의 것이 있으면 뒤의 것을 쓰지 않습니다. 이 순서를 바꾸지 마십시오 —
고객이 지정한 색이 레퍼런스에 밀리면 항의가 들어옵니다.
