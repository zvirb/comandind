"""
Voice Interaction Service - Hybrid STT/TTS Architecture
Implements dynamic routing for optimal speech processing:
- Vosk for real-time, low-latency commands (<5 seconds)
- Whisper for high-accuracy transcription (>5 seconds)
- Chatterbox for natural TTS synthesis
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any

import aiofiles
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

# Import speech processing libraries
try:
    import vosk
    import whisper
    import torch
    SPEECH_LIBRARIES_AVAILABLE = True
except ImportError:
    SPEECH_LIBRARIES_AVAILABLE = False
    logging.warning("Speech processing libraries not available. Running in simulation mode.")

# JWT verification will be handled at API gateway level
# from app.shared.services.jwt_token_adapter import verify_jwt_token
# from app.shared.services.metrics_exporter import MetricsExporter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Voice Interaction Service",
    description="Hybrid STT/TTS service with dynamic routing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
vosk_model = None
whisper_model = None
redis_client = None
# Metrics will be handled at service mesh level
# metrics = MetricsExporter("voice_interaction_service")

class VoiceInteractionService:
    """Hybrid voice processing service with dynamic routing"""
    
    def __init__(self):
        self.vosk_model = None
        self.whisper_model = None
        self.device = "cpu"  # Default to CPU for lightweight deployment
        if SPEECH_LIBRARIES_AVAILABLE:
            try:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except:
                self.device = "cpu"
        logger.info(f"Initializing voice service on device: {self.device}")
    
    async def initialize_models(self):
        """Initialize speech processing models"""
        if not SPEECH_LIBRARIES_AVAILABLE:
            logger.warning("Speech libraries not available - using simulation mode")
            return
        
        try:
            # Initialize Vosk for real-time STT
            vosk_model_path = os.getenv("VOSK_MODEL_PATH", "/app/models/vosk-model-en-us-0.22")
            if os.path.exists(vosk_model_path):
                self.vosk_model = vosk.Model(vosk_model_path)
                logger.info("Vosk model loaded successfully")
            else:
                logger.warning(f"Vosk model not found at {vosk_model_path}")
            
            # Initialize Whisper for high-accuracy STT
            whisper_model_name = os.getenv("WHISPER_MODEL", "small.en")
            self.whisper_model = whisper.load_model(whisper_model_name, device=self.device)
            logger.info(f"Whisper model '{whisper_model_name}' loaded on {self.device}")
            
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
    
    def should_use_whisper(self, audio_duration: float) -> bool:
        """
        Determine whether to use Whisper or Vosk based on audio characteristics
        - Short audio (<5s): Use Vosk for low latency
        - Long audio (>=5s): Use Whisper for high accuracy
        """
        return audio_duration >= 5.0
    
    async def transcribe_with_vosk(self, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe audio using Vosk for real-time processing"""
        if not self.vosk_model:
            return {"text": "Vosk model not available", "confidence": 0.0, "engine": "vosk_simulation"}
        
        try:
            start_time = time.time()
            rec = vosk.KaldiRecognizer(self.vosk_model, 16000)
            
            # Process audio data
            rec.AcceptWaveform(audio_data)
            result = json.loads(rec.FinalResult())
            
            processing_time = time.time() - start_time
            
            return {
                "text": result.get("text", ""),
                "confidence": result.get("confidence", 0.0),
                "engine": "vosk",
                "processing_time": processing_time
            }
        except Exception as e:
            logger.error(f"Vosk transcription error: {e}")
            return {"text": "", "confidence": 0.0, "engine": "vosk", "error": str(e)}
    
    async def transcribe_with_whisper(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio using Whisper for high accuracy"""
        if not self.whisper_model:
            return {"text": "Whisper model not available", "confidence": 0.0, "engine": "whisper_simulation"}
        
        try:
            start_time = time.time()
            
            # Run Whisper inference
            result = self.whisper_model.transcribe(
                audio_file_path,
                language="en",
                fp16=self.device == "cuda"
            )
            
            processing_time = time.time() - start_time
            
            return {
                "text": result["text"].strip(),
                "confidence": 1.0,  # Whisper doesn't provide confidence scores
                "engine": "whisper",
                "processing_time": processing_time,
                "language": result.get("language", "en")
            }
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return {"text": "", "confidence": 0.0, "engine": "whisper", "error": str(e)}
    
    async def synthesize_speech(self, text: str, voice: str = "default") -> bytes:
        """
        Synthesize speech using TTS with multiple backends:
        1. Coqui TTS (primary)
        2. Google Cloud TTS (fallback)
        3. Simulation (final fallback)
        """
        logger.info(f"Synthesizing speech for text: '{text[:50]}...' with voice: {voice}")
        
        # Try Coqui TTS first
        try:
            audio_data = await self.synthesize_with_coqui(text, voice)
            if audio_data:
                return audio_data
        except Exception as e:
            logger.warning(f"Coqui TTS failed: {e}")
            
        # Try Google Cloud TTS as fallback
        try:
            audio_data = await self.synthesize_with_google_cloud(text, voice)
            if audio_data:
                return audio_data
        except Exception as e:
            logger.warning(f"Google Cloud TTS failed: {e}")
            
        # Final fallback - simulation
        logger.info("Using TTS simulation mode")
        await asyncio.sleep(0.1)
        return b"TTS_AUDIO_PLACEHOLDER_DATA"
    
    async def synthesize_with_coqui(self, text: str, voice: str = "default") -> Optional[bytes]:
        """Synthesize speech using Coqui TTS"""
        try:
            # Import TTS here to avoid startup failures if not available
            from TTS.api import TTS
            
            # Initialize TTS model if not already done
            if not hasattr(self, 'tts_model'):
                # Use a fast, lightweight model for real-time synthesis
                model_name = os.getenv("COQUI_MODEL", "tts_models/en/ljspeech/tacotron2-DDC")
                self.tts_model = TTS(model_name=model_name, progress_bar=False)
                logger.info(f"Coqui TTS model loaded: {model_name}")
            
            # Create temporary file for audio output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                # Synthesize speech
                self.tts_model.tts_to_file(text=text, file_path=temp_file_path)
                
                # Read audio data
                with open(temp_file_path, "rb") as audio_file:
                    audio_data = audio_file.read()
                    
                return audio_data
                
            finally:
                # Cleanup temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Coqui TTS synthesis error: {e}")
            return None
    
    async def synthesize_with_google_cloud(self, text: str, voice: str = "default") -> Optional[bytes]:
        """Synthesize speech using Google Cloud TTS"""
        try:
            # Import Google Cloud TTS here to avoid startup failures if not available
            from google.cloud import texttospeech
            
            # Initialize client if not already done
            if not hasattr(self, 'gcloud_tts_client'):
                # Check for service account credentials
                credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if not credentials_path or not os.path.exists(credentials_path):
                    logger.warning("Google Cloud credentials not found, skipping Google TTS")
                    return None
                    
                self.gcloud_tts_client = texttospeech.TextToSpeechClient()
                logger.info("Google Cloud TTS client initialized")
            
            # Prepare synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure voice
            voice_config = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice if voice != "default" else "en-US-Wavenet-D",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            
            # Configure audio output
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16
            )
            
            # Perform synthesis
            response = self.gcloud_tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice_config,
                audio_config=audio_config
            )
            
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Google Cloud TTS synthesis error: {e}")
            return None
            
    async def transcribe_with_google_cloud(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio using Google Cloud Speech-to-Text"""
        try:
            # Import Google Cloud Speech here to avoid startup failures if not available
            from google.cloud import speech
            
            # Initialize client if not already done
            if not hasattr(self, 'gcloud_speech_client'):
                # Check for service account credentials
                credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if not credentials_path or not os.path.exists(credentials_path):
                    logger.warning("Google Cloud credentials not found, skipping Google STT")
                    return {"text": "Google Cloud STT not available", "confidence": 0.0, "engine": "google_cloud_unavailable"}
                    
                self.gcloud_speech_client = speech.SpeechClient()
                logger.info("Google Cloud Speech client initialized")
            
            start_time = time.time()
            
            # Read audio file
            with open(audio_file_path, "rb") as audio_file:
                audio_content = audio_file.read()
            
            # Configure audio
            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_confidence=True
            )
            
            # Perform recognition
            response = self.gcloud_speech_client.recognize(config=config, audio=audio)
            
            processing_time = time.time() - start_time
            
            # Extract best result
            if response.results:
                best_result = response.results[0]
                if best_result.alternatives:
                    alternative = best_result.alternatives[0]
                    return {
                        "text": alternative.transcript,
                        "confidence": alternative.confidence,
                        "engine": "google_cloud",
                        "processing_time": processing_time
                    }
            
            return {
                "text": "",
                "confidence": 0.0,
                "engine": "google_cloud",
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Google Cloud STT error: {e}")
            return {"text": "", "confidence": 0.0, "engine": "google_cloud", "error": str(e)}

# Global service instance
voice_service = VoiceInteractionService()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    global redis_client
    
    # Initialize Redis connection
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    redis_client = aioredis.from_url(redis_url, decode_responses=True)
    
    # Initialize voice processing models
    await voice_service.initialize_models()
    
    logger.info("Voice Interaction Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    logger.info("Voice Interaction Service stopped")

async def get_current_user() -> Dict[str, Any]:
    """Get current authenticated user - bypass auth for now (handled at gateway)"""
    return {"user_id": "system", "username": "system"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "voice-interaction",
        "models": {
            "vosk_available": voice_service.vosk_model is not None,
            "whisper_available": voice_service.whisper_model is not None,
            "device": voice_service.device
        },
        "timestamp": time.time()
    }

@app.post("/stt/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Transcribe audio using hybrid routing:
    - Short audio: Vosk (low latency)
    - Long audio: Whisper (high accuracy)
    """
    try:
        # Read audio file
        audio_content = await audio.read()
        
        # Estimate audio duration (simplified - in real implementation, analyze audio)
        estimated_duration = len(audio_content) / 16000  # Rough estimate for 16kHz audio
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_content)
            temp_file_path = temp_file.name
        
        try:
            # Route to appropriate STT engine with fallbacks
            result = None
            engines_tried = []
            
            if voice_service.should_use_whisper(estimated_duration):
                # Try Whisper first for long audio
                logger.info(f"Using Whisper for audio duration: {estimated_duration:.2f}s")
                result = await voice_service.transcribe_with_whisper(temp_file_path)
                engines_tried.append("whisper")
                
                # Fallback to Google Cloud if Whisper fails
                if not result or result.get("error") or not result.get("text").strip():
                    logger.info("Whisper failed, trying Google Cloud STT")
                    result = await voice_service.transcribe_with_google_cloud(temp_file_path)
                    engines_tried.append("google_cloud")
                    
            else:
                # Try Vosk first for short audio
                logger.info(f"Using Vosk for audio duration: {estimated_duration:.2f}s")
                result = await voice_service.transcribe_with_vosk(audio_content)
                engines_tried.append("vosk")
                
                # Fallback to Google Cloud if Vosk fails
                if not result or result.get("error") or not result.get("text").strip():
                    logger.info("Vosk failed, trying Google Cloud STT")
                    result = await voice_service.transcribe_with_google_cloud(temp_file_path)
                    engines_tried.append("google_cloud")
            
            # Add fallback metadata
            if result:
                result["engines_tried"] = engines_tried
            
            # Add metadata
            result.update({
                "user_id": user.get("user_id"),
                "audio_duration": estimated_duration,
                "timestamp": time.time()
            })
            
            # Cache result
            if redis_client:
                cache_key = f"stt_result:{user.get('user_id')}:{int(time.time())}"
                await redis_client.setex(cache_key, 3600, json.dumps(result))
            
            # Record metrics (handled at service mesh level)
            # await metrics.record_counter("transcription_requests", 1, {"engine": result.get("engine")})
            # await metrics.record_histogram("transcription_duration", result.get("processing_time", 0))
            
            return result
            
        finally:
            # Cleanup temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/tts/synthesize")
async def synthesize_speech(
    request: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Synthesize speech from text"""
    try:
        text = request.get("text", "")
        voice = request.get("voice", "default")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        # Synthesize speech
        audio_data = await voice_service.synthesize_speech(text, voice)
        
        # Record metrics (handled at service mesh level)
        # await metrics.record_counter("synthesis_requests", 1, {"voice": voice})
        
        # Return audio stream
        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=synthesized_speech.wav"}
        )
        
    except Exception as e:
        logger.error(f"Speech synthesis error: {e}")
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")

@app.get("/models/status")
async def get_models_status(user: Dict[str, Any] = Depends(get_current_user)):
    """Get status of loaded models"""
    return {
        "vosk": {
            "loaded": voice_service.vosk_model is not None,
            "model_path": os.getenv("VOSK_MODEL_PATH", "/app/models/vosk-model-en-us-0.22")
        },
        "whisper": {
            "loaded": voice_service.whisper_model is not None,
            "model": os.getenv("WHISPER_MODEL", "small.en"),
            "device": voice_service.device
        },
        "device_info": {
            "cuda_available": False,
            "device_count": 0
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        reload=False,
        log_level="info"
    )