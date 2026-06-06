"""
utils/audio.py
알람음(notice) 기능을 담당하는 유틸리티 모듈
"""
import streamlit as st
import base64

# 시스템 알림음 Base64로 미리 로드 가능한 사운드 URL 또는 짧은 비프음 바이너리
# 여기서는 안정적이고 무해한 내장 오디오(브라우저가 경고음으로 쓸 수 있는 짧은 base64 beep 또는 무료 사운드)를 정의하거나,
# 브라우저의 Synthesis(말하기) 또는 Web Audio API를 사용하는 JS 코드를 주입하여 알림을 보냅니다.
# Web Audio API를 사용해 Synth Beep 음을 재생하면 별도의 오디오 파일 없이 소리를 낼 수 있습니다.

def play_notice_sound():
    """브라우저에서 직접 신시사이저 비프음(알림음)을 재생합니다."""
    # Web Audio API를 이용한 비프음 생성 자바스크립트
    # 사용자 인터랙션이 발생한 후에만 소리가 납니다.
    beep_js = """
    <script>
    (function() {
        try {
            var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            var oscillator = audioCtx.createOscillator();
            var gainNode = audioCtx.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            
            oscillator.type = 'sine'; // sine, square, sawtooth, triangle
            oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); // 880Hz (A5)
            gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime); // 볼륨 조절
            
            oscillator.start();
            
            // 0.15초 동안 재생 후 멈춤
            gainNode.gain.exponentialRampToValueAtTime(0.00001, audioCtx.currentTime + 0.15);
            oscillator.stop(audioCtx.currentTime + 0.15);
        } catch(e) {
            console.error("오디오 재생 실패:", e);
        }
    })();
    </script>
    """
    st.components.v1.html(beep_js, height=0, width=0)
