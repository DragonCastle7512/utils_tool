import { useState } from "react";

// 문자 세트 상수 정의 (컴포넌트 외부에 배치)
const CHAR_SETS = {
  lowercase: "abcdefghijklmnopqrstuvwxyz",
  uppercase: "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
  numbers: "0123456789",
  specials: "!@#$%^&*-=+?",
};

// 암호학적으로 강력한 난수 기반 문자열 생성 및 피셔-예이츠 셔플 (순수 함수)
function generateRandomString(length, options) {
  // 활성화된 문자 세트 확인
  const activePools = Object.keys(options).filter((key) => options[key]);
  
  if (activePools.length === 0) {
    return "";
  }

  const result = [];
  
  // 1. 각 활성화된 세트에서 최소 1글자씩 먼저 강제 포함
  activePools.forEach((poolKey) => {
    const set = CHAR_SETS[poolKey];
    const randomValues = new Uint32Array(1);
    window.crypto.getRandomValues(randomValues);
    const randomIndex = randomValues[0] % set.length;
    result.push(set[randomIndex]);
  });

  // 2. 전체 문자 풀(Pool) 합성
  let combinedPool = "";
  activePools.forEach((poolKey) => {
    combinedPool += CHAR_SETS[poolKey];
  });

  // 3. 남은 길이만큼 전체 풀에서 랜덤 선택하여 추가
  const remainingLength = length - result.length;
  if (remainingLength > 0) {
    const randomValues = new Uint32Array(remainingLength);
    window.crypto.getRandomValues(randomValues);
    for (let i = 0; i < remainingLength; i++) {
      const randomIndex = randomValues[i] % combinedPool.length;
      result.push(combinedPool[randomIndex]);
    }
  }

  // 4. 결과 배열 무작위 셔플 (Fisher-Yates Shuffle)
  const shuffleArray = new Uint32Array(result.length);
  window.crypto.getRandomValues(shuffleArray);
  for (let i = result.length - 1; i > 0; i--) {
    const j = shuffleArray[i] % (i + 1);
    const temp = result[i];
    result[i] = result[j];
    result[j] = temp;
  }

  return result.join("");
}

