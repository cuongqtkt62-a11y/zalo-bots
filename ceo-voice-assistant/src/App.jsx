import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [micError, setMicError] = useState(false);
  const isRecordingRef = useRef(false);
  const [logs, setLogs] = useState([]);
  
  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const scriptProcessorRef = useRef(null);
  const nextPlayTimeRef = useRef(0);
  const recordingAudioContextRef = useRef(null);

  const connectWS = () => {
    // Kết nối tới Backend Proxy
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}`;
      
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      addLog('✅ Connected to JARVIS Core');
      // Bắt đầu gửi frame đầu tiên là clientContent (bắt buộc bởi Gemini Live API)
      ws.send(JSON.stringify({
        clientContent: {
          turns: [
            { role: "user", parts: [{ text: "Xin chào JARVIS" }] }
          ],
          turnComplete: true
        }
      }));
    };

    ws.onmessage = async (event) => {
      if (typeof event.data === 'string') {
        const msg = JSON.parse(event.data);
        handleServerMessage(msg);
      } else if (event.data instanceof Blob) {
        // Có thể server trả về nhị phân trực tiếp
        const arrayBuffer = await event.data.arrayBuffer();
        playAudioBuffer(arrayBuffer);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsRecording(false);
      addLog('❌ Disconnected from JARVIS Core');
    };
  };

  const handleServerMessage = (msg) => {
    if (msg.serverContent?.modelTurn?.parts) {
      const parts = msg.serverContent.modelTurn.parts;
      for (const part of parts) {
        if (part.inlineData && part.inlineData.data) {
          // Xử lý Audio (base64)
          const base64Audio = part.inlineData.data;
          const binaryString = atob(base64Audio);
          const len = binaryString.length;
          const bytes = new Uint8Array(len);
          for (let i = 0; i < len; i++) {
              bytes[i] = binaryString.charCodeAt(i);
          }
          playAudioBuffer(bytes.buffer);
        }
      }
    }

    if (msg.toolCall) {
      handleToolCall(msg.toolCall);
    }
  };

  const playAudioBuffer = async (arrayBuffer) => {
    if (!audioContextRef.current) return;
    
    // Gemini trả về Raw PCM 16-bit 24kHz. Cần decode.
    // Để đơn giản, Web Audio API decodeAudioData cần header WAV, nhưng Gemini trả Raw PCM.
    // Khởi tạo bộ chuyển đổi PCM sang AudioBuffer
    const audioContext = audioContextRef.current;
    
    const int16Array = new Int16Array(arrayBuffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    const audioBuffer = audioContext.createBuffer(1, float32Array.length, 24000);
    audioBuffer.getChannelData(0).set(float32Array);

    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    
    // Xếp hàng phát âm thanh để không bị đè lên nhau (Audio Queue)
    if (nextPlayTimeRef.current < audioContext.currentTime) {
      nextPlayTimeRef.current = audioContext.currentTime;
    }
    source.start(nextPlayTimeRef.current);
    nextPlayTimeRef.current += audioBuffer.duration;
  };

  const handleToolCall = async (toolCall) => {
    addLog(`🛠️ AI Action: ${toolCall.functionCalls[0].name}`);
    const call = toolCall.functionCalls[0];
    let responseObj = {};

    if (call.name === 'open_google_maps') {
      const address = call.args.address;
      addLog(`🗺️ Opening Maps for: ${address}`);
      const encodedAddress = encodeURIComponent(address);
      const url = `https://www.google.com/maps/dir/?api=1&destination=${encodedAddress}`;
      
      // Simulate click to bypass some popup blockers
      const link = document.createElement('a');
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      responseObj = { status: "Success", action: "Google Maps Opened" };
    } 
    else if (call.name === 'get_assistants_report') {
      addLog('📊 Fetching reports from backend...');
      try {
        const res = await fetch('/api/reports');
        const data = await res.json();
        responseObj = data;
      } catch (err) {
        responseObj = { error: err.message };
      }
    }

    // Gửi Tool Response về Gemini
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        toolResponse: {
          functionResponses: [
            {
              id: call.id,
              name: call.name,
              response: responseObj
            }
          ]
        }
      }));
    }
  };

  const initAudioPlayback = () => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    }
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
  };

  const handleInitialize = async () => {
    try {
      // 1. Dùng onClick chuẩn để vượt qua kiểm duyệt chặn popup/mic của Safari
      initAudioPlayback();
      if (!recordingAudioContextRef.current) {
        recordingAudioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      }
      if (recordingAudioContextRef.current.state === 'suspended') {
        recordingAudioContextRef.current.resume();
      }
      
      // 2. Xin quyền Micro 1 lần duy nhất để Safari hiện bảng hỏi "Cho phép"
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Tắt stream ngay vì chỉ cần xin quyền
      stream.getTracks().forEach(track => track.stop());
      
      setIsInitialized(true);
      addLog('✅ Khởi tạo thành công, đã có quyền Micro!');
    } catch (err) {
      setMicError(true);
      addLog('❌ Microphone access denied during init');
      console.error(err);
    }
  };

  const startRecording = async () => {
    if (isRecordingRef.current) return;
    isRecordingRef.current = true;
    
    initAudioPlayback(); // Unlock audio playback context during user gesture (iOS Safari requirement)
    
    // MUST create recording context synchronously during user gesture to bypass iOS suspension!
    if (!recordingAudioContextRef.current) {
      recordingAudioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    }
    if (recordingAudioContextRef.current.state === 'suspended') {
      recordingAudioContextRef.current.resume();
    }
    
    if (!isConnected) {
      connectWS();
      // Đợi tối đa 3 giây cho WebSocket mở thay vì fix cứng 1 giây
      for (let i = 0; i < 30; i++) {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) break;
        await new Promise(r => setTimeout(r, 100));
      }
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const source = recordingAudioContextRef.current.createMediaStreamSource(stream);
      
      const processor = recordingAudioContextRef.current.createScriptProcessor(4096, 1, 1);
      scriptProcessorRef.current = processor;

      source.connect(processor);
      processor.connect(recordingAudioContextRef.current.destination);

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Chuyển Float32 sang Int16
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          let s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        // Chuyển Int16Array thành Base64
        const uint8Array = new Uint8Array(pcm16.buffer);
        let binary = '';
        for (let i = 0; i < uint8Array.byteLength; i++) {
            binary += String.fromCharCode(uint8Array[i]);
        }
        const base64Audio = btoa(binary);

        // Gửi qua WS
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            realtimeInput: {
              mediaChunks: [{
                mimeType: "audio/pcm;rate=16000",
                data: base64Audio
              }]
            }
          }));
        }
      };

      setIsRecording(true);
      addLog('🎙️ Recording started...');
    } catch (err) {
      isRecordingRef.current = false;
      setMicError(true);
      addLog('❌ Microphone access denied');
      console.error(err);
    }
  };

  const stopRecording = () => {
    if (!isRecordingRef.current) return;
    isRecordingRef.current = false;
    
    setIsRecording(false);
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (recordingAudioContextRef.current) {
      recordingAudioContextRef.current.close();
      recordingAudioContextRef.current = null;
    }
    addLog('⏹️ Recording stopped');

    // Force Gemini to respond immediately since user released the button
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        clientContent: {
          turns: [],
          turnComplete: true
        }
      }));
    }
  };

  const addLog = (msg) => {
    setLogs(prev => [...prev, msg].slice(-5));
  };

  return (
    <div className="App dark-mode">
      {micError && (
        <div className="mic-error-overlay">
          <h2>⚠️ LỖI MICROPHONE</h2>
          <p>Trình duyệt đang <b>CHẶN</b> quyền ghi âm của bạn!</p>
          <div style={{ textAlign: 'left', padding: '10px 20px' }}>
            <p>👉 <b>Nếu đang dùng Zalo/FB:</b> Bấm dấu 3 chấm (⋮) góc phải, chọn "Mở bằng trình duyệt".</p>
            <p>👉 <b>Nếu đang dùng iPhone (Safari):</b> Bạn đã lỡ bấm "Từ chối" trước đó. Hãy vào <b>Cài đặt &gt; Safari &gt; Micrô</b> và chọn <b>Cho phép</b> hoặc <b>Hỏi</b>, sau đó tải lại trang.</p>
            <p>👉 <b>Nếu đang dùng Android (Chrome):</b> Bấm vào biểu tượng ổ khóa cạnh thanh địa chỉ web, chọn Quyền (Permissions) và Bật Micro.</p>
          </div>
          <button className="btn-close-error" onClick={() => setMicError(false)}>Đã hiểu</button>
        </div>
      )}

      <h1>OPC CEO Assistant</h1>
      
      <div className="voice-container">
        <div className={`orb ${isRecording ? 'pulsing' : ''} ${isConnected ? 'active' : ''}`}></div>
        
        {!isInitialized ? (
          <button 
            className="btn-mic"
            onClick={handleInitialize}
          >
            BẤM ĐỂ BẮT ĐẦU
          </button>
        ) : (
          <button 
            className="btn-mic"
            onPointerDown={(e) => { e.preventDefault(); startRecording(); }}
            onPointerUp={(e) => { e.preventDefault(); stopRecording(); }}
            onPointerCancel={(e) => { e.preventDefault(); stopRecording(); }}
            onPointerOut={(e) => { e.preventDefault(); stopRecording(); }}
          >
            {isRecording ? "ĐANG LẮNG NGHE..." : "GIỮ ĐỂ NÓI"}
          </button>
        )}
      </div>

      <div className="logs">
        {logs.map((l, idx) => <p key={idx}>{l}</p>)}
      </div>
    </div>
  );
}

export default App;
