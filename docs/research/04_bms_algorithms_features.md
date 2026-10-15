---
type: Source
title: BMS 알고리즘·신규 기능 조사
description: 요구 R3, O2 설계 근거 — 오픈소스 BMS, ISC 감지, 스웰링, RUL, 만충 시간
tags: [research, bms, isc, swelling, rul, ttf, foxbms]
timestamp: 2026-10-15T00:00:00Z
---

# BMS 알고리즘·신규 기능

## 1. 오픈소스 BMS 참고: foxBMS (Fraunhofer IISB)

| 항목 | 내용 | 검증 |
|---|---|---|
| 상태 추정 모듈 | SOC, SOE, SOH, SOF 알고리즘을 감싸는 래퍼. 알고리즘은 설정 파일(`bms.json`)에서 선택 | ✅ 공식 문서 |
| 라이선스 | 상태 추정 소스 헤더가 `SPDX-License-Identifier: BSD-3-Clause` | ✅ 파일 단위 (저장소 전체 확인 필요) |
| AI | LSTM SOC 추정을 오프라인 학습 후 장치에서 실행한 사례 (논문) | 🟡 |
| 활용 | 모듈 구조, 상태 추정 API 설계, 테스트 방식 참고용. 코드 차용 시 파일별 라이선스 확인 | - |

## 2. 내부 단락(ISC/ISD) 감지

| 방법 | 요지 | 출처 | 검증 |
|---|---|---|---|
| pseudo-OCV 1차 차분 (모델 프리) | 단자 전압, 전류, 오프라인 R0–SOC 표만 사용. ISC가 만드는 고주파 편차를 저주파 분극 변화와 분리. 실험 10건 + 오탐 1건에서 100% 감지 보고 | arXiv 2506.13394 | 🟡 |
| 평균차 모델 + 적응 예측 | 셀 전압 이상으로 온라인 진단, 실차 데이터 적용 | Batteries 2022 (Cao et al.) | 🟡 |
| 팩 내 일관성 + RLS | 평균차 모델에 재귀 최소제곱 | Tsinghua ECS 초록 | 🟡 |
| 팩 단자 전압 기반 | 셀 전압이 없을 때 고장 셀 OCV와 단락 저항 추정 | Energies 2018 | 🟡 |
| 자가방전 이상 | 이웃 셀 대비 SOC 발산으로 이상 자가방전 감지 | 미국 특허 12306262 | 🟡 |
| 검증 데이터 | 재현 가능한 내부 단락을 만들기 어려워 **외부 저항으로 모사**하는 경우가 많음 | INL 보고서 | 🟡 |
| ML | 랜덤 포레스트·RF-NN 비교, 전기화학-열-ISC 결합 모델로 합성 데이터 | PHM Society 논문 2편 | 🟡 |
| **공개 데이터셋** | 이번 조사에서 ISC 전용 공개 데이터셋은 찾지 못함 | - | - |

## 3. 스웰링

| 항목 | 요지 | 출처 | 검증 |
|---|---|---|---|
| 현상학 모델 | 1-D 힘 모델, 1차 이완 모델, 3-D 팽창 모델. 이완 모델이 휴지 중 동적 팽창을 예측 | Oh et al., J. Power Sources 2016 (U. Michigan) | 🟡 |
| 데이터 | 전압·팽창을 함께 측정한 데이터와 축소 차수 모델 (Michigan Deep Blue) | Michigan | 🟡 |
| 원인 분해 | 두께 변화는 주로 흑연 삽입 팽창. 2C 이상에서는 발열에 의한 열팽창이 크게 기여 | Auburn 포스터 | 🟡 |
| 가스 팽창 | 파우치 가스 팽창(bulging)의 균질화 기계 모델, 배터리 시뮬레이션에 포함 가능 | Giudici et al., arXiv 2411.13197 (Oxford) | 🟡 |
| 가역 팽창 | 기존 안전 평가 모델에 SOC 의존 두께 변화가 빠져 있음 | Höschele & Ellersdorfer, Batteries 2023 | 🟡 |
| BMS 신호로 활용 | 팽창 정보를 SOC/SOH 추정 입력으로 사용 (특히 실리콘 음극) | 미국 특허 12206098 | 🟡 |
| **갭** | 파우치 두께를 ECM 기반 SOC/SOH 관측기와 융합한 양산 BMS 알고리즘 공개 자료는 찾지 못함 | - | - |

**결론**: 가역(SOC·온도) + 비가역(SEI·가스) 분리 모델을 기준으로 삼는다. 두께·압력 센서 데이터가 없으면 검증이 불가능하므로 데이터 요청이 선행돼야 한다.

## 4. SOH·RUL·만충 시간

| 항목 | 요지 | 검증 |
|---|---|---|
| 전압 기반 SOH | 전압 제어 ECM(쿨롱 카운팅 대신 전압 입력), 자기 보정, 노화에 강건, 임의 부하에서 SOH 추정 (Schmider et al., Offenburg) | 🟡 |
| RUL | 경험적 용량 감소 모델 + 파티클 필터, GP 회귀, 딥러닝(데이터 증강 하이브리드 등) 다수 | 🟡 / ⚪ |
| 만충 시간 | 충전 프로파일 + ECM 전진 시뮬레이션, 테이블 근사가 일반적 | ⚪ (추가 조사 필요) |

## 출처

- https://iisb-foxbms.iisb.fraunhofer.de/foxbms/docs/latest/software/modules/application/algorithm/state-estimation/state-estimation.html
- https://iisb-foxbms.iisb.fraunhofer.de/foxbms/docs/latest/_static/doxygen/src/html/state__estimation_8c.html
- https://www.vde-verlag.de/proceedings-en/565245089.html
- https://arxiv.org/pdf/2506.13394
- https://doaj.org/article/9b6420f6bad04af5906a0a7a9df76962
- https://ecs.confex.com/ecs/231/webprogram/Paper97521.html
- https://remotecenter.postech.ac.kr/bitstream/2014.oak/94970/1/energies-11-01669.pdf
- https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12306262
- https://inldigitallibrary.inl.gov/sites/sti/sti/Sort_1809.pdf
- https://papers.phmsociety.org/index.php/phme/article/download/3980/2403
- https://papers.phmsociety.org/index.php/phme/article/download/4035/2422
- https://arxiv.org/pdf/2411.13197
- https://public.websites.umich.edu/~annastef/papers_battery\Oh2016JPS.pdf
- https://deepblue.lib.umich.edu/data/downloads/3197xm284
- https://www.eng.auburn.edu/auepri/img/Poster PDFs/ip2025liionthermalstress.pdf
- https://graz.elsevierpure.com/files/72052965/batteries-09-00417-v2.pdf
- https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12206098
- https://opus.hs-offenburg.de/solrsearch/index/search/searchtype/authorsearch/author/Schmider%2C+David
- https://arxiv.org/pdf/2603.27186
