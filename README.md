# NX Section Layer Thickness Analyzer

NX(Unigraphics)에서 캡처한 제품 단면 스크린샷을 불러와, OpenCV 기반
자동 엣지 검출 + 사용자 수직선 클릭 방식으로 적층 부품의 두께를 측정하고,
엑셀 스타일 테이블에 축적하여 `.xlsx` 파일로 내보내는 PyQt6 데스크톱
프로그램입니다.

## 기능

- **드래그 & 드롭**: NX 스크린샷(PNG/JPG/BMP/TIFF)을 캔버스에 바로 드롭
- **스케일 보정**: 두 점 클릭 + 실제 mm 입력으로 픽셀↔mm 비율 저장
- **하이브리드 레이어 검출**: Canny 엣지 검출 + 수직 측정선을 이용해
  레이어 경계를 자동 분할, 픽셀/밀리미터 두께 동시 산출
- **실시간 테이블**: 우측의 Excel 스타일 테이블(Layer / Top / Bottom /
  Thickness(px) / Thickness(mm))에 즉시 반영, 레이어 이름 편집 가능
- **Excel 내보내기**: pandas + openpyxl로 메타(mm/pixel, 이미지 경로)와
  측정 테이블을 포함한 `.xlsx` 저장

## 설치

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 실행

```bash
python main.py
```

## 사용 순서

1. NX에서 단면을 캡처한 이미지를 캔버스에 드래그&드롭하거나
   `파일 → 이미지 열기…` 로 불러옵니다.
2. `기준선 설정` 버튼을 누른 뒤 단면 내에서 이미 실제 길이를 알고 있는 두
   점(예: 치수선 양 끝, 제품 폭 등)을 클릭하고, 다이얼로그에 실제 mm 값을
   입력합니다.
3. `측정선 그리기` 버튼을 누르고 적층부를 가로지르는 두 점을 클릭합니다.
   기본적으로 Shift를 누르지 않으면 두 번째 점은 첫 번째 점과 동일한 X로
   스냅되어 완전한 수직선이 그어집니다.
4. 자동으로 엣지가 검출되고 우측 테이블에 `Layer 1 … N`이 추가됩니다. 필요
   시 레이어 이름을 셀에서 편집하거나, `선택 행 삭제`로 잘못 검출된 행을
   지울 수 있습니다.
5. `Excel로 내보내기` 버튼으로 결과를 `.xlsx`로 저장합니다.

## 프로젝트 구조

```
sc_auto_measure/
├── main.py                  # PyQt6 엔트리포인트
├── requirements.txt
├── app/
│   ├── core/
│   │   ├── measurement.py        # Layer / Measurement 데이터 모델
│   │   ├── scale_calibrator.py   # 픽셀 ↔ mm 변환
│   │   ├── edge_detector.py      # OpenCV Canny + 수직선 프로파일
│   │   └── excel_exporter.py     # pandas + openpyxl 저장
│   └── gui/
│       ├── main_window.py        # 좌 캔버스 / 우 테이블 레이아웃
│       ├── image_canvas.py       # 드래그&드롭, 클릭, 오버레이
│       ├── measurement_table.py  # QTableWidget 래퍼
│       └── scale_dialog.py       # 실제 길이 입력 다이얼로그
└── tests/
    └── test_core.py              # 핵심 모듈 유닛 테스트
```

## 테스트

```bash
pip install pytest
pytest
```

## 메모

- `측정선 그리기`는 기본적으로 수직으로 스냅됩니다. 자유 각도로 그리려면
  두 번째 클릭 시 **Shift** 키를 누르세요.
- 캔버스는 마우스 휠로 확대/축소, 드래그로 스크롤할 수 있습니다(탐색 모드).