export default function RandomStringGenerator() {
  const [length, setLength] = useState(12);
  const [options, setOptions] = useState({
    lowercase: true,
    uppercase: false,
    numbers: true,
    specials: false,
  });
  
  // 초기 렌더링 시점에 상태 초기화 함수를 통해 즉시 문자열 생성
  const [generatedString, setGeneratedString] = useState(() => 
    generateRandomString(12, {
      lowercase: true,
      uppercase: false,
      numbers: true,
      specials: false,
    })
  );
  
  const [copied, setCopied] = useState(false);
  const [spinning, setSpinning] = useState(false);

  // 길이 입력 제한 핸들러 (슬라이더 및 직접 입력창용)
  const handleLengthChange = (value) => {
    let numValue = parseInt(value, 10);
    if (isNaN(numValue)) return;
    if (numValue < 6) numValue = 6;
    if (numValue > 30) numValue = 30;
    
    setLength(numValue);
    setGeneratedString(generateRandomString(numValue, options));
  };

  // 체크박스 핸들러
  const handleCheckboxChange = (key) => {
    const nextOptions = {
      ...options,
      [key]: !options[key],
    };
    setOptions(nextOptions);
    setGeneratedString(generateRandomString(length, nextOptions));
  };

  // 복사 핸들러
  const handleCopy = async () => {
    if (!generatedString) return;
    try {
      await navigator.clipboard.writeText(generatedString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("클립보드 복사 실패:", err);
    }
  };

  // 수동 재생성 핸들러
  const handleRegenerate = () => {
    setSpinning(true);
    setGeneratedString(generateRandomString(length, options));
    setTimeout(() => setSpinning(false), 600);
  };

  // 강도(Strength) 평가 로직
  const getStrength = () => {
    const activeCount = Object.values(options).filter(Boolean).length;
    if (activeCount === 0 || length < 6) return { label: "없음", score: 0, class: "" };
    
    // 강도 점수 산출
    let score = 1;
    if (length >= 10) score += 1;
    if (length >= 15) score += 1;
    if (activeCount >= 3) score += 1;
    if (activeCount === 4 && length >= 12) score += 1;

    if (score <= 2) {
      return { label: "약함 (Weak)", score: 1, class: "weak" };
    } else if (score <= 4) {
      return { label: "보통 (Medium)", score: 2, class: "medium" };
    } else {
      return { label: "강함 (Strong)", score: 3, class: "strong" };
    }
  };

  const strength = getStrength();

  return (
    <div className="generator-container">
      <div className="generator-card">
        <div className="generator-header">
          <h2 className="generator-title">랜덤 문자열 생성기</h2>
          <p className="generator-subtitle">
            암호학적으로 안전한 무작위 문자열을 브라우저 로컬 환경에서 즉시 생성합니다.
          </p>
        </div>

        {/* 결과값 및 액션 버튼 */}
        <div className="result-box-container">
          <span className={`result-text ${!generatedString ? "empty" : ""}`}>
            {generatedString || "문자 종류를 1개 이상 선택해 주세요."}
          </span>
          <div className="action-buttons">
            <button
              className={`icon-btn copy-btn ${copied ? "copied" : ""}`}
              onClick={handleCopy}
              disabled={!generatedString}
              title={copied ? "복사 완료!" : "클립보드 복사"}
            >
              {copied ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              )}
            </button>
            <button
              className={`icon-btn refresh-btn ${spinning ? "spinning" : ""}`}
              onClick={handleRegenerate}
              disabled={Object.values(options).filter(Boolean).length === 0}
              title="새 문자열 생성"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
              </svg>
            </button>
          </div>
        </div>

        {/* 길이 설정 (슬라이더 및 입력창 연동) */}
        <div className="control-group">
          <div className="control-label">
            <span>길이 설정</span>
            <span className="control-value">{length} 자</span>
          </div>
          <div className="slider-wrapper">
            <input
              type="range"
              min="6"
              max="30"
              value={length}
              onChange={(e) => handleLengthChange(e.target.value)}
              className="slider-input"
            />
            <input
              type="number"
              min="6"
              max="30"
              value={length}
              onChange={(e) => handleLengthChange(e.target.value)}
              className="number-input"
            />
          </div>
        </div>

        {/* 문자 구성 체크박스들 */}
        <div className="control-group">
          <div className="control-label">
            <span>문자 구성</span>
          </div>
          <div className="options-grid">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={options.numbers}
                onChange={() => handleCheckboxChange("numbers")}
              />
              <span>숫자 (0-9)</span>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={options.lowercase}
                onChange={() => handleCheckboxChange("lowercase")}
              />
              <span>영문 소문자 (a-z)</span>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={options.uppercase}
                onChange={() => handleCheckboxChange("uppercase")}
              />
              <span>영문 대문자 (A-Z)</span>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={options.specials}
                onChange={() => handleCheckboxChange("specials")}
              />
              <span>특수문자 (!@#$%^&*-=+?)</span>
            </label>
          </div>
        </div>

        {/* 강도 표시기 */}
        <div className="strength-section">
          <div className="strength-header">
            <span>비밀번호 안전도</span>
            <span className={`strength-status ${strength.class}`}>{strength.label}</span>
          </div>
          <div className="strength-bar-container">
            <div className={`strength-bar ${strength.score >= 1 ? strength.class : ""}`} />
            <div className={`strength-bar ${strength.score >= 2 ? strength.class : ""}`} />
            <div className={`strength-bar ${strength.score >= 3 ? strength.class : ""}`} />
          </div>
        </div>

        {/* 경고 알림 */}
        {Object.values(options).filter(Boolean).length === 0 && (
          <p className="warning-message">최소 하나 이상의 문자 구성을 선택해야 생성할 수 있습니다.</p>
        )}
      </div>
    </div>
  );
}
