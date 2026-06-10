import React from "react";

// 사이드바 컴포넌트: 유틸리티 서비스 선택 및 대화 세션 목록 관리
export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  loading
}) {
  return (
    <aside className="sidebar">
      {/* 플랫폼 로고 및 헤더 */}
      <div className="sidebar-brand">
        <svg
          className="brand-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
        </svg>
        <span className="brand-name">AI Util Hub</span>
      </div>

      {/* 유틸리티 서비스 선택 메뉴 (왼쪽 사이드바 핵심) */}
      <div className="sidebar-menu-section">
        <h3 className="menu-title">유틸리티 서비스</h3>
        <ul className="menu-list">
          <li className="menu-item active">
            <svg
              className="menu-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
            </svg>
            <span>AI 웹사이트 빌더</span>
          </li>
        </ul>
      </div>

      {/* 세션 히스토리 목록 */}
      <div className="sidebar-history-section">
        <div className="history-header">
          <h3 className="menu-title">기획 히스토리</h3>
          <button
            className="new-btn"
            onClick={onCreateSession}
            disabled={loading}
            title="새로운 기획 생성"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        </div>

        {sessions.length === 0 ? (
          <div className="empty-history">생성된 기획이 없습니다.</div>
        ) : (
          <ul className="history-list">
            {sessions.map((session) => (
              <li
                key={session.session_id}
                className={`history-item ${
                  activeSessionId === session.session_id ? "active" : ""
                }`}
                onClick={() => onSelectSession(session.session_id)}
              >
                <svg
                  className="history-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                <span className="history-title" title={session.title}>
                  {session.title}
                </span>
                <span className={`status-badge ${session.status.toLowerCase()}`}>
                  {session.status === "CLARIFYING"
                    ? "기획중"
                    : session.status === "DESIGNING"
                    ? "생성중"
                    : "완료"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
