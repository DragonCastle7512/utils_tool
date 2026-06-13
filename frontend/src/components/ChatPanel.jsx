import React, { useState, useRef, useEffect } from "react";

// 대화형 기획 채팅 패널 컴포넌트
export default function ChatPanel({
  session,
  messages,
  onSendMessage,
  loading,
  framework,
  onChangeFramework
}) {
  const [input, setInput] = useState("");
  const [selectedImage, setSelectedImage] = useState(null); // { file, base64, type }
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // 메시지가 추가되면 최하단으로 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onloadend = () => {
      setSelectedImage({
        file: file,
        base64: reader.result.split(",")[1], // Strip out 'data:image/...;base64,' prefix
        type: file.type
      });
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveImage = () => {
    setSelectedImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if ((!input.trim() && !selectedImage) || loading) return;
    onSendMessage(input, selectedImage);
    setInput("");
    setSelectedImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  if (!session) {
    return (
      <div className="chat-placeholder">
        <svg
          className="placeholder-logo"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <h2>AI 웹사이트 빌더 기획 대화</h2>
        <p>왼쪽 사이드바에서 기획 히스토리를 선택하거나 새 기획을 시작해 주세요.</p>
      </div>
    );
  }

  return (
    <div className="chat-panel">
      {/* 채팅 상단 정보 영역 */}
      <header className="chat-header">
        <div className="header-info">
          <h2>{session.title}</h2>
          <div className="session-status-container">
            <span className={`status-dot ${session.status.toLowerCase()}`}></span>
            <span className="status-text">
              {session.status === "CLARIFYING"
                ? "상세 요구사항 기획 중"
                : session.status === "DESIGNING"
                ? "코드 생성 에이전트 동작 중"
                : "웹사이트 구축 완료"}
            </span>
          </div>
        </div>

        {/* 프레임워크 선택 옵션 */}
        <div className="framework-selector">
          <label htmlFor="framework">대상 기술:</label>
          <select
            id="framework"
            value={framework}
            onChange={(e) => onChangeFramework(e.target.value)}
            disabled={session.status === "DESIGNING"}
          >
            <option value="vanilla">HTML / CSS / JS (Vanilla)</option>
            <option value="react">React (Vite App)</option>
            <option value="vue">Vue 3 (SFC Layout)</option>
          </select>
        </div>
      </header>

      {/* 대화 내용 목록 */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="initial-helper">
            <p className="bot-welcome">
              👋 반갑습니다! 만들고 싶으신 웹사이트에 대해 알려주세요.<br />
              (예: "화장품 판매용 핑크 톤 쇼핑몰 만들어줘", "개발자 포트폴리오 다크 모드 사이트 필요해")
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div
              key={index}
              className={`message-bubble ${
                msg.role === "user" ? "user" : "assistant"
              }`}
            >
              <div className="bubble-sender">
                {msg.role === "user" ? "나 (User)" : "기획 에이전트"}
              </div>
              <div className="bubble-content">
                {msg.image_data && msg.mime_type && (
                  <div className="bubble-image-container">
                    <img 
                      src={`data:${msg.mime_type};base64,${msg.image_data}`} 
                      alt="User draft mockup" 
                      className="bubble-image" 
                    />
                  </div>
                )}
                {msg.message}
              </div>
            </div>
          ))
        )}

        {/* 로딩 표시 */}
        {loading && (
          <div className="message-bubble assistant loading">
            <div className="bubble-sender">기획 에이전트</div>
            <div className="bubble-content">
              <span className="dot-flashing"></span>
              <span className="loading-text">요구사항 분석 및 기획 진행 중...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 이미지 미리보기 */}
      {selectedImage && (
        <div className="selected-image-preview">
          <img src={`data:${selectedImage.type};base64,${selectedImage.base64}`} alt="preview" />
          <button type="button" onClick={handleRemoveImage} className="remove-preview-btn">✕</button>
        </div>
      )}

      {/* 메시지 입력 영역 */}
      <form className="chat-input-area" onSubmit={handleSubmit}>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleImageChange}
          accept="image/*"
          style={{ display: "none" }}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="attach-btn"
          disabled={loading || session.status === "DESIGNING"}
          title="초안 이미지 추가"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        </button>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            loading
              ? "답변 대기 중..."
              : "만들고 싶은 홈페이지 설명 또는 초안 이미지 업로드..."
          }
          disabled={loading || session.status === "DESIGNING"}
        />
        <button
          type="submit"
          className="send-btn"
          disabled={(!input.trim() && !selectedImage) || loading || session.status === "DESIGNING"}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </div>
  );
}
