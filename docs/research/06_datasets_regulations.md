---
type: Source
title: 공개 데이터셋·규제 조사
description: 검증·학습용 공개 배터리 데이터셋과 BMS 관련 규제(EU 배터리 규정)
tags: [research, datasets, regulation, eu-battery-passport]
timestamp: 2026-10-15T00:00:00Z
---

# 공개 데이터셋·규제

## 1. 공개 배터리 데이터셋

| 데이터셋 | 내용 | 라이선스 | 검증 |
|---|---|---|---|
| NASA PCoE (Randomized and Recommissioned Battery Dataset) | 무작위 부하 노화 | 미국 정부 저작물 (data.gov 기재) | 🟡 |
| NASA PCoE 기본 노화 데이터 | 18650 노화 | 확인 필요 | ⚪ |
| CALCE (Maryland) | 다양한 셀 사이클링 | 확인 필요 | 🟡 내용만 |
| Oxford Battery Degradation Dataset 1 | 소형 LCO 파우치, 40°C, Artemis 주행 사이클 | 확인 필요 | 🟡 내용만 |
| Severson et al. (MIT/Stanford/TRI) | 124개 LFP/흑연 18650, 급속충전 프로토콜 | 확인 필요 | 🟡 내용만 |
| 데이터셋 비교 자료 | Volta Foundation 비교표, Edinburgh 리뷰 "Li-ion battery data and where to find it", GitHub 목록(lappemic/open-source-battery-data) | - | 🟡 |

**주의**: 이번 조사에서 대부분의 데이터셋 라이선스를 확인하지 못했다. 사내 평가셋에 넣기 전에 각 다운로드 페이지에서 라이선스를 확인하고 [라이선스 표](/research/05_licenses_dependencies.md)에 추가한다. ISC 전용 공개 데이터셋은 찾지 못했다.

**용도**: RUL·SOH 알고리즘 기준선 검증, 합성 데이터(M11) 현실성 비교, 평가셋 보강. 사내 데이터가 주이고 공개 데이터는 보조다.

## 2. EU 배터리 규정 (Regulation (EU) 2023/1542)

| 항목 | 내용 | 검증 |
|---|---|---|
| 배터리 여권 | EV 배터리 여권이 2027-02-18부터 의무, 데이터 항목 71개 중 51개 요구 (Article 77, Annex XIII) | 🟡 벤더 블로그 |
| BMS 유래 데이터 | SOH, SOC, 사이클 수 등 사용 중 갱신되는 개별 배터리 데이터를 BMS에서 얻어 제조사 텔레매틱스로 전달한다는 해석 | 🟡 |
| 갱신 주기 | 연속 BMS 피드가 의무인지에 대해 해석이 엇갈림. 집행위는 정보 성격과 비례성에 따라 정한다는 입장으로 보도됨 | 🟡 충돌 |
| 접근 제한 | 실시간 SOH와 BMS 정보는 인증된 사용자만 접근 | 🟡 |
| BMS 탑재 | 2024-05부터 해당 배터리에 SOH·SOC 추정이 가능한 BMS 탑재 요구 | 🟡 |
| EV 배터리 정의 | M, N, O 범주 차량의 구동 배터리, 또는 L 범주에서 25 kg 초과 | 🟡 |

**주의**: 규정 원문(Annex XIII)과 이행법(측정 방법, 갱신 주기)을 직접 확인하지 않았다. 추가 기능 F11을 착수하기 전에 원문을 확인한다.

**시사점**: SOH 산출 근거와 추적성(어떤 알고리즘·파라미터 버전으로 계산했는지)이 규제 대응에 쓰일 수 있다. 우리 계획의 실행 기록(run.json), 파라미터 버전 관리와 잘 맞는다.

## 3. 기능안전·기타 표준 (조사 필요)

ISO 26262(차량 기능안전), IEC 62619/62133(2차 전지 안전), UN ECE R100(전기차 안전), ASPICE는 이번에 조사하지 않았다. 사내 적용 여부를 확인한 뒤(미결 질문 Q9) 산출물 형식에 반영한다.

## 출처

- https://catalog.data.gov/dataset/randomized-and-recommissioned-battery-dataset
- https://github.com/lappemic/open-source-battery-data
- https://volta.foundation/comparison-of-open-datasets-for-lithium-ion-battery-testing/
- https://www.pure.ed.ac.uk/ws/files/206117798/Batteries_Li_ion_battery_data_and_where_to_find_it_final_draft_.pdf
- https://arxiv.org/pdf/2309.14125
- https://codibly.com/blog/articles/eu-battery-regulation-passport-bess-operators
- https://www.sibros.tech/post/navigating-the-eu-battery-passport-what-oems-need-to-know-before-2027
- https://elevenes.com/news/the-eu-battery-passport-what-it-requires-who-benefits-who-pays/
- https://www.khl.com/news/an-introduction-to-digital-battery-passports/8033907.article
- https://automotive.messefrankfurt.com/global/en/news-insights/industry-insights/european-battery-passport.html
