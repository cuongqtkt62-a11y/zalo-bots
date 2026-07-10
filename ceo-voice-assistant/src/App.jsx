import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [logs, setLogs] = useState([]);
  
  const wsRef = useRef(null);
  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const scriptProcessorRef = useRef(null);

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
    source.start(0);
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
      window.open(url, '_blank');
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

  const startRecording = async () => {
    initAudioPlayback(); // Unlock audio playback context during user gesture (iOS Safari requirement)
    
    if (!isConnected) {
      connectWS();
      // Đợi 1 chút để connect
      await new Promise(r => setTimeout(r, 1000));
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(stream);
      
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      scriptProcessorRef.current = processor;

      source.connect(processor);
      processor.connect(audioContext.destination);

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
      addLog('❌ Microphone access denied');
      console.error(err);
    }
  };

  const stopRecording = () => {
    setIsRecording(false);
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
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
      <h1>OPC CEO Assistant</h1>
      
      <div className="voice-container">
        <div className={`orb ${isRecording ? 'pulsing' : ''} ${isConnected ? 'active' : ''}`}></div>
        
        <button 
          className="btn-mic"
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
        >
          {isRecording ? "ĐANG LẮNG NGHE..." : "GIỮ ĐỂ NÓI"}
        </button>
      </div>

      <div className="logs">
        {logs.map((l, idx) => <p key={idx}>{l}</p>)}
      </div>
    </div>
  );
}

export default App;
