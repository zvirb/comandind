import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Volume2, VolumeX, Play, Pause, Square, AlertCircle, Loader, Waves } from 'lucide-react';
import { SecureAuth } from '../utils/secureAuth';
import { useAuth } from '../context/AuthContext';

/**
 * VoiceInteraction Component
 * Provides voice recording, transcription, and text-to-speech capabilities
 * Integrates with the voice interaction service on port 8006
 */
const VoiceInteraction = ({ onTranscription, className = "" }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [transcription, setTranscription] = useState('');
  const [error, setError] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [serviceStatus, setServiceStatus] = useState('unknown');
  
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const audioStreamRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const audioLevelTimerRef = useRef(null);
  const audioPlayerRef = useRef(null);
  
  const { isAuthenticated } = useAuth();

  // Check voice service status on mount
  useEffect(() => {
    checkVoiceServiceStatus();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (audioLevelTimerRef.current) {
        clearInterval(audioLevelTimerRef.current);
      }
    };
  }, []);

  const checkVoiceServiceStatus = async () => {
    try {
      const response = await SecureAuth.makeSecureRequest('/api/v1/voice/health');
      if (response.ok) {
        const data = await response.json();
        setServiceStatus(data.status === 'healthy' ? 'online' : 'degraded');
      } else {
        setServiceStatus('offline');
      }
    } catch (error) {
      console.error('Voice service health check failed:', error);
      setServiceStatus('offline');
    }
  };

  const startRecording = async () => {
    if (!isAuthenticated) {
      setError('Please log in to use voice features');
      return;
    }

    if (serviceStatus === 'offline') {
      setError('Voice service is currently offline');
      return;
    }

    try {
      setError(null);
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });
      
      audioStreamRef.current = stream;

      // Set up audio context for visualization
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      
      analyserRef.current.fftSize = 256;
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      // Start audio level monitoring
      audioLevelTimerRef.current = setInterval(() => {
        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((sum, value) => sum + value, 0) / bufferLength;
        setAudioLevel(average / 255); // Normalize to 0-1
      }, 100);

      // Set up media recorder
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
          ? 'audio/webm;codecs=opus' 
          : 'audio/webm'
      });

      const audioChunks = [];
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        setAudioBlob(audioBlob);
        
        // Stop audio stream
        if (audioStreamRef.current) {
          audioStreamRef.current.getTracks().forEach(track => track.stop());
          audioStreamRef.current = null;
        }
        
        // Clean up audio level monitoring
        if (audioLevelTimerRef.current) {
          clearInterval(audioLevelTimerRef.current);
          audioLevelTimerRef.current = null;
        }
        setAudioLevel(0);
      };

      // Start recording
      mediaRecorderRef.current.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      // Start timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (error) {
      console.error('Error starting recording:', error);
      setError('Failed to access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
    }
  };

  const transcribeAudio = async () => {
    if (!audioBlob) {
      setError('No audio to transcribe');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const response = await SecureAuth.makeSecureRequest('/api/v1/voice/stt/transcribe', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Transcription failed');
      }

      const result = await response.json();
      
      if (result.text) {
        setTranscription(result.text);
        if (onTranscription) {
          onTranscription(result.text, result);
        }
      } else {
        setError('No speech detected in recording');
      }

    } catch (error) {
      console.error('Transcription error:', error);
      setError(`Transcription failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const synthesizeSpeech = async (text) => {
    if (!text.trim()) {
      setError('No text to synthesize');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const response = await SecureAuth.makeSecureRequest('/api/v1/voice/tts/synthesize', {
        method: 'POST',
        body: JSON.stringify({
          text: text,
          voice: 'default'
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Speech synthesis failed');
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = audioUrl;
        audioPlayerRef.current.play();
        setIsPlaying(true);
      }

    } catch (error) {
      console.error('Speech synthesis error:', error);
      setError(`Speech synthesis failed: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const playRecording = () => {
    if (audioBlob) {
      const audioUrl = URL.createObjectURL(audioBlob);
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = audioUrl;
        audioPlayerRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getServiceStatusColor = () => {
    switch (serviceStatus) {
      case 'online': return 'bg-green-400';
      case 'degraded': return 'bg-yellow-400';
      case 'offline': return 'bg-red-400';
      default: return 'bg-gray-400';
    }
  };

  return (
    <div className={`voice-interaction bg-gray-900/50 backdrop-blur-lg border border-gray-800 rounded-lg p-4 ${className}`}>
      {/* Service Status Indicator */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Voice Interaction</h3>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${getServiceStatusColor()}`}></div>
          <span className="text-xs text-gray-400 capitalize">{serviceStatus}</span>
        </div>
      </div>

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-4 p-3 bg-red-900/20 border border-red-800 rounded-lg flex items-center space-x-2"
          >
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-400">{error}</p>
            <button 
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-300"
            >
              ×
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Recording Controls */}
      <div className="space-y-4">
        
        {/* Main Recording Button */}
        <div className="flex items-center justify-center">
          <motion.button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isProcessing || serviceStatus === 'offline'}
            className={`relative p-4 rounded-full transition-all duration-300 ${
              isRecording 
                ? 'bg-red-500 hover:bg-red-600 scale-110' 
                : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            whileTap={{ scale: 0.95 }}
          >
            {isRecording ? (
              <Square className="w-6 h-6 text-white" />
            ) : (
              <Mic className="w-6 h-6 text-white" />
            )}
            
            {/* Audio Level Visualization */}
            {isRecording && (
              <motion.div
                className="absolute inset-0 rounded-full border-2 border-white/30"
                animate={{ 
                  scale: [1, 1 + (audioLevel * 0.5), 1],
                  opacity: [0.3, 0.6, 0.3]
                }}
                transition={{ duration: 0.5, repeat: Infinity }}
              />
            )}
          </motion.button>
        </div>

        {/* Recording Status */}
        {isRecording && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center"
          >
            <div className="flex items-center justify-center space-x-2 text-red-400">
              <Waves className="w-4 h-4 animate-pulse" />
              <span className="text-sm font-medium">Recording: {formatTime(recordingTime)}</span>
            </div>
            <div className="mt-2 w-full bg-gray-800 rounded-full h-2">
              <div 
                className="bg-red-500 h-2 rounded-full transition-all duration-100"
                style={{ width: `${Math.min(audioLevel * 100, 100)}%` }}
              />
            </div>
          </motion.div>
        )}

        {/* Audio Playback and Actions */}
        {audioBlob && !isRecording && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-3"
          >
            <div className="flex items-center justify-center space-x-3">
              <button
                onClick={playRecording}
                disabled={isProcessing}
                className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition disabled:opacity-50"
              >
                <Play className="w-4 h-4 text-white" />
              </button>
              
              <button
                onClick={transcribeAudio}
                disabled={isProcessing}
                className="px-4 py-2 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 rounded-lg text-sm font-medium transition disabled:opacity-50 flex items-center space-x-2"
              >
                {isProcessing ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <span>Transcribe</span>
                )}
              </button>
            </div>

            {/* Transcription Result */}
            {transcription && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="p-3 bg-gray-800/50 border border-gray-700 rounded-lg"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm text-gray-300 mb-2">Transcription:</p>
                    <p className="text-white">{transcription}</p>
                  </div>
                  <button
                    onClick={() => synthesizeSpeech(transcription)}
                    disabled={isProcessing}
                    className="ml-3 p-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition disabled:opacity-50"
                    title="Read aloud"
                  >
                    <Volume2 className="w-4 h-4 text-white" />
                  </button>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}
      </div>

      {/* Hidden audio player for TTS */}
      <audio 
        ref={audioPlayerRef}
        onEnded={() => setIsPlaying(false)}
        className="hidden"
      />
    </div>
  );
};

export default VoiceInteraction;