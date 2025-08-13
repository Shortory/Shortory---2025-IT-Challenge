<h2 align="center">⚡️ Reaction-to-Shorts : 시청자의 반응으로 생성하는 하이라이트 쇼츠 자동화 서비스 </h2>

<br/>

<p align="center">
  <img src="https://github.com/user-attachments/assets/958b828e-98cd-4c80-94cc-713e2299a74b"  width="200" />
</p>

<br/>
<h4 align="center">Shortory는 시청자의 감정과 댓글의 타임스탬프를 분석해 영상 속 하이라이트를 자동으로 추출하는 숏폼 제작 웹 서비스입니다.</strong></h4>


<img width="2580" height="1300" alt="image" src="https://github.com/user-attachments/assets/49a27316-465b-4965-99a5-8e94c364af34" />
<img width="2580" height="1408" alt="image" src="https://github.com/user-attachments/assets/afcdcc89-a8d9-48a1-94fd-15545568495f" />
<img width="2580" height="1384" alt="image" src="https://github.com/user-attachments/assets/f27aabe9-a052-4d37-81d8-83df1c3d7324" />
<img width="2580" height="1306" alt="image" src="https://github.com/user-attachments/assets/7b484919-8061-4515-943e-857a0e74dee5" />

 

<br/>
<br/>

## 프로젝트 개요
<br/>
<p align="center">
  <img src="https://github.com/user-attachments/assets/72bcdc35-3dca-419b-812f-522ff8620ef9" alt="아키텍처" width="70%">
</p>


**숏토리(Shortory)** 는 서로 독립적으로 동작하는 두 가지 방식으로 숏폼 하이라이트 영상을 자동 생성합니다.
- 반응 기반 모드: 웹캠으로 수집한 시청자의 표정·시선 데이터를 분석해 집중도/감정 반응이 두드러진 구간을 자동 선정하여 클립을 생성합니다.
- 댓글 타임스탬프 기반 모드: 유튜브 댓글에 포함된 타임스탬프를 수집·집계해 언급 빈도가 높은 구간을 하이라이트로 추출합니다.

<br />

## Creator & Reviewer Flow

<img width="1526" height="640" alt="image" src="https://github.com/user-attachments/assets/ca6d53b1-e3e5-48f4-9e5b-bd8fc5b68d43" />

<br />

## ⭐️ 주요 기능 
### 1. 감정 기반 숏츠 생성

시청자의 **웹캠 영상을 프레임 단위로 분석** 하여, 얼굴에서 추출한 감정과 집중도를 바탕으로 5가지 감정(`happy`, `sad`, `angry`, `neutral`, `surprise`) 중 가장 높은 확률의 감정을 기반으로 숏폼 영상을 자동 생성합니다.

### 2. 타임스탬프 기준 숏츠 생성

**유튜브 댓글 속 타임스탬프** 를 자동으로 추출하고, **가장 많이 언급된 상위 5개 구간을 기준으로** 하이라이트 클립 영상을 자동 생성합니다.

| 기능 | 설명 |
| --- | --- |
| 🔍 댓글 분석 | 유튜브 댓글에서 타임스탬프 수집 → 그룹화 → 빈도 계산 → 상위 5개 → 클립 생성 |
| 🧠 감정/집중 분석 | 표정 분석과 집중도 분석을 통해 감정 몰입도 높은 장면 감지 |
| ✂️ 클립 생성 | ±10초 범위 영상 추출 |
| 📂 숏폼 분류 | 감정별 숏폼 정렬 및 다운로드 |


<br />

### ⚙️ Architecture 구조도

<p align="center">
  <img src="<img width="1336" height="799" alt="image" src="https://github.com/user-attachments/assets/6fc4df2e-ee90-42b1-ab25-82515a238610" />">
</p>


<br />

### 타임스탬프(timestamp) 정의

**타임스탬프**는 영상 속 특정 시점을 나타내는 시간 정보로, 일반적으로 `"00:45"`, `"3:15"`, `"12:34"`와 같은 **`분:초` 또는 `시:분:초` 형식**으로 표현됩니다.

유튜브 댓글에서는 시청자들이 인상 깊었던 장면에 대해 “**10:43 아이유 레전드**”처럼 타임스탬프를 남기며 명장면을 직접 표시합니다.

> ✅ 숏토리에서는 이 댓글 속 타임스탬프를 자동 감지하여, 시청자가 선택한 하이라이트 구간을 숏폼 영상으로 자동 생성합니다.
>

<img src="https://github.com/user-attachments/assets/fb7c50c5-995d-4a43-9227-73cd851575a2" alt="타임스탬프 예시" width="60%">

출처: 뿅뿅지구오락실3 tvN D ENT 유튜브 영상 댓글 화면 캡처
<br>
https://www.youtube.com/watch?v=aLF3YHUvm7E 


<br />

## 감정 인식 모델 생성 과정
MobileNetV2 기반 전이 학습(Transfer Learning)과 파인튜닝(Fine-tuning)을 활용하여 감정 인식 모델을 구축하였습니다.
emotion_tl2_model.h5 모델을 다운받아 실행 가능합니다.

아래 버튼을 클릭하면 Colab에서 직접 확인할 수 있습니다:

👉 [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1x7WFKhHi4zHMAH6r4oPw4L2PdZCwyqqW?usp=sharing)

### 1. 데이터 구성
- **데이터셋**: FER2013
- **클래스**: angry, happy, neutral, sad, surprise (총 5개 감정)

### 2. 모델 구조
- **기반 모델**: MobileNetV2 (ImageNet 사전학습)

### 3. 학습 전략
- **1단계 (전이 학습)** →  **2단계 (파인튜닝)** → **클래스 불균형 보정** → **콜백**

#### 📉 Phase 1 Train VS Validation
<img width="600" alt="image" src="https://github.com/user-attachments/assets/c5567d31-d10f-4719-9613-0a7caa605ceb" />

#### 📉 Phase 2 Fine-tuning
<img width="600" alt="image" src="https://github.com/user-attachments/assets/3e408dd9-1cd0-4607-967f-db3828e4e2aa" />


<br />





<p align="center"><strong>
  
## 💚 팀원 소개

<table align="center">
  <thead>
    <tr align="center">
      <th>FULLSTACK</th>
      <th>AI & BACKEND</th>
      <th>BACKEND</th>
      <th>AI & FRONTEND</th>
    </tr>
  </thead>
  <tbody>
    <tr align="center">
      <td>황채원</td>
      <td>문성원</td>
      <td>박시현</td>
      <td>한송미</td>
    </tr>
    <tr align="center">
      <td><img src="https://github.com/user-attachments/assets/0a99a63f-3aee-4581-b3c6-f8d7a3017a27" width="100"/></td>
      <td><img src="https://github.com/user-attachments/assets/bb1d2e9a-f1e6-4a12-ba8c-19bcfcab2492" width="100"/></td>
      <td><img src="https://github.com/user-attachments/assets/ce52b7d9-39cc-4004-ac1b-9caf91b4b8e6" width="100"/></td>
      <td><img src="https://github.com/user-attachments/assets/07d9bece-9517-4d7f-9bf3-b553fbb877cb" width="100"/></td>
    </tr>
    <tr align="center">
      <td><a href="https://github.com/ChaewonHwang-01">ChaewonHwang-01</a></td>
      <td><a href="https://github.com/m-seongwon">m-seongwon</a></td>
      <td><a href="https://github.com/Sihyun32">Sihyun32</a></td>
      <td><a href="https://github.com/0weny">0weny</a></td>
    </tr>
  </tbody>
</table>
