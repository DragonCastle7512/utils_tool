import { useState } from "react";

// 웹사이트 프리뷰 및 코드 조회 패널 컴포넌트
export default function PreviewPanel({ design, loading, progressMessage }) {
  const [activeTab, setActiveTab] = useState("preview"); // "preview" | "code"
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);

  return (
    <div className="preview-panel">
      {/* 프리뷰 상단 헤더 탭 메뉴 */}
      <header className="preview-header">
        <div className="tabs">
          <button
            className={`tab-btn ${activeTab === "preview" ? "active" : ""}`}
            onClick={() => setActiveTab("preview")}
          >
            <svg
              className="tab-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            <span>실시간 프리뷰 (Preview)</span>
          </button>
          <button
            className={`tab-btn ${activeTab === "code" ? "active" : ""}`}
            onClick={() => setActiveTab("code")}
            disabled={!design}
          >
            <svg
              className="tab-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
            <span>생성된 소스코드 (Code)</span>
          </button>
        </div>

        {design && (
          <div className="version-info">
            <span>버전: v{design.version}</span>
            <span className="design-framework-badge">{design.framework.toUpperCase()}</span>
          </div>
        )}
      </header>

      {/* 탭 본문 영역 */}
      <div className="preview-body">
        {loading ? (
          <div className="preview-loading">
            <div className="spinner"></div>
            <p>{progressMessage || "디자인 에이전트가 코드를 완성하고 있습니다..."}</p>
          </div>
        ) : !design ? (
          // 디자인 코드가 없을 때의 빈 페이지 뷰
          <div className="preview-empty">
            <svg
              className="empty-logo"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1"
            >
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
            <h3>화면 미리보기 영역</h3>
            <p>메인 에이전트와 대화를 마치면 디자인 에이전트가 코드를 구성하여 여기에 화면을 표시합니다.</p>
          </div>
        ) : activeTab === "preview" ? (
          // 실시간 렌더링 뷰 (iframe 활용)
          <div className="iframe-wrapper">
            <iframe
              title="live-website-preview"
              srcDoc={design.preview_html}
              sandbox="allow-scripts"
            />
          </div>
        ) : (
          // 가상 소스코드 파일 뷰어
          <div className="code-viewer">
            {/* 코드 파일 트리 목록 */}
            <div className="file-tree">
              <h4>파일 구조</h4>
              <ul>
                {design.files.map((file, idx) => (
                  <li
                    key={idx}
                    className={`file-item ${idx === selectedFileIndex ? "active" : ""}`}
                    onClick={() => setSelectedFileIndex(idx)}
                  >
                    <svg
                      className="file-icon"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                      <polyline points="13 2 13 9 20 9" />
                    </svg>
                    <span>{file.path}</span>
                  </li>
                ))}
              </ul>
            </div>
            {/* 선택한 파일의 소스 코드 렌더러 */}
            <div className="code-viewport">
              <div className="code-header">{design.files[selectedFileIndex]?.path}</div>
              <pre className="code-content">
                <code>{design.files[selectedFileIndex]?.content}</code>
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
