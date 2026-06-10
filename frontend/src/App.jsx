import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";
import PreviewPanel from "./components/PreviewPanel";
import "./App.css";

const API_BASE = "http://localhost:8000";

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [activeDesign, setActiveDesign] = useState(null);
  const [framework, setFramework] = useState("vanilla");
  
  const [loading, setLoading] = useState(false);
  const [sidebarLoading, setSidebarLoading] = useState(false);

  // 현재 활성화된 세션의 상세 메타데이터 찾기
  const activeSession = sessions.find((s) => s.session_id === activeSessionId);

  // 컴포넌트 마운트 시 세션 목록 조회
  useEffect(() => {
    fetchSessions();
  }, []);

  // 활성화된 세션이 변경될 때마다 채팅 및 디자인 내역을 조회
  useEffect(() => {
    if (activeSessionId) {
      fetchSessionDetails(activeSessionId);
    } else {
      setMessages([]);
      setActiveDesign(null);
    }
  }, [activeSessionId]);

  // 세션 목록 API 호출
  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
        // 만약 선택된 세션이 없고 세션 목록이 존재한다면 첫 번째 세션을 자동으로 선택
        if (data.length > 0 && !activeSessionId) {
          setActiveSessionId(data[0].session_id);
        }
      }
    } catch (err) {
      console.error("세션 목록을 불러오는 중 오류가 발생했습니다:", err);
    }
  };

  // 특정 세션의 대화 내역 및 소스코드 조회
  const fetchSessionDetails = async (sessionId) => {
    try {
      // 1. 대화 내역 조회
      const historyRes = await fetch(`${API_BASE}/api/sessions/${sessionId}/history`);
      if (historyRes.ok) {
        const historyData = await historyRes.json();
        setMessages(historyData);
      }

      // 2. 생성된 소스코드 내역 조회
      const designsRes = await fetch(`${API_BASE}/api/sessions/${sessionId}/designs`);
      if (designsRes.ok) {
        const designsData = await designsRes.json();
        if (designsData.length > 0) {
          // 가장 마지막 버전의 디자인 정보를 활성화
          const latestDesign = designsData[designsData.length - 1];
          setActiveDesign(latestDesign);
          setFramework(latestDesign.framework);
        } else {
          setActiveDesign(null);
        }
      }
    } catch (err) {
      console.error("세션 정보를 불러오는 중 오류가 발생했습니다:", err);
    }
  };

  // 신규 세션 기획 생성 요청
  const handleCreateSession = async () => {
    const title = prompt("새로운 기획 주제를 입력하세요:", "새 웹사이트 기획");
    if (!title || !title.trim()) return;

    setSidebarLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim() })
      });
      if (res.ok) {
        const newSession = await res.json();
        await fetchSessions();
        setActiveSessionId(newSession.session_id);
      }
    } catch (err) {
      console.error("세션을 생성하는 중 오류가 발생했습니다:", err);
    } finally {
      setSidebarLoading(false);
    }
  };

  // 에이전트와 대화 메시지 송수신
  const handleSendMessage = async (text) => {
    if (!activeSessionId) return;

    // 사용자 화면에 자신의 말풍선 즉시 추가
    const userMessage = { role: "user", message: text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/sessions/${activeSessionId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          framework: framework
        })
      });

      if (res.ok) {
        const data = await res.json();
        
        // 메인 에이전트의 답변 말풍선 추가
        const botMessage = { role: "assistant", message: data.reply };
        setMessages((prev) => [...prev, botMessage]);

        // 에이전트 판단기가 기획 완료를 판정하여 디자인 코드가 생성된 경우
        if (data.is_ready && data.design) {
          setActiveDesign(data.design);
        }
        
        // 세션의 상태(기획중, 생성중, 완료)가 바뀔 수 있으므로 세션 리스트 정보 갱신
        await fetchSessions();
      }
    } catch (err) {
      console.error("메시지를 전송하는 중 오류가 발생했습니다:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", message: "백엔드 서버와 통신할 수 없습니다. 서버 구동 상태를 확인해 주세요." }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* 좌측 사이드바 패널 */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={setActiveSessionId}
        onCreateSession={handleCreateSession}
        loading={sidebarLoading}
      />

      {/* 중앙/우측 콘텐츠 스플릿 레이아웃 */}
      <main className="main-content">
        {/* 중앙: 대화 기획 채팅창 */}
        <ChatPanel
          session={activeSession}
          messages={messages}
          onSendMessage={handleSendMessage}
          loading={loading}
          framework={framework}
          onChangeFramework={setFramework}
        />

        {/* 우측: 실시간 웹 프리뷰 및 소스코드 뷰어 */}
        <PreviewPanel
          design={activeDesign}
          loading={loading && activeSession?.status === "DESIGNING"}
        />
      </main>
    </div>
  );
}
